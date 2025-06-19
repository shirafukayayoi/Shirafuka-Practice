import os
import shutil
import time
import zipfile

import requests
from dotenv import load_dotenv

load_dotenv()

# --- 設定 ---
GITHUB_USERNAME = "shirafukayayoi"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

DOWNLOAD_DIR = "Downloaded_github_repos"


# --- メイン処理 ---
def download_and_extract_all_github_repos(
    username, token=None, download_base_dir="downloaded_repos"
):
    error_repos = []
    
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

    if not os.path.exists(download_base_dir):
        os.makedirs(download_base_dir)
        print(
            f"[Info] ダウンロードベースディレクトリ '{download_base_dir}' を作成しました。"
        )
    
    page = 1
    while True:
        # プライベートリポジトリも含めて取得するには /user/repos を使用
        if token:
            repos_url = f"https://api.github.com/user/repos?per_page=100&page={page}&affiliation=owner"
            print(f"\n[Info] 認証されたユーザーのリポジトリ一覧をページ {page} から取得中: {repos_url}")
        else:
            repos_url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
            print(f"\n[Info] 公開リポジトリ一覧をページ {page} から取得中: {repos_url}")

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

            print(f"[Info] リポジトリ '{repo_name}' の情報:")
            print(f"[Info]   フォーク: {repo.get('fork', False)}")
            print(f"[Info]   アーカイブ済み: {repo.get('archived', False)}")
            print(f"[Info]   プライベート: {repo.get('private', False)}")
            
            zip_url = None
            if "zipball_url" in repo and repo["zipball_url"]:
                zip_url = repo["zipball_url"]
                print(f"[Info]   zipball_url使用: {zip_url}")
            elif "archive_url" in repo and repo["archive_url"]:
                archive_url = repo["archive_url"]
                zip_url = archive_url.replace("{archive_format}{/ref}", "zipball/main")
                print(f"[Info]   archive_url から zipball_url を生成: {zip_url}")
            elif "html_url" in repo and repo["html_url"]:
                html_url = repo["html_url"]
                zip_url = f"{html_url}/archive/refs/heads/main.zip"
                print(f"[Info]   html_url から zipball_url を生成: {zip_url}")
            else:
                print(
                    f"[Error] リポジトリ '{repo_name}' のダウンロードURLを取得できません。スキップします。"
                )
                error_repos.append({
                    "name": repo_name, 
                    "error": "ダウンロードURLを取得できません",
                    "repo": repo,
                    "headers": headers,
                    "download_base_dir": download_base_dir
                })
                continue

            temp_zip_file = f"{repo_name}.zip"

            extract_path = os.path.join(download_base_dir, repo_name)
            temp_zip_save_path = os.path.join(download_base_dir, temp_zip_file)

            print(f"[Info] リポジトリ '{repo_name}' の処理を開始します...")

            if os.path.exists(extract_path):
                print(f"[Info] '{extract_path}' は既に存在します。スキップします。")
                continue

            try:
                print(f"[Info] '{repo_name}' のZIPファイルをダウンロード中...")
                repo_response = requests.get(zip_url, headers=headers, stream=True)
                if repo_response.status_code == 200:
                    with open(temp_zip_save_path, "wb") as f:
                        for chunk in repo_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(
                        f"[Info] ZIPファイルを '{temp_zip_save_path}' に保存しました。"
                    )

                    print(f"[Info] '{temp_zip_save_path}' を解凍中...")
                    with zipfile.ZipFile(temp_zip_save_path, "r") as zip_ref:
                        first_dir = next(
                            (item for item in zip_ref.namelist() if "/" in item), None
                        )
                        if first_dir:
                            extracted_root_name = first_dir.split("/")[0]

                            zip_ref.extractall(download_base_dir)

                            extracted_full_path = os.path.join(
                                download_base_dir, extracted_root_name
                            )

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
                            zip_ref.extractall(extract_path)
                            print(
                                f"[Info] ZIPファイルを直接 '{extract_path}' に解凍しました。"
                            )

                    print(f"[Info] 一時ZIPファイル '{temp_zip_save_path}' を削除中...")
                    max_retries = 5
                    for attempt in range(max_retries):
                        try:
                            if os.path.exists(temp_zip_save_path):
                                os.chmod(temp_zip_save_path, 0o777)
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
                                time.sleep(1 + attempt)
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
                    error_repos.append({
                        "name": repo_name, 
                        "error": f"ZIPダウンロードに失敗 (ステータスコード: {repo_response.status_code})",
                        "repo": repo,
                        "headers": headers,
                        "download_base_dir": download_base_dir,
                        "zip_url": zip_url
                    })
            except zipfile.BadZipFile:
                print(f"[Error] '{temp_zip_save_path}' は不正なZIPファイルです。")
                error_repos.append({
                    "name": repo_name, 
                    "error": "不正なZIPファイル",
                    "repo": repo,
                    "headers": headers,
                    "download_base_dir": download_base_dir,
                    "zip_url": zip_url
                })
            except Exception as e:
                print(f"[Error] 処理中に予期せぬエラーが発生しました: {e}")
                error_repos.append({
                    "name": repo_name, 
                    "error": f"予期せぬエラー: {str(e)}",
                    "repo": repo,
                    "headers": headers,
                    "download_base_dir": download_base_dir,
                    "zip_url": zip_url if 'zip_url' in locals() else None
                })
            finally:
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
                            else:                                print(
                                    f"[Error] 最終クリーンアップに失敗しました。ファイル '{temp_zip_save_path}' が残存している可能性があります。"
                                )

            time.sleep(0.1)

        page += 1
        time.sleep(1)

    print("\n[Info] 全リポジトリのダウンロードと解凍処理が完了しました。")
    
    if error_repos:
        print(f"\n[Error] 以下の {len(error_repos)} 個のリポジトリでエラーが発生しました:")
        print("=" * 60)
        for error_repo in error_repos:
            print(f"[Error] リポジトリ: {error_repo['name']}")
            print(f"[Error] エラー内容: {error_repo['error']}")
            print("-" * 40)
        print("=" * 60)
        
        print(f"\n[Info] エラーしたリポジトリの再試行を開始します...")
        retry_error_repos(error_repos)
    else:
        print("[Info] 全てのリポジトリが正常に処理されました。")


def retry_error_repos(error_repos):
    """エラーが発生したリポジトリの再試行処理"""
    successful_retries = []
    failed_retries = []
    
    for error_repo in error_repos:
        repo_name = error_repo['name']
        print(f"\n[Info] リポジトリ '{repo_name}' の再試行を開始します...")
        
        # 再試行に必要な情報を取得
        repo = error_repo.get('repo')
        headers = error_repo.get('headers', {})
        download_base_dir = error_repo.get('download_base_dir', 'downloaded_repos')
        
        if not repo:
            print(f"[Error] リポジトリ '{repo_name}' の情報が不完全です。再試行をスキップします。")
            failed_retries.append({"name": repo_name, "error": "リポジトリ情報が不完全"})
            continue
        
        # 解凍先のディレクトリが既に存在するかチェック
        extract_path = os.path.join(download_base_dir, repo_name)
        if os.path.exists(extract_path):
            print(f"[Info] '{extract_path}' は既に存在します。再試行をスキップします。")
            successful_retries.append(repo_name)
            continue
        
        # ダウンロード試行
        success = retry_single_repo(repo, headers, download_base_dir)
        if success:
            successful_retries.append(repo_name)
            print(f"[Info] リポジトリ '{repo_name}' の再試行が成功しました。")
        else:
            failed_retries.append({"name": repo_name, "error": "再試行でも失敗"})
            print(f"[Error] リポジトリ '{repo_name}' の再試行が失敗しました。")
    
    # 再試行結果の表示
    print(f"\n[Info] 再試行結果:")
    print(f"[Info] 成功: {len(successful_retries)} 個")
    print(f"[Info] 失敗: {len(failed_retries)} 個")
    
    if successful_retries:
        print(f"\n[Info] 再試行で成功したリポジトリ:")
        for repo_name in successful_retries:
            print(f"[Info] - {repo_name}")
    
    if failed_retries:
        print(f"\n[Error] 再試行でも失敗したリポジトリ:")
        for failed_repo in failed_retries:
            print(f"[Error] - {failed_repo['name']}: {failed_repo['error']}")


def retry_single_repo(repo, headers, download_base_dir):
    """単一のリポジトリの再試行処理"""
    repo_name = repo["name"]
    
    zip_url = None
    if "zipball_url" in repo and repo["zipball_url"]:
        zip_url = repo["zipball_url"]
    elif "archive_url" in repo and repo["archive_url"]:
        archive_url = repo["archive_url"]
        zip_url = archive_url.replace("{archive_format}{/ref}", "zipball/main")
    elif "html_url" in repo and repo["html_url"]:
        html_url = repo["html_url"]
        zip_url = f"{html_url}/archive/refs/heads/main.zip"
    
    if not zip_url:
        print(f"[Error] リポジトリ '{repo_name}' のダウンロードURLを取得できません。")
        return False
    
    temp_zip_file = f"{repo_name}.zip"
    extract_path = os.path.join(download_base_dir, repo_name)
    temp_zip_save_path = os.path.join(download_base_dir, temp_zip_file)
    
    try:
        # ZIPファイルをダウンロード
        print(f"[Info] '{repo_name}' のZIPファイルを再ダウンロード中...")
        repo_response = requests.get(zip_url, headers=headers, stream=True)
        if repo_response.status_code == 200:
            with open(temp_zip_save_path, "wb") as f:
                for chunk in repo_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # ZIPファイルを解凍
            print(f"[Info] '{temp_zip_save_path}' を解凍中...")
            with zipfile.ZipFile(temp_zip_save_path, "r") as zip_ref:
                first_dir = next(
                    (item for item in zip_ref.namelist() if "/" in item), None
                )
                if first_dir:
                    extracted_root_name = first_dir.split("/")[0]
                    zip_ref.extractall(download_base_dir)
                    extracted_full_path = os.path.join(download_base_dir, extracted_root_name)
                    
                    if os.path.exists(extracted_full_path):
                        os.rename(extracted_full_path, extract_path)
                        print(f"[Info] '{extracted_full_path}' を '{extract_path}' にリネームしました。")
                    else:
                        print(f"[Error] 解凍されたルートディレクトリが見つかりませんでした: '{extracted_full_path}'")
                        return False
                else:
                    zip_ref.extractall(extract_path)
            
            try:
                if os.path.exists(temp_zip_save_path):
                    os.chmod(temp_zip_save_path, 0o777)
                    os.remove(temp_zip_save_path)
            except Exception as e:
                print(f"[Warning] 一時ZIPファイルの削除に失敗: {e}")
            
            return True
        else:
            print(f"[Error] '{repo_name}' のZIPダウンロードに失敗しました。ステータスコード: {repo_response.status_code}")
            return False
            
    except zipfile.BadZipFile:
        print(f"[Error] '{temp_zip_save_path}' は不正なZIPファイルです。")
        return False
    except Exception as e:
        print(f"[Error] 処理中に予期せぬエラーが発生しました: {e}")
        return False
    finally:
        if os.path.exists(temp_zip_save_path):
            try:
                os.chmod(temp_zip_save_path, 0o777)
                os.remove(temp_zip_save_path)
            except:
                pass


if __name__ == "__main__":
    download_and_extract_all_github_repos(GITHUB_USERNAME, GITHUB_TOKEN, DOWNLOAD_DIR)
