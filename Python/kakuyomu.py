import requests
from bs4 import BeautifulSoup

# カクヨムの月間ランキングページのURL
url = 'https://kakuyomu.jp/rankings/monthly'

# リクエストを送信してページ内容を取得
response = requests.get(url)

# レスポンスの内容を解析
soup = BeautifulSoup(response.content, 'html.parser')

# ランキングのセクションを見つける
ranking_section = soup.find('div', class_='widget-ranking')

if ranking_section:
    # タイトルを取得してログとして出力
    titles = ranking_section.find_all('h4', class_='widget-work-title')

    for index, title in enumerate(titles):
        print(f"{index + 1}: {title.text.strip()}")
else:
    print("ランキングセクションが見つかりませんでした。HTML構造を確認してください。")
