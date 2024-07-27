import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os

load_dotenv()

def main():
    spreadsheet = GoogleSpreadsheet()
    spreadsheet.read_data()

class GoogleSpreadsheet:
    def __init__(self):
        self.scope = ['https://spreadsheets.google.com/feeds',
                        'https://www.googleapis.com/auth/drive']
        self.creds = Credentials.from_service_account_file('credentials.json', scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        self.spreadsheet = self.client.open_by_url(os.environ["TEMPLETE_GOOGLE_SHEET_ID"])
        self.sheet = self.spreadsheet.sheet1  # 最初のシートにアクセス
        print("Google Spreadsheetに接続しました")

    # Googleスプレッドシートにデータを読み込む
    def read_data(self):
        print(self.sheet.get_all_values()) 

if __name__ == "__main__":
    main()