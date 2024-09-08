from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv

def main():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=chrome_options)

    bookmeter = BookMeterLogin(driver)
    data = bookmeter.GetBooks()
    csv_writer = CSVWriter(data)
    csv_writer.write_csv()

class BookMeterLogin:
    def __init__(self, driver):
        self.driver = driver
        self.login_url = "https://bookmeter.com/users/1291485/books/stacked"

    def GetBooks(self):
        self.driver.get(self.login_url)
        self.driver.set_window_size(1000, 1000)  # ウィンドウサイズを指定

        try:
            last_page_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[1]/section/div/ul/li[last()]/a"))
            )
            last_page_url = last_page_element.get_attribute("href")
            last_page = int(last_page_url.split("=")[-1])
            print(f"最終ページ: {last_page}")
        except Exception as e:
            print(f"最終ページ取得エラー: {e}")
            last_page = 1  # エラー時はデフォルトで1ページとする

        all_links = []  # リンクを全て追加するリスト

        for i in range(1, last_page + 1):
            try:
                url = f"https://bookmeter.com/users/1291485/books/stacked?page={i}"
                self.driver.get(url)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@class='detail__title']/a"))
                )
                elements = self.driver.find_elements(By.XPATH, "//div[@class='detail__title']/a")
                links = [element.get_attribute("href") for element in elements]
                all_links.extend(links)  # リンクを全て追加
            except Exception as e:
                print(f"ページ {i} のリンク取得エラー: {e}")

        data = []  # データを格納するリストに変更

        for link in all_links:
            time.sleep(5)
            self.driver.get(link)

            titles_elements = self.driver.find_elements(By.CLASS_NAME, "inner__title")
            titles_text = titles_elements[0].text if titles_elements else "タイトル不明"
            try:
                titles, _ = titles_text.split(' (', 1)
            except ValueError:
                titles = titles_text

            authors_elements = self.driver.find_elements(By.CSS_SELECTOR, "ul.header__authors a")
            authors = ', '.join([element.text for element in authors_elements])

            pages_elements = self.driver.find_elements(By.XPATH, "//dt[contains(text(), 'ページ数')]/following-sibling::dd/span[1]")
            pages_text = ' '.join([element.text for element in pages_elements])
            pages = ''.join(filter(str.isdigit, pages_text))
            try:
                links_elements = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, f"//img[@alt='BOOK☆WALKER']/ancestor::a"))
                )
                links = links_elements.get_attribute("href")
            except Exception:
                print("リンクが見つかりません")
                links = ""

            # データをリストに追加
            data.append((titles, authors, pages, links, "積読本"))
            print(titles, authors, pages, links)
        return data

class CSVWriter:
    def __init__(self, data):
        self.data = data

    def write_csv(self):
        with open("bookmeter.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["タイトル", "著者", "ページ数", "URL", "状態"])
            writer.writerows(self.data)

if __name__ == "__main__":
    main()
