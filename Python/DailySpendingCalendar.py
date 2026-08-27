from __future__ import annotations

import argparse
import hashlib
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import gspread
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
TOKENS_DIR = ROOT_DIR / "tokens"

CALENDAR_ID = (
    "d9dfe83301068dfa2d677079e02370cd982d78a487936068bd8ce95cf27e526c"
    "@group.calendar.google.com"
)
SPREADSHEET_ID_ENV = "YUCHO_SHEET"
SHEET_NAMES = ("Visa", "PayPay")
TIME_ZONE = ZoneInfo("Asia/Tokyo")

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"


@dataclass(frozen=True)
class Transaction:
    occurred_at: str
    amount: int
    store: str
    source: str
    payment_type: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="指定日の支出合計と明細を Google カレンダーへ登録します。"
    )
    parser.add_argument(
        "--date",
        dest="target_date",
        help="集計日 (YYYY-MM-DD)。省略時は日本時間の今日です。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="カレンダーへ書き込まず、登録内容だけを表示します。",
    )
    parser.add_argument(
        "--delete-if-empty",
        action="store_true",
        help="対象日の支出が0件なら、以前作成した同日の予定を削除します。",
    )
    return parser.parse_args()


def load_credentials(token_filename: str, scopes: list[str]) -> Credentials:
    """既存プロジェクトと同じ credentials.json を使ってOAuth認証する。"""
    credentials_path = TOKENS_DIR / "credentials.json"
    token_path = TOKENS_DIR / token_filename

    if not credentials_path.exists():
        raise FileNotFoundError(f"OAuth設定が見つかりません: {credentials_path}")

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), scopes
            )
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def spreadsheet_login() -> gspread.Spreadsheet:
    spreadsheet_id = os.getenv(SPREADSHEET_ID_ENV)
    if not spreadsheet_id:
        raise RuntimeError(f"環境変数 {SPREADSHEET_ID_ENV} が設定されていません。")

    # 既存の sheet_token.json は書き込み権限で発行されているため、ここでも再利用できる。
    # 読み取り専用トークンを新規発行したい場合は、ファイル名を変更する。
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = load_credentials("sheet_token.json", scopes)
    return gspread.authorize(creds).open_by_key(spreadsheet_id)


def calendar_login():
    creds = load_credentials("calendar_token.json", [CALENDAR_SCOPE])
    return build("calendar", "v3", credentials=creds)


def parse_date(value: str | None) -> date:
    if value is None:
        return datetime.now(TIME_ZONE).date()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("--date は YYYY-MM-DD 形式で指定してください。") from error


def parse_amount(value: str) -> int:
    normalized = (
        value.replace(",", "")
        .replace("円", "")
        .replace("JPY", "")
        .replace("¥", "")
        .strip()
    )
    if "." in normalized:
        integer_part, decimal_part = normalized.split(".", 1)
        if decimal_part and set(decimal_part) == {"0"}:
            normalized = integer_part
    return int(normalized)


def parse_transaction_date(value: str) -> date | None:
    normalized = value.strip().replace("-", "/")[:10]
    try:
        return datetime.strptime(normalized, "%Y/%m/%d").date()
    except ValueError:
        return None


def load_transactions_for_date(
    spreadsheet: gspread.Spreadsheet, target_date: date
) -> list[Transaction]:
    transactions: list[Transaction] = []

    for sheet_name in SHEET_NAMES:
        worksheet = spreadsheet.worksheet(sheet_name)
        rows = worksheet.get_all_values()
        if not rows:
            continue

        headers = [header.strip() for header in rows[0]]
        required = ["日時", "金額", "店舗", "決済元", "決済種別"]
        missing = [name for name in required if name not in headers]
        if missing:
            raise RuntimeError(
                f"{sheet_name} シートに必要な列がありません: {', '.join(missing)}"
            )

        indexes = {name: headers.index(name) for name in required}
        for row in rows[1:]:
            # 途中に短い行や空行があっても安全に読み飛ばす。
            if len(row) <= max(indexes.values()):
                continue
            occurred_on = parse_transaction_date(row[indexes["日時"]])
            if occurred_on != target_date:
                continue
            try:
                amount = parse_amount(row[indexes["金額"]])
            except ValueError:
                print(
                    f"警告: {sheet_name} の金額を解釈できないため除外: "
                    f"{row[indexes['金額']]}"
                )
                continue

            transactions.append(
                Transaction(
                    occurred_at=row[indexes["日時"]].strip(),
                    amount=amount,
                    store=row[indexes["店舗"]].strip() or "不明",
                    source=row[indexes["決済元"]].strip() or sheet_name,
                    payment_type=row[indexes["決済種別"]].strip() or "不明",
                )
            )

    # 同じ明細が両シートや重複行に存在しても、カレンダーでは1件として扱う。
    unique = {
        (
            item.occurred_at,
            item.amount,
            item.store,
            item.source,
            item.payment_type,
        ): item
        for item in transactions
    }
    return sorted(unique.values(), key=lambda item: item.occurred_at)


def format_description(target_date: date, transactions: list[Transaction]) -> str:
    total = sum(item.amount for item in transactions)
    lines = [
        f"{target_date:%Y/%m/%d} の支出明細",
        f"合計: ¥{total:,}",
        f"件数: {len(transactions)}件",
        "",
    ]

    for item in transactions:
        time_text = item.occurred_at.strip()
        if " " in time_text:
            time_text = time_text.split(" ", 1)[1][:5]
        else:
            time_text = "時刻不明"
        lines.append(
            f"・{time_text}  {item.store}  ¥{item.amount:,}"
            f"（{item.source} / {item.payment_type}）"
        )

    lines.extend(["", "仕訳帳の Visa・PayPay シートから自動集計"])
    description = "\n".join(lines)

    # Calendar APIの説明欄を極端に大きくしない。末尾に省略表示を残す。
    max_length = 7500
    if len(description) > max_length:
        description = description[: max_length - 20].rstrip() + "\n…（明細を一部省略）"
    return description


def stable_event_id(target_date: date) -> str:
    """このスクリプト専用で日付ごとに一意な、Calendar互換のイベントID。"""
    digest = hashlib.sha256(
        f"daily-spending:{CALENDAR_ID}:{target_date.isoformat()}".encode("utf-8")
    ).hexdigest()[:24]
    return f"spending{target_date:%Y%m%d}{digest}"


def find_existing_events(service, target_date: date) -> list[dict]:
    response = (
        service.events()
        .list(
            calendarId=CALENDAR_ID,
            privateExtendedProperty=f"spending_date={target_date.isoformat()}",
            singleEvents=True,
            showDeleted=False,
            maxResults=10,
        )
        .execute()
    )
    return response.get("items", [])


def build_event_body(target_date: date, transactions: list[Transaction]) -> dict:
    total = sum(item.amount for item in transactions)
    return {
        "summary": f"支出 ¥{total:,}（{len(transactions)}件）",
        "description": format_description(target_date, transactions),
        "start": {"date": target_date.isoformat()},
        "end": {"date": (target_date + timedelta(days=1)).isoformat()},
        "transparency": "transparent",
        "extendedProperties": {
            "private": {
                "spending_date": target_date.isoformat(),
                "managed_by": "DailySpendingCalendar.py",
            }
        },
    }


def upsert_calendar_event(service, target_date: date, transactions: list[Transaction]) -> str:
    event_body = build_event_body(target_date, transactions)
    existing_events = find_existing_events(service, target_date)

    if existing_events:
        event_id = existing_events[0]["id"]
        event = (
            service.events()
            .update(calendarId=CALENDAR_ID, eventId=event_id, body=event_body)
            .execute()
        )
        # 過去の不具合などで重複していた場合は、このスクリプト管理分を1件に戻す。
        for duplicate in existing_events[1:]:
            service.events().delete(
                calendarId=CALENDAR_ID, eventId=duplicate["id"]
            ).execute()
        return event.get("htmlLink", "")

    event_body["id"] = stable_event_id(target_date)
    try:
        event = (
            service.events()
            .insert(calendarId=CALENDAR_ID, body=event_body)
            .execute()
        )
    except Exception as error:
        # 固定IDの予定が既にあり、拡張プロパティ検索に出なかった場合だけ更新を試す。
        status = getattr(getattr(error, "resp", None), "status", None)
        if status != 409:
            raise
        event = (
            service.events()
            .update(
                calendarId=CALENDAR_ID,
                eventId=event_body.pop("id"),
                body=event_body,
            )
            .execute()
        )
    return event.get("htmlLink", "")


def delete_existing_event(service, target_date: date) -> int:
    existing_events = find_existing_events(service, target_date)
    for event in existing_events:
        service.events().delete(
            calendarId=CALENDAR_ID, eventId=event["id"]
        ).execute()
    return len(existing_events)


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    load_dotenv(SCRIPT_DIR / ".env")
    args = parse_args()
    target_date = parse_date(args.target_date)

    spreadsheet = spreadsheet_login()
    transactions = load_transactions_for_date(spreadsheet, target_date)
    event_body = build_event_body(target_date, transactions)

    print(event_body["summary"])
    print(event_body["description"])

    if args.dry_run:
        print("\n[dry-run] カレンダーは変更していません。")
        return

    service = calendar_login()
    if not transactions:
        if args.delete_if_empty:
            deleted = delete_existing_event(service, target_date)
            print(f"\n支出が0件のため、既存予定を{deleted}件削除しました。")
        else:
            print("\n支出が0件のため、カレンダーは変更していません。")
        return

    event_url = upsert_calendar_event(service, target_date, transactions)
    print("\nカレンダーへの登録・更新が完了しました。")
    if event_url:
        print(event_url)


if __name__ == "__main__":
    main()
