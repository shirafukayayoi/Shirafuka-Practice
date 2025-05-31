import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()


def main():
    url = input("URLを入力してください: ")
    webscraping = Webscraping(url)
    game_title, formatted_date = webscraping.get_html()
    print(f"タイトル: {game_title}, 日付: {formatted_date}")
    # google_calendar = GoogleCalendar()
    # google_calendar.Add_event(game_title, formatted_date, url)


class Webscraping:
    def __init__(self, url):
        self.url = url
        self.session = requests.session()

    def get_html(self):
        try:
            response = self.session.get(self.url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"[Error] エラーが発生しました: {e}")
            return

        response.encoding = response.apparent_encoding
        html_soup = BeautifulSoup(response.text, "html.parser")

        try:
            # 指定されたクラスのリンクを探す
            button = html_soup.find(
                "div", class_="turtle-component turtle-Button large fill css-w5doa7"
            )
            if button:
                link = button.find("a")
                if link and "href" in link.attrs:
                    href = link["href"]
                    print(f"リンクをクリックします: {href}")
                    # 抽出したリンクにアクセス
                    h_soup = BeautifulSoup(
                        self.session.get(href).content, "html.parser"
                    )
                    title = h_soup.title.string
                    print(f"ページのタイトル: {title}")
                    print(self.session.cookies.get_dict())
                    game_title_element = h_soup.select_one(".productTitle__headline")
                    date_element = h_soup.select_one(
                        ".contentsDetailBottom__tableDataRight p"
                    )

                    if game_title_element and date_element:
                        game_title = game_title_element.text
                        date_text = date_element.text.strip()

                        # 日付のフォーマットを変換
                        date_match = re.search(r"(\d{4})/(\d{2})/(\d{2})", date_text)
                        if date_match:
                            year, month, day = date_match.groups()
                            formatted_date = f"{year}-{month}-{day}"
                            print(f"タイトル: {game_title}, 日付: {formatted_date}")
                            return game_title, formatted_date
                        else:
                            print("[Error] 日付のフォーマットが認識できませんでした。")
                    else:
                        print("[Error] ゲームタイトルまたは日付が見つかりませんでした。")
                else:
                    print("[Error] リンクが見つかりませんでした")
            else:
                print("[Error] 指定されたクラスのボタンが見つかりませんでした")
        except Exception as e:
            print(f"エラーが発生しました: {e}")

    def access_link(self, href):
        try:
            response = self.session.get(href)
            response.raise_for_status()
            print("[Info] リンクにアクセスしました")
        except requests.exceptions.RequestException as e:
            print(f"リンクへのアクセスでエラーが発生しました: {e}")


class GoogleCalendar:
    def __init__(self):
        self.creds = None  # 認証情報の初期化
        if os.path.exists(
            "tokens/calendar_token.json"
        ):  # credentials.json ファイルに保存された認証情報をロードする
            self.creds = Credentials.from_authorized_user_file("tokens/calendar_token.json")

        # 認証情報(calendar_token.json)がない場合や期限切れの場合は、ユーザーに認証を求める
        if (
            not self.creds or not self.creds.valid
        ):  # cerds.validはtrueかfalseを返し、切れている場合はtrue
            if (
                self.creds and self.creds.expired and self.creds.refresh_token            ):  # tokenがあった場合、期限切れかどうかを確認
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(  # tokenがない場合、認証を行う
                    "tokens/credentials.json",
                    ["https://www.googleapis.com/auth/calendar.events"],
                )
                self.creds = flow.run_local_server(port=0)
            # 認証情報を保存する
            with open("tokens/calendar_token.json", "w") as token:                token.write(
                    self.creds.to_json()
                )  # 認証情報が入っているself.credsをjson形式に変換して保存する
        self.service = build("calendar", "v3", credentials=self.creds)
        print("[Info] Google Calendarに接続しました")

    def Add_event(self, game_title, formatted_date, url):
        event = {
            "summary": game_title,
            "description": url,
            "start": {"date": formatted_date, "timeZone": "Asia/Tokyo"},
            "end": {"date": formatted_date, "timeZone": "Asia/Tokyo"},
        }
        self.service.events().insert(
            calendarId=os.getenv("OTAKATU_GOOGLECALENDAR_ID"), body=event
        ).execute()
        print("[Info] Google Calendarにイベントを追加しました。")


if __name__ == "__main__":
    main()
