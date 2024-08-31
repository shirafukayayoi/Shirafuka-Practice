from yt_dlp import YoutubeDL

# ダウンロードするURL
url = input("URLを入力してください: ")

# オプション
ydl_opts = {
    'format': 'bestvideo+bestaudio/best'  # 最良の画質と音質をダウンロード
}
with YoutubeDL(ydl_opts) as ydl:
    res = ydl.download(url)