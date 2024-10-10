import pickle
import os.path
import time
import logging
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
import gspread
from googleapiclient.errors import HttpError

# ロギングの設定
logging.basicConfig(filename='youtube_api.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    url = input("GoogleスプレッドシートのURLを入力してください: ")
    spreadsheet_id = extract_spreadsheet_id(url)
    if not spreadsheet_id:
        print("無効なスプレッドシートURLです。処理を終了します。")
        return

    google_spreadsheet = GoogleSpreadsheet(spreadsheet_id)
    video_ids = google_spreadsheet.read_data()
    if not video_ids:
        print("スプレッドシートから動画IDを取得できませんでした。処理を終了します。")
        return

    playlist_url = input("プレイリストのURLを入力してください: ")
    playlist_id = extract_playlist_id(playlist_url)
    if not playlist_id:
        print("無効なプレイリストURLです。処理を終了します。")
        return
    
    youtube_playlist_get = YoutubePlayListGet()

    # 既存のプレイリストの中身を消す
    youtube_playlist_get.clear_playlist(playlist_id)

    # 新しい動画を追加
    youtube_playlist_get.add_video(playlist_id, video_ids)

def extract_spreadsheet_id(url):
    """GoogleスプレッドシートのURLからスプレッドシートIDを抽出する"""
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)
    return None

def extract_playlist_id(url):
    """YouTubeプレイリストのURLからプレイリストIDを抽出する"""
    match = re.search(r'list=([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None

class GoogleSpreadsheet:
    def __init__(self, spreadsheet_id):
        self.scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        self.creds = Credentials.from_service_account_file('service_token.json', scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
        self.sheet = self.spreadsheet.sheet1  # 最初のシートにアクセス
    
    def read_data(self):
        data = self.sheet.get_all_values()[1:]  # 2行目以降のデータを取得
        video_ids = []

        for row in data:
            # 各行の文字列からすべての動画IDを抽出
            matches = re.findall(r'v=([a-zA-Z0-9_-]+)', row[0])
            if not matches:
                logging.warning(f"Invalid URL format in row: {row[0]}")
                continue
            for video_id in matches:
                video_ids.append([row[0], video_id])
        
        return video_ids

class YoutubePlayListGet:
    def __init__(self):
        self.scope = ['https://www.googleapis.com/auth/youtube.force-ssl']
        self.client_secrets_file = 'credentials.json'
        self.flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, self.scope)
        self.creds = self.flow.run_local_server(port=0)
        self.youtube = build('youtube', 'v3', credentials=self.creds)

    def clear_playlist(self, playlist_id):
        logging.info(f"Clearing playlist {playlist_id}")
        next_page_token = None

        while True:
            retries = 0
            while True:
                try:
                    request = self.youtube.playlistItems().list(
                        part='id',
                        playlistId=playlist_id,
                        maxResults=50,  # 最大50アイテムを取得
                        pageToken=next_page_token  # 次のページのトークン
                    )
                    response = request.execute()
                    logging.info(f"Retrieved {len(response.get('items', []))} items from playlist {playlist_id}")

                    # 各アイテムを削除
                    for item in response.get('items', []):
                        delete_request = self.youtube.playlistItems().delete(id=item['id'])
                        delete_request.execute()
                        logging.info(f"Deleted video {item['id']} from playlist {playlist_id}")

                    # 次のページが存在する場合はトークンを更新
                    next_page_token = response.get('nextPageToken')
                    if not next_page_token:  # 次のページがなければループを終了
                        return
                    break
                except HttpError as e:
                    logging.error(f"Error occurred: {e}")
                    if e.resp.status == 403 and 'quotaExceeded' in str(e):
                        logging.warning("APIクォータが超過しました。再試行します。")
                        retries += 1
                        wait_time = min(2 ** retries, 300)  # 最大300秒待機
                        logging.info(f"Waiting for {wait_time} seconds before retrying.")
                        time.sleep(wait_time)
                    else:
                        break

    def add_video(self, playlist_id, video_ids):
        logging.info(f"Adding videos to playlist {playlist_id}")
        if not video_ids:
            logging.warning("No video IDs found. Skipping video addition.")
            return

        for data in video_ids:
            video_url, video_id = data  # リストからURLとvideo_idを取得
            retries = 0
            while True:
                try:
                    request = self.youtube.playlistItems().insert(
                        part='snippet',
                        body={
                            'snippet': {
                                'playlistId': playlist_id,
                                'resourceId': {
                                    'kind': 'youtube#video',
                                    'videoId': video_id  # 正しくvideo_idを使う
                                }
                            }
                        }
                    )
                    response = request.execute()
                    logging.info(f"Added video {video_id} to playlist {playlist_id}")
                    break
                except HttpError as e:
                    logging.error(f"Error occurred: {e}")
                    if e.resp.status == 403 and 'quotaExceeded' in str(e):
                        logging.warning("APIクォータが超過しました。再試行します。")
                        retries += 1
                        wait_time = min(2 ** retries, 300)  # 最大300秒待機
                        logging.info(f"Waiting for {wait_time} seconds before retrying.")
                        time.sleep(wait_time)
                    else:
                        break

if __name__ == "__main__":
    main()
