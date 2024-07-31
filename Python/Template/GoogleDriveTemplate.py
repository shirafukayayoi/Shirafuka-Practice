import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

def main():
    drive_auth = GoogleDriveAuth()
    sheets_service = drive_auth.get_sheets_service()
    title = '例1'
    drive_auth.create_spreadsheet(title) 


class GoogleDriveAuth:
    SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']

    def __init__(self, token_path='token.pickle', credentials_path='client_secret.json'):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.creds = None
        self.drive = None
        self.sheets = None
        self.authenticate()

    def authenticate(self):
        """OAuth2認証を行うメソッド"""
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            elif os.path.exists(self.credentials_path):
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)

        if self.creds and self.creds.valid:
            self.drive = build('drive', 'v3', credentials=self.creds)
            self.sheets = build('sheets', 'v4', credentials=self.creds)
        else:
            print('Drive or Sheets auth failed.')

    def get_drive_service(self):
        """Google Drive APIのサービスインスタンスを返すメソッド"""
        if self.drive:
            return self.drive
        else:
            print('Drive service is not available.')
            return None

    def get_sheets_service(self):
        """Google Sheets APIのサービスインスタンスを返すメソッド"""
        if self.sheets:
            return self.sheets
        else:
            print('Sheets service is not available.')
            return None

    #
    def create_spreadsheet(self, title):
        if not self.sheets:
            print('Sheets service is not available.')
            return None

        spreadsheet = {
            'properties': {
                'title': title
            }
        }

        request = self.sheets.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        spreadsheet_id = request.get('spreadsheetId')
        print(f'Spreadsheet created with ID: {spreadsheet_id}')
        return spreadsheet_id

if __name__ == '__main__':
    main()
