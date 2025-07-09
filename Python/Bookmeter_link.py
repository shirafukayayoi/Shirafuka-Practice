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
                        found_valid_link = False
                        
                        for element in bookwalker_elements:
                            href = await element.get_attribute("href")
                            if href and "bookwalker.jp" in href:
                                
                                # キャンペーンURL、select URL、サンプルページを除外し、本の詳細ページのみを対象とする
                                if ("/select/" in href or 
                                    "/campaign/" in href or 
                                    "/special/" in href or
                                    "/fair/" in href or
                                    "/event/" in href or
                                    "sample=1" in href or
                                    "&sample=" in href or
                                    "?sample=" in href):
                                    continue  # キャンペーン系URL・サンプルページはスキップ
                                
                                # サンプルページも除外
                                if "?sample=" in href or "&sample=" in href:
                                    continue  # サンプルページはスキップ
                                
                                # 本の詳細ページのパターンをチェック
                                # 様々なUUID形式のリンクを検出
                                import re

                                # より柔軟なUUID形式のパターン
                                # 例: /de742576b8-d235-4b6f-8195-605eac63b2da/, /de1bf25fcb-e679-4407-80a0-36b446fbaee7/, /de03d378c5-06a4-47f2-8746-ce5e16b817bf/
                                uuid_patterns = [
                                    r'/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/',  # 標準的なUUID
                                    r'/[a-f0-9]{10}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/',  # 10桁開始のUUID
                                    r'/[a-f0-9]{2}[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/',  # de付きのUUID
                                ]
                                
                                is_valid_book_link = False
                                for pattern in uuid_patterns:
                                    if re.search(pattern, href):
                                        is_valid_book_link = True
                                        break
                                
                                if is_valid_book_link:
                                    clean_link = href.split("?")[0] if "?" in href else href
                                    bookwalker_links.append(clean_link)
                                    print(f"[Info] BOOK☆WALKERリンクを発見: {clean_link}")
                                    found_valid_link = True
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
        
        # リトライ機能付きでログイン処理
        retry_count = 0
        success = False
        
        while not success:
            try:
                await self.page.goto("https://member.bookwalker.jp/app/03/login")
                await self.page.fill('input[name="j_username"]', email)
                await self.page.fill('input[name="j_password"]', password)
                await self.page.click('.lt_loginBtn')
                print("[Info] BOOK☆WALKERにログインしました")
                await asyncio.sleep(20)  # ログイン後の待機
                success = True
                
            except Exception as e:
                retry_count += 1
                print(f"[Error] BOOK☆WALKERへのログインに失敗しました (試行 {retry_count}回目): {e}")
                
                # 5回を超えた場合はリセット
                if retry_count > 5:
                    print(f"[Info] ログイン試行回数が5回を超えました。一度BOOK☆WALKERトップページにアクセスしてリセットします...")
                    try:
                        await self.page.goto("https://bookwalker.jp/")
                        await asyncio.sleep(3)
                        retry_count = 0
                        print(f"[Info] リセット完了。再度ログインを試行します...")
                    except Exception as reset_error:
                        print(f"[Error] リセットに失敗しました: {reset_error}")
                        await asyncio.sleep(5)
                else:
                    print(f"[Info] 3秒待って再試行します...")
                    await asyncio.sleep(3)
        
    async def bookwalker_clickboxlink(self, bookwalker_links):
        for i, link in enumerate(bookwalker_links, 1):
            print(f"[Info] {i}/{len(bookwalker_links)} 件目のBOOK☆WALKERリンクを処理中: {link}")
            
            # リトライ機能付きでページアクセス
            retry_count = 0
            success = False
            
            while not success:
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
                    
                    # 登録済みボタンをチェック（既に登録されているかチェック）
                    unregister_button = await self.page.query_selector('button.js-own-book-unregister')
                    
                    if unregister_button:
                        print(f"[Info] 既に「持っている本として登録済み」です。スキップします: {link}")
                    else:
                        # 「持っている本として登録する」ボタンを探す
                        register_button = await self.page.query_selector('button.js-own-other-modal-open')
                        
                        if register_button:
                            print(f"[Info] 「持っている本として登録する」ボタンを発見しました")
                            await register_button.click()
                            await asyncio.sleep(2)  # モーダル表示待機
                            
                            # モーダル内の「紙書籍を書店で」ボタンをクリック
                            bookstore_button = await self.page.query_selector('button.js-own-book-register[data-action-label="bookstore"]')
                            
                            if bookstore_button:
                                await bookstore_button.click()
                                print(f"[Info] 「紙書籍を書店で」ボタンをクリックしました: {link}")
                                await asyncio.sleep(2)  # 登録完了待機
                            else:
                                print(f"[Warning] 「紙書籍を書店で」ボタンが見つかりませんでした: {link}")
                        else:
                            print(f"[Warning] 「持っている本として登録する」ボタンが見つかりませんでした: {link}")
                    
                    success = True  # 正常に処理完了
                    
                except Exception as e:
                    retry_count += 1
                    print(f"[Error] BOOK☆WALKERリンクの処理に失敗しました (試行 {retry_count}回目): {e}")
                    
                    # 5回を超えた場合はリセット
                    if retry_count > 5:
                        print(f"[Info] 試行回数が5回を超えました。一度トップページにアクセスしてリセットします...")
                        try:
                            await self.page.goto("https://bookwalker.jp/")
                            await asyncio.sleep(3)
                            retry_count = 0
                            print(f"[Info] リセット完了。再度処理を開始します...")
                        except Exception as reset_error:
                            print(f"[Error] リセットに失敗しました: {reset_error}")
                            await asyncio.sleep(5)
                    else:
                        print(f"[Info] 2秒待って再試行します...")
                        await asyncio.sleep(2)
        
            await asyncio.sleep(1)  # 次のリンク処理前の待機
        


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        scraping = Bookmeter_getLinkList(page)
        
        # Bookmeter_getLinkListのインスタンスを作成
        bookmeter_links = await scraping.get_link_list()
        print(f"[Info] Bookmeterから取得したリンク数: {len(bookmeter_links)} 件")
        
        if not bookmeter_links:
            print("[Error] Bookmeterからリンクが取得できませんでした。処理を終了します。")
            await browser.close()
            return

        bookwalker_links = await scraping.bookmeter_get_link_list(bookmeter_links)
        print(f"[Info] BOOK☆WALKERリンク数: {len(bookwalker_links)} 件")
        
        # BOOK☆WALKERリンクが取得できなかった場合の詳細情報
        if not bookwalker_links:
            print("[Warning] BOOK☆WALKERリンクが1件も取得できませんでした。")
            print("[Info] 考えられる原因:")
            print("  1. BookmeterページにBOOK☆WALKERへのリンクが存在しない")
            print("  2. UUID形式でないリンクが多い（キャンペーンURLなど）")
            print("  3. ページの読み込みエラーやタイムアウト")
            print("[Info] 処理を終了します。")
            await browser.close()
            return
        
        # BOOK☆WALKERにログイン
        print(f"[Info] BOOK☆WALKERログイン処理を開始します...")
        await scraping.bookwalker_login()
        await asyncio.sleep(1)  # ログイン後の待機
        
        # 各BOOK☆WALKERページで登録処理
        print(f"[Info] {len(bookwalker_links)} 件のBOOK☆WALKERリンクの登録処理を開始します...")
        await scraping.bookwalker_clickboxlink(bookwalker_links)
        print(f"[Info] 全ての処理が完了しました")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
