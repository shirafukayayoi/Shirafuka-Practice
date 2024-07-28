from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os

def main():
    calendar = GoogleCalendar()   # initを実行するために必要

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
    def get_events(self):
        

if __name__ == '__main__':
    main()