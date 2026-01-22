import base64
import os
import re

import gspread
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


def gmail_login():
    credentials_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "tokens", "credentials.json"
    )
    gmail_token_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "tokens", "gmail_token.json"
    )
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds = None
    if os.path.exists(gmail_token_path):
        creds = Credentials.from_authorized_user_file(gmail_token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(gmail_token_path, "w") as token:
            token.write(creds.to_json())
    service = build("gmail", "v1", credentials=creds)
    return service


def spreadsheet_login():
    credentials_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "tokens", "credentials.json"
    )
    sheet_token_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "tokens", "sheet_token.json"
    )
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = None
    if os.path.exists(sheet_token_path):
        creds = Credentials.from_authorized_user_file(sheet_token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(sheet_token_path, "w") as token:
            token.write(creds.to_json())
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(os.getenv("YUCHO_SHEET"))
    sheet = spreadsheet.sheet1
    return sheet, spreadsheet, sheet


def _extract_plain_text_from_payload(payload: dict) -> str:
    """Prefer text/plain part, fallback to body."""
    parts = payload.get("parts")
    if parts:
        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    data = payload.get("body", {}).get("data")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return ""


def get_yucho_message(service):
    results = (
        service.users()
        .messages()
        .list(
            userId="me",
            q='subject:"【ゆうちょデビット】ご利用のお知らせ"',
            maxResults=5,
        )
        .execute()
    )
    messages = results.get("messages", [])

    while "nextPageToken" in results:
        page_token = results["nextPageToken"]
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                q='subject:"【ゆうちょデビット】ご利用のお知らせ"',
                maxResults=5,
                pageToken=page_token,
            )
            .execute()
        )
        messages.extend(results.get("messages", []))

    messages = list(reversed(messages))

    pattern_date = r"\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}"
    pattern_amount = r"\d{1,3}(,\d{3})*円"
    pattern_store = r"利用店舗\s+(.*)"

    dates = []
    amounts = []
    stores = []
    errors = []

    for message in messages:
        msg = service.users().messages().get(userId="me", id=message["id"]).execute()
        text = _extract_plain_text_from_payload(msg.get("payload", {}))

        strings_date = re.search(pattern_date, text)
        strings_amount = re.search(pattern_amount, text)
        strings_store = re.search(pattern_store, text)

        if strings_date and strings_amount and strings_store:
            dates.append(strings_date.group())
            amount_value = strings_amount.group().replace("円", "").replace(",", "")
            amounts.append(int(amount_value))
            stores.append(strings_store.group(1))
        else:
            errors.append(text[:200])

    if errors:
        print(f"[Warn] ゆうちょでパースできなかったメール {len(errors)} 件")
        for idx, sample in enumerate(errors[:3], start=1):
            print(f"[Warn] sample{idx}: {sample}")

    return dates, amounts, stores

def get_sumitomo_message(service):
    results = (
        service.users()
        .messages()
        .list(
            userId="me",
            q='subject:"ご利用のお知らせ【三井住友カード】"',
            maxResults=5,
        )
        .execute()
    )
    messages = results.get("messages", [])

    while "nextPageToken" in results:
        page_token = results["nextPageToken"]
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                q='subject:"ご利用のお知らせ【三井住友カード】"',
                maxResults=5,
                pageToken=page_token,
            )
            .execute()
        )
        messages.extend(results.get("messages", []))

    messages = list(reversed(messages))
    pattern_date = r"利用日[^0-9]*(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})"
    pattern_amount = r"利用金額[^0-9]*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)\s*円"
    pattern_store = r"利用先[^:：]*[:：]\s*(.*)"

    dates = []
    amounts = []
    stores = []
    errors = []

    for message in messages:
        msg = service.users().messages().get(userId="me", id=message["id"]).execute()
        text = _extract_plain_text_from_payload(msg.get("payload", {}))

        match_date = re.search(pattern_date, text)
        match_amount = re.search(pattern_amount, text)
        match_store = re.search(pattern_store, text)

        if match_date and match_amount and match_store:
            dates.append(match_date.group(1))
            amount_value = match_amount.group(1).replace(",", "")
            amounts.append(int(amount_value))
            stores.append(match_store.group(1).strip())
        else:
            errors.append(text[:200])

    if errors:
        print(f"[Warn] 三井住友でパースできなかったメール {len(errors)} 件")
        for idx, sample in enumerate(errors[:3], start=1):
            print(f"[Warn] sample{idx}: {sample}")

    return dates, amounts, stores


def while_yuchomail_output(dates, amounts, stores, sheet):
    if len(dates) != len(amounts) or len(dates) != len(stores):
        print("[Error] The lengths of dates, amounts, and stores lists do not match.")
        return

    # 重複防止（日付+金額+店舗）
    unique_rows = []
    seen = set()
    for d, a, s in zip(dates, amounts, stores):
        key = (d, a, s)
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append([d, a, s])
    dates = [r[0] for r in unique_rows]
    amounts = [r[1] for r in unique_rows]
    stores = [r[2] for r in unique_rows]

    sheet.clear()
    sheet.update("A1", [["日付", "金額", "店舗"]])
    rows = [[dates[i], amounts[i], stores[i]] for i in range(len(dates))]
    sheet.append_rows(rows)
    for row in rows:
        print(f"[Info] {row}")
    sheet.update("H1", [["合計"]])
    sheet.update("H2", [["=SUM(B2:B)"]], value_input_option="USER_ENTERED")
    sheet.update(
        "E1",
        [
            [
                "店舗",
            ]
        ],
    )
    sheet.update(
        "F1",
        [
            [
                "合計金額",
            ]
        ],
    )
    sheet.update(
        "E2",
        [["=ARRAYFORMULA({UNIQUE(C2:C), SUMIF(C2:C, UNIQUE(C2:C), B2:B)})"]],
        value_input_option="USER_ENTERED",
    )
    # 日別合計の最大値をJ2へ
    # 1日最大の合計とその日付
    sheet.update(
        "J1",
        [["日付(最大日)", "1日最大"]],
    )
    daily_max_date = '=IFERROR(INDEX(QUERY({LEFT(A2:A,10),B2:B},"select Col1,sum(Col2) where Col1 is not null group by Col1 order by sum(Col2) desc",0),2,1),"")'
    daily_max_sum = '=IFERROR(INDEX(QUERY({LEFT(A2:A,10),B2:B},"select Col1,sum(Col2) where Col1 is not null group by Col1 order by sum(Col2) desc",0),2,2),0)'
    sheet.update(
        "J2",
        [[daily_max_date, daily_max_sum]],
        value_input_option="USER_ENTERED",
    )
    # 店舗別TOP5をJ4から縦に出力（店舗名と合計）
    sheet.update(
        "J3",
        [["店舗TOP10", "金額"]],
    )
    sheet.update(
        "J4",
        [["=QUERY({E2:F},\"select Col1, Col2 where Col1 is not null order by Col2 desc limit 10\",0)"]],
        value_input_option="USER_ENTERED",
    )
    # 月別合計をL列に出力
    sheet.update(
        "L1",
        [["月別", "合計"]],
    )
    sheet.update(
        "L2",
        [["=QUERY({ARRAYFORMULA(LEFT(A2:A,7)),B2:B},\"select Col1, sum(Col2) where Col1 is not null group by Col1 order by Col1\",0)"]],
        value_input_option="USER_ENTERED",
    )
    # 高額TOP5（全体）をH4から出力（日付・金額・店舗）
    sheet.update(
        "H15",
        [["高額TOP5(日付)", "金額", "店舗"]],
    )
    sheet.update(
        "H16",
        [["=QUERY({A2:C},\"select Col1, Col2, Col3 where Col2 is not null order by Col2 desc limit 5\",0)"]],
        value_input_option="USER_ENTERED",
    )
    # 金額列に通貨書式を適用
    currency_fmt = {"numberFormat": {"type": "CURRENCY", "pattern": "¥#,##0"}}
    sheet.format("B2:B", currency_fmt)
    sheet.format("F2:F", currency_fmt)
    sheet.format("H2", currency_fmt)
    sheet.format("K2:K", currency_fmt)
    sheet.format("M2:M", currency_fmt)
    sheet.format("I11:I", currency_fmt)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv()
    service = gmail_login()
    dates, amounts, stores = get_yucho_message(service)
    s_dates, s_amounts, s_stores = get_sumitomo_message(service)
    dates += s_dates
    amounts += s_amounts
    stores += s_stores
    sheet, spreadsheet, sheet = spreadsheet_login()
    while_yuchomail_output(dates, amounts, stores, sheet)
