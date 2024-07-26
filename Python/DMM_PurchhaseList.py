from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import csv
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

def main():
    today = datetime.now().strftime("%Y-%m-%d")     # 今日の日付を取得（ファイル名に入れるため）
    login_url = "https://accounts.dmm.co.jp/service/login/password/=/path=SgVTFksZDEtUDFNKUkQfGA__"
    email = os.environ.get("DMM_EMAIL")
    password = os.environ.get("DMM_PASSWORD")
    csv_title = f"DMM_{today}_PURCHASED_LIST.csv"

    driver = webdriver.Chrome()
    
    dmm_login = DMMLogin(driver, login_url, email, password)
    dmm_login.login()   # ログイン関数の実行
    
    dmm_library = DMMLibrary(driver)    # initにdriverを渡す
    dmm_library.navigate_to_library()
    data = dmm_library.scroll_and_collect_data()    # 取得した値をdataに格納

    csv_writer = CSVWriter(csv_title)
    csv_writer.write_data(data)
    
    driver.quit()

class DMMLogin:
    # 一番最初に実行される関数、必要な情報を受け取る
    def __init__(self, driver, login_url, email, password):
        self.driver = driver
        self.login_url = login_url
        self.email = email
        self.password = password

    # ログイン処理
    def login(self):
        self.driver.get(self.login_url)
        self.driver.set_window_size(1000, 1000) # ウィンドウサイズを指定
        time.sleep(10)
        
        try:
            # ユーザー名入力
            name_box = self.driver.find_element(By.NAME, "login_id")
            name_box.send_keys(self.email)
            print("ユーザー名入力完了")
        except Exception as e:
            print(f"ユーザー名入力フィールドが見つかりません: {e}")
        
        try:
            # パスワード入力
            pass_box = self.driver.find_element(By.NAME, "password")
            pass_box.send_keys(self.password)
            print("パスワード入力完了")
        except Exception as e:
            print(f"パスワード入力フィールドが見つかりません: {e}")
        
        try:
            # ログイン状態を保つためのチェックボックス
            remember_box = self.driver.find_element(By.CLASS_NAME, "checkbox-input")
            remember_box.click()
            print("チェックボックス選択完了")
        except Exception as e:
            print(f"チェックボックスが見つかりません: {e}")
        
        try:
            # フォームを送信
            login_button = self.driver.find_element(By.XPATH, '//input[@value="ログイン"]')
            login_button.click()
            print("フォームを送信しました")
        except Exception as e:
            print(f"フォームの送信に失敗しました: {e}")
        
        print("ログイン完了")
        time.sleep(4)

class DMMLibrary:
    # 一番最初に実行される関数
    def __init__(self, driver):
        self.driver = driver

    def navigate_to_library(self):
        self.driver.get("https://www.dmm.co.jp/dc/-/mylibrary/")
        try:
            # 「はい」をクリック
            yes_button = self.driver.find_element(By.XPATH, "//a[contains(@href, 'declared=yes')]")
            yes_button.click()
            print("「はい」をクリックしました")
        except Exception as e:
            print(f"「はい」が見つかりません: {e}")
        time.sleep(4)

    def scroll_and_collect_data(self):
        try:
            svg_path = self.driver.find_element(By.XPATH, "//*[@class='silex-element-content']")
            svg_path.click()
        except Exception as e:
            print(f"「×」が見つかりません")
        
        actions = self.driver.find_element(By.CLASS_NAME,"purchasedListArea1Znew")
        previous_scroll_height = 0
        
        while True:
            # 現在のスクロール位置を取得
            current_scroll_height = self.driver.execute_script("return arguments[0].scrollTop + arguments[0].clientHeight;", actions)
            
            # スクロールする
            self.driver.execute_script("arguments[0].scrollTop += arguments[0].clientHeight;", actions)
            
            # しばらく待つ（スクロールが完了するまで）
            time.sleep(1)
            
            # 新しいスクロール位置を取得
            new_scroll_height = self.driver.execute_script("return arguments[0].scrollTop + arguments[0].clientHeight;", actions)
            
            # スクロールが止まった場合
            if new_scroll_height == current_scroll_height:
                break
        
        # データ収集
        titles = self.driver.find_elements(By.CLASS_NAME, "productTitle3sdi8")
        circles = self.driver.find_elements(By.CLASS_NAME, "circleName209pI")
        kinds = self.driver.find_elements(By.CLASS_NAME, "default3EHgn")

        # 各リストの長さを取得
        length = min(len(titles), len(circles), len(kinds))
        data = [(titles[i].text, circles[i].text, kinds[i].text) for i in range(length)]
        
        # データを出力
        for title, circle, kind in data:
            print(title, circle, kind)

        return data


class CSVWriter:
    def __init__(self, filename):
        self.filename = filename

    def write_data(self, data):
        with open(self.filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["タイトル", "サークル", "種類"])
            writer.writerows(data)

if __name__ == "__main__":  # このファイルが直接実行された場合のみ実行される。
    main()