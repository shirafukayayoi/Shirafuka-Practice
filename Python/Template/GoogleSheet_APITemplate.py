import os
import pickle
import time

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# スコープ設定
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def main():
    spreadsheet_url = input("スプレッドシートのURLを入力してください: ")
    spreadsheet_id = spreadsheet_url.split("/")[-2]
    google_spreadsheet = GoogleSpreadSheet(spreadsheet_id)
    google_spreadsheet.get_column_data("A")


class GoogleSpreadSheet:
    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        self.creds = None

        # token.pickleが存在する場合はそれを読み込み、認証情報を再利用
        if os.path.exists("token.pickle"):
            with open("token.pickle", "rb") as token:
                self.creds = pickle.load(token)

        # 認証情報がない場合、または無効な場合、再認証を行う
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # 新しい認証情報をtoken.pickleに保存
            with open("token.pickle", "wb") as token:
                pickle.dump(self.creds, token)

        # Google Sheets APIのサービスを作成
        self.service = build("sheets", "v4", credentials=self.creds)

    def get_column_data(self, column):  # 特定の列のデータを取得する
        sheet_name = self.get_sheet_name()

        # リクエスト間隔を設ける
        time.sleep(1)  # 1秒待機

        # 指定された列のデータを取得
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{sheet_name}!{column}:{column}",  # A列を取得
                )
                .execute()
            )

            data = result.get("values", [])

            # データの存在チェック
            if data:
                print("取得したデータ:")
                for row in data:
                    print(row)
            else:
                print("指定した列にはデータがありません。")
        except Exception as e:
            print(f"データ取得中にエラーが発生しました: {e}")

    def get_sheet_name(self):  # 特定のスプレッドシートのシート名を取得する
        try:
            result = (
                self.service.spreadsheets()
                .get(spreadsheetId=self.spreadsheet_id)
                .execute()
            )

            sheet_name = result["sheets"][0]["properties"]["title"]
            print(f"取得したシート名: {sheet_name}")
            return sheet_name
        except Exception as e:
            print(f"シート名の取得中にエラーが発生しました: {e}")
            return None

    def write_data(self):  # データを書き込む
        data = ["Hello", "World"]  # デモ用のデータ

        # データを書き込む
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=self.spreadsheet_id,
                    range="Sheet1!A1",  # 書き込む範囲
                    valueInputOption="RAW",
                    body={"values": [data]},
                )
                .execute()
            )
            print(f"データが書き込まれました: {result}")
        except Exception as e:
            print(f"データ書き込み中にエラーが発生しました: {e}")


if __name__ == "__main__":
    main()
