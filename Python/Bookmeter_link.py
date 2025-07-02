import asyncio
import json
import os

from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()


class Bookmeter_getLinkList:
    def __init__(self, page):
        self.page = page

    async def get_link_list(self):
        # 本のタイトルリンクを取得
        all_title_links = []
        
        # 読んだ本のリストを取得
        await self.page.goto("https://bookmeter.com/users/1291485/books/read")
        print("[Info] 読んだ本のページを処理中...")
        
        # ページリンクの取得
        try:
            selector = ".bm-pagination__link"
            pagination_links = await self.page.query_selector_all(selector)
            last_page_link = await pagination_links[-1].get_attribute("href")
            print(f"[Info] 読んだ本の最終ページリンク: {last_page_link}")
        except Exception as e:
            print(f"[Error] 読んだ本のページリンクの取得に失敗しました: {e}")
            return
        
        # 読んだ本のリンクを取得
        for i in range(1,int(last_page_link.split("page=")[-1]) + 1):
            page_url = f"https://bookmeter.com/users/1291485/books/read?page={i}"
            await self.page.goto(page_url)
            print(f"[Info] 読んだ本のページ {i} を読み込みました")

            # 各ページの本のタイトルリンクを取得
            success = False
            retry_count = 0
            
            while not success:
                try:
                    title_links = await self.page.query_selector_all(".detail__title a")
                    if not title_links:
                        retry_count += 1
                        print(f"[Warning] 読んだ本のページ {i} には本のタイトルリンクが見つかりませんでした (試行 {retry_count}回目)")
                        print(f"[Info] 2秒待って再試行します...")
                        await asyncio.sleep(2)
                        continue
                    
                    # リンクが見つかった場合の処理
                    for link in title_links:
                        href = await link.get_attribute("href")
                        full_link = "https://bookmeter.com" + href if href else None
                        # hrefが存在する場合のみ追加
                        if full_link:
                            all_title_links.append(full_link)
                            print(f"[Info] 読んだ本のタイトルリンクを取得しました: {full_link}")
                    await asyncio.sleep(0.5)  # 少し待機してから次の処理へ
                    success = True
                    
                except Exception as e:
                    retry_count += 1
                    print(f"[Error] 読んだ本のタイトルリンクの取得に失敗しました (試行 {retry_count}回目): {e}")
                    print(f"[Info] 2秒待って再試行します...")
                    await asyncio.sleep(2)

        print(f"[Info] 読んだ本の取得完了: {len(all_title_links)} 件")
        
        # 積読本のリストを取得
        await self.page.goto("https://bookmeter.com/users/1291485/books/stacked")
        print("[Info] 積読本のページを処理中...")
        
        # 積読本のページリンクの取得
        try:
            selector = ".bm-pagination__link"
            pagination_links = await self.page.query_selector_all(selector)
            if pagination_links:
                last_page_link = await pagination_links[-1].get_attribute("href")
                print(f"[Info] 積読本の最終ページリンク: {last_page_link}")
                max_page = int(last_page_link.split("page=")[-1])
            else:
                print("[Info] 積読本のページネーションが見つかりません。1ページのみ処理します。")
                max_page = 1
        except Exception as e:
            print(f"[Error] 積読本のページリンクの取得に失敗しました: {e}")
            max_page = 1
        
        # 積読本のリンクを取得
        for i in range(1, max_page + 1):
            page_url = f"https://bookmeter.com/users/1291485/books/stacked?page={i}"
            await self.page.goto(page_url)
            print(f"[Info] 積読本のページ {i} を読み込みました")

            # 各ページの本のタイトルリンクを取得
            success = False
            retry_count = 0
            
            while not success:
                try:
                    title_links = await self.page.query_selector_all(".detail__title a")
                    if not title_links:
                        retry_count += 1
                        print(f"[Warning] 積読本のページ {i} には本のタイトルリンクが見つかりませんでした (試行 {retry_count}回目)")
                        print(f"[Info] 2秒待って再試行します...")
                        await asyncio.sleep(2)
                        continue
                    
                    # リンクが見つかった場合の処理
                    for link in title_links:
                        href = await link.get_attribute("href")
                        full_link = "https://bookmeter.com" + href if href else None
                        # hrefが存在する場合のみ追加
                        if full_link:
                            all_title_links.append(full_link)
                            print(f"[Info] 積読本のタイトルリンクを取得しました: {full_link}")
                    await asyncio.sleep(0.5)  # 少し待機してから次の処理へ
                    success = True
                    
                except Exception as e:
                    retry_count += 1
                    print(f"[Error] 積読本のタイトルリンクの取得に失敗しました (試行 {retry_count}回目): {e}")
                    print(f"[Info] 2秒待って再試行します...")
                    await asyncio.sleep(2)

        print(f"[Info] 積読本の取得完了: 追加で {len(all_title_links) - (len(all_title_links) - len([link for link in all_title_links if 'stacked' in str(link)]))} 件")
        
        # 取得したリンクの総数を表示
        print(f"[Info] 全体の取得完了: 読んだ本 + 積読本 = 全 {len(all_title_links)} 件の本のリンクを取得しました")
        return all_title_links

    async def bookmeter_get_link_list(self, bookmeter_get_link_list):
        bookwalker_links = []
        
        for i, link in enumerate(bookmeter_get_link_list, 1):
            print(f"[Info] {i}/{len(bookmeter_get_link_list)} 件目のページを処理中: {link}")
            
            # リトライ機能付きでページアクセス
            retry_count = 0
            success = False
            
            while not success:
                try:
                    await self.page.goto(link)
                    await asyncio.sleep(1)  # ページ読み込み待機
                    
                    # BOOK☆WALKERのリンクを探す
                    bookwalker_elements = await self.page.query_selector_all('a[href*="bookwalker.jp"]')
                    
                    if bookwalker_elements:
                        for element in bookwalker_elements:
                            href = await element.get_attribute("href")
                            if href and "bookwalker.jp" in href:
                                clean_link = href.split("?")[0] if "?" in href else href
                                bookwalker_links.append(clean_link)
                                print(f"[Info] BOOK☆WALKERリンクを発見: {clean_link}")
                                break
                        success = True
                    else:
                        # BOOK☆WALKERリンクが見つからない場合、サーバーエラーをチェック
                        page_content = await self.page.content()
                        if "サーバーエラー" in page_content:
                            retry_count += 1
                            print(f"[Warning] サーバーエラーが検出されました (試行 {retry_count}回目)")
                            print(f"[Info] 12秒待って再試行します...")
                            await asyncio.sleep(12)
                            continue
                        else:
                            print(f"[Warning] BOOK☆WALKERリンクが見つかりませんでした")
                            success = True  # リンクがない場合も成功とみなして次へ
                    
                except Exception as e:
                    retry_count += 1
                    print(f"[Error] ページアクセスに失敗しました (試行 {retry_count}回目): {e}")
                    print(f"[Info] 1秒待って再試行します...")
                    await asyncio.sleep(1)
        
            await asyncio.sleep(1)  # リクエスト間隔を空ける
        
        print(f"[Info] BOOK☆WALKERリンク取得完了: 全 {len(bookwalker_links)} 件のリンクを取得しました")
        await asyncio.sleep(1)  # 最後の待機
        return bookwalker_links
        
    async def bookwalker_login(self):
        password = os.getenv("BOOKWALKER_PASSWORD")
        if not password:
            print("[Error] BOOK☆WALKERのパスワードが環境変数に設定されていません")
            return
        email = os.getenv("BOOKWALKER_EMAIL")
        if not email:
            print("[Error] BOOK☆WALKERのメールアドレスが環境変数に設定されていません")
            return
        
        await self.page.goto("https://member.bookwalker.jp/app/03/login")
        try:
            await self.page.fill('input[name="j_username"]', email)
            await self.page.fill('input[name="j_password"]', password)
            await self.page.click('.lt_loginBtn')
            print("[Info] BOOK☆WALKERにログインしました")
            await asyncio.sleep(20)  # ログイン後の待機
        except Exception as e:
            print(f"[Error] BOOK☆WALKERへのログインに失敗しました: {e}")
        
    async def bookwalker_clickboxlink(self, bookwalker_links):
        for i, link in enumerate(bookwalker_links, 1):
            print(f"[Info] {i}/{len(bookwalker_links)} 件目のBOOK☆WALKERリンクを処理中: {link}")
            try:
                await self.page.goto(link)
                await asyncio.sleep(2)  # ページ読み込み待機
                
                # ログインボタンが存在するかチェック
                login_button = await self.page.query_selector('a[data-action-label="member_login"]')
                if login_button:
                    print(f"[Info] ログインボタンが見つかりました。クリックします...")
                    await login_button.click()
                    await asyncio.sleep(3)  # ログイン処理後の待機
                    print(f"[Info] ログインボタンをクリックしました。元のページに戻ります...")
                    
                    # 元のページに戻る
                    await self.page.goto(link)
                    await asyncio.sleep(2)  # ページ読み込み待機
            
                await asyncio.sleep(2)  # リロード後の待機
                
                # チェックボタンを探す
                check_button = await self.page.query_selector('button.t-c-check-list-button.js-check-list')
                
                if check_button:
                    # ボタンのクラスを確認してチェック状態を判定
                    button_classes = await check_button.get_attribute('class')
                    is_checked = '--checked' in button_classes if button_classes else False
                    
                    if is_checked:
                        print(f"[Info] 既にチェック済みです。スキップします: {link}")
                    else:
                        # チェックされていない場合はクリック
                        await check_button.click()
                        print(f"[Info] チェックボタンをクリックしました: {link}")
                        await asyncio.sleep(1)  # クリック後の待機
                else:
                    print(f"[Warning] チェックボタンが見つかりませんでした: {link}")
                
            except Exception as e:
                print(f"[Error] BOOK☆WALKERリンクの処理に失敗しました: {e}")
    
        await asyncio.sleep(1)  # 次のリンク処理前の待機
        


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        scraping = Bookmeter_getLinkList(page)
        # Bookmeter_getLinkListのインスタンスを作成
        bookmeter_links = await scraping.get_link_list()

        bookwalker_links = await scraping.bookmeter_get_link_list(bookmeter_links)
        await asyncio.sleep(1)  # リンク取得後の待機
        await scraping.bookwalker_login()
        await asyncio.sleep(1)  # ログイン後の待機
        await scraping.bookwalker_clickboxlink(bookwalker_links)


if __name__ == "__main__":
    asyncio.run(main())
