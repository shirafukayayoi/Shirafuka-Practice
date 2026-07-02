from __future__ import annotations

import argparse
import base64
import csv
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

import gspread
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from gspread.exceptions import WorksheetNotFound


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
TOKENS_DIR = ROOT_DIR / "tokens"
SPREADSHEET_ID_ENV = "YUCHO_SHEET"

VISA_SHEET_NAME = "Visa"
PAYPAY_SHEET_NAME = "PayPay"
CANCEL_SHEET_NAME = "キャンセル"
SUMMARY_SHEET_NAME = "決済"
MONTHLY_SHEET_NAME = "月別"
STORE_SHEET_NAME = "店舗別"
MONTHLY_CHART_SHEET_NAME = "月別グラフ"
STORE_CHART_SHEET_NAME = "店舗別グラフ"
MONTHLY_STORE_SHEET_NAME = "月別店舗"
MONTHLY_STORE_PIVOT_SHEET_NAME = "月別店舗ピボット"

TRANSACTION_HEADERS = ["日時", "金額", "店舗", "決済元", "決済種別"]
CURRENCY_FORMAT = {"numberFormat": {"type": "CURRENCY", "pattern": "¥#,##0"}}
MAIN_STEP_TOTAL = 9
PROGRESS_BAR_WIDTH = 28


@dataclass(frozen=True)
class Transaction:
    occurred_at: str
    amount: int
    store: str
    source: str
    payment_type: str

    def as_row(self) -> list[object]:
        return [
            self.occurred_at,
            self.amount,
            self.store,
            self.source,
            self.payment_type,
        ]

    def key(self) -> tuple[str, int, str, str, str]:
        return (
            self.occurred_at.strip(),
            self.amount,
            _normalize_store(self.store),
            self.source.strip(),
            self.payment_type.strip(),
        )


def _progress_bar(current: int, total: int, width: int = PROGRESS_BAR_WIDTH) -> str:
    if total <= 0:
        filled = 0
        percent = 0
    else:
        filled = min(width, max(0, round(width * current / total)))
        percent = min(100, max(0, round(100 * current / total)))
    return f"[{'#' * filled}{'-' * (width - filled)}] {current}/{total} {percent:3d}%"


def log_step(step: int, message: str) -> None:
    print(f"全体 {_progress_bar(step, MAIN_STEP_TOTAL)}  {message}", flush=True)


def log_info(message: str) -> None:
    print(f"  - {message}", flush=True)


def log_warning(message: str) -> None:
    print(f"  ! {message}", flush=True)


def log_progress(label: str, current: int, total: int) -> None:
    print(f"\r{label} {_progress_bar(current, total)}", end="", flush=True)
    if current >= total:
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ゆうちょ・三井住友・PayPay の決済履歴をスプレッドシートへ反映します。"
    )
    parser.add_argument(
        "--paypay-csv",
        dest="paypay_csv",
        help="PayPay取引CSVのパス。指定時のみPayPayシートを再構築します。",
    )
    return parser.parse_args()


def _load_credentials(token_filename: str, scopes: list[str]) -> Credentials:
    credentials_path = TOKENS_DIR / "credentials.json"
    token_path = TOKENS_DIR / token_filename
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def gmail_login():
    creds = _load_credentials(
        "gmail_token.json", ["https://www.googleapis.com/auth/gmail.readonly"]
    )
    return build("gmail", "v1", credentials=creds)


def spreadsheet_login() -> tuple[gspread.Spreadsheet, Credentials]:
    creds = _load_credentials(
        "sheet_token.json", ["https://www.googleapis.com/auth/spreadsheets"]
    )
    spreadsheet_id = os.getenv(SPREADSHEET_ID_ENV)
    if not spreadsheet_id:
        raise RuntimeError(f"{SPREADSHEET_ID_ENV} が設定されていません。")

    client = gspread.authorize(creds)
    return client.open_by_key(spreadsheet_id), creds


def _build_sheets_service(creds: Credentials):
    return build("sheets", "v4", credentials=creds)


def _decode_message_data(data: str | None) -> str:
    if not data:
        return ""
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")


def _extract_plain_text_from_payload(payload: dict) -> str:
    mime_type = payload.get("mimeType", "")
    if mime_type == "text/plain":
        return _decode_message_data(payload.get("body", {}).get("data"))

    for part in payload.get("parts", []) or []:
        text = _extract_plain_text_from_payload(part)
        if text:
            return text

    return _decode_message_data(payload.get("body", {}).get("data"))


def _search_messages(service, query: str) -> list[dict]:
    messages: list[dict] = []
    page_token = None

    while True:
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=100, pageToken=page_token)
            .execute()
        )
        messages.extend(response.get("messages", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    results = list(reversed(messages))
    log_info(f"検索完了: {len(results)} 件のメールが見つかりました。")
    return results


def _normalize_store(store: str) -> str:
    normalized = re.sub(r"\s+", " ", store).strip()
    normalized = re.sub(r"\s*●?\s*[（(]買物[）)]\s*$", "", normalized).strip()
    return re.sub(r"\s*●\s*$", "", normalized).strip()


def _parse_amount(text: str) -> int:
    normalized = (
        text.replace(",", "")
        .replace("円", "")
        .replace("JPY", "")
        .replace("¥", "")
        .strip()
    )
    normalized = re.sub(r"\.0+$", "", normalized)
    if not normalized or normalized == "-":
        raise ValueError("金額が空です。")
    return int(normalized)


def _amount_pattern() -> str:
    return r"([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)(?:\.0+)?\s*(?:円|JPY)"


def _datetime_pattern() -> str:
    return r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}(?::\d{2})?)"


def _first_match(patterns: Iterable[str], text: str) -> re.Match[str] | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            return match
    return None


def _extract_labeled_value(text: str, labels: Iterable[str]) -> str | None:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        normalized_line = (
            line.replace("◇", "")
            .replace("◆", "")
            .replace("■", "")
            .replace("\u3000", " ")
        )

        for label in labels:
            if label not in normalized_line:
                continue

            parts = re.split(r"[:：]", normalized_line, maxsplit=1)
            if len(parts) == 2:
                return parts[1].strip()

            index = normalized_line.find(label)
            if index >= 0:
                return normalized_line[index + len(label) :].strip()

    return None


def _extract_lines_after_match(text: str, pattern: str) -> list[str]:
    lines = text.splitlines()
    for index, raw_line in enumerate(lines):
        if re.search(pattern, raw_line):
            return [line.strip() for line in lines[index + 1 :] if line.strip()]
    return []


def _extract_sumitomo_inline_values(text: str) -> tuple[str | None, str | None, str | None]:
    date_match = re.search(rf"ご利用日時\s*[:：]\s*{_datetime_pattern()}", text)
    if not date_match:
        return None, None, None

    store_text = None
    amount_text = None
    following_lines = _extract_lines_after_match(text, r"ご利用日時\s*[:：]")

    for line in following_lines:
        amount_match = re.fullmatch(_amount_pattern(), line)
        if amount_match:
            amount_text = amount_match.group(1)
            break

        if store_text is None and not re.search(r"^(本メール|ご利用情報|身に覚え)", line):
            store_text = _normalize_store(line)

    return date_match.group(1), amount_text, store_text


def _detect_sumitomo_payment_type(text: str) -> str:
    normalized_text = text.replace("\u3000", " ")
    if re.search(r"Ｏｌｉｖｅ／クレジット|Olive/クレジット|クレジットモード", normalized_text):
        return "クレジット"
    if re.search(r"デビット|Debit|iDデビット", normalized_text, re.IGNORECASE):
        return "デビット"
    return "不明"


def _collect_transactions(service, query: str, parser, label: str) -> list[Transaction]:
    transactions: list[Transaction] = []
    errors: list[str] = []
    log_info(f"{label}メールを検索中...")
    messages = _search_messages(service, query)
    log_info(f"{label}メールの本文を取得・解析中...")
    total_messages = len(messages)
    progress_interval = max(1, total_messages // PROGRESS_BAR_WIDTH) if total_messages else 1

    if total_messages:
        log_progress(f"{label}解析", 0, total_messages)

    for index, message in enumerate(messages, start=1):
        payload = service.users().messages().get(userId="me", id=message["id"]).execute()
        text = _extract_plain_text_from_payload(payload.get("payload", {}))

        try:
            transactions.append(parser(text))
        except ValueError:
            errors.append(text[:200])

        if index == total_messages or index % progress_interval == 0:
            log_progress(f"{label}解析", index, total_messages)

    if errors:
        log_warning(f"{label}でパースできなかったメール {len(errors)} 件")
        for index, sample in enumerate(errors[:3], start=1):
            log_warning(f"sample{index}: {sample}")

    log_info(f"{label}の取得件数: {len(transactions)}")
    return transactions


def _parse_yucho_transaction(text: str) -> Transaction:
    date_match = _first_match([r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})"], text)
    amount_text = _extract_labeled_value(text, ["ご利用金額", "利用金額"])
    store_text = _extract_labeled_value(text, ["ご利用店舗", "利用店舗"])

    if not amount_text:
        amount_match = _first_match(
            [
                r"ご利用金額\s*[:：]?\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)\s*円",
                r"([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)\s*円",
            ],
            text,
        )
        amount_text = amount_match.group(1) if amount_match else None

    if not store_text:
        store_match = _first_match(
            [
                r"ご利用店舗\s*[:：]?\s*(.+)",
                r"利用店舗\s*[:：]?\s*(.+)",
            ],
            text,
        )
        store_text = store_match.group(1) if store_match else None

    if not date_match or not amount_text or not store_text:
        raise ValueError("ゆうちょメールの必要情報を抽出できませんでした。")

    return Transaction(
        occurred_at=date_match.group(1),
        amount=_parse_amount(amount_text),
        store=_normalize_store(store_text),
        source="ゆうちょ",
        payment_type="デビット",
    )


def _parse_sumitomo_transaction(text: str) -> Transaction:
    date_text = _extract_labeled_value(text, ["ご利用日", "利用日"])
    amount_text = _extract_labeled_value(text, ["ご利用金額", "利用金額"])
    store_text = _extract_labeled_value(text, ["ご利用先", "利用先"])

    date_match = (
        re.search(_datetime_pattern(), date_text)
        if date_text
        else None
    )

    if not date_match or not amount_text or not store_text:
        inline_date, inline_amount, inline_store = _extract_sumitomo_inline_values(text)
        date_match = re.search(_datetime_pattern(), inline_date or "")
        amount_text = amount_text or inline_amount
        store_text = store_text or inline_store

    if not date_match or not amount_text or not store_text:
        raise ValueError("三井住友メールの必要情報を抽出できませんでした。")

    return Transaction(
        occurred_at=date_match.group(1),
        amount=_parse_amount(amount_text),
        store=_normalize_store(store_text),
        source="三井住友",
        payment_type=_detect_sumitomo_payment_type(text),
    )


def get_visa_transactions(service) -> list[Transaction]:
    yucho_transactions = _collect_transactions(
        service,
        'subject:"【ゆうちょデビット】ご利用のお知らせ"',
        _parse_yucho_transaction,
        "ゆうちょ",
    )
    sumitomo_transactions = _collect_transactions(
        service,
        'subject:"ご利用のお知らせ【三井住友カード】"',
        _parse_sumitomo_transaction,
        "三井住友",
    )

    unique_transactions = {
        (
            transaction.occurred_at,
            transaction.amount,
            transaction.store,
            transaction.source,
            transaction.payment_type,
        ): transaction
        for transaction in yucho_transactions + sumitomo_transactions
    }

    transactions = sorted(unique_transactions.values(), key=lambda item: item.occurred_at)
    log_info(f"Visaシート反映件数: {len(transactions)}")
    return transactions


def _open_paypay_csv(path: Path):
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "cp932", "utf-8"):
        handle = None
        try:
            handle = path.open("r", encoding=encoding, newline="")
            handle.read(1)
            handle.seek(0)
            return handle
        except UnicodeDecodeError as error:
            last_error = error
            if handle is not None:
                handle.close()
    if last_error:
        raise last_error
    raise RuntimeError("PayPay CSV を開けませんでした。")


def load_paypay_transactions(csv_path: str) -> list[Transaction]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"PayPay CSV が見つかりません: {path}")

    transactions: list[Transaction] = []

    with _open_paypay_csv(path) as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {"取引日", "出金金額（円）", "取引内容", "取引先"}
        if not reader.fieldnames or not required_columns.issubset(set(reader.fieldnames)):
            raise ValueError("PayPay CSV の列名が想定と異なります。")

        for row in reader:
            if row.get("取引内容") != "支払い":
                continue

            amount_text = (row.get("出金金額（円）") or "").replace(",", "").strip()
            if not amount_text or amount_text == "-":
                continue

            transactions.append(
                Transaction(
                    occurred_at=(row.get("取引日") or "").strip(),
                    amount=_parse_amount(amount_text),
                    store=_normalize_store(row.get("取引先") or ""),
                    source="PayPay",
                    payment_type="PayPay",
                )
            )

    unique_transactions = {
        (
            transaction.occurred_at,
            transaction.amount,
            transaction.store,
            transaction.source,
            transaction.payment_type,
        ): transaction
        for transaction in transactions
    }

    result = sorted(unique_transactions.values(), key=lambda item: item.occurred_at)
    log_info(f"PayPayシート反映件数: {len(result)}")
    return result


def get_or_create_worksheet(
    spreadsheet: gspread.Spreadsheet,
    title: str,
    rows: int = 1000,
    cols: int = 26,
) -> gspread.Worksheet:
    try:
        worksheet = spreadsheet.worksheet(title)
    except WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

    if worksheet.row_count < rows:
        worksheet.add_rows(rows - worksheet.row_count)
    if worksheet.col_count < cols:
        worksheet.add_cols(cols - worksheet.col_count)

    return worksheet


def get_or_recreate_grid_worksheet(
    spreadsheet: gspread.Spreadsheet,
    sheets_service,
    title: str,
    rows: int,
    cols: int,
) -> gspread.Worksheet:
    metadata = (
        sheets_service.spreadsheets()
        .get(spreadsheetId=spreadsheet.id, fields="sheets(properties(sheetId,title,sheetType))")
        .execute()
    )
    for sheet in metadata.get("sheets", []):
        properties = sheet.get("properties", {})
        if properties.get("title") == title and properties.get("sheetType") == "OBJECT":
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet.id,
                body={"requests": [{"deleteSheet": {"sheetId": properties["sheetId"]}}]},
            ).execute()
            return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

    return get_or_create_worksheet(spreadsheet, title, rows=rows, cols=cols)


def write_transactions(worksheet: gspread.Worksheet, transactions: list[Transaction]) -> None:
    rows = [TRANSACTION_HEADERS] + [transaction.as_row() for transaction in transactions]
    worksheet.clear()
    worksheet.update(values=rows, range_name="A1")
    worksheet.format("B2:B", CURRENCY_FORMAT)


def write_empty_headers(worksheet: gspread.Worksheet) -> None:
    worksheet.clear()
    worksheet.update(values=[TRANSACTION_HEADERS], range_name="A1")
    worksheet.format("B2:B", CURRENCY_FORMAT)


def ensure_transaction_headers(worksheet: gspread.Worksheet) -> None:
    current_headers = worksheet.row_values(1)
    if current_headers[: len(TRANSACTION_HEADERS)] != TRANSACTION_HEADERS:
        worksheet.update(values=[TRANSACTION_HEADERS], range_name="A1")
    worksheet.format("B2:B", CURRENCY_FORMAT)


def _transaction_key_from_row(row: list[str]) -> tuple[str, int, str, str, str] | None:
    if len(row) < len(TRANSACTION_HEADERS):
        return None

    occurred_at, amount_text, store, source, payment_type = [
        (cell or "").strip() for cell in row[: len(TRANSACTION_HEADERS)]
    ]
    if not occurred_at or not amount_text or not store or not source or not payment_type:
        return None

    try:
        amount = _parse_amount(amount_text)
    except ValueError:
        return None

    return (
        occurred_at,
        amount,
        _normalize_store(store),
        source,
        payment_type,
    )


def load_cancelled_transaction_keys(
    worksheet: gspread.Worksheet,
) -> set[tuple[str, int, str, str, str]]:
    ensure_transaction_headers(worksheet)
    rows = worksheet.get_all_values()[1:]
    keys = {
        key
        for row in rows
        if (key := _transaction_key_from_row(row)) is not None
    }
    log_info(f"キャンセル表登録件数: {len(keys)}")
    return keys


def exclude_cancelled_transactions(
    transactions: list[Transaction],
    cancelled_keys: set[tuple[str, int, str, str, str]],
) -> list[Transaction]:
    if not cancelled_keys:
        log_info("キャンセル除外件数: 0")
        return transactions

    filtered = [
        transaction
        for transaction in transactions
        if transaction.key() not in cancelled_keys
    ]
    log_info(f"キャンセル除外件数: {len(transactions) - len(filtered)}")
    return filtered


def _parse_transaction_date(text: str) -> date | None:
    date_text = (text or "").strip()[:10]
    try:
        return datetime.strptime(date_text, "%Y/%m/%d").date()
    except ValueError:
        return None


def _transaction_amount_from_row(row: list[str]) -> int | None:
    if len(row) < 2:
        return None

    try:
        return _parse_amount(row[1])
    except ValueError:
        return None


def _summary_rows_from_worksheet(worksheet: gspread.Worksheet) -> list[tuple[date, int]]:
    rows: list[tuple[date, int]] = []
    for row in worksheet.get_all_values()[1:]:
        occurred_on = _parse_transaction_date(row[0] if row else "")
        amount = _transaction_amount_from_row(row)
        if occurred_on is not None and amount is not None:
            rows.append((occurred_on, amount))
    return rows


def _format_yen(amount: int) -> str:
    return f"¥{amount:,}"


def print_execution_summary(worksheets: Iterable[gspread.Worksheet]) -> None:
    today = date.today()
    rows: list[tuple[date, int]] = []
    for worksheet in worksheets:
        rows.extend(_summary_rows_from_worksheet(worksheet))

    all_time_total = sum(amount for _, amount in rows)
    year_total = sum(amount for occurred_on, amount in rows if occurred_on.year == today.year)
    month_total = sum(
        amount
        for occurred_on, amount in rows
        if occurred_on.year == today.year and occurred_on.month == today.month
    )

    print()
    print("実行サマリー")
    print(f"  - 今までの合計: {_format_yen(all_time_total)}")
    print(f"  - {today.year}年の合計: {_format_yen(year_total)}")
    print(f"  - {today.year}/{today.month:02d} の合計: {_format_yen(month_total)}")
    print(f"  - 集計対象の取引件数: {len(rows)}件")


def combined_transactions_formula() -> str:
    return "{'Visa'!A2:E;'PayPay'!A2:E}"


def write_total_sheet(worksheet: gspread.Worksheet) -> None:
    worksheet.clear()
    worksheet.update(
        values=[
            ["項目", "金額"],
            [
                "全合計",
                f'=IFERROR(SUM(QUERY({combined_transactions_formula()},"select Col2 where Col1 is not null",0)),0)',
            ],
        ],
        range_name="A1",
        value_input_option="USER_ENTERED",
    )
    worksheet.format("B2:B", CURRENCY_FORMAT)


def write_monthly_sheet(worksheet: gspread.Worksheet) -> None:
    worksheet.clear()
    worksheet.update(
        values=[["月", "合計"]],
        range_name="A1",
        value_input_option="USER_ENTERED",
    )
    worksheet.update(
        values=[
            [
                f'=IFERROR(QUERY({{ARRAYFORMULA(LEFT(QUERY({combined_transactions_formula()},"select Col1 where Col1 is not null",0),7)),QUERY({combined_transactions_formula()},"select Col2 where Col1 is not null",0)}},"select Col1, sum(Col2) group by Col1 order by Col1 label sum(Col2) \'\'",0),{{"",""}})'
            ]
        ],
        range_name="A2",
        value_input_option="USER_ENTERED",
    )
    worksheet.format("B2:B", CURRENCY_FORMAT)


def write_store_sheet(worksheet: gspread.Worksheet) -> None:
    worksheet.clear()
    worksheet.update(
        values=[["店舗", "合計"]],
        range_name="A1",
        value_input_option="USER_ENTERED",
    )
    worksheet.update(
        values=[
            [
                f'=IFERROR(QUERY({combined_transactions_formula()},"select Col3, sum(Col2) where Col1 is not null group by Col3 order by sum(Col2) desc label sum(Col2) \'\'",0),{{"",""}})'
            ]
        ],
        range_name="A2",
        value_input_option="USER_ENTERED",
    )
    worksheet.format("B2:B", CURRENCY_FORMAT)


def write_monthly_store_sheet(worksheet: gspread.Worksheet) -> None:
    worksheet.clear()
    worksheet.update(
        values=[["月", "店舗", "合計"]],
        range_name="A1",
        value_input_option="USER_ENTERED",
    )
    worksheet.update(
        values=[
            [
                f'=IFERROR(QUERY({{ARRAYFORMULA(LEFT(QUERY({combined_transactions_formula()},"select Col1 where Col1 is not null",0),7)),QUERY({combined_transactions_formula()},"select Col3 where Col1 is not null",0),QUERY({combined_transactions_formula()},"select Col2 where Col1 is not null",0)}},"select Col1, Col2, sum(Col3) group by Col1, Col2 order by Col1, sum(Col3) desc label sum(Col3) \'\'",0),{{"","",""}})'
            ]
        ],
        range_name="A2",
        value_input_option="USER_ENTERED",
    )
    worksheet.format("C2:C", CURRENCY_FORMAT)


def write_monthly_store_pivot_sheet(worksheet: gspread.Worksheet) -> None:
    worksheet.clear()
    worksheet.update(
        values=[["店舗", "月別利用額"]],
        range_name="A1",
        value_input_option="USER_ENTERED",
    )
    worksheet.update(
        values=[
            [
                f'=IFERROR(QUERY({{QUERY({combined_transactions_formula()},"select Col3 where Col1 is not null",0),ARRAYFORMULA(LEFT(QUERY({combined_transactions_formula()},"select Col1 where Col1 is not null",0),7)),QUERY({combined_transactions_formula()},"select Col2 where Col1 is not null",0)}},"select Col1, sum(Col3) where Col1 is not null group by Col1 pivot Col2 label sum(Col3) \'\'",0),{{"店舗"}})'
            ]
        ],
        range_name="A2",
        value_input_option="USER_ENTERED",
    )
    worksheet.format("B2:ZZ", CURRENCY_FORMAT)


def _delete_existing_charts(sheets_service, spreadsheet_id: str, target_sheet_ids: set[int]) -> None:
    metadata = (
        sheets_service.spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            fields="sheets(properties(sheetId),charts(chartId,position))",
        )
        .execute()
    )

    delete_requests = []
    for sheet in metadata.get("sheets", []):
        for chart in sheet.get("charts", []):
            position = chart.get("position", {})
            anchor = position.get("overlayPosition", {}).get("anchorCell", {})
            if position.get("sheetId") in target_sheet_ids or anchor.get("sheetId") in target_sheet_ids:
                delete_requests.append(
                    {"deleteEmbeddedObject": {"objectId": chart["chartId"]}}
                )

    if delete_requests:
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": delete_requests},
        ).execute()


def _source_range(sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int):
    return {
        "sources": [
            {
                "sheetId": sheet_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
                "startColumnIndex": start_col,
                "endColumnIndex": end_col,
            }
        ]
    }


def _chart_position(target_sheet_id: int, height_pixels: int):
    return {
        "overlayPosition": {
            "anchorCell": {
                "sheetId": target_sheet_id,
                "rowIndex": 0,
                "columnIndex": 0,
            },
            "offsetXPixels": 0,
            "offsetYPixels": 0,
            "widthPixels": 720,
            "heightPixels": height_pixels,
        }
    }


def _monthly_chart_spec(monthly_sheet: gspread.Worksheet) -> dict:
    return {
        "title": "月別支出推移",
        "basicChart": {
            "chartType": "COLUMN",
            "legendPosition": "NO_LEGEND",
            "axis": [
                {"position": "BOTTOM_AXIS", "title": "月"},
                {"position": "LEFT_AXIS", "title": "金額"},
            ],
            "domains": [
                {"domain": {"sourceRange": _source_range(monthly_sheet.id, 1, 2000, 0, 1)}}
            ],
            "series": [
                {
                    "series": {
                        "sourceRange": _source_range(monthly_sheet.id, 1, 2000, 1, 2)
                    },
                    "targetAxis": "LEFT_AXIS",
                }
            ],
            "headerCount": 0,
        },
    }


def _store_chart_spec(store_sheet: gspread.Worksheet) -> dict:
    return {
        "title": "店舗別支出上位",
        "basicChart": {
            "chartType": "BAR",
            "legendPosition": "NO_LEGEND",
            "axis": [
                {"position": "BOTTOM_AXIS", "title": "金額"},
                {"position": "LEFT_AXIS", "title": "店舗"},
            ],
            "domains": [
                {"domain": {"sourceRange": _source_range(store_sheet.id, 1, 11, 0, 1)}}
            ],
            "series": [
                {
                    "series": {
                        "sourceRange": _source_range(store_sheet.id, 1, 11, 1, 2)
                    },
                    "targetAxis": "BOTTOM_AXIS",
                }
            ],
            "headerCount": 0,
        },
    }


def _chart_request(
    spec: dict,
    target_sheet_id: int,
    height_pixels: int,
) -> dict:
    return {
        "addChart": {
            "chart": {
                "spec": spec,
                "position": _chart_position(target_sheet_id, height_pixels),
            }
        }
    }


def create_summary_charts(
    spreadsheet: gspread.Spreadsheet,
    creds: Credentials,
    monthly_sheet: gspread.Worksheet,
    store_sheet: gspread.Worksheet,
    monthly_chart_sheet: gspread.Worksheet,
    store_chart_sheet: gspread.Worksheet,
) -> None:
    sheets_service = _build_sheets_service(creds)
    spreadsheet_id = spreadsheet.id
    _delete_existing_charts(
        sheets_service,
        spreadsheet_id,
        {monthly_sheet.id, store_sheet.id, monthly_chart_sheet.id, store_chart_sheet.id},
    )

    requests = [
        _chart_request(_monthly_chart_spec(monthly_sheet), monthly_chart_sheet.id, 420),
        _chart_request(_store_chart_spec(store_sheet), store_chart_sheet.id, 520),
    ]

    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()


def main() -> None:
    os.chdir(SCRIPT_DIR)
    log_step(1, "環境変数を読み込み中...")
    load_dotenv(ROOT_DIR / ".env")
    load_dotenv(SCRIPT_DIR / ".env")
    args = parse_args()

    log_step(2, "Gmail に認証中...")
    service = gmail_login()
    log_step(3, "スプレッドシートに認証中...")
    spreadsheet, sheet_creds = spreadsheet_login()
    sheets_service = _build_sheets_service(sheet_creds)

    log_step(4, "ワークシートを確認・作成中...")
    visa_sheet = get_or_create_worksheet(spreadsheet, VISA_SHEET_NAME, rows=2000, cols=8)
    paypay_sheet = get_or_create_worksheet(spreadsheet, PAYPAY_SHEET_NAME, rows=2000, cols=8)
    cancel_sheet = get_or_create_worksheet(
        spreadsheet, CANCEL_SHEET_NAME, rows=1000, cols=8
    )
    summary_sheet = get_or_create_worksheet(spreadsheet, SUMMARY_SHEET_NAME, rows=200, cols=8)
    monthly_sheet = get_or_create_worksheet(spreadsheet, MONTHLY_SHEET_NAME, rows=2000, cols=8)
    store_sheet = get_or_create_worksheet(spreadsheet, STORE_SHEET_NAME, rows=2000, cols=8)
    monthly_chart_sheet = get_or_recreate_grid_worksheet(
        spreadsheet,
        sheets_service,
        MONTHLY_CHART_SHEET_NAME,
        rows=30,
        cols=12,
    )
    store_chart_sheet = get_or_recreate_grid_worksheet(
        spreadsheet,
        sheets_service,
        STORE_CHART_SHEET_NAME,
        rows=30,
        cols=12,
    )
    monthly_store_sheet = get_or_create_worksheet(
        spreadsheet, MONTHLY_STORE_SHEET_NAME, rows=5000, cols=8
    )
    monthly_store_pivot_sheet = get_or_create_worksheet(
        spreadsheet, MONTHLY_STORE_PIVOT_SHEET_NAME, rows=5000, cols=60
    )

    log_step(5, "Visa 取引を取得してシートへ反映中...")
    visa_transactions = get_visa_transactions(service)
    cancelled_keys = load_cancelled_transaction_keys(cancel_sheet)
    visa_transactions = exclude_cancelled_transactions(visa_transactions, cancelled_keys)
    write_transactions(visa_sheet, visa_transactions)

    log_step(6, "PayPay 取引の反映可否を確認中...")
    if args.paypay_csv:
        log_info(f"PayPay CSV を読み込みます: {args.paypay_csv}")
        paypay_transactions = load_paypay_transactions(args.paypay_csv)
        write_transactions(paypay_sheet, paypay_transactions)
    elif not paypay_sheet.get_all_values():
        log_info("PayPay シートが空のため、ヘッダーのみ初期化します。")
        write_empty_headers(paypay_sheet)
    else:
        log_info("PayPay CSV 未指定のため、既存の PayPay シートをそのまま利用します。")

    log_step(7, "集計シートを更新中...")
    write_total_sheet(summary_sheet)
    write_monthly_sheet(monthly_sheet)
    write_store_sheet(store_sheet)
    write_monthly_store_sheet(monthly_store_sheet)
    write_monthly_store_pivot_sheet(monthly_store_pivot_sheet)
    log_step(8, "グラフを作成中...")
    create_summary_charts(
        spreadsheet,
        sheet_creds,
        monthly_sheet,
        store_sheet,
        monthly_chart_sheet,
        store_chart_sheet,
    )

    log_step(9, "実行結果を集計中...")
    print_execution_summary([visa_sheet, paypay_sheet])
    log_info("スプレッドシートの更新が完了しました。")


if __name__ == "__main__":
    main()
