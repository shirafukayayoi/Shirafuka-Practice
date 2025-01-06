import os
import time

import gspread
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# .envファイルの読み込み
load_dotenv()


class DMMLogin:
    def __init__(self, driver, login_url, email, password):
        self.driver = driver
        self.login_url = login_url
        self.email = email
        self.password = password

    def login(self):
        self.driver.get(self.login_url)
        self.driver.set_window_size(1000, 1000)  # ウィンドウサイズを指定
        time.sleep(10)

        try:
            name_box = self.driver.find_element(By.NAME, "login_id")
            name_box.send_keys(self.email)
            print("ユーザー名入力完了")
        except Exception as e:
            print(f"ユーザー名入力フィールドが見つかりません: {e}")

        try:
            pass_box = self.driver.find_element(By.NAME, "password")
            pass_box.send_keys(self.password)
            print("パスワード入力完了")
        except Exception as e:
            print(f"パスワード入力フィールドが見つかりません: {e}")

        try:
            time.sleep(3)
            login_button = self.driver.find_element(
                By.XPATH, '//button[text()="ログイン"]'
            )
            self.driver.execute_script("arguments[0].click();", login_button)
            print("フォームを送信しました")
        except Exception as e:
            print(f"フォームの送信に失敗しました: {e}")

        print("ログイン完了")


class DMMLibrary:
    def __init__(self, driver):
        self.driver = driver

    def navigate_to_library(self):
        time.sleep(3)
        self.driver.get("https://www.dmm.co.jp/dc/-/mylibrary/")
        try:
            time.sleep(3)
            yes_button = self.driver.find_element(
                By.XPATH, "//a[contains(@href, 'declared=yes')]"
            )
            yes_button.click()
            print("「はい」をクリックしました")
        except Exception as e:
            print(f"「はい」が見つかりません: {e}")
        time.sleep(4)

    def scroll_and_collect_data(self):
        try:
            svg_path = self.driver.find_element(
                By.XPATH, "//*[@class='silex-element-content']"
            )
            svg_path.click()
        except Exception as e:
            print(f"「×」が見つかりません")

        actions = self.driver.find_element(By.CLASS_NAME, "purchasedListArea1Znew")
        previous_scroll_height = 0

        while True:
            current_scroll_height = self.driver.execute_script(
                "return arguments[0].scrollTop + arguments[0].clientHeight;", actions
            )
            self.driver.execute_script(
                "arguments[0].scrollTop += arguments[0].clientHeight;", actions
            )
            time.sleep(1)
            new_scroll_height = self.driver.execute_script(
                "return arguments[0].scrollTop + arguments[0].clientHeight;", actions
            )
            if new_scroll_height == current_scroll_height:
                break

        titles = self.driver.find_elements(By.CLASS_NAME, "productTitle3sdi8")
        circles = self.driver.find_elements(By.CLASS_NAME, "circleName209pI")
        kinds = self.driver.find_elements(By.CLASS_NAME, "default3EHgn")

        length = min(len(titles), len(circles), len(kinds))
        data = [(titles[i].text, circles[i].text, kinds[i].text) for i in range(length)]

        return data


class GoogleSpreadsheet:
    def __init__(self, spreadsheet_id):
        self.scope = ["https://www.googleapis.com/auth/spreadsheets"]
        self.creds = None
        if os.path.exists("sheet_token.json"):
            self.creds = Credentials.from_authorized_user_file(
                "sheet_token.json", self.scope
            )
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", self.scope
                )
                self.creds = flow.run_local_server(port=0)
            with open("sheet_token.json", "w") as token:
                token.write(self.creds.to_json())
        self.client = gspread.authorize(self.creds)
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
        self.sheet = self.spreadsheet.sheet1  # 最初のシートにアクセス
        self.sheet.clear()

    def write_data(self, data):
        all_data = [["タイトル", "サークル", "種類"]] + data
        self.sheet.insert_rows(all_data)

    def AutoFilter(self, data, spreadsheet_id):
        # シートの情報を取得
        sheet = self.spreadsheet.sheet1

        # 最終列の計算（data の最初の要素の長さで判断）
        last_column_num = len(data[0]) if data else 3
        print(f"最終列は{last_column_num}です")

        # 列番号をアルファベットに変換
        def num2alpha(num):
            if num <= 26:
                return chr(64 + num)
            elif num % 26 == 0:
                return num2alpha(num // 26 - 1) + chr(90)
            else:
                return num2alpha(num // 26) + chr(64 + num % 26)

        last_column_alp = num2alpha(last_column_num)
        print(f"最終列のアルファベットは{last_column_alp}です")

        # フィルターを設定
        requests = [
            {
                "setBasicFilter": {
                    "filter": {
                        "range": {
                            "sheetId": sheet.id,
                            "startRowIndex": 0,
                            "endRowIndex": len(data)
                            + 1,  # 行数の指定（ヘッダー行を含むため +1）
                            "startColumnIndex": 0,
                            "endColumnIndex": last_column_num,
                        }
                    }
                }
            }
        ]

        body = {"requests": requests}

        service = build("sheets", "v4", credentials=self.creds)
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body
        ).execute()
        print("フィルターを設定しました")


if __name__ == "__main__":
    email = os.environ["DMM_EMAIL"]
    password = os.environ["DMM_PASSWORD"]
    spreadsheet_id = os.environ["DMM_GOOGLE_SHEET_URL"]

    login_url = "https://accounts.dmm.co.jp/service/login/password/=/path=SgVTFksZDEtUDFNKUkQfGA__"

    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=chrome_options)

    dmm_login = DMMLogin(driver, login_url, email, password)
    dmm_login.login()  # ログイン関数の実行

    dmm_library = DMMLibrary(driver)  # initにdriverを渡す
    dmm_library.navigate_to_library()
    data = dmm_library.scroll_and_collect_data()  # 取得した値をdataに格納
    driver.quit()

    google_spreadsheet = GoogleSpreadsheet(spreadsheet_id)
    google_spreadsheet.write_data(data)
    google_spreadsheet.AutoFilter(data, spreadsheet_id)
