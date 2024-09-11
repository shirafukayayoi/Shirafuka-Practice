import requests
from bs4 import BeautifulSoup
import time
import csv

def main():
    url = "https://bookmeter.com/users/1291485/books/stacked"
    web_scraping = WebScraping(url)
    data = web_scraping.get_html()
    csv_writer = CSVwriter(data)
    csv_writer.write_csv()

class WebScraping:
    def __init__(self, url):
        self.url = url
        self.session = requests.Session()  # Sessionオブジェクトを初期化
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'
        }
        self.data = []
        self.all_links = []
        
    def get_html(self):
        # 初回リクエスト処理
        try:
            req = self.session.get(self.url, headers=self.headers)
            req.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"初回リクエストでエラーが発生しました: {e}")
            return

        req.encoding = req.apparent_encoding
        html_soup = BeautifulSoup(req.text, "html.parser")

        # ページリンクの取得
        try:
            pagination_links = html_soup.find_all('a', class_="bm-pagination__link")
            last_page_link = pagination_links[-1].get('href')

            if 'page=' in last_page_link:
                last_page_number = last_page_link.split('page=')[-1]
            else:
                print("ページ番号が見つかりませんでした")
        except Exception:
            print("ページリンクの取得に失敗しました")
            return
        
        # 各ページのリンクを取得して処理
        for i in range(1, int(last_page_number) + 1):
            page_url = f"https://bookmeter.com/users/1291485/books/stacked?page={i}"
            
            # リトライ処理の統合
            for attempt in range(3):  # 最大3回リトライ
                try:
                    req = self.session.get(page_url, headers=self.headers)
                    req.raise_for_status()
                    break  # 成功したらループを抜ける
                except requests.exceptions.RequestException as e:
                    print(f"ページリクエストでエラーが発生しました: {e}")
                    if attempt < 2:  # リトライの余地があれば待機
                        print(f"5秒後に再試行します...")
                        time.sleep(5)
                    else:
                        print("最大試行回数に達しました。次のページに進みます。")
                        req = None
                        break

            if req is None:
                continue  # リトライ後も失敗した場合は次のページへ

            req.encoding = req.apparent_encoding
            page_soup = BeautifulSoup(req.text, "html.parser")
            
            # <div class="detail__title"> 内の <a> タグを探す
            detail_divs = page_soup.find_all('div', class_="detail__title")

            for div in detail_divs:
                a_tag = div.find('a')
                if a_tag and a_tag.get('href'):
                    href = a_tag.get('href')
                    base_link = "https://bookmeter.com" + href
                    self.all_links.append(base_link)
                else:
                    print("hrefが存在しません")
        
        for link in self.all_links:
            try:
                time.sleep(5)
                req = self.session.get(link, headers=self.headers)
                req.raise_for_status()
                req.encoding = req.apparent_encoding
            except requests.exceptions.RequestException as e:
                print(f"リンクリクエストでエラーが発生しました: {e}")
                continue
            html_soup = BeautifulSoup(req.text, "html.parser")

            title_text = html_soup.find('h1', class_="inner__title")
            if title_text:
                title = title_text.text.split(' (', 1)[0]  # タイトル部分だけを取得
            
            authors_elements = html_soup.select('ul.header__authors a')  # 著者リンクのセレクタ
            authors = authors_elements[0].text if authors_elements else "著者不明"  # authors_elements[0].textで取得、なかった場合はelse

            # ページ数を取得するロジック
            page_number = html_soup.find('dt', text='ページ数').find_next_sibling('dd').find('span').text

            # リンク処理の修正
            link_samples = [a['href'] for a in html_soup.find_all('a', href=True) if 'bookwalker.jp' in a['href']]
            links = link_samples[0].split('?')[0] if link_samples else ""  # 最初のリンクのみを処理

            self.data.append((title, authors, page_number, links))

            print(title, authors, page_number, links)
        return self.data

class CSVwriter:
    def __init__(self, data):
        self.data = data

    def write_csv(self):
        with open("bookmeter_data.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["タイトル", "著者", "ページ数", "URL"])
            writer.writerows(self.data)

if __name__ == "__main__":
    main()