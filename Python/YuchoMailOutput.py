from __future__ import annotations

import argparse
import base64
import csv
import os
import re
from dataclasses import dataclass
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
SUMMARY_SHEET_NAME = "決済"
MONTHLY_SHEET_NAME = "月別"
STORE_SHEET_NAME = "店舗別"
MONTHLY_STORE_SHEET_NAME = "月別店舗"
MONTHLY_STORE_PIVOT_SHEET_NAME = "月別店舗ピボット"

TRANSACTION_HEADERS = ["日時", "金額", "店舗", "決済元"]
CURRENCY_FORMAT = {"numberFormat": {"type": "CURRENCY", "pattern": "¥#,##0"}}


@dataclass(frozen=True)
class Transaction:
    occurred_at: str
    amount: int
    store: str
    source: str

    def as_row(self) -> list[object]:
        return [self.occurred_at, self.amount, self.store, self.source]


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

    return list(reversed(messages))


def _normalize_store(store: str) -> str:
    return re.sub(r"\s+", " ", store).strip()


def _parse_amount(text: str) -> int:
    normalized = text.replace(",", "").replace("円", "").strip()
    if not normalized or normalized == "-":
        raise ValueError("金額が空です。")
    return int(normalized)


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


def _collect_transactions(service, query: str, parser, label: str) -> list[Transaction]:
    transactions: list[Transaction] = []
    errors: list[str] = []

    for message in _search_messages(service, query):
        payload = service.users().messages().get(userId="me", id=message["id"]).execute()
        text = _extract_plain_text_from_payload(payload.get("payload", {}))

        try:
            transactions.append(parser(text))
        except ValueError:
            errors.append(text[:200])

    if errors:
        print(f"[Warn] {label}でパースできなかったメール {len(errors)} 件")
        for index, sample in enumerate(errors[:3], start=1):
            print(f"[Warn] sample{index}: {sample}")

    print(f"[Info] {label}の取得件数: {len(transactions)}")
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
    )


def _parse_sumitomo_transaction(text: str) -> Transaction:
    date_text = _extract_labeled_value(text, ["ご利用日", "利用日"])
    amount_text = _extract_labeled_value(text, ["ご利用金額", "利用金額"])
    store_text = _extract_labeled_value(text, ["ご利用先", "利用先"])

    date_match = (
        re.search(r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})", date_text)
        if date_text
        else None
    )

    if not date_match or not amount_text or not store_text:
        raise ValueError("三井住友メールの必要情報を抽出できませんでした。")

    return Transaction(
        occurred_at=date_match.group(1),
        amount=_parse_amount(amount_text),
        store=_normalize_store(store_text),
        source="三井住友",
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
        ): transaction
        for transaction in yucho_transactions + sumitomo_transactions
    }

    transactions = sorted(unique_transactions.values(), key=lambda item: item.occurred_at)
    print(f"[Info] Visaシート反映件数: {len(transactions)}")
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
                )
            )

    unique_transactions = {
        (
            transaction.occurred_at,
            transaction.amount,
            transaction.store,
            transaction.source,
        ): transaction
        for transaction in transactions
    }

    result = sorted(unique_transactions.values(), key=lambda item: item.occurred_at)
    print(f"[Info] PayPayシート反映件数: {len(result)}")
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


def write_transactions(worksheet: gspread.Worksheet, transactions: list[Transaction]) -> None:
    rows = [TRANSACTION_HEADERS] + [transaction.as_row() for transaction in transactions]
    worksheet.clear()
    worksheet.update(values=rows, range_name="A1")
    worksheet.format("B2:B", CURRENCY_FORMAT)


def write_empty_headers(worksheet: gspread.Worksheet) -> None:
    worksheet.clear()
    worksheet.update(values=[TRANSACTION_HEADERS], range_name="A1")
    worksheet.format("B2:B", CURRENCY_FORMAT)


def combined_transactions_formula() -> str:
    return "{'Visa'!A2:D;'PayPay'!A2:D}"


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
            anchor = chart.get("position", {}).get("overlayPosition", {}).get("anchorCell", {})
            if anchor.get("sheetId") in target_sheet_ids:
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


def create_summary_charts(
    spreadsheet: gspread.Spreadsheet,
    creds: Credentials,
    monthly_sheet: gspread.Worksheet,
    store_sheet: gspread.Worksheet,
) -> None:
    sheets_service = _build_sheets_service(creds)
    spreadsheet_id = spreadsheet.id
    _delete_existing_charts(sheets_service, spreadsheet_id, {monthly_sheet.id, store_sheet.id})

    requests = [
        {
            "addChart": {
                "chart": {
                    "spec": {
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
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {
                                "sheetId": monthly_sheet.id,
                                "rowIndex": 0,
                                "columnIndex": 3,
                            },
                            "offsetXPixels": 16,
                            "offsetYPixels": 16,
                            "widthPixels": 720,
                            "heightPixels": 420,
                        }
                    },
                }
            }
        },
        {
            "addChart": {
                "chart": {
                    "spec": {
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
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {
                                "sheetId": store_sheet.id,
                                "rowIndex": 0,
                                "columnIndex": 3,
                            },
                            "offsetXPixels": 16,
                            "offsetYPixels": 16,
                            "widthPixels": 720,
                            "heightPixels": 520,
                        }
                    },
                }
            }
        },
    ]

    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()


def main() -> None:
    os.chdir(SCRIPT_DIR)
    load_dotenv(ROOT_DIR / ".env")
    load_dotenv(SCRIPT_DIR / ".env")
    args = parse_args()

    service = gmail_login()
    spreadsheet, sheet_creds = spreadsheet_login()

    visa_sheet = get_or_create_worksheet(spreadsheet, VISA_SHEET_NAME, rows=2000, cols=8)
    paypay_sheet = get_or_create_worksheet(spreadsheet, PAYPAY_SHEET_NAME, rows=2000, cols=8)
    summary_sheet = get_or_create_worksheet(spreadsheet, SUMMARY_SHEET_NAME, rows=200, cols=8)
    monthly_sheet = get_or_create_worksheet(spreadsheet, MONTHLY_SHEET_NAME, rows=2000, cols=8)
    store_sheet = get_or_create_worksheet(spreadsheet, STORE_SHEET_NAME, rows=2000, cols=8)
    monthly_store_sheet = get_or_create_worksheet(
        spreadsheet, MONTHLY_STORE_SHEET_NAME, rows=5000, cols=8
    )
    monthly_store_pivot_sheet = get_or_create_worksheet(
        spreadsheet, MONTHLY_STORE_PIVOT_SHEET_NAME, rows=5000, cols=60
    )

    visa_transactions = get_visa_transactions(service)
    write_transactions(visa_sheet, visa_transactions)

    if args.paypay_csv:
        paypay_transactions = load_paypay_transactions(args.paypay_csv)
        write_transactions(paypay_sheet, paypay_transactions)
    elif not paypay_sheet.get_all_values():
        write_empty_headers(paypay_sheet)

    write_total_sheet(summary_sheet)
    write_monthly_sheet(monthly_sheet)
    write_store_sheet(store_sheet)
    write_monthly_store_sheet(monthly_store_sheet)
    write_monthly_store_pivot_sheet(monthly_store_pivot_sheet)
    create_summary_charts(spreadsheet, sheet_creds, monthly_sheet, store_sheet)

    print("[Info] スプレッドシートの更新が完了しました。")


if __name__ == "__main__":
    main()
