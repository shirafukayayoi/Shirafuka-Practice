from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os
import datetime
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def main():
    Calendar_id = os.environ["TEMPLATE_GOOGLE_CALENDAR_ID"]

    google_calendar = GoogleCalendar()   # initを実行するために必要
    google_calendar.Add_event_from_csv(Calendar_id)

class GoogleCalendar:
    def __init__(self):
        self.creds = None   # 認証情報の初期化
        if os.path.exists('token.json'):    # credentials.json ファイルに保存された認証情報をロードする
            self.creds = Credentials.from_authorized_user_file('token.json')
        
        # 認証情報(token.json)がない場合や期限切れの場合は、ユーザーに認証を求める
        if not self.creds or not self.creds.valid:   # cerds.validはtrueかfalseを返し、切れている場合はtrue
            if self.creds and self.creds.expired and self.creds.refresh_token:  # tokenがあった場合、期限切れかどうかを確認
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(   # tokenがない場合、認証を行う
                    'Calendar_credentials.json', ['https://www.googleapis.com/auth/calendar.events'])
                self.creds = flow.run_local_server(port=0)
            # 認証情報を保存する
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())   # 認証情報が入っているself.credsをjson形式に変換して保存する
        self.service = build('calendar', 'v3', credentials=self.creds)
        print("Google Calendarに接続しました")
    
    # Googleカレンダーのイベントを取得する
    def get_events(self, Calendar_id):
        month = int(input("取得したい月を入力してください: "))
        year = datetime.datetime.now().year  # 現在の年を取得
        start_date = datetime.datetime(year, month, 1).isoformat() + 'Z'    # zでUTC時間に変換

        if month == 12:     # 12月の場合、次の年の1月まで取得
            end_date = datetime.datetime(year+1, 1, 1).isoformat() + 'Z'    # 12月から1月分増やして1月にする
        else:
            end_date = datetime.datetime(year, month+1, 1).isoformat() + 'Z' # 12月以外は次の月にする
        
        event_result = self.service.events().list(      # listはイベントの一覧を取得するメゾット、辞書形式でまとめる
            calendarId= Calendar_id,
            timeMin=start_date, 
            timeMax=end_date, 
            singleEvents=True,  # 重複するイベントを1つにまとめる
            orderBy='startTime' # 開始時間に並び替え
                ).execute()     # 実行
        
        events = event_result.get('items', [])     # 取得した値のitemsを取得、ない場合は空のリストを返す
        for event in events:    # for文で1つずつ取り出す
            print(event['summary'])    # イベントのタイトルを表示

    # Googleカレンダーにイベントを追加する
    def Add_event(self, Calendar_id,):
        event_name = input("イベント名を入力してください: ")
        event = {   # イベントの情報を辞書形式でまとめる
            'summary': event_name,
            'description': 'PythonからGoogleカレンダーにイベントを追加する',
            'start': {  # 開始時間
                'dateTime': '2021-08-01T09:00:00',
                'timeZone': 'Asia/Tokyo'
            },
            'end': {    # 終了時間
                'dateTime': '2021-08-01T17:00:00',
                'timeZone': 'Asia/Tokyo'
            },
        }
        self.service.events().insert(
            calendarId= Calendar_id,
            body=event
        ).execute()
        print("イベントを追加しました")
    
    # CSVファイルからイベントを追加する
    def Add_event_from_csv(self, Calendar_id):
        """タイトル,詳細,日付"""
        csv_file = input("CSVファイルのパスを入力してください: ")
        df = pd.read_csv(csv_file)
        for index, row in df.iterrows():
            event = {
                'summary': row['タイトル'],
                'description': row['詳細'],
                'start': {
                    'date': row['日付'],
                    'timeZone': 'Asia/Tokyo'
                },
                'end': {
                    'date': row['日付'],
                    'timeZone': 'Asia/Tokyo'
                },
            }
            self.service.events().insert(
                calendarId= Calendar_id,
                body=event
            ).execute()
            print(f"{row['タイトル']}を追加しました")

if __name__ == '__main__':
    main()