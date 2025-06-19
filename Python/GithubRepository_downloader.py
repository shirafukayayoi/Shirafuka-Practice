import os
import shutil  # shutilモジュールを追加（ディレクトリ削除用）
import time
import zipfile  # zipfileモジュールを追加

import requests
from dotenv import load_dotenv

load_dotenv()  # 関数として呼び出し

# --- 設定 ---
GITHUB_USERNAME = "shirafukayayoi"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # 環境変数からトークンを取得

DOWNLOAD_DIR = (
    "downloaded_github_repos"  # ZIPファイルの一時保存および解凍先のルートディレクトリ
)


# --- メイン処理 ---
def download_and_extract_all_github_repos(
    username, token=None, download_base_dir="downloaded_repos"
):
    if not token:
        print("[Error] Personal Access Token (PAT) が設定されていません。")
        print(
            "[Error] プライベートリポジトリへのアクセスや、APIリクエスト制限の緩和ができません。"
        )
        print(
            "[Error] 環境変数 'GITHUB_TOKEN' を設定するか、プログラム内で直接指定してください。"
        )

    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"

    # ダウンロード先のベースディレクトリが存在しない場合は作成
    if not os.path.exists(download_base_dir):
        os.makedirs(download_base_dir)
        print(
            f"[Info] ダウンロードベースディレクトリ '{download_base_dir}' を作成しました。"
        )

    page = 1
    while True:
        repos_url = (
            f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        )
        print(f"\n[Info] リポジトリ一覧をページ {page} から取得中: {repos_url}")

        response = requests.get(repos_url, headers=headers)

        if response.status_code != 200:
            print(
                f"[Error] リポジトリ一覧の取得に失敗しました。ステータスコード: {response.status_code}"
            )
            print(f"[Error] レスポンス: {response.json()}")
            break

        repos = response.json()

        if not repos:
            print("[Info] 全てのリポジトリの取得が完了しました。")
            break

        for repo in repos:
            repo_name = repo["name"]

            # デバッグ: リポジトリの詳細情報を確認
            print(f"[Info] リポジトリ '{repo_name}' の情報:")
            print(f"[Info]   フォーク: {repo.get('fork', False)}")
            print(f"[Info]   アーカイブ済み: {repo.get('archived', False)}")
            print(f"[Info]   プライベート: {repo.get('private', False)}")

            # zipball_url の存在確認と代替手段の検討
            zip_url = None
            if "zipball_url" in repo and repo["zipball_url"]:
                zip_url = repo["zipball_url"]
                print(f"[Info]   zipball_url使用: {zip_url}")
            elif "archive_url" in repo and repo["archive_url"]:
                # archive_url がある場合は zipball 形式に変換
                archive_url = repo["archive_url"]
                zip_url = archive_url.replace("{archive_format}{/ref}", "zipball/main")
                print(f"[Info]   archive_url から zipball_url を生成: {zip_url}")
            elif "html_url" in repo and repo["html_url"]:
                # html_url から直接 zipball URL を生成
                html_url = repo["html_url"]
                zip_url = f"{html_url}/archive/refs/heads/main.zip"
                print(f"[Info]   html_url から zipball_url を生成: {zip_url}")
            else:
                print(
                    f"[Error] リポジトリ '{repo_name}' のダウンロードURLを取得できません。スキップします。"
                )
                continue

            temp_zip_file = f"{repo_name}.zip"  # 一時的に保存するZIPファイル名

            # 解凍先のディレクトリをリポジトリ名にする
            extract_path = os.path.join(download_base_dir, repo_name)
            # 一時ZIPファイルの保存パス
            temp_zip_save_path = os.path.join(download_base_dir, temp_zip_file)

            print(f"[Info] リポジトリ '{repo_name}' の処理を開始します...")

            # 既に解凍済みのディレクトリが存在する場合は、スキップするか削除するか選択できます。
            # 今回は、既に存在する場合は「スキップ」します。
            if os.path.exists(extract_path):
                print(f"[Info] '{extract_path}' は既に存在します。スキップします。")
                continue  # 次のリポジトリへ

            try:
                # 1. ZIPファイルをダウンロード
                print(f"[Info] '{repo_name}' のZIPファイルをダウンロード中...")
                repo_response = requests.get(zip_url, headers=headers, stream=True)
                if repo_response.status_code == 200:
                    with open(temp_zip_save_path, "wb") as f:
                        for chunk in repo_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(
                        f"[Info] ZIPファイルを '{temp_zip_save_path}' に保存しました。"
                    )

                    # 2. ZIPファイルを解凍
                    print(f"[Info] '{temp_zip_save_path}' を解凍中...")
                    with zipfile.ZipFile(temp_zip_save_path, "r") as zip_ref:
                        # ZIPファイル内のルートディレクトリ名を取得
                        # GitHubのzipballは通常、リポジトリ名-コミットハッシュのようなルートディレクトリを持つ
                        # 例: user-repo-abcdef1234567890/
                        first_dir = next(
                            (item for item in zip_ref.namelist() if "/" in item), None
                        )
                        if first_dir:
                            # ルートディレクトリ部分だけを取得 (例: user-repo-abcdef1234567890)
                            extracted_root_name = first_dir.split("/")[0]

                            # ターゲットのディレクトリに解凍
                            zip_ref.extractall(
                                download_base_dir
                            )  # まずベースディレクトリに解凍

                            # 解凍されたルートディレクトリのパス
                            extracted_full_path = os.path.join(
                                download_base_dir, extracted_root_name
                            )

                            # 目的のリポジトリ名を持つディレクトリに移動 (リネーム)
                            if os.path.exists(extracted_full_path):
                                os.rename(extracted_full_path, extract_path)
                                print(
                                    f"[Info] '{extracted_full_path}' を '{extract_path}' にリネームしました。"
                                )
                            else:
                                print(
                                    f"[Error] 解凍されたルートディレクトリが見つかりませんでした: '{extracted_full_path}'"
                                )
                        else:
                            # ZIPファイル内にルートディレクトリがない場合（稀ですが念のため）
                            zip_ref.extractall(extract_path)
                            print(
                                f"[Info] ZIPファイルを直接 '{extract_path}' に解凍しました。"
                            )

                    # 3. 一時的なZIPファイルを削除（Windowsでのアクセス拒否エラー対策）
                    print(f"[Info] 一時ZIPファイル '{temp_zip_save_path}' を削除中...")
                    max_retries = 5
                    for attempt in range(max_retries):
                        try:
                            # ファイルの属性をリセットしてから削除
                            if os.path.exists(temp_zip_save_path):
                                os.chmod(
                                    temp_zip_save_path, 0o777
                                )  # 書き込み権限を付与
                                os.remove(temp_zip_save_path)
                                print(
                                    f"[Info] 一時ZIPファイル '{temp_zip_save_path}' を削除しました。"
                                )
                                break
                        except PermissionError as pe:
                            if attempt < max_retries - 1:
                                print(
                                    f"[Error] 削除に失敗しました（試行 {attempt + 1}/{max_retries}）: {pe}"
                                )
                                print(
                                    f"[Info] {1 + attempt} 秒待機してから再試行します..."
                                )
                                time.sleep(1 + attempt)  # 待機時間を徐々に延長
                            else:
                                print(
                                    f"[Error] 一時ZIPファイル '{temp_zip_save_path}' の削除に失敗しました: {pe}"
                                )
                                print(f"[Error] 手動で削除してください。")
                        except Exception as e:
                            print(f"[Error] 削除中に予期せぬエラーが発生しました: {e}")
                            break

                else:
                    print(
                        f"[Error] '{repo_name}' のZIPダウンロードに失敗しました。ステータスコード: {repo_response.status_code}"
                    )
            except zipfile.BadZipFile:
                print(f"[Error] '{temp_zip_save_path}' は不正なZIPファイルです。")
            except Exception as e:
                print(f"[Error] 処理中に予期せぬエラーが発生しました: {e}")
            finally:
                # 処理が終わったら一時ZIPファイルが存在していたら削除（リトライ機能付き）
                if os.path.exists(temp_zip_save_path):
                    print(
                        f"[Info] 最終クリーンアップ: '{temp_zip_save_path}' の削除を試行します..."
                    )
                    max_final_retries = 3
                    for attempt in range(max_final_retries):
                        try:
                            os.chmod(temp_zip_save_path, 0o777)
                            os.remove(temp_zip_save_path)
                            print(
                                f"[Info] 最終クリーンアップ完了: '{temp_zip_save_path}' を削除しました。"
                            )
                            break
                        except (PermissionError, FileNotFoundError):
                            if attempt < max_final_retries - 1:
                                time.sleep(2)  # より長く待機
                            else:
                                print(
                                    f"[Error] 最終クリーンアップに失敗しました。ファイル '{temp_zip_save_path}' が残存している可能性があります。"
                                )

            # GitHub API のレート制限に配慮するため、少し待機する
            time.sleep(0.1)  # 必要に応じて調整

        page += 1
        time.sleep(1)  # ページごとに少し待機

    print("\n[Info] 全リポジトリのダウンロードと解凍処理が完了しました。")


if __name__ == "__main__":
    download_and_extract_all_github_repos(GITHUB_USERNAME, GITHUB_TOKEN, DOWNLOAD_DIR)
