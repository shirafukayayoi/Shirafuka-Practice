import json
import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()


def load_calendar_id(category_name: str = "", legacy_key: str = "") -> str:
    calendar_ids_path = (
        Path(__file__).resolve().parent.parent / "tokens" / "calendar_ids.json"
    )
    if not calendar_ids_path.exists():
        raise FileNotFoundError(
            f"カレンダーID設定ファイルが見つかりません: {calendar_ids_path}"
        )

    with calendar_ids_path.open("r", encoding="utf-8") as f:
        calendar_ids = json.load(f)

    if isinstance(calendar_ids, dict) and isinstance(
        calendar_ids.get("calendar_map"), dict
    ):
        if category_name:
            mapped_id = calendar_ids["calendar_map"].get(category_name)
            if mapped_id:
                return mapped_id
        default_id = calendar_ids.get("default_calendar_id")
        if default_id:
            return default_id

    calendar_id = ""
    if legacy_key:
        calendar_id = calendar_ids.get(legacy_key, "")
    if not calendar_id and category_name:
        calendar_id = calendar_ids.get(category_name, "")
    if not calendar_id:
        calendar_id = calendar_ids.get("default", "")
    if not calendar_id:
        raise KeyError(
            f"calendar_ids.json に '{category_name or legacy_key}' または default_calendar_id/default が設定されていません。"
        )
    return calendar_id


def main():
    url = input("URLを入力してください: ")
    webscraping = Webscraping(url)
    book_title, formatted_date = webscraping.get_html()
    google_calendar = GoogleCalendar()
    google_calendar.add_event(book_title, formatted_date)


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
            book_title_element = html_soup.select_one(".p-main__title")
            date_element = html_soup.select_one(".p-action-box__info-schedule.nowrap")

            if book_title_element and date_element:
                book_title = book_title_element.text
                date_text = date_element.text

                # 正規表現を使用して日付を抽出
                date_match = re.search(r"(\d{4})/(\d{2})/(\d{2})", date_text)
                if date_match:
                    year, month, day = date_match.groups()
                    formatted_date = f"{year}-{month}-{day}"
                    print(f"[Info] タイトル: {book_title}, 日付: {formatted_date}")
                else:
                    print("[Error] 日付のフォーマットが認識できませんでした。")
            else:
                print("[Error] 指定された要素が見つかりませんでした。")
        except Exception as e:
            print(f"[Error] エラーが発生しました: {e}")
        return book_title, formatted_date


class GoogleCalendar:
    def __init__(self):
        self.calendar_id = load_calendar_id(
            category_name="ラノベ・漫画カレンダー", legacy_key="bookwalker"
        )
        self.creds = None  # 認証情報の初期化

        if os.path.exists(
            "tokens/calendar_token.json"
        ):  # credentials.json ファイルに保存された認証情報をロードする
            self.creds = Credentials.from_authorized_user_file(
                "tokens/calendar_token.json"
            )  # 認証情報(calendar_token.json)がない場合や期限切れの場合は、ユーザーに認証を求める
        if (
            not self.creds or not self.creds.valid
        ):  # cerds.validはtrueかfalseを返し、切れている場合はtrue
            if (
                self.creds and self.creds.expired and self.creds.refresh_token
            ):  # tokenがあった場合、期限切れかどうかを確認
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(  # tokenがない場合、認証を行う
                    "tokens/credentials.json",
                    ["https://www.googleapis.com/auth/calendar.events"],
                )
                self.creds = flow.run_local_server(port=0)
            # 認証情報を保存する
            with open("tokens/calendar_token.json", "w") as token:
                token.write(
                    self.creds.to_json()
                )  # 認証情報が入っているself.credsをjson形式に変換して保存する
        self.service = build("calendar", "v3", credentials=self.creds)
        print("[Info] Google Calendarに接続しました")

    def add_event(self, book_title, formatted_date):
        event = {
            "summary": book_title,
            "start": {"date": formatted_date, "timeZone": "Asia/Tokyo"},
            "end": {"date": formatted_date, "timeZone": "Asia/Tokyo"},
        }
        self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
        print("[Info] Google Calendarにイベントを追加しました。")


if __name__ == "__main__":
    main()
