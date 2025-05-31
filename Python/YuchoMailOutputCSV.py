import base64
import csv
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


def get_email_messages(service):
    results = (
        service.users()
        .messages()
        .list(
            userId="me", 
            q="subject:【ゆうちょデビット】ご利用のお知らせ",
            maxResults=10,
        ).execute()
    )
    messages = results.get("messages", [])

    while "nextPageToken" in results:
        page_token = results["nextPageToken"]
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                q="subject:【ゆうちょデビット】ご利用のお知らせ",
                pageToken=page_token,
                maxResults=10,
            )
        ).execute()
        messages.extend(results.get("messages", []))

    messages =list(reversed(messages))
    
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
            # 店舗名から改行を削除して1行にする
            store_name = strings_store.group(1).replace("\n", " ").replace("\r", " ").strip()
            stores.append(store_name)

    return dates, amounts, stores

def save_to_csv(dates, amounts, stores):
    csv_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "yucho_mail_output.csv"
    )
    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Date", "Amount", "Store"])
        for date, amount, store in zip(dates, amounts, stores):
            writer.writerow([date, amount, store])
    print(f"[Info] CSV file saved at {csv_path}")

if __name__ == "__main__":
    load_dotenv()
    service = gmail_login()
    dates, amounts, stores = get_email_messages(service)
    save_to_csv(dates, amounts, stores)
    print("[Info] Yucho mail output completed.")
