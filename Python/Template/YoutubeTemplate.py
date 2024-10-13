import os
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import pytz
import requests
from dotenv import load_dotenv

# .envファイルからAPIキーを読み込む
load_dotenv()


def main():
    youtube_url = input("YouTube動画のURLを入力してください: ")
    youtube = YoutubeTemplate(youtube_url)
    youtube.get_scheduled_live_info()


class YoutubeTemplate:
    def __init__(self, youtube_url):
        self.youtube_url = youtube_url
        self.API_KEY = os.getenv("YOUTUBE_API_KEY")

    # YouTube Data APIを使用して、配信予定のライブ情報を取得
    def get_scheduled_live_info(self):
        # URLから動画IDを抽出
        parsed_url = urlparse(self.youtube_url)
        video_id = parse_qs(parsed_url.query).get("v")

        if not video_id:
            print("無効なURLです。動画IDが見つかりません。")
            return

        video_id = video_id[0]

        # YouTube Data APIで動画情報を取得
        api_url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={self.API_KEY}&part=snippet,liveStreamingDetails"
        response = requests.get(api_url)

        if response.status_code != 200:
            print(f"APIリクエストエラー: {response.status_code}")
            return

        data = response.json()

        if "items" not in data or len(data["items"]) == 0:
            print("動画情報が見つかりません。")
            return

        video_info = data["items"][0]["snippet"]
        live_info = data["items"][0].get("liveStreamingDetails", {})

        title = video_info["title"]
        published_at = video_info["publishedAt"]
        live_broadcast_content = video_info["liveBroadcastContent"]

        # 配信予定のライブかどうかを確認
        if live_broadcast_content == "upcoming":
            scheduled_start_time_utc = live_info.get("scheduledStartTime")

            if scheduled_start_time_utc:
                # UTC時間をdatetimeオブジェクトに変換
                utc_time = datetime.strptime(
                    scheduled_start_time_utc, "%Y-%m-%dT%H:%M:%SZ"
                )
                utc_time = utc_time.replace(tzinfo=pytz.utc)

                # Asia/Tokyoタイムゾーンに変換
                tokyo_tz = pytz.timezone("Asia/Tokyo")
                scheduled_start_time_tokyo = utc_time.astimezone(tokyo_tz)

                print(
                    f"タイトル: {title}\n更新日: {published_at}\n予定開始時間 (Asia/Tokyo): {scheduled_start_time_tokyo.isoformat()}"
                )
            else:
                print("予定開始時間が見つかりません。")
        else:
            print(
                f"タイトル: {title}\n更新日: {published_at}\nこの動画は配信予定のライブではありません。"
            )


if __name__ == "__main__":
    main()
