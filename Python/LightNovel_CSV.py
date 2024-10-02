import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from datetime import datetime

def main():
    manager = LightNovelEventManager()
    titles, dates = manager.check_new_novels()  # titlesとdatesの2つを取得
    csv_manager = CSVManager()
    csv_manager.write_csv(titles, dates)  # ここも修正


class LightNovelEventManager:
    def __init__(self):
        self.year = 2024
        self.month = 10
        self.titles = []  # 初期化
        self.dates = []   # 初期化
        self.medias = []  # 初期化
    
    def check_new_novels(self):
        for page in range(1, 6):
            base_url = "https://books.rakuten.co.jp/calendar/001017/monthly/"
            query_params = {
                "tid": f"{self.year}-{self.month:02}-01",
                "p": str(page),
                "s": "14",
                "#rclist": ""
            }
            url = base_url + "?" + urlencode(query_params)

            try:
                req = requests.get(url)
                req.raise_for_status()
                req.encoding = req.apparent_encoding
            except requests.exceptions.RequestException as e:
                print(f"リクエスト中にエラーが発生しました: {e}")
                return [], []  # 空のリストを返す
            
            html_soup = BeautifulSoup(req.text, "html.parser")

            titles = html_soup.find_all(class_="item-title__text")
            dates = html_soup.find_all(class_="item-release__date")
            
            title_list = [title.get_text().strip() for title in titles]
            # convert_japanese_dateを使用して日付を変換
            date_list = [self.convert_japanese_date(date.get_text().strip()) for date in dates]

            self.titles.extend(title_list)
            self.dates.extend(date_list)

        return self.titles, self.dates

    def convert_japanese_date(self, japanese_date_str):
        if '上旬' in japanese_date_str:
            return f"{self.year}-{self.month}-02"

        # 日本語の日付をパースする
        try:
            date_obj = datetime.strptime(japanese_date_str, '%m月 %d日')
        except ValueError:
            return ''  # パースできない場合も空文字列を返す
        
        # 年を追加して目的の形式に変換する
        formatted_date = date_obj.replace(year=self.year).strftime('%Y-%m-%d')
        return formatted_date

class CSVManager:
    def __init__(self):
        self.file_name = "LightNovel.csv"
    
    def write_csv(self, title, date):
        with open(self.file_name, "w", encoding="utf-8") as f:
            f.write("名前,詳細,日付\n")
            for i in range(len(title)):
                f.write(f"{title[i]}, ,{date[i]}\n")

if __name__ == "__main__":
    main()
