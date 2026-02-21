import datetime
import json
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()


def load_calendar_id(category_name: str = "", legacy_key: str = "") -> str:
    calendar_ids_path = (
        Path(__file__).resolve().parent.parent.parent / "tokens" / "calendar_ids.json"
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
    Calendar_id = load_calendar_id(legacy_key="template")

    google_calendar = GoogleCalendar()  # initを実行するために必要
    google_calendar.Add_event_from_csv(Calendar_id)


class GoogleCalendar:
    def __init__(self):
        self.creds = None  # 認証情報の初期化
        if os.path.exists(
            "../tokens/token.json"
        ):  # credentials.json ファイルに保存された認証情報をロードする
            self.creds = Credentials.from_authorized_user_file("../tokens/token.json")

        # 認証情報(token.json)がない場合や期限切れの場合は、ユーザーに認証を求める
        if (
            not self.creds or not self.creds.valid
        ):  # cerds.validはtrueかfalseを返し、切れている場合はtrue
            if (
                self.creds and self.creds.expired and self.creds.refresh_token
            ):  # tokenがあった場合、期限切れかどうかを確認
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(  # tokenがない場合、認証を行う
                    "Calendar_credentials.json",
                    ["https://www.googleapis.com/auth/calendar.events"],
                )
                self.creds = flow.run_local_server(port=0)
            # 認証情報を保存する
            with open("../tokens/token.json", "w") as token:
                token.write(
                    self.creds.to_json()
                )  # 認証情報が入っているself.credsをjson形式に変換して保存する
        self.service = build("calendar", "v3", credentials=self.creds)
        print("[Info] Google Calendarに接続しました")

    # Googleカレンダーのイベントを取得する
    def get_events(self, Calendar_id):
        month = int(input("取得したい月を入力してください: "))
        year = datetime.datetime.now().year  # 現在の年を取得
        start_date = (
            datetime.datetime(year, month, 1).isoformat() + "Z"
        )  # zでUTC時間に変換

        if month == 12:  # 12月の場合、次の年の1月まで取得
            end_date = (
                datetime.datetime(year + 1, 1, 1).isoformat() + "Z"
            )  # 12月から1月分増やして1月にする
        else:
            end_date = (
                datetime.datetime(year, month + 1, 1).isoformat() + "Z"
            )  # 12月以外は次の月にする

        event_result = (
            self.service.events()
            .list(  # listはイベントの一覧を取得するメゾット、辞書形式でまとめる
                calendarId=Calendar_id,
                timeMin=start_date,
                timeMax=end_date,
                singleEvents=True,  # 重複するイベントを1つにまとめる
                orderBy="startTime",  # 開始時間に並び替え
            )
            .execute()
        )  # 実行

        events = event_result.get(
            "items", []
        )  # 取得した値のitemsを取得、ない場合は空のリストを返す
        for event in events:  # for文で1つずつ取り出す
            print(event["summary"])  # イベントのタイトルを表示

    # Googleカレンダーにイベントを追加する
    def Add_event(
        self,
        Calendar_id,
    ):
        event_name = input("イベント名を入力してください: ")
        event = {  # イベントの情報を辞書形式でまとめる
            "summary": event_name,
            "description": "PythonからGoogleカレンダーにイベントを追加する",
            "start": {  # 開始時間
                "dateTime": "2021-08-01T09:00:00",
                "timeZone": "Asia/Tokyo",
            },
            "end": {  # 終了時間
                "dateTime": "2021-08-01T17:00:00",
                "timeZone": "Asia/Tokyo",
            },
        }
        self.service.events().insert(calendarId=Calendar_id, body=event).execute()
        print("イベントを追加しました")

    # CSVファイルからイベントを追加する
    def Add_event_from_csv(self, Calendar_id):
        """タイトル,詳細,予定開始時間,予定終了時間"""
        csv_file = input("CSVファイルのパスを入力してください: ")
        df = pd.read_csv(csv_file)
        for index, row in df.iterrows():
            event = {
                "summary": row["タイトル"],
                "start": {"dateTime": row["予定開始時間"], "timeZone": "Asia/Tokyo"},
                "end": {"dateTime": row["予定終了時間"], "timeZone": "Asia/Tokyo"},
            }
            # 詳細欄が空でない場合のみdescriptionを追加
            if pd.notna(row["詳細"]):
                event["description"] = row["詳細"]
            if pd.notna(row["場所"]):
                event["location"] = row["場所"]
            self.service.events().insert(calendarId=Calendar_id, body=event).execute()
            print(f"{row['タイトル']}を追加しました")


if __name__ == "__main__":
    main()
