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
import time
from dotenv import load_dotenv
import os
import requests
import discord
import sys

load_dotenv()

def main():
    today = datetime.today().strftime('%Y-%m-%d')
    count = 0
    order = input("ジャンルはなんですか？（ローマ字で）")
    Filetitle = f"BookWalker_{today}_{order}_SalesList"
    folder_id = os.environ['BOOKWALKER_FOLDER_ID']

    scraping = WebScraping()
    data = scraping.get_html()
    spreadsheet = GoogleDriveAuth()
    if data:
        spreadsheet.get_drive_service()
        spreadsheet.create_spreadsheet(Filetitle, data, count, folder_id)
        spreadsheet.AutoFilter()
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.spreadsheet_id}"
        discord_bot = DiscordBOT(os.environ['DISCORD_TOKEN'])
        discord_bot.run(sheet_url, count)
    sys.exit()

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
class GoogleDriveAuth:
    SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']

    def __init__(self, token_path='token.pickle', credentials_path='credentials.json'):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.creds = None
        self.drive_service = None
        self.sheets_service = None

        # OAuth2認証とサービスインスタンスの初期化
        self.authenticate()

    def authenticate(self):
        """OAuth2 認証を行い、Drive API と Sheets API のサービスを初期化"""
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            elif os.path.exists(self.credentials_path):
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
                self.creds = flow.run_local_server(port=0)  # 認証フローを実行
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)

        # サービスの初期化
        if self.creds and self.creds.valid:
            self.drive_service = build('drive', 'v3', credentials=self.creds)
            self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        else:
            print('Drive or Sheets auth failed.')

    def create_spreadsheet(self, title, folder_id):
        """新しいスプレッドシートを作成し、指定したフォルダに移動"""
        now = datetime.now().strftime('%Y-%m-%d')
        if self.sheets_service is None:
            print("Sheets serviceが初期化されていません。")
            return None
        
        # スプレッドシート作成
        spreadsheet = {
            'properties': {
                'title': f"{now}_{title}"
            }
        }

        request = self.sheets_service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        spreadsheet_id = request.get('spreadsheetId')
        print(f'Spreadsheet created with ID: {spreadsheet_id}')

        # フォルダに移動
        file_metadata = {
            'parents': [folder_id]
        }

        self.drive_service.files().update(
            fileId=spreadsheet_id,
            addParents=folder_id,
            removeParents='root',
            fields='id, parents'
        ).execute()

        return spreadsheet_id

    def write_data(self, spreadsheet_id, data):
        """スプレッドシートにデータを書き込む"""
        if self.sheets_service is None:
            print("Sheets serviceが初期化されていません。")
            return None

        # データ書き込み
        body = {
            'values': data
        }

        result = self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='Sheet1!A1',
            valueInputOption='RAW',
            body=body
        ).execute()

        print(f"{result.get('updatedCells')} cells updated.")

    def AutoFilter(self, spreadsheet_id, data):
        """スプレッドシートにフィルターを設定する"""
        if self.sheets_service is None:
            print("Sheets serviceが初期化されていません。")
            return None

        # シートの情報を取得
        spreadsheet = self.sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_name = spreadsheet['sheets'][0]['properties']['title']
        sheet_id = spreadsheet['sheets'][0]['properties']['sheetId']

        # 最終列の計算（data の最初の要素の長さで判断）
        last_column_num = len(data[0]) if data else 3
        print(f"最終列は{last_column_num}です")

        # 列番号をアルファベットに変換
        def num2alpha(num):
            if num <= 26:
                return chr(64 + num)
            elif num % 26 == 0:
                return num2alpha(num // 26 - 1) + chr(90)
            else:
                return num2alpha(num // 26) + chr(64 + num % 26)

        last_column_alp = num2alpha(last_column_num)
        print(f'最終列のアルファベットは{last_column_alp}です')

        # フィルターを設定するリクエスト
        requests = [{
            'setBasicFilter': {
                'filter': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': len(data) + 1,  # 行数の指定（ヘッダー行を含むため +1）
                        'startColumnIndex': 0,
                        'endColumnIndex': last_column_num
                    }
                }
            }
        }]

        # リクエストをGoogle Sheets APIに送信
        body = {
            'requests': requests
        }

        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        print("フィルターを設定しました")

class DiscordBOT:
    def __init__(self, token):
        self.token = token
        self.channel_id = "1279375531992682556"

        # Intents を設定
        self.intents = discord.Intents.default()
        self.intents.message_content = True  # メッセージの内容を受け取るための設定

        self.bot = discord.Client(intents=self.intents)

    async def send_message(self, message):
        channel = self.bot.get_channel(int(self.channel_id))
        if channel:
            await channel.send(message)
            print("メッセージを送信しました")
        else:
            print("チャンネルが見つかりませんでした")

    def run(self, sheet_url, count):
        @self.bot.event
        async def on_ready():
            print(f'Logged in as {self.bot.user} (ID: {self.bot.user.id})')
            await self.send_message(f"BOOK☆WALKERのセールリストを取得、{count}回書き込みました:\n{sheet_url}")
        self.bot.run(self.token)

if __name__ == "__main__":
    main()