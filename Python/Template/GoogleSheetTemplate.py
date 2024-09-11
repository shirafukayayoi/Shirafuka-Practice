import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
import gspread
from dotenv import load_dotenv

load_dotenv()

def main():
    spreadsheet = GoogleSpreadsheet()
    spreadsheet.read_data()

# スプレッドシートだけを扱うクラス
class GoogleSpreadsheet:
    def __init__(self, spreadsheet_id):
        self.scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        self.creds = Credentials.from_service_account_file('credentials.json', scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
        self.sheet = self.spreadsheet.sheet1  # 最初のシートにアクセス

class GoogleSpreadsheet_Drive:
    SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']

    def __init__(self, token_path='token.pickle', credentials_path='client_secret.json'):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.sheet_creds = Credentials.from_service_account_file('sheet_credentials.json', scopes=self.SCOPES)
        self.sheetclient = gspread.authorize(self.sheet_creds)
        self.spreadsheet = self.sheetclient.open_by_url(os.environ["TEMPLETE_GOOGLE_SHEET_URL"])
        self.sheet = self.spreadsheet.sheet1
        self.drive, self.sheets = self.authenticate_and_init_services()

    def authenticate_and_init_services(self):
        """認証とサービス初期化を1つにまとめたメソッド"""
        creds = None
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
            creds = flow.run_local_server(port=0)
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        if creds and creds.valid:
            drive = build('drive', 'v3', credentials=creds)
            sheets = build('sheets', 'v4', credentials=creds)
            return drive, sheets
        else:
            print('Drive or Sheets auth failed.')
            return None, None

    def get_drive_service(self):
        return self.drive if self.drive else print('Drive service is not available.')

    def get_sheets_service(self):
        return self.sheets if self.sheets else print('Sheets service is not available.')

    # Googleスプレッドシートを作成する
    def create_spreadsheet(self, title):
        if not self.sheets:
            print('Sheets service is not available.')
            return None

        spreadsheet = {
            'properties': {
                'title': title
            }
        }

        request = self.sheets.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        spreadsheet_id = request.get('spreadsheetId')
        print(f'スプレットシートid: {spreadsheet_id}')
        return spreadsheet_id
        

    # Googleスプレッドシートにデータを読み込む
    def read_data(self):
        print(self.sheet.get_all_values()) 

    # Googleスプレッドシートの全てのデータを消す
    def clear_data(self, spreadsheet_id):
        sheet = self.client.open_by_key(spreadsheet_id).sheet1
        sheet.clear()

    # Googleスプレッドシートにデータを書き込む
    def write_data(self, spreadsheet_id, data):
        sheet = self.client.open_by_key(spreadsheet_id).sheet1
        sheet.append_row(data)

    # Googleスプレッドシートの1行目だけ書き込む
    def write_header(self, spreadsheet_id, data):
        sheet = self.client.open_by_key(spreadsheet_id).sheet1
        sheet.insert_row(data, 1)

    # フィルターを設定する
    def AutoFilter(self, spreadsheet_id):
        sheet = self.client.open_by_key(spreadsheet_id).sheet1
        last_column_num = len(sheet.row_values(1))
        print(f"最終列は{last_column_num}です")

        def num2alpha(num):
            if num <= 26:
                return chr(64 + num)
            elif num % 26 == 0:
                return num2alpha(num // 26 - 1) + chr(90)
            else:
                return num2alpha(num // 26) + chr(64 + num % 26)

        last_column_alp = num2alpha(last_column_num)
        print(f'最終列のアルファベットは{last_column_alp}です')
        sheet.set_basic_filter(f'A1:{last_column_alp}1')
        print("フィルターを設定しました")

if __name__ == '__main__':
    main()
