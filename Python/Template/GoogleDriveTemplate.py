import os.path
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


def main():
    drive_auth = GoogleDriveAuth()
    folder_id = "1XIGV331ZwuZKc-LawO-gvP4E19dZscLQ"
    drive_auth.get_spreadsheet(folder_id)


class GoogleDriveAuth:
    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
    ]

    def __init__(
        self, token_path="token.pickle", credentials_path="drive_credentials.json"
    ):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.creds = None
        self.drive_service = None
        self.sheets_service = None

        # OAuth2認証とサービスインスタンスの初期化
        if os.path.exists(self.token_path):
            with open(self.token_path, "rb") as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            elif os.path.exists(self.credentials_path):
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            with open(self.token_path, "wb") as token:
                pickle.dump(self.creds, token)

        if self.creds and self.creds.valid:
            self.drive_service = build("drive", "v3", credentials=self.creds)
            self.sheets_service = build("sheets", "v4", credentials=self.creds)
        else:
            print("Drive or Sheets auth failed.")

    # 新しいスプレッドシートを作成するメソッド
    def create_spreadsheet(self, title):
        if not self.sheets_service:
            print("Sheets service is not available.")
            return None

        spreadsheet = {"properties": {"title": title}}

        request = (
            self.sheets_service.spreadsheets()
            .create(body=spreadsheet, fields="spreadsheetId")
            .execute()
        )
        spreadsheet_id = request.get("spreadsheetId")
        print(f"Spreadsheet created with ID: {spreadsheet_id}")
        return spreadsheet_id

    # ファイルの移動をするメソッド
    def move_files(self):
        folder_id = os.environ["BOOKWALKER_FOLDER_ID"]
        file_id = input("Please enter the file ID: ")
        file_metadata = {"parents": [folder_id]}
        self.drive_service.files().update(
            fileId=file_id,
            addParents=folder_id,
            removeParents="root",
            fields="id, parents",
        ).execute()

    # 特定のフォルダのスプレッドシートを取得するメソッド
    def get_spreadsheet(self, folder_id):
        if not self.drive_service:
            print("Drive service is not available.")
            return None

        results = (
            self.drive_service.files()
            .list(
                q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'",
                fields="files(id, name)",
            )
            .execute()
        )
        items = results.get("files", [])

        if not items:
            print("No files found.")
        else:
            print("Files:")
            for item in items:
                print(f"{item['name']} ({item['id']})")
        return items


if __name__ == "__main__":
    main()
