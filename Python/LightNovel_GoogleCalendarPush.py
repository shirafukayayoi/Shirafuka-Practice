from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import datetime
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from datetime import datetime, date, timedelta

# 指定する年と月
year = input("年を入力してください：")
month = input("月を入力してください：")

# 出力する出版社を指定
target_media = ["電撃文庫", "講談社ラノベ文庫", "HJ文庫", "GA文庫", "ガガガ文庫", "ファンタジア文庫", "MF文庫J"]

# カレンダーidを指定
calendar_id = ''

# GoogleCalendarの認証情報のロード
creds = None
# credentials.json ファイルに保存された認証情報をロードする
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json')

# 認証情報がない場合や期限切れの場合は、ユーザーに認証を求める
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', ['https://www.googleapis.com/auth/calendar.events'])
        creds = flow.run_local_server(port=0)
    # 認証情報を保存する
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

# Google Calendar API の使用
service = build('calendar', 'v3', credentials=creds)

# ベースのurl
base_url = "https://books.rakuten.co.jp/calendar/001017/monthly/"
query_params = {
    "tid": f"{year}-{month:02}-01",  # ここで日付を固定してみましたが、必要に応じて変更してください
    "p": "{}",
    "s": "14",
    "#rclist": ""
}

# 日本語の日付を変換する関数
def convert_japanese_date(japanese_date_str, year):

    if '上旬' in japanese_date_str:
        return f"{year}-{month}-02"

    # 日本語の日付をパースする
    try:
        date_obj = datetime.strptime(japanese_date_str, '%m月 %d日')
    except ValueError:
        return ''  # パースできない場合も空文字列を返す
    
    # 年を追加して目的の形式に変換する
    formatted_date = date_obj.replace(year=year).strftime('%Y-%m-%d')
    return formatted_date


def get_events(service, calendar_id, time_min=None, time_max=None):
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])

for page in range(1, 5):
    query_params["p"] = str(page)
    url = base_url + "?" + urlencode(query_params)
    req = requests.get(url)

    if req.status_code == 200:
        req.encoding = req.apparent_encoding
        html_soup = BeautifulSoup(req.text, "html.parser")
        
        title_list = []
        date_list = []

        titles = html_soup.find_all(class_="item-title__text")
        if titles:
            for title in titles:
                title_list.append(title.get_text().strip())
        else:
            print("指定されたクラスの要素が見つかりません。")

        dates = html_soup.find_all(class_="item-release__date")
        if dates:
            for date in dates:
                date_list.append(date.get_text().strip())
        else:
            print("指定された要素は見つかりません。")

        media_items = html_soup.find_all(class_="item-title__media")

        for i, title in enumerate(title_list):
            if i < len(media_items):
                media = media_items[i].get_text().strip()
                formatted_date = convert_japanese_date(date_list[i], year)

                def check_duplicate(service, calendar_id, event_date, title):
                    time_min = (datetime.strptime(event_date, '%Y-%m-%d') + timedelta(days=-1)).strftime('%Y-%m-%d') + 'T00:00:00Z'
                    time_max = event_date + 'T00:00:00Z'
                    events = get_events(service, calendar_id, time_min, time_max)
                    
                    for event in events:
                        if event['summary'] == title and 'date' in event['start']:
                            return True
                    return False

                if check_duplicate(service, calendar_id, formatted_date, title):
                    print(f'{title} のイベントは既にカレンダーに存在します。')
                    continue

                if any(target in media for target in target_media):
                    event = {
                        'summary': title,
                        'start': {
                            'date': formatted_date,
                            'timeZone': 'Asia/Tokyo',
                        },
                        'end': {
                        'date': formatted_date,
                            'timeZone': 'Asia/Tokyo',
                        },
                    }

                    event = service.events().insert(calendarId=calendar_id, body=event).execute()
                    print(f'{title} のイベントが追加されました。')

            else:
                print(f"インデックス {i} が範囲外になったため終了します。")
                break

    else:
        print(f"リクエストが失敗しました。ステータスコード: {req.status_code}")
