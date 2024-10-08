import csv
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import gspread
from dotenv import load_dotenv
import os.path

load_dotenv()

def main():
    url = input("プレイリストのURLを入力してください: ")
    getplaylist = YoutubePlayListGet(url)
    data = getplaylist.get_playlist()
    
    google_drive = GoogleDriveAuth(url)  # ここを修正
    spreadsheet_id = google_drive.spreadsheet_id
    google_drive.write_csv(spreadsheet_id, data)

class YoutubePlayListGet:
    def __init__(self, url):
        self.url = url
        self.playlist_id = self.extract_playlist_id(url)
        self.youtube_service = self.get_youtube_service()

    def extract_playlist_id(self, url):
        # URLからプレイリストIDを抽出する
        if "list=" in url:
            return url.split("list=")[-1]
        return None

    def get_youtube_service(self):
        SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']
        creds = None

        # 認証処理
        if os.path.exists('Youtube_PlayList_token.pickle'):
            with open('Youtube_PlayList_token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('drive_credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('Youtube_PlayList_token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        return build('youtube', 'v3', credentials=creds)

    def get_playlist(self):
        data = []
        next_page_token = None
        
        while True:
            request = self.youtube_service.playlistItems().list(
                part="snippet",
                playlistId=self.playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response.get("items", []):
                title = item["snippet"]["title"]
                video_url = f"https://www.youtube.com/watch?v={item['snippet']['resourceId']['videoId']}"
                data.append([title, video_url])

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return data

class GoogleDriveAuth:
    SCOPES = [
        'https://www.googleapis.com/auth/drive', 
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file',  # スコープを追加
        'https://www.googleapis.com/auth/youtube.readonly'
    ]

    def __init__(self, url, token_path='Youtube_PlayList_token.pickle', credentials_path='drive_credentials.json'):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.creds = None
        self.drive_service = None
        self.sheets_service = None

        # 既存のトークンを削除
        if os.path.exists(self.token_path):
            os.remove(self.token_path)

        # 認証プロセス
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)

        if self.creds and self.creds.valid:
            self.drive_service = build('drive', 'v3', credentials=self.creds)
            self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        else:
            print('Drive or Sheets auth failed.')

        # スプレッドシートの作成
        spreadsheet = {
            'properties': {
                'title': f"Youtube_PlayList_「{url}」"
            }
        }

        request = self.sheets_service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        self.spreadsheet_id = request.get('spreadsheetId')

        folder_id = os.getenv('YOUTUBE_PLAYLIST_FOLDER_ID')

        # フォルダにスプレッドシートを移動
        file_metadata = {
            'parents': [folder_id]
        }
        self.drive_service.files().update(fileId=self.spreadsheet_id, addParents=folder_id).execute()

    def write_csv(self, spreadsheet_id, data):
        spreadsheet = self.sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_name = spreadsheet['sheets'][0]['properties']['title']

        body = {
            'values': data
        }
        
        result = self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!A1',
            valueInputOption='RAW',
            body=body
        ).execute()

        print(f"{result.get('updatedCells')} cells updated.")

if __name__ == '__main__':
    main()
