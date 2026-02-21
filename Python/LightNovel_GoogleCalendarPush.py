import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 環境変数のロード
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
    manager = LightNovelEventManager()

    total_novels = 0

    for page in range(1, 6):
        page_novels = manager.process_page(page)
        total_novels += page_novels

    manager.send_to_discord(
        f"合計 {total_novels} 件のライトノベル情報がGoogleカレンダーに追加されました。"
    )


class LightNovelEventManager:
    def __init__(self):
        self.year = 2024
        self.month = 10
        self.calendar_id = load_calendar_id(
            category_name="ラノベ・漫画カレンダー", legacy_key="lightnovel"
        )
        self.discord_webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
        self.creds = self.authenticate_google()
        self.service = build("calendar", "v3", credentials=self.creds)

    def send_to_discord(self, message):
        data = {"content": message}
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(
                self.discord_webhook_url, data=json.dumps(data), headers=headers
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Discordへの送信に失敗しました: {e}")

    def authenticate_google(self):
        creds = None
        if os.path.exists("tokens/token.json"):
            creds = Credentials.from_authorized_user_file("tokens/token.json")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json",
                    ["https://www.googleapis.com/auth/calendar.events"],
                )
                creds = flow.run_local_server(port=0)
            with open("tokens/token.json", "w") as token:
                token.write(creds.to_json())

        return creds

    def convert_japanese_date(self, japanese_date_str):
        if "上旬" in japanese_date_str:
            return f"{self.year}-{self.month:02}-01"
        try:
            date_obj = datetime.strptime(japanese_date_str, "%m月 %d日")
            return date_obj.replace(year=self.year).strftime("%Y-%m-%d")
        except ValueError:
            return ""

    def get_events(self, time_min=None, time_max=None):
        events_result = (
            self.service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return events_result.get("items", [])

    def check_duplicate(self, event_date, title):
        time_min = (
            datetime.strptime(event_date, "%Y-%m-%d") - timedelta(days=1)
        ).strftime("%Y-%m-%d") + "T00:00:00Z"
        time_max = event_date + "T00:00:00Z"
        events = self.get_events(time_min, time_max)
        return any(
            event["summary"] == title and "date" in event["start"] for event in events
        )

    def fetch_titles_and_dates(self, html_soup):
        titles = html_soup.find_all(class_="item-title__text")
        dates = html_soup.find_all(class_="item-release__date")
        media_items = html_soup.find_all(class_="item-title__media")

        title_list = [title.get_text().strip() for title in titles]
        date_list = [date.get_text().strip() for date in dates]
        media_list = [media.get_text().strip() for media in media_items]

        return title_list, date_list, media_list

    def process_page(self, page):
        base_url = "https://books.rakuten.co.jp/calendar/001017/monthly/"
        query_params = {
            "tid": f"{self.year}-{self.month:02}-01",
            "p": str(page),
            "s": "14",
            "#rclist": "",
        }
        url = base_url + "?" + urlencode(query_params)

        try:
            req = requests.get(url)
            req.raise_for_status()
            req.encoding = req.apparent_encoding
        except requests.exceptions.RequestException as e:
            print(f"リクエスト中にエラーが発生しました: {e}")
            return 0

        html_soup = BeautifulSoup(req.text, "html.parser")
        title_list, date_list, media_list = self.fetch_titles_and_dates(html_soup)

        novel_count = 0

        for i, title in enumerate(title_list):
            if i < len(media_list):
                media = media_list[i]
                formatted_date = self.convert_japanese_date(date_list[i])

                if self.check_duplicate(formatted_date, title):
                    print(f"{title} のイベントは既にカレンダーに存在します。")
                    continue

                event = {
                    "summary": title,
                    "start": {"date": formatted_date, "timeZone": "Asia/Tokyo"},
                    "end": {"date": formatted_date, "timeZone": "Asia/Tokyo"},
                }
                self.service.events().insert(
                    calendarId=self.calendar_id, body=event
                ).execute()
                print(f"{title} のイベントが追加されました。")
                novel_count += 1
            else:
                print("指定されたクラスの要素が見つかりません。")
                break

        return novel_count


if __name__ == "__main__":
    main()
