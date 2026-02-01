"""
Tools Auto Updater
GitHub Releases APIを使用してToolsフォルダー内のツールを最新版に自動更新するスクリプト
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psutil
import requests
from dotenv import load_dotenv

# スクリプトのディレクトリを基準にパスを設定
SCRIPT_DIR = Path(__file__).parent.resolve()
WORKSPACE_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = WORKSPACE_ROOT / "settings" / "tools_config.json"

# 環境変数の読み込み
load_dotenv(SCRIPT_DIR / ".env")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


class ToolUpdater:
    """ツール更新を管理するクラス"""

    def __init__(self, config_path: Path):
        """
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path
        self.tools_config = self._load_config()
        self.session = requests.Session()

        # GitHub API認証設定
        # 認証エラーを防ぐため、トークンは任意設定とする
        if GITHUB_TOKEN:
            # Classic token: "ghp_" で始まる
            # Fine-grained token: "github_pat_" で始まる
            # 両方とも Bearer または token 形式で使用可能
            auth_header = f"token {GITHUB_TOKEN}" if GITHUB_TOKEN.startswith("ghp_") else f"Bearer {GITHUB_TOKEN}"
            self.session.headers.update({
                "Authorization": auth_header,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            })
            print("[Info] GitHub認証を使用します（レート制限: 5000リクエスト/時）")
        else:
            self.session.headers.update({
                "Accept": "application/vnd.github+json",
            })
            print(
                "[Info] GitHub認証なしで実行します（レート制限: 60リクエスト/時）"
            )
            print("[Info] レート制限を緩和するには、.envにGITHUB_TOKENを設定してください")

    def _load_config(self) -> List[Dict]:
        """設定ファイルを読み込む

        Returns:
            ツール設定のリスト

        Raises:
            FileNotFoundError: 設定ファイルが見つからない場合
            json.JSONDecodeError: JSON解析に失敗した場合
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"設定ファイルが見つかりません: {self.config_path}"
            )

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        if not isinstance(config, list):
            raise ValueError("設定ファイルは配列形式である必要があります")

        return config

    def _is_process_running(self, process_name: str) -> bool:
        """指定されたプロセスが実行中かチェック

        Args:
            process_name: プロセス名（例: "yt-dlp.exe"）

        Returns:
            実行中の場合True
        """
        for process in psutil.process_iter(["name"]):
            try:
                if process.info["name"] and process.info["name"].lower() == process_name.lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def _get_current_version(self, tool_path: Path, version_command: List[str]) -> Optional[str]:
        """現在インストールされているツールのバージョンを取得

        Args:
            tool_path: ツールの実行ファイルパス
            version_command: バージョン確認コマンドの引数リスト

        Returns:
            バージョン文字列（取得失敗時はNone）
        """
        if not tool_path.exists():
            return None

        try:
            result = subprocess.run(
                [str(tool_path)] + version_command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return version
            else:
                print(f"[Warning] バージョン取得失敗: {result.stderr.strip()}")
                return None
        except FileNotFoundError:
            return None
        except subprocess.TimeoutExpired:
            print(f"[Warning] バージョン取得がタイムアウトしました: {tool_path}")
            return None
        except Exception as e:
            print(f"[Warning] バージョン取得エラー: {e}")
            return None

    def _get_latest_release(self, repo: str) -> Optional[Dict]:
        """GitHub Releases APIから最新リリース情報を取得

        Args:
            repo: リポジトリ名（例: "yt-dlp/yt-dlp"）

        Returns:
            リリース情報のDict（取得失敗時はNone）
        """
        url = f"https://api.github.com/repos/{repo}/releases/latest"

        try:
            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print(f"[Error] リポジトリが見つかりません: {repo}")
                return None
            elif response.status_code == 401:
                print(f"[Warning] GitHub認証に失敗しました。トークンが無効か期限切れの可能性があります。")
                print(f"[Info] 認証なしで再試行します...")
                # 認証なしで再試行
                if GITHUB_TOKEN:
                    retry_response = requests.get(url, timeout=30, headers={"Accept": "application/vnd.github+json"})
                    if retry_response.status_code == 200:
                        return retry_response.json()
                return None
            elif response.status_code == 403:
                print(
                    f"[Error] APIレート制限に達しました。しばらく待ってから再試行してください。"
                )
                # レート制限情報を表示
                if "X-RateLimit-Reset" in response.headers:
                    reset_time = int(response.headers["X-RateLimit-Reset"])
                    import datetime
                    reset_datetime = datetime.datetime.fromtimestamp(reset_time)
                    print(f"[Info] リセット時刻: {reset_datetime}")
                return None
            else:
                print(
                    f"[Error] リリース情報の取得に失敗しました: {response.status_code}"
                )
                return None
        except requests.exceptions.RequestException as e:
            print(f"[Error] ネットワークエラー: {e}")
            return None

    def _download_file(
        self, url: str, dest_path: Path, retry_count: int = 3
    ) -> bool:
        """ファイルをダウンロード

        Args:
            url: ダウンロードURL
            dest_path: 保存先パス
            retry_count: リトライ回数

        Returns:
            成功時True、失敗時False
        """
        for attempt in range(retry_count):
            try:
                print(f"[Info] ダウンロード中... ({attempt + 1}/{retry_count})")

                response = self.session.get(url, stream=True, timeout=60)
                response.raise_for_status()

                # ファイルサイズを取得
                total_size = int(response.headers.get("content-length", 0))
                downloaded_size = 0

                with open(dest_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)

                            # 進捗表示（10%刻み）
                            if total_size > 0:
                                progress = int((downloaded_size / total_size) * 100)
                                if progress % 10 == 0:
                                    print(
                                        f"[Info] ダウンロード進捗: {progress}%",
                                        end="\r",
                                    )

                print(f"\n[Info] ダウンロード完了: {dest_path}")
                return True

            except requests.exceptions.RequestException as e:
                print(f"[Warning] ダウンロード失敗 (試行 {attempt + 1}/{retry_count}): {e}")
                if attempt < retry_count - 1:
                    time.sleep(2)
                else:
                    print(f"[Error] ダウンロードに失敗しました: {url}")
                    return False

        return False

    def _safe_update_file(
        self, source_path: Path, target_path: Path, backup_suffix: str = ".bak"
    ) -> bool:
        """ファイルを安全に更新（バックアップ→置き換え→バックアップ削除）

        Args:
            source_path: 新しいファイルのパス
            target_path: 置き換え対象のファイルパス
            backup_suffix: バックアップファイルの接尾辞

        Returns:
            成功時True、失敗時False
        """
        backup_path = target_path.with_suffix(target_path.suffix + backup_suffix)

        try:
            # 既存ファイルが存在する場合はバックアップ
            if target_path.exists():
                shutil.copy2(target_path, backup_path)
                print(f"[Info] バックアップ作成: {backup_path.name}")

            # ファイルを置き換え
            os.replace(source_path, target_path)
            print(f"[Info] ファイル更新完了: {target_path}")

            # バックアップを削除
            if backup_path.exists():
                backup_path.unlink()
                print(f"[Info] バックアップ削除: {backup_path.name}")

            return True

        except Exception as e:
            print(f"[Error] ファイル更新失敗: {e}")

            # エラー時はバックアップから復元を試みる
            if backup_path.exists():
                try:
                    shutil.copy2(backup_path, target_path)
                    print(f"[Info] バックアップから復元しました: {target_path}")
                    backup_path.unlink()
                except Exception as restore_error:
                    print(f"[Error] 復元にも失敗しました: {restore_error}")

            return False

    def check_version(self, tool_name: Optional[str] = None) -> None:
        """ツールのバージョンを確認

        Args:
            tool_name: 確認するツール名（Noneの場合は全ツール）
        """
        tools_to_check = (
            [t for t in self.tools_config if t["name"] == tool_name]
            if tool_name
            else self.tools_config
        )

        if not tools_to_check:
            print(f"[Error] ツールが見つかりません: {tool_name}")
            return

        for tool in tools_to_check:
            if not tool.get("enabled", True):
                print(f"[Info] {tool['name']}: 無効化されています")
                continue

            print(f"\n{'='*60}")
            print(f"ツール: {tool['name']}")
            print(f"説明: {tool.get('description', 'N/A')}")
            print(f"リポジトリ: {tool['repo']}")

            # 現在のバージョン確認
            install_path = WORKSPACE_ROOT / tool["install_path"]
            current_version = self._get_current_version(
                install_path, tool.get("version_command", ["--version"])
            )

            if current_version:
                print(f"現在のバージョン: {current_version}")
            else:
                print("現在のバージョン: インストールされていません")

            # 最新バージョン確認
            release = self._get_latest_release(tool["repo"])
            if release:
                latest_version = release.get("tag_name", "不明")
                print(f"最新のバージョン: {latest_version}")

                if current_version and current_version == latest_version:
                    print("[Info] 最新版です")
                elif current_version:
                    print("[Info] 更新が利用可能です")
                else:
                    print("[Info] インストールが必要です")
            else:
                print("最新のバージョン: 取得失敗")

    def update_tool(self, tool_name: str) -> bool:
        """指定されたツールを更新

        Args:
            tool_name: 更新するツール名

        Returns:
            成功時True、失敗時False
        """
        # 設定を検索
        tool_config = next((t for t in self.tools_config if t["name"] == tool_name), None)

        if not tool_config:
            print(f"[Error] ツールが見つかりません: {tool_name}")
            return False

        if not tool_config.get("enabled", True):
            print(f"[Info] {tool_name}は無効化されています")
            return False

        print(f"\n{'='*60}")
        print(f"[Info] {tool_name}の更新を開始します...")

        # プロセス実行中チェック
        process_name = Path(tool_config["asset_name"]).name
        if self._is_process_running(process_name):
            print(
                f"[Warning] {process_name}が実行中です。更新をスキップします。"
            )
            print(
                f"[Warning] 更新するには、{process_name}を終了してから再度実行してください。"
            )
            return False

        # 現在のバージョン確認
        install_path = WORKSPACE_ROOT / tool_config["install_path"]
        current_version = self._get_current_version(
            install_path, tool_config.get("version_command", ["--version"])
        )

        if current_version:
            print(f"[Info] 現在のバージョン: {current_version}")

        # 最新リリース情報を取得
        release = self._get_latest_release(tool_config["repo"])
        if not release:
            print(f"[Error] 最新リリース情報の取得に失敗しました")
            return False

        latest_version = release.get("tag_name", "不明")
        print(f"[Info] 最新のバージョン: {latest_version}")

        # バージョン比較
        if current_version == latest_version:
            print(f"[Info] {tool_name}は既に最新版です")
            return True

        # アセットを検索
        assets = release.get("assets", [])
        asset = next(
            (a for a in assets if a["name"] == tool_config["asset_name"]), None
        )

        if not asset:
            print(
                f"[Error] アセットが見つかりません: {tool_config['asset_name']}"
            )
            print(f"[Info] 利用可能なアセット: {[a['name'] for a in assets]}")
            return False

        download_url = asset["browser_download_url"]
        print(f"[Info] ダウンロードURL: {download_url}")

        # 一時ファイルにダウンロード
        temp_path = install_path.with_suffix(install_path.suffix + ".tmp")

        # インストールディレクトリが存在しない場合は作成
        install_path.parent.mkdir(parents=True, exist_ok=True)

        if not self._download_file(download_url, temp_path):
            if temp_path.exists():
                temp_path.unlink()
            return False

        # ダウンロードしたファイルのバージョン確認
        downloaded_version = self._get_current_version(
            temp_path, tool_config.get("version_command", ["--version"])
        )

        if downloaded_version:
            print(f"[Info] ダウンロードファイルのバージョン: {downloaded_version}")
        else:
            print(
                f"[Warning] ダウンロードファイルのバージョン確認に失敗しました"
            )

        # ファイルを安全に更新
        if self._safe_update_file(temp_path, install_path):
            print(f"[Success] {tool_name}を{latest_version}に更新しました")
            return True
        else:
            # 失敗時は一時ファイルを削除
            if temp_path.exists():
                temp_path.unlink()
            return False

    def update_all_tools(self) -> None:
        """有効な全ツールを更新"""
        enabled_tools = [t for t in self.tools_config if t.get("enabled", True)]

        if not enabled_tools:
            print("[Info] 更新対象のツールがありません")
            return

        print(f"[Info] {len(enabled_tools)}個のツールを更新します...")

        success_count = 0
        fail_count = 0

        for tool in enabled_tools:
            result = self.update_tool(tool["name"])
            if result:
                success_count += 1
            else:
                fail_count += 1

        print(f"\n{'='*60}")
        print(f"[Info] 更新完了: 成功={success_count}, 失敗={fail_count}")


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="Toolsフォルダー内のツールを自動更新します",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 全ツールのバージョンを確認
  python ToolsUpdater.py --check

  # 特定ツールのバージョンを確認
  python ToolsUpdater.py --check --tool yt-dlp

  # 全ツールを更新
  python ToolsUpdater.py --update-all

  # 特定ツールを更新
  python ToolsUpdater.py --update --tool yt-dlp
        """,
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="バージョン確認のみ（更新しない）",
    )

    parser.add_argument(
        "--update",
        action="store_true",
        help="指定されたツールを更新",
    )

    parser.add_argument(
        "--update-all",
        action="store_true",
        help="有効な全ツールを更新",
    )

    parser.add_argument(
        "--tool",
        type=str,
        help="対象のツール名（例: yt-dlp）",
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PATH,
        help=f"設定ファイルのパス（デフォルト: {CONFIG_PATH}）",
    )

    args = parser.parse_args()

    # 引数チェック
    if not any([args.check, args.update, args.update_all]):
        parser.print_help()
        return

    if args.update and not args.tool:
        print("[Error] --updateを使用する場合は--toolでツール名を指定してください")
        return

    try:
        updater = ToolUpdater(args.config)

        if args.check:
            updater.check_version(args.tool)
        elif args.update:
            updater.update_tool(args.tool)
        elif args.update_all:
            updater.update_all_tools()

    except FileNotFoundError as e:
        print(f"[Error] {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"[Error] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[Info] 処理を中断しました")
        sys.exit(0)
    except Exception as e:
        print(f"[Error] 予期しないエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
