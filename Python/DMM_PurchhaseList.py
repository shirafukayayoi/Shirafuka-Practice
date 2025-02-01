import asyncio
import json
import os

import gspread
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from playwright.async_api import async_playwright

# .envファイルの読み込み
load_dotenv()


class DMMLibrary:
    def __init__(self, page):
        self.page = page

    async def navigate_to_library(self):
        await self.page.goto("https://www.dmm.co.jp/dc/-/mylibrary/")
        try:
            await asyncio.sleep(3)
            await self.page.click('a[href*="declared=yes"]')
            print("「はい」をクリックしました")
        except Exception as e:
            print(f"「はい」が見つかりません: {e}")
        await asyncio.sleep(4)

    async def scroll_and_collect_data(self):
        try:
            # 「×」ボタンをクリック
            await self.page.click(".silex-element-content")
            print("「×」をクリックしました")
        except Exception as e:
            print(f"「×」が見つかりません: {e}")

        # スクロール対象の要素を取得
        actions = self.page.locator(".purchasedListArea1Znew")
        if await actions.count() == 0:
            print("スクロール対象の要素が見つかりません")
            return []

        previous_scroll_height = 0

        while True:
            # 現在のスクロール位置と要素の高さを取得
            current_scroll_height = await self.page.evaluate(
                "(element) => element.scrollTop + element.clientHeight",
                await actions.element_handle(),
            )

            # スクロールを実行
            await self.page.evaluate(
                "(element) => { element.scrollTop += element.clientHeight; }",
                await actions.element_handle(),
            )
            await asyncio.sleep(1)

            # 新しいスクロール位置を取得
            new_scroll_height = await self.page.evaluate(
                "(element) => element.scrollTop + element.clientHeight",
                await actions.element_handle(),
            )

            # スクロールが終了したか確認
            if new_scroll_height == current_scroll_height:
                print("スクロールが終了しました")
                break

        # タイトル、サークル、種類を取得
        titles = await self.page.query_selector_all(".productTitle3sdi8")
        circles = await self.page.query_selector_all(".circleName209pI")
        kinds = await self.page.query_selector_all(".default3EHgn")

        titles_text = [await title.inner_text() for title in titles]
        circles_text = [await circle.inner_text() for circle in circles]
        kinds_text = [await kind.inner_text() for kind in kinds]

        length = min(len(titles_text), len(circles_text), len(kinds_text))
        data = [(titles_text[i], circles_text[i], kinds_text[i]) for i in range(length)]

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
        self.sheet = self.spreadsheet.sheet1
        self.sheet.clear()

    def write_data(self, data):
        all_data = [["タイトル", "サークル", "種類"]] + data
        self.sheet.insert_rows(all_data)

    def AutoFilter(self, data, spreadsheet_id):
        sheet = self.spreadsheet.sheet1
        last_column_num = len(data[0]) if data else 3
        print(f"最終列は{last_column_num}です")

        def num2alpha(num):
            if num <= 26:
                return chr(64 + num)
            elif num % 26 == 0:
                return num2alpha(num // 26 - 1) + chr(90)
            else:
                return num2alpha(num // 26) + chr(64 + num % 26)

        last_column_alp = num2alpha(last_column_num)
        print(f"最終列のアルファベットは{last_column_alp}です")

        requests = [
            {
                "setBasicFilter": {
                    "filter": {
                        "range": {
                            "sheetId": sheet.id,
                            "startRowIndex": 0,
                            "endRowIndex": len(data) + 1,
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


async def main():
    email = os.environ["DMM_EMAIL"]
    password = os.environ["DMM_PASSWORD"]
    spreadsheet_id = os.environ["DMM_GOOGLE_SHEET_URL"]

    login_url = "https://accounts.dmm.co.jp/service/login/password/=/path=SgVTFksZDEtUDFNKUkQfGA__"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        if os.path.exists("dmm_cookies.json"):
            with open("dmm_cookies.json", "r") as f:
                cookies = json.load(f)
            await page.context.add_cookies(cookies)
            print("クッキーを読み込みました")
        else:
            # DMMにログイン
            await page.goto(login_url)
            await page.fill('input[name="login_id"]', email)
            await page.fill('input[name="password"]', password)
            await page.click('button:text("ログイン")')
            print("ログイン完了")
            cookies = await page.context.cookies()
            with open("dmm_cookies.json", "w") as f:
                json.dump(cookies, f)
                print("クッキーを保存しました")

            await asyncio.sleep(3)

        dmm_library = DMMLibrary(page)
        await dmm_library.navigate_to_library()
        data = await dmm_library.scroll_and_collect_data()
        await browser.close()

    google_spreadsheet = GoogleSpreadsheet(spreadsheet_id)
    google_spreadsheet.write_data(data)
    google_spreadsheet.AutoFilter(data, spreadsheet_id)


if __name__ == "__main__":
    asyncio.run(main())
