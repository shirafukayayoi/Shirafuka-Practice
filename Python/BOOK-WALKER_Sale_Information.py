import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
import gspread
import time
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

def main():
    today = datetime.today().strftime('%Y-%m-%d')
    count = 0
    order = input("ジャンルはなんですか？（ローマ字で）")
    Filetitle = f"BookWalker_{today}_{order}_SalesList"
    folder_id = os.environ['BOOKWALKER_FOLDER_ID']

    scraping = WebScraping()
    data = scraping.get_html()
    spreadsheet = GoogleSpreadsheet()
    if data:
        spreadsheet.get_drive_service()
        spreadsheet.create_spreadsheet(Filetitle, data, count, folder_id)
        spreadsheet.AutoFilter()
        discord = discord_send_message()
        discord.send_message(f"BookWalkerのセール情報をGoogleスプレットシートに書き込みました:\nhttps://docs.google.com/spreadsheets/d/{spreadsheet.spreadsheet_id}")

class WebScraping:
    def __init__(self):
        self.base_url = input("URLを入力してください: ")
        self.endpage = 0
        self.title_list = []
        self.author_list = []
        self.money_list = []
        self.label_list = []
        self.enddate_list = []
        self.query_params = {
            "page": "{}"
        }
        self.session = requests.Session()
        retry = Retry(connect=5, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def get_html(self):
        try:
            req = self.session.get(self.base_url)
            req.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"初回リクエストでエラーが発生しました: {e}")
            return

        req.encoding = req.apparent_encoding
        html_soup = BeautifulSoup(req.text, "html.parser")

        # ページ数を取得
        pager_boxes = html_soup.find_all(class_="o-pager-box-num")
        if pager_boxes:
            # 最後のページ番号を取得
            self.endpage = int(pager_boxes[-1].get_text())
        else:
            print("ページ数を取得できませんでした")
            return

        # 各ページのデータを取得
        for page in range(1, int(self.endpage) + 1):
            self.query_params["page"] = str(page)
            url = self.base_url + "&" + urlencode(self.query_params)
            try:
                req = self.session.get(url)
                req.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"{page}ページ目のリクエストでエラーが発生しました: {e}")
                continue

            req.encoding = req.apparent_encoding
            html_soup = BeautifulSoup(req.text, "html.parser")
            titles = html_soup.find_all(class_="o-card-ttl__text")
            authors = html_soup.find_all('a', {'data-action-label': '著者名'})
            moneys = html_soup.find_all(class_="m-book-item__price-num")
            labels = html_soup.find_all('a', {'data-action-label': 'レーベル名'})
            enddates = html_soup.find_all(class_="a-card-period")

            if titles and authors and labels and enddates and moneys:
                for title, author, label, enddate, money in zip(titles, authors, labels, enddates, moneys):
                    self.title_list.append(title.get_text().strip())
                    self.author_list.append(author.get_text().strip())
                    self.label_list.append(label.get_text().strip())
                    
                    # 日付のフォーマット変換
                    formatted_date = self.format_date(enddate.get_text().strip())
                    self.enddate_list.append(formatted_date)
                    
                    # お金の額の処理
                    money_text = money.get_text().strip()
                    # カンマや円記号を取り除く
                    money_text = money_text.replace(',', '').replace('¥', '')
                    try:
                        money_value = float(money_text)
                    except ValueError:
                        money_value = 0.0  # 数値変換に失敗した場合は0.0を設定

                    self.money_list.append(money_value)
                    
                    print(f"{len(self.enddate_list)}件目のデータを取得しました")


        # データの総数を表示
        print(f"タイトルの数: {len(self.title_list)}")
        print(f"著者の数: {len(self.author_list)}")
        print(f"レーベルの数: {len(self.label_list)}")
        print(f"終了日の数: {len(self.enddate_list)}")

        data = [(self.title_list[i], self.author_list[i], self.money_list[i], self.label_list[i], self.enddate_list[i]) for i in range(len(self.title_list))]
        return data
    
    def format_date(self, date_str):
        input_date = date_str.split('(')[0]
        try:
            date_obj = datetime.strptime(input_date, '%Y/%m/%d')
            formatted_date = date_obj.strftime('%Y-%m-%d')
        except ValueError:
            print(f"日付のパースに失敗しました: {date_str}")
        return formatted_date

class GoogleSpreadsheet:
    SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']

    def __init__(self, token_path='token.pickle', credentials_path='client_secret.json'):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.sheet_creds = Credentials.from_service_account_file('sheet_credentials.json', scopes=self.SCOPES)
        self.creds = None
        self.drive = None
        self.sheetclient = gspread.authorize(self.sheet_creds)
        self.sheet = None  # 最初のシートにアクセス
        self.client = None 
        self.spreadsheet_id = None
        self.authenticate()

    def authenticate(self):
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            elif os.path.exists(self.credentials_path):
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)

        if self.creds and self.creds.valid:
            self.drive = build('drive', 'v3', credentials=self.creds)
            self.sheets = build('sheets', 'v4', credentials=self.creds)
            self.client = gspread.authorize(self.creds)
        else:
            print('Drive or Sheets auth failed.')

    def get_drive_service(self):
        """Google Drive APIのサービスインスタンスを返すメソッド"""
        if self.drive:
            return self.drive
        else:
            print('Drive service is not available.')
            return None

    def get_sheets_service(self):
        """Google Sheets APIのサービスインスタンスを返すメソッド"""
        if self.sheets:
            return self.sheets
        else:
            print('Sheets service is not available.')
            return None

    def create_spreadsheet(self, title, data, count, folder_id):
        if not self.sheets:
            print('Sheets service is not available.')
            return None

        if not self.drive:
            print('Drive service is not available.')
            return None

        # スプレッドシートの作成
        spreadsheet = {
            'properties': {
                'title': title
            }
        }
        request = self.sheets.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        spreadsheet_id = request.get('spreadsheetId')
        print(f'Spreadsheet ID: {spreadsheet_id}')

        # フォルダIDに移動するためのファイルアップデート
        file_metadata = {
            'parents': [folder_id]
        }
        self.drive.files().update(
            fileId=spreadsheet_id,
            addParents=folder_id,
            removeParents='root',
            fields='id, parents'
        ).execute()

        self.spreadsheet_id = spreadsheet_id
        sheet = self.client.open_by_key(spreadsheet_id).sheet1
        sheet.insert_row(['タイトル', '著者', '価格', 'レーベル', '終了日'], 1)
        for row in data:
            time.sleep(1)
            sheet.append_row(row)
            count += 1
            print(row)
        print(f"{count}回データを書き込みました。")
        return self.spreadsheet_id

    # フィルターの設定
    def AutoFilter(self):
        self.sheet = self.client.open_by_key(self.spreadsheet_id).sheet1
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
    
class discord_send_message:
    def __init__(self):
        self.discord_webhook_url = os.environ['DISCORD_WEBHOOK_URL']

    def send_message(self, message):
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "content": message
        }
        response = requests.post(self.discord_webhook_url, headers=headers, data=json.dumps(data))
        print(response.status_code)
if __name__ == "__main__":
    main()
