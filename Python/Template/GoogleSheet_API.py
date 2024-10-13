import time

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


def main():
    spreadsheet_url = input("スプレッドシートのURLを入力してください: ")
    spreadsheet_id = spreadsheet_url.split("/")[-2]
    google_spreadsheet = GoogleSpreadSheet(spreadsheet_id)
    google_spreadsheet.get_column_data("A")


class GoogleSpreadSheet:
    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        self.creds = Credentials.from_service_account_file("service_token.json")
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

        spreadsheet = (
            self.client.spreadsheets().get(spreadsheetId=self.sheet_url).execute()
        )  # 認証を行い、スプレッドシートの情報を取得
        sheet_name = self.get_sheet_name()

        result = (
            self.service.spreadsheets()
            .values()
            .update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption="RAW",
                body={"values": [data]},
            )
            .execute()
        )


if __name__ == "__main__":
    main()
