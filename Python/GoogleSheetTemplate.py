import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os

load_dotenv()

def main():
    spreadsheet = GoogleSpreadsheet()   # initを実行するために必要
    spreadsheet.get_last_column_and_convert_to_alpha()
    

# 認証情報を使ってGoogleスプレッドシートにアクセスするクラス
class GoogleSpreadsheet:
    def __init__(self):
        self.scope = ['https://spreadsheets.google.com/feeds',
                        'https://www.googleapis.com/auth/drive']
        self.creds = Credentials.from_service_account_file('credentials.json', scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        self.spreadsheet = self.client.open_by_url(os.environ["TEMPLETE_GOOGLE_SHEET_URL"])
        self.sheet = self.spreadsheet.sheet1  # 最初のシートにアクセス
        print("Google Spreadsheetに接続しました")

    # Googleスプレッドシートにデータを読み込む
    def read_data(self):
        print(self.sheet.get_all_values()) 

    # Googleスプレッドシートの全てのデータを消す
    def clear_data(self):
        self.sheet.clear()
    
    # Googleスプレッドシートにデータを書き込む
    def write_data(self, data):
        self.sheet.append_row(data)
    
    # Googleスプレッドシートの1行目だけ書き込む
    def write_header(self, data):
        self.sheet.insert_row(data, 1)  # 1の値を変えると行を指定できる

    # フィルターを設定する
    def get_last_column_and_convert_to_alpha(self):
        # 最終列の数値を取得
        last_column_num = len(self.sheet.row_values(1))
        print(f"最終列は{last_column_num}です")
        
        # 数値からアルファベットを求める内部関数
        def num2alpha(num):
            if num <= 26:
                return chr(64 + num)
            elif num % 26 == 0:
                return num2alpha(num // 26 - 1) + chr(90)
            else:
                return num2alpha(num // 26) + chr(64 + num % 26)
        
        # 最終列を数値→アルファベットへ変換
        last_column_alp = num2alpha(last_column_num)
        print(f'最終列のアルファベットは{last_column_alp}です')
        self.sheet.set_basic_filter(name=(f'A:{last_column_alp}'))
        print("フィルターを設定しました")

if __name__ == "__main__":
    main()