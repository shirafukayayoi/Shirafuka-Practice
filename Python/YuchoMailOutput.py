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
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds = None
    if os.path.exists("gmail_token.json"):
        creds = Credentials.from_authorized_user_file("gmail_token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("gmail_token.json", "w") as token:
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
            maxResults=100,
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
                maxResults=100,
                pageToken=page_token,
            )
            .execute()
        )
        messages.extend(results.get("messages", []))

    # 古いメッセージから処理するために逆順にする
    messages.reverse()

    pattern_date = r"\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}"
    pattern_amount = r"\d{1,3}(,\d{3})*"
    pattern_store = r"利用店舗\s+(.*)"

    data = []
    amount = []
    store = []

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
            text_data = payload["body"]["data"]
            text = base64.urlsafe_b64decode(text_data).decode("utf-8")

        strings_date = re.search(pattern_date, text)
        strings_amount = re.search(pattern_amount, text)
        strings_store = re.search(pattern_store, text)

        if strings_date:
            data.append(strings_date.group())
        if strings_amount:
            amount.append(strings_amount.group())
        if strings_store:
            store.append(strings_store.group(1))

    return data, amount, store


def spreadsheet_login():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_service_account_file(
        "service_token.json", scopes=scope
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(os.getenv("YUCHO_SHEET"))
    sheet = spreadsheet.sheet1
    return sheet, spreadsheet, sheet


def while_yuchomail_output(data, amount, store, sheet):
    sheet.clear()
    sheet.update("A1", [["日付", "金額", "店舗"]])
    rows = [[data[i], float(amount[i]), store[i]] for i in range(len(data))]
    sheet.append_rows(rows)
    for row in rows:
        print(row)
    sheet.update("E1", [["合計"]])
    sheet.update("E2", [["=SUM(B:B)"]], value_input_option="USER_ENTERED")


if __name__ == "__main__":
    load_dotenv()
    service = gmail_login()
    data, amount, store = get_yucho_message(service)
    sheet, spreadsheet, sheet = spreadsheet_login()
    while_yuchomail_output(data, amount, store, sheet)
