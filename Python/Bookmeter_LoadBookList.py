import os
import time

import gspread
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()


class WebScraping:
    def __init__(self, url, spreadsheet_id):
        self.url = url
        self.session = requests.Session()  # Sessionオブジェクトを初期化
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
        }
        self.data = []
        self.all_links = []
        self.spreadsheet = GoogleSpreadsheet(spreadsheet_id)

    def get_html(self, spreadsheet_id):
        # 初回リクエスト処理
        try:
            req = self.session.get(self.url, headers=self.headers)
            req.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"初回リクエストでエラーが発生しました: {e}")
            return

        req.encoding = req.apparent_encoding
        html_soup = BeautifulSoup(req.text, "html.parser")

        # ページリンクの取得
        try:
            pagination_links = html_soup.find_all("a", class_="bm-pagination__link")
            last_page_link = pagination_links[-1].get("href")

            if "page=" in last_page_link:
                last_page_number = last_page_link.split("page=")[-1]
            else:
                print("ページ番号が見つかりませんでした")
        except Exception:
            print("ページリンクの取得に失敗しました")
            return

        # 各ページのリンクを取得して処理
        for i in range(1, int(last_page_number) + 1):
            page_url = self.url + f"?page={i}"

            # リトライ処理の統合
            for attempt in range(3):  # 最大3回リトライ
                try:
                    req = self.session.get(page_url, headers=self.headers)
                    req.raise_for_status()
                    break  # 成功したらループを抜ける
                except requests.exceptions.RequestException as e:
                    print(f"ページリクエストでエラーが発生しました: {e}")
                    if attempt < 2:  # リトライの余地があれば待機
                        print(f"5秒後に再試行します...")
                        time.sleep(5)
                    else:
                        print("最大試行回数に達しました。次のページに進みます。")
                        req = None
                        break

            if req is None:
                continue  # リトライ後も失敗した場合は次のページへ

            req.encoding = req.apparent_encoding
            page_soup = BeautifulSoup(req.text, "html.parser")

            # <div class="detail__title"> 内の <a> タグを探す
            detail_divs = page_soup.find_all("div", class_="detail__title")

            for div in detail_divs:
                a_tag = div.find("a")
                if a_tag and a_tag.get("href"):
                    href = a_tag.get("href")
                    base_link = "https://bookmeter.com" + href
                    self.all_links.append(base_link)
                else:
                    print("hrefが存在しません")

        for link in self.all_links:
            try:
                time.sleep(5)
                req = self.session.get(link, headers=self.headers)
                req.raise_for_status()
                req.encoding = req.apparent_encoding
            except requests.exceptions.RequestException as e:
                print(f"リンクリクエストでエラーが発生しました: {e}")
                continue
            html_soup = BeautifulSoup(req.text, "html.parser")

            title_text = html_soup.find("h1", class_="inner__title")
            if title_text:
                title = title_text.text.split(" (", 1)[0]  # タイトル部分だけを取得

            authors_elements = html_soup.select(
                "ul.header__authors a"
            )  # 著者リンクのセレクタ
            authors = (
                authors_elements[0].text if authors_elements else "著者不明"
            )  # authors_elements[0].textで取得、なかった場合はelse

            # ページ数を取得するロジック
            page_number = int(
                html_soup.find("dt", string="ページ数")
                .find_next_sibling("dd")
                .find("span")
                .text
            )

            # リンク処理の修正
            link_samples = [
                a["href"]
                for a in html_soup.find_all("a", href=True)
                if "bookwalker.jp" in a["href"]
            ]
            links = (
                link_samples[0].split("?")[0] if link_samples else ""
            )  # 最初のリンクのみを処理

            self.data.append([title, authors, page_number, links])
            print(title, authors, page_number, links)
        self.spreadsheet.write_data(self.data)
        self.spreadsheet.AutoFilter(spreadsheet_id)


class GoogleSpreadsheet:
    def __init__(self, spreadsheet_id):
        self.scope = ["https://www.googleapis.com/auth/spreadsheets"]
        self.creds = None
        if os.path.exists("sheet_token.json"):
            self.creds = Credentials.from_authorized_user_file(
                "sheet_token.json", self.scope
            )
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", self.scope
                )
                self.creds = flow.run_local_server(port=0)
            with open("sheet_token.json", "w") as token:
                token.write(self.creds.to_json())
        self.client = gspread.authorize(self.creds)
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
        self.sheet = self.spreadsheet.sheet1  # 最初のシートにアクセス
        self.sheet.clear()  # シートをクリア
        self.sheet.insert_row(["タイトル", "著者", "ページ数", "URL"], 1)

    def write_data(self, data):
        self.sheet.append_rows(data)

    def AutoFilter(self, spreadsheet_id):
        sheet = self.client.open_by_key(spreadsheet_id).sheet1
        last_column_num = len(sheet.row_values(1))  # 列数を取得

        def num2alpha(num):
            alphabet = ""
            while num > 0:
                num, remainder = divmod(num - 1, 26)
                alphabet = chr(65 + remainder) + alphabet
            return alphabet

        last_column_alp = num2alpha(last_column_num)  # 列をアルファベットに変換
        print(f"最後の列: {last_column_alp}")  # デバッグ用出力
        sheet.set_basic_filter(f"A1:{last_column_alp}1")  # 範囲を指定してフィルター設定


if __name__ == "__main__":
    url = input("読書メーターのURLを入力してください: ")
    spreadsheet_id = "1BaWrynhH4oYqd1UcmKeGTN81fC_huPHbLGXcl06nIRQ"

    web_scraping = WebScraping(url, spreadsheet_id)
    web_scraping.get_html()
