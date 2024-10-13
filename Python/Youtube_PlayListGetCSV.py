from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from dotenv import load_dotenv
import os.path
from datetime import datetime

# 環境変数の読み込み
load_dotenv()

def main():
    # プレイリストのURLをユーザーから取得
    url = input("プレイリストのURLを入力してください: ")
    getplaylist = YoutubePlayListGet(url)
    playlist_name = getplaylist.check_playlist_name()
    data = getplaylist.get_playlist()
    
    google_drive = GoogleDriveAuth()  # GoogleDriveAuthのインスタンスを生成
    spreadsheet_id = google_drive.create_spreadsheet(playlist_name)  # スプレッドシートを作成

    # spreadsheet_idがNoneでないことを確認
    if spreadsheet_id is None:
        print("スプレッドシートが作成されていません。")
        return  # プログラムを終了

    # スプレッドシートにデータを書き込む
    google_drive.write_csv(spreadsheet_id, data)

class YoutubePlayListGet:
    def __init__(self, url):
        self.url = url
        self.playlist_id = self.extract_playlist_id(url)  # プレイリストIDを抽出
        self.youtube_service = self.get_youtube_service()  # YouTube APIのサービスを取得

    def extract_playlist_id(self, url):
        # URLからプレイリストIDを抽出する
        if "list=" in url:
            return url.split("list=")[-1]
        return None

    def check_playlist_name(self):
        # プレイリストのタイトルを取得
        request = self.youtube_service.playlists().list(
            part="snippet",
            id=self.playlist_id
        )
        response = request.execute()
        return response["items"][0]["snippet"]["title"]

    def get_youtube_service(self):
        SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']
        creds = None

        # 認証処理
        if os.path.exists('youtube_PlayList_token.pickle'):
            with open('youtube_PlayList_token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=8080)  # 認証フローを実行
            with open('youtube_PlayList_token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        return build('youtube', 'v3', credentials=creds)  # YouTube APIのサービスを構築

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
                data.append([title, video_url])  # タイトルとURLをデータに追加

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break  # 次のページがなければループを終了

        return data  # データを返す

class GoogleDriveAuth:
    SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']

    def __init__(self, token_path='token.pickle', credentials_path='credentials.json'):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.creds = None
        self.drive_service = None
        self.sheets_service = None

        # OAuth2認証とサービスインスタンスの初期化
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

    def create_spreadsheet(self, playlist_name):
        now = datetime.now().strftime('%Y-%m-%d')
        if self.sheets_service is None:
            print("Sheets serviceが初期化されていません。")
            return None
        
        # 新しいスプレッドシートを作成
        spreadsheet = {
            'properties': {
                'title': f"{now}_{playlist_name}"
            }
        }

        request = self.sheets_service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        spreadsheet_id = request.get('spreadsheetId')
        print(f'Spreadsheet created with ID: {spreadsheet_id}')

        # 環境変数からフォルダIDを取得
        folder_id = os.environ["YOUTUBE_PLAYLIST_FOLDER_ID"]
        file_metadata = {
            'parents': [folder_id]
        }

        # スプレッドシートの親フォルダを更新
        self.drive_service.files().update(
            fileId=spreadsheet_id,
            addParents=folder_id,
            removeParents='root',
            fields='id, parents'
        ).execute()

        return spreadsheet_id  # スプレッドシートIDを返す

    def write_csv(self, spreadsheet_id, data):
        # スプレッドシートのタイトルを取得
        spreadsheet = self.sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_name = spreadsheet['sheets'][0]['properties']['title']

        # データをスプレッドシートに書き込む
        body = {
            'values': data
        }
        
        result = self.sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!A1',
            valueInputOption='RAW',
            body=body
        ).execute()

        print(f"{result.get('updates').get('updatedCells')} cells updated.")  # 更新されたセルの数を表示

if __name__ == '__main__':
    main()  # メイン関数を実行
