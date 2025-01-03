import base64
import os
import re

import gspread
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


def gmail_login():
    credentials_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "credentials.json"
    )
    gmail_token_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "gmail_token.json"
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

    for message in messages:
        msg = service.users().messages().get(userId="me", id=message["id"]).execute()
        payload = msg["payload"]
        parts = payload.get("parts")
        text = ""
        if parts:
            for part in parts:
                if part["mimeType"] == "text/plain":
                    data = part["body"]["data"]
                    text = base64.urlsafe_b64decode(data).decode("utf-8")
        else:
            data = payload["body"]["data"]
            text = base64.urlsafe_b64decode(data).decode("utf-8")

        strings_date = re.search(pattern_date, text)
        strings_amount = re.search(pattern_amount, text)
        strings_store = re.search(pattern_store, text)

        if strings_date:
            dates.append(strings_date.group())
        if strings_amount:
            amount_value = strings_amount.group().replace("円", "").replace(",", "")
            amounts.append(int(amount_value))
        if strings_store:
            stores.append(strings_store.group(1))

    return dates, amounts, stores


def spreadsheet_login():
    service_token_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "service_token.json"
    )
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_service_account_file(
        service_token_path, scopes=scope
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(os.getenv("YUCHO_SHEET"))
    sheet = spreadsheet.sheet1
    return sheet, spreadsheet, sheet


def while_yuchomail_output(dates, amounts, stores, sheet):
    if len(dates) != len(amounts) or len(dates) != len(stores):
        print("Error: The lengths of dates, amounts, and stores lists do not match.")
        return

    sheet.clear()
    sheet.update("A1", [["日付", "金額", "店舗"]])
    rows = [[dates[i], amounts[i], stores[i]] for i in range(len(dates))]
    sheet.append_rows(rows)
    for row in rows:
        print(row)
    sheet.update("E1", [["合計"]])
    sheet.update("E2", [["=SUM(B2:B)"]], value_input_option="USER_ENTERED")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv()
    service = gmail_login()
    dates, amounts, stores = get_yucho_message(service)
    sheet, spreadsheet, sheet = spreadsheet_login()
    while_yuchomail_output(dates, amounts, stores, sheet)
