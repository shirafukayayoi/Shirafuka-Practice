import os

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

# OAuth 2.0のスコープ
SCOPES = ['https://www.googleapis.com/auth/drive']


class GoogleDriveTemplate:
    def __init__(self, credentials_json_path, token_json_path='tokens/drive_token.json'):
        """
        Args:
            credentials_json_path (str): OAuth 2.0クライアントIDのJSONファイルパス
            token_json_path (str): アクセストークンを保存するJSONファイルパス
        """
        self.credentials_json_path = credentials_json_path
        self.token_json_path = token_json_path
        self.service = self.authenticate()

    def authenticate(self):
        """OAuth 2.0を使用してGoogle Driveサービスの認証を行います。"""
        creds = None
        
        # トークンファイルが存在する場合は読み込む
        if os.path.exists(self.token_json_path):
            creds = Credentials.from_authorized_user_file(self.token_json_path, SCOPES)
        
        # 認証情報が無効または存在しない場合
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # トークンをリフレッシュ
                try:
                    creds.refresh(Request())
                    print("トークンをリフレッシュしました。")
                except Exception as e:
                    print(f"トークンのリフレッシュに失敗しました: {e}")
                    creds = None
            
            if not creds:
                # 新しい認証フローを開始
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_json_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    print("新しい認証を完了しました。")
                except Exception as e:
                    print(f"認証中にエラーが発生しました: {e}")
                    return None
            
            # トークンを保存
            try:
                os.makedirs(os.path.dirname(self.token_json_path), exist_ok=True)
                with open(self.token_json_path, 'w') as token:
                    token.write(creds.to_json())
                print(f"トークンを保存しました: {self.token_json_path}")
            except Exception as e:
                print(f"トークンの保存に失敗しました: {e}")
        
        try:
            service = build('drive', 'v3', credentials=creds)
            print("認証に成功しました。")
            return service
        except Exception as e:
            print(f"サービスの構築中にエラーが発生しました: {e}")
            return None

    def list_files(self, page_size=10, folder_id=None):
        """Google Driveのファイル一覧を取得します。
        
        Args:
            page_size (int): 一覧表示するファイル数
            folder_id (str): ファイルを一覧表示するフォルダーID（オプション）
        """
        try:
            query = None
            if folder_id:
                query = f"'{folder_id}' in parents"
            
            results = self.service.files().list(
                pageSize=page_size,
                q=query,
                fields="nextPageToken, files(id, name)"
            ).execute()
            items = results.get('files', [])
            return items
        except HttpError as error:
            print(f"エラーが発生しました: {error}")
            return None

    def upload_file(self, file_path, mime_type, folder_id=None):
        """Google Driveにファイルをアップロードします。
        
        Args:
            file_path (str): アップロードするファイルのパス
            mime_type (str): ファイルのMIMEタイプ
            folder_id (str): アップロード先のフォルダーID（オプション）
        """
        from googleapiclient.http import MediaFileUpload

        file_metadata = {'name': os.path.basename(file_path)}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(file_path, mimetype=mime_type)

        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id',
                supportsAllDrives=True
            ).execute()
            return file.get('id')
        except HttpError as error:
            print(f"エラーが発生しました: {error}")
            return None

if __name__ == "__main__":
    # 使用例
    # OAuth 2.0クライアントIDのJSONファイルパス（Google Cloud Consoleからダウンロード）
    credentials_path = 'tokens/credentials.json'
    # アクセストークンを保存するファイルパス
    token_path = 'tokens/drive_token.json'
    
    drive_template = GoogleDriveTemplate(credentials_path, token_path)

    folder_id = os.getenv('VIDEO_OUTPUT_FOLDER_ID')
    
    # ルートディレクトリにファイルをアップロード
    drive_template.upload_file('example.txt', 'text/plain', folder_id=folder_id)
    
    # 特定のフォルダーにファイルをアップロード（フォルダーIDを指定）
    # drive_template.upload_file('example.txt', 'text/plain', folder_id='YOUR_FOLDER_ID')
    
    # ルートディレクトリのファイル一覧を取得
    # drive_template.list_files()
    
    # 特定のフォルダーのファイル一覧を取得
    # drive_template.list_files(folder_id='YOUR_FOLDER_ID')

    