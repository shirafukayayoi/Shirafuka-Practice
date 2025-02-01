import json
import os
import time

from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright

load_dotenv()


class InstagramUpdateNote:
    def __init__(self, playwright):
        self.loginurl = "https://www.instagram.com/accounts/login/"
        self.username = os.getenv("INSTAGRAM_ID")
        self.password = os.getenv("INSTAGRAM_PASSWORD")
        self.browser = playwright.chromium.launch(headless=False)

    def login(self, page: Page):
        # クッキーが存在する場合はクッキーを読み込む
        try:
            with open("cookies.json", "r") as f:
                cookies = json.load(f)
            page.context.add_cookies(cookies)
            print("Cookies loaded")

            # クッキーが有効かどうかを確認するためにインボックスに移動
            page.goto("https://www.instagram.com/direct/inbox/?next=%2F", timeout=60000)
            print("Navigated to inbox page")

            # クッキーが有効であれば、通知ボタンをクリック
            if page.url == "https://www.instagram.com/direct/inbox/?next=%2F":
                print("Logged in with cookies")
                try:
                    # 通知ボタンをクリック
                    notification_button = page.locator("button._a9--._ap36._a9_1")
                    notification_button.click()
                    print("Clicked 'Later' button")
                except Exception as e:
                    print(
                        f"An error occurred while clicking the notification button: {e}"
                    )
                return  # ログイン処理をスキップ

        except FileNotFoundError:
            print("No cookies found, proceeding with login")
        except Exception as e:
            print(f"An error occurred while loading cookies: {e}")

        # クッキーが無効または存在しない場合、ログイン処理を行う
        try:
            # ログインページに移動
            page.goto(self.loginurl, timeout=60000)  # タイムアウトを60秒に設定
            print("Navigated to login page")

            # ユーザー名の入力フィールドを待機して特定
            username_field = page.get_by_label(
                "電話番号、ユーザーネーム、またはメールアドレス"
            )
            username_field.fill(self.username)
            print("Filled username")

            # パスワードの入力フィールドを待機して特定
            password_field = page.get_by_label("パスワード")
            password_field.fill(self.password)
            print("Filled password")

            # ログインボタンを待機して特定
            login_button = page.locator("button._acan._acap._acas._aj1-")
            login_button.click()
            print("Clicked login button")

            time.sleep(5)  # ログイン処理が完了するのを待つ

            # クッキーを保存
            cookies = page.context.cookies()
            with open("cookies.json", "w") as f:
                json.dump(cookies, f)
            print("Cookies saved")

            # インボックスに移動
            page.goto("https://www.instagram.com/direct/inbox/?next=%2F")
            print("Navigated to inbox page")

            # 通知ボタンをクリック
            notification_button = page.locator("button._a9--._ap36._a9_1")
            notification_button.click()
            print("Clicked 'Later' button")

        except Exception as e:
            print(f"An error occurred: {e}")

    def update_note(self, page: Page, text):
        try:
            time.sleep(3)
            # メッセージボタンをクリック
            message_button = page.locator("svg[aria-label='Messenger']")
            message_button.click()
            print("Clicked message button")

            time.sleep(2)  # ページが読み込まれるのを待つ

            # メッセージリスト内の特定のメッセージをクリック
            message_item = page.locator("span.x1lliihq.x6ikm8r.x10wlt62.x1n2onr6").first
            message_item.click()
            print("Clicked message item")

            time.sleep(2)  # メッセージが開くのを待つ

            # 「新しいノートを残す」ボタンをテキストで特定してクリック
            new_note_button = page.get_by_text("新しいノートを残す")
            new_note_button.click()
            print("Clicked '新しいノートを残す' button")

            time.sleep(5)  # テキストボックスが表示されるのを待つ

            # テキストボックスを特定してクリック
            text_box = page.locator("div[aria-label='感じたことをシェア…']")
            text_box.click()
            print("Clicked text box")

            # テキストボックスに特定の文字を入力
            text_box.type(text)
            print("Typed text into the text box")

            time.sleep(4)  # テキストが入力されるのを待つ

            # 「シェア」ボタンを特定してクリック
            share_button = page.get_by_role("button", name="シェア", exact=True)
            share_button.click()
            print("Clicked 'シェア' button")

        except Exception as e:
            print(f"An error occurred while updating the note: {e}")


if __name__ == "__main__":
    with sync_playwright() as p:
        text = input("Enter the text you want to share: ")
        insta = InstagramUpdateNote(p)
        page = insta.browser.new_page()
        insta.login(page)
        insta.update_note(page, text)
        insta.browser.close()
