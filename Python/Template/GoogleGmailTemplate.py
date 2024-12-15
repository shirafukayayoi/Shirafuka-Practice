import base64
import os.path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()


def main():
    gmail = Gmail()
    message = gmail.get_search_message()


class Gmail:
    def __init__(self):
        self.scope = ["https://www.googleapis.com/auth/gmail.readonly"]
        self.creds = None
        self.service = None
        self.authenticate()

    def authenticate(self):
        if os.path.exists("gmail_token.json"):
            self.creds = Credentials.from_authorized_user_file(
                "gmail_token.json", self.scope
            )
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", self.scope
                )
                self.creds = flow.run_local_server(port=0)
            with open("gmail_token.json", "w") as token:
                token.write(self.creds.to_json())
        self.service = build("gmail", "v1", credentials=self.creds)
        print("認証完了")

    # 最新のメッセージを取得する
    def get_latest_message(self):
        service = build("gmail", "v1", credentials=self.creds)
        results = service.users().messages().list(userId="me", maxResults=1).execute()
        messages = results.get("messages", [])

        if not messages:
            print("No messages found.")
            return None

        message = (
            service.users().messages().get(userId="me", id=messages[0]["id"]).execute()
        )
        payload = message.get("payload", {})
        headers = payload.get("headers", [])
        for header in headers:
            if header["name"] == "Subject":
                print("Subject:", header["value"])

        if "parts" in payload:
            parts = payload["parts"]
            for part in parts:
                if part["mimeType"] == "text/plain":
                    data = part["body"]["data"]
                    text = base64.urlsafe_b64decode(data).decode("utf-8")
                    print("Message body:", text)
                    return text
        else:
            data = payload["body"]["data"]
            text = base64.urlsafe_b64decode(data).decode("utf-8")
            print("Message body:", text)
            return text

    # 特定のメッセージを複数取得し、テキストファイルにまとめる
    def get_search_message(self):
        user_email = os.getenv("GMAIL_TEMPLETE_EMAIL")
        search_query = f"from:{user_email}"
        results = (
            self.service.users()
            .messages()
            .list(
                userId="me", q=search_query, maxResults=10
            )  # 取得するメッセージの最大数を設定
            .execute()
        )
        messages = results.get("messages", [])
        if not messages:
            print("No messages found.")
            return None
        else:
            message_bodies = []
            for message in messages:
                msg = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=message["id"])
                    .execute()
                )
                payload = msg["payload"]
                headers = payload.get("headers")
                parts = payload.get("parts")
                if headers:
                    for header in headers:
                        if header["name"] == "Subject":
                            print("Subject:", header["value"])
                if parts:
                    for part in parts:
                        if part["mimeType"] == "text/plain":
                            data = part["body"]["data"]
                            text = base64.urlsafe_b64decode(data).decode("utf-8")
                            print("Message body:", text)
                            message_bodies.append(text)
                else:
                    data = payload["body"]["data"]
                    text = base64.urlsafe_b64decode(data).decode("utf-8")
                    print("Message body:", text)
                    message_bodies.append(text)

            # テキストファイルに保存
            with open("message.txt", "w") as f:
                for message_body in message_bodies:
                    f.write(message_body + "\n")
            return message_bodies


if __name__ == "__main__":
    main()
