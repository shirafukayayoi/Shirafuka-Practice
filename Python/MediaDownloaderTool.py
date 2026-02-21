import glob
import json
import os
import os.path
import re
import subprocess
import time

import cv2
from dotenv import load_dotenv

load_dotenv()

# moviepyはフォールバック用に遅延インポート
try:
    from moviepy import CompositeVideoClip, VideoFileClip, vfx

    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# スクリプトのディレクトリとプロジェクトルートを取得
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # Shirafuka-Practiceディレクトリ
TOKENS_DIR = os.path.join(PROJECT_ROOT, "tokens")


class MediaDownloader:
    def __init__(self):
        self.ytdlp_path = os.getenv("YT-DLP_PATH")

    def download_video(self, url, output_path="."):
        """
        指定された動画URLから動画をMP4形式でダウンロードします。
        外部のyt-dlp.exeを使用してダウンロードします。
        成功した場合、ダウンロード情報を返します。

        :param url: ダウンロードする動画URL
        :param output_path: 保存先のディレクトリ
        :return: ダウンロード情報 or None
        """
        # ダウンロード前のファイルリストを取得
        before_files = set(glob.glob(os.path.join(output_path, "*.mp4")))

        # yt-dlpコマンドを構築
        output_template = os.path.join(output_path, "%(title)s.%(ext)s")
        command = [
            self.ytdlp_path,
            "-f",
            "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]",
            "-o",
            output_template,
            "--no-playlist",  # プレイリストの場合は最初の1件のみ
            "--print",
            "after_move:filepath",  # ダウンロード後のファイルパスを出力
            url,
        ]

        try:
            print(f"[Info] 動画をダウンロード中...: {url}")
            # Windows環境での文字化け対策: chcp 65001を使用してUTF-8モードで実行
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            # 出力を表示
            print(result.stdout)

            # --print で出力されたファイルパスを取得
            output_lines = result.stdout.strip().split("\n")
            downloaded_filepath = None
            for line in reversed(output_lines):
                line = line.strip()
                if line.endswith(".mp4") and os.path.exists(line):
                    downloaded_filepath = line
                    break

            # 見つからない場合は差分から取得
            if not downloaded_filepath:
                after_files = set(glob.glob(os.path.join(output_path, "*.mp4")))
                new_files = after_files - before_files
                if new_files:
                    downloaded_filepath = list(new_files)[0]
                elif after_files:
                    # 最新の更新時刻のファイルを選択
                    downloaded_filepath = max(after_files, key=os.path.getmtime)

            if downloaded_filepath and os.path.exists(downloaded_filepath):
                print(f"[Info] ダウンロードが完了しました: {downloaded_filepath}")
                return {"filepath": downloaded_filepath}
            else:
                print("[Error] ダウンロードされたファイルが見つかりませんでした。")
                return None

        except subprocess.CalledProcessError as e:
            print(f"[Error] エラーが発生しました: {e}")
            print(f"[Error] エラー出力: {e.stderr}")
            return None
        except Exception as e:
            print(f"[Error] 予期しないエラーが発生しました: {e}")
            return None


class VideoVerticalConverter:
    def __init__(self, input_path, output_path, resolution=(1080, 1920)):
        self.input_path = input_path
        self.output_path = output_path
        self.width, self.height = resolution
        self.ffmpeg_path = os.getenv(
            "FFMPEG_PATH",
            "C:\\Users\\ron06\\AppData\\Local\\Microsoft\\WinGet\\Links\\ffmpeg.exe",
        )
        self.ffprobe_path = os.getenv(
            "FFPROBE_PATH",
            "C:\\Users\\ron06\\AppData\\Local\\Microsoft\\WinGet\\Links\\ffprobe.exe",
        )

    def _get_video_info(self):
        """動画のメタデータを取得"""
        try:
            cmd = [
                self.ffprobe_path,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                self.input_path,
            ]
            result = subprocess.run(
                cmd, capture_output=True, encoding="utf-8", errors="replace", check=True
            )

            if not result.stdout:
                raise ValueError("ffprobeから出力が得られませんでした")

            info = json.loads(result.stdout)

            # ビデオストリームを取得
            video_stream = next(
                (s for s in info["streams"] if s["codec_type"] == "video"), None
            )
            if not video_stream:
                raise ValueError("ビデオストリームが見つかりません")

            width = int(video_stream["width"])
            height = int(video_stream["height"])

            # FPS取得（r_frame_rateから）
            fps_str = video_stream.get("r_frame_rate", "30/1")
            fps_parts = fps_str.split("/")
            fps = float(fps_parts[0]) / float(fps_parts[1])

            duration = float(info["format"].get("duration", 0))

            return {"width": width, "height": height, "fps": fps, "duration": duration}
        except subprocess.CalledProcessError as e:
            print(f"[Warning] ffprobeの実行に失敗: {e}")
            if e.stderr:
                print(f"[Warning] エラー詳細: {e.stderr}")
            return None
        except json.JSONDecodeError as e:
            print(f"[Warning] ffprobeの出力をJSONとして解析できませんでした: {e}")
            return None
        except Exception as e:
            print(f"[Warning] ffprobeでの動画情報取得に失敗: {e}")
            return None

    def _build_ffmpeg_command_gpu(self, video_info):
        """GPU処理用のffmpegコマンドを構築"""
        orig_W = video_info["width"]
        orig_H = video_info["height"]
        W, H = self.width, self.height

        # 背景の計算（すべて偶数に丸める）
        scale_factor_bg = H / orig_H
        resized_bg_width = int(orig_W * scale_factor_bg) & ~1  # 偶数に丸める
        temp_width = int(resized_bg_width / 3) & ~1  # 偶数に丸める
        temp_height = int(H / 3) & ~1  # 偶数に丸める

        # 前景の計算（すべて偶数に丸める）
        foreground_width = W & ~1  # 偶数に丸める
        scale_factor_fg = foreground_width / orig_W
        foreground_height = int(orig_H * scale_factor_fg) & ~1  # 偶数に丸める

        # オーバーレイ位置も偶数に丸める
        crop_x = int((resized_bg_width - W) / 2) & ~1
        overlay_x = int((W - foreground_width) / 2) & ~1
        overlay_y = int((H - foreground_height) / 2) & ~1

        # フィルターグラフの構築
        filter_complex = (
            f"[0:v]split=2[bg][fg];"
            # 背景処理
            f"[bg]hwupload_cuda,"
            f"scale_cuda=w={temp_width}:h={temp_height},"
            f"scale_cuda=w={resized_bg_width}:h={H},"
            f"hwdownload,format=yuv420p,"
            f"crop={W}:{H}:{crop_x}:0,"
            f"eq=brightness=0.2,"
            f"gblur=sigma=17[bg_blur];"
            # 前景処理
            f"[fg]hwupload_cuda,"
            f"scale_cuda=w={foreground_width}:h={foreground_height},"
            f"hwdownload,format=yuv420p[fg_scaled];"
            # 合成
            f"[bg_blur][fg_scaled]overlay=x={overlay_x}:y={overlay_y}"
        )

        cmd = [
            self.ffmpeg_path,
            "-y",  # 上書き
            "-i",
            self.input_path,
            "-filter_complex",
            filter_complex,
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p4",  # p1(fastest)-p7(slowest), p4=balanced
            "-rc:v",
            "vbr",
            "-cq:v",
            "19",
            "-b:v",
            "5M",
            "-maxrate:v",
            "10M",
            "-c:a",
            "copy",
            self.output_path,
        ]

        return cmd

    def _generate_gpu(self):
        """GPU処理で縦型動画を生成"""
        print("[Info] GPU処理を開始します...")
        start_time = time.time()

        # 動画情報取得
        video_info = self._get_video_info()
        if not video_info:
            raise RuntimeError("動画情報の取得に失敗しました")

        print(
            f"[Info] 入力動画: {video_info['width']}x{video_info['height']} @ {video_info['fps']:.2f}fps, {video_info['duration']:.1f}秒"
        )

        # コマンド構築
        cmd = self._build_ffmpeg_command_gpu(video_info)

        # デバッグ: コマンドをログ出力
        print(f"[Debug] ffmpegコマンド: {' '.join(cmd)}")

        # 実行
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
        )

        # 進捗表示とエラーメッセージの収集
        duration = video_info["duration"]
        output_lines = []

        for line in process.stdout:
            output_lines.append(line)
            # timeパターンでの進捗取得
            time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", line)
            if time_match:
                h, m, s = time_match.groups()
                current_time = int(h) * 3600 + int(m) * 60 + float(s)
                if duration > 0:
                    progress = (current_time / duration) * 100
                    print(f"\r[Info] 処理中: {progress:.1f}%", end="", flush=True)

        print()  # 改行
        process.wait()

        if process.returncode != 0:
            # エラー時は最後の30行を表示
            print("[Error] ffmpegの出力（最後の30行）:")
            for line in output_lines[-30:]:
                print(line.rstrip())
            raise RuntimeError(
                f"ffmpegの実行に失敗しました (終了コード: {process.returncode})"
            )

        elapsed = time.time() - start_time
        print(f"[Info] GPU処理完了: {elapsed:.1f}秒")

    def _generate_cpu_fallback(self):
        """CPUフォールバック処理（moviepy使用）"""
        if not MOVIEPY_AVAILABLE:
            raise RuntimeError(
                "moviepyが利用できません。GPU処理にも失敗したため、処理を続行できません。"
            )

        print("[Info] CPUフォールバック処理を開始します...")
        start_time = time.time()

        original_clip = VideoFileClip(self.input_path)

        W, H = self.width, self.height
        orig_W, orig_H = original_clip.size

        # 背景クリップの作成（すべて偶数に丸める）
        scale_factor_bg = H / orig_H
        resized_bg_width = int(orig_W * scale_factor_bg) & ~1  # 偶数に丸める
        temp_width = int(resized_bg_width / 3) & ~1  # 偶数に丸める
        temp_height = int(H / 3) & ~1  # 偶数に丸める

        x_center = resized_bg_width / 2
        y_center = H / 2
        x1 = int(x_center - W / 2) & ~1  # 偶数に丸める
        y1 = int(y_center - H / 2) & ~1  # 偶数に丸める
        x2 = int(x_center + W / 2) & ~1  # 偶数に丸める
        y2 = int(y_center + H / 2) & ~1  # 偶数に丸める

        def process_frame(frame):
            frame = (frame * 1.2).clip(0, 255).astype("uint8")
            return cv2.GaussianBlur(frame, (51, 51), 0)

        background_clip = (
            original_clip.copy()
            .resized((temp_width, temp_height))
            .resized((resized_bg_width, H))
            .cropped(x1=x1, y1=y1, x2=x2, y2=y2)
            .image_transform(process_frame)
        )

        # 前景クリップの作成（すべて偶数に丸める）
        foreground_width = W & ~1  # 偶数に丸める
        scale_factor_fg = foreground_width / orig_W
        foreground_height = int(orig_H * scale_factor_fg) & ~1  # 偶数に丸める

        foreground_clip = original_clip.copy().resized(
            (foreground_width, foreground_height)
        )

        # 合成位置も偶数に丸める
        x_pos = int((W - foreground_width) / 2) & ~1
        y_pos = int((H - foreground_height) / 2) & ~1

        final_clip = CompositeVideoClip(
            [
                background_clip.with_position("center"),
                foreground_clip.with_position((x_pos, y_pos)),
            ],
            size=(W, H),
        ).with_duration(original_clip.duration)

        # エンコード（NVENCを試してからCPUへフォールバック）
        try:
            final_clip.write_videofile(
                self.output_path,
                codec="h264_nvenc",
                audio_codec="aac",
                fps=original_clip.fps,
                preset="medium",
                ffmpeg_params=[
                    "-rc:v",
                    "vbr",
                    "-cq:v",
                    "19",
                    "-b:v",
                    "5M",
                    "-maxrate:v",
                    "10M",
                ],
            )
        except Exception:
            final_clip.write_videofile(
                self.output_path,
                codec="libx264",
                audio_codec="aac",
                fps=original_clip.fps,
                threads=16,
            )

        original_clip.close()
        final_clip.close()

        elapsed = time.time() - start_time
        print(f"[Info] CPUフォールバック処理完了: {elapsed:.1f}秒")

    def generate(self):
        """縦型動画を生成する"""
        if not os.path.exists(self.input_path):
            print(f"[Error] 入力ファイルが見つかりません -> {self.input_path}")
            return

        # GPU処理を試みる
        try:
            self._generate_gpu()
            print(f"[Info] 縦型動画の生成が完了しました: {self.output_path}")
            return
        except Exception as e:
            print(f"[Warning] GPU処理に失敗しました: {e}")
            print("[Info] CPUフォールバックを試みます...")

        # CPUフォールバック
        try:
            self._generate_cpu_fallback()
            print(f"[Info] 縦型動画の生成が完了しました: {self.output_path}")
        except Exception as e:
            print(f"[Error] 縦型動画の生成に失敗しました: {e}")
            raise


class GoogleDriveManager:

    def __init__(self):
        """
        Google Drive APIマネージャーを初期化します（OAuth 2.0認証）。
        """
        self.SCOPES = [
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.readonly",
        ]

        # OAuth 2.0認証を使用
        credentials_path = os.path.join(TOKENS_DIR, "credentials.json")
        token_path = os.path.join(TOKENS_DIR, "drive_token.json")

        self.creds = None

        # トークンファイルが存在する場合は読み込む
        if os.path.exists(token_path):
            self.creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)

        # 認証情報が無効または存在しない場合
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                # トークンをリフレッシュ
                try:
                    self.creds.refresh(Request())
                    print("[Info] トークンをリフレッシュしました")
                except Exception as e:
                    print(f"[Error] トークンのリフレッシュに失敗しました: {e}")
                    self.creds = None

            if not self.creds:
                # 新しい認証フローを開始
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, self.SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                    print("[Info] 新しい認証を完了しました")
                except Exception as e:
                    print(f"[Error] 認証中にエラーが発生しました: {e}")
                    raise

            # トークンを保存
            try:
                with open(token_path, "w") as token:
                    token.write(self.creds.to_json())
                print(f"[Info] トークンを保存しました: {token_path}")
            except Exception as e:
                print(f"[Error] トークンの保存に失敗しました: {e}")

        self.service = build("drive", "v3", credentials=self.creds)
        print("[Info] 認証方式: OAuth 2.0")

    def check_connection(self):
        """
        Google Drive APIへの接続が可能かどうかを確認します。

        :return: 接続可能な場合True、それ以外False
        """
        try:
            # Google Drive APIへの簡単なクエリを実行して接続を確認
            self.service.about().get(fields="user").execute()
            print("[Info] ✓ Google Drive APIへの接続に成功しました")
            return True
        except Exception as e:
            print(f"[Error] ✗ Google Drive APIへの接続に失敗しました: {e}")
            return False

    def check_folder_access(self, folder_id):
        """
        指定されたフォルダーへのアクセスが可能かどうかを確認します。

        :param folder_id: 確認するフォルダーのID
        :return: アクセス可能な場合True、それ以外False
        """
        if not folder_id:
            print("[Error] ✗ フォルダーIDが指定されていません")
            return False

        try:
            folder = (
                self.service.files()
                .get(fileId=folder_id, fields="id, name, capabilities")
                .execute()
            )
            folder_name = folder.get("name", "不明")
            can_add_children = folder.get("capabilities", {}).get(
                "canAddChildren", False
            )

            if can_add_children:
                print(f"[Info] ✓ フォルダー '{folder_name}' へのアクセスに成功しました")
                return True
            else:
                print(
                    f"[Error] ✗ フォルダー '{folder_name}' へのアップロード権限がありません"
                )
                return False

        except Exception as e:
            print(f"[Error] ✗ フォルダーへのアクセスに失敗しました: {e}")
            return False

    def upload_file(self, file_path, folder_id, file_name=None):
        """
        Google Driveにファイルをアップロードします。

        :param file_path: アップロードするファイルのパス
        :param folder_id: アップロード先のフォルダーID
        :param file_name: Google Drive上のファイル名（指定しない場合は元のファイル名を使用）
        :return: アップロードされたファイルID
        """
        try:
            if folder_id:
                self.service.files().get(fileId=folder_id, fields="id").execute()
                print(f"[Info] アップロード先フォルダーを確認しました")

            # ファイル名が指定されていない場合は元のファイル名を使用
            upload_name = file_name if file_name else os.path.basename(file_path)

            file_metadata = {
                "name": upload_name,
                "parents": [folder_id] if folder_id else [],
            }
            media = MediaFileUpload(file_path, resumable=True)
            file = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )
            print(
                f"[Info] ファイルがGoogle Driveにアップロードされました。ファイルID: {file.get('id')}"
            )
            return file.get("id")
        except Exception as e:
            print(f"[Error] アップロード中にエラーが発生しました: {e}")
            return None


if __name__ == "__main__":
    # --- Google Drive接続確認 ---
    print("=" * 60)
    print("Google Drive接続確認")
    print("=" * 60)

    folder_id = os.getenv("VIDEO_OUTPUT_FOLDER_ID")
    drive_available = False
    drive_manager = None

    try:
        drive_manager = GoogleDriveManager()
        if (
            drive_manager.check_connection()
            and folder_id
            and drive_manager.check_folder_access(folder_id)
        ):
            drive_available = True
            print("[Info] ✓ Google Driveへのアップロードが利用可能です\n")
        else:
            print("[Error] ✗ Google Driveへのアップロードはスキップされます\n")
    except Exception as e:
        print(f"[Error] ✗ Google Drive接続に失敗しました: {e}")
        print("[Error] ✗ Google Driveへのアップロードはスキップされます\n")

    print("=" * 60)
    print("動画処理開始")
    print("=" * 60)

    user_input = input(
        "動画URLまたはローカルファイルのパスを入力してください: "
    ).strip()

    # ファイルパスかURLかを判定
    is_local_file = os.path.exists(user_input)

    if is_local_file:
        # ローカルファイルのパスが入力された場合
        print(f"[Info] ローカルファイルを使用します: {user_input}")
        print("[Info] 縦型動画の編集を開始します...")
        downloaded_file = user_input
    else:
        # 動画URLとして処理
        print(f"[Info] 動画をダウンロードします: {user_input}")
        downloader = MediaDownloader()
        info = downloader.download_video(user_input)

        if info:
            downloaded_file = info.get("filepath")
            if not (downloaded_file and os.path.exists(downloaded_file)):
                print("[Error] ダウンロードされたファイルが見つかりませんでした。")
                downloaded_file = None
        else:
            print("[Error] ダウンロードに失敗したため、動画編集は行いません。")
            downloaded_file = None

    # ダウンロード済みまたはローカルファイルが存在する場合に編集を実行
    if downloaded_file:
        print(f"[Info] 動画ファイルを処理します: {downloaded_file}")
        print("[Info] 縦型動画の編集を開始します...")

        # --- 縦型動画変換 ---
        output_vertical_file = "output_vertical.mp4"
        converter = VideoVerticalConverter(
            input_path=downloaded_file, output_path=output_vertical_file
        )
        converter.generate()

        # --- Google Driveアップロード ---
        if drive_available:
            print(f"[Info] Google Driveにアップロード中... (フォルダーID: {folder_id})")
            # 元の動画ファイル名をそのまま使用
            original_filename = os.path.basename(downloaded_file)

            result = drive_manager.upload_file(
                output_vertical_file, folder_id, file_name=original_filename
            )
            if not result:
                print(
                    "[Error] Google Driveへのアップロードに失敗しました。ファイルはローカルに保持されます。"
                )
        else:
            print(
                "[Info] Google Driveへのアップロードをスキップします（接続確認に失敗しました）"
            )

        # --- ファイルのクリーンアップ ---
        print("[Info] 不要なファイルを削除しています...")
        # ファイルハンドルが完全に解放されるまで少し待機
        time.sleep(1)

        # 削除対象のファイルリスト
        files_to_delete = [output_vertical_file]

        # ローカルファイルでない場合（ダウンロードした場合）、ダウンロードファイルも削除
        if not is_local_file and downloaded_file:
            files_to_delete.append(downloaded_file)

        # .partファイルも検索して削除対象に追加
        current_dir = os.path.dirname(downloaded_file) if downloaded_file else "."
        part_files = glob.glob(os.path.join(current_dir, "*.part"))
        files_to_delete.extend(part_files)

        for file_to_delete in files_to_delete:
            if file_to_delete and os.path.exists(file_to_delete):
                try:
                    os.remove(file_to_delete)
                    print(f"[Info] 削除しました: {file_to_delete}")
                except PermissionError:
                    print(
                        f"[Error] ファイルを削除できませんでした（使用中）: {file_to_delete}"
                    )
                    print(f"[Error] 手動で削除してください。")
                except Exception as e:
                    print(
                        f"[Error] ファイル削除中にエラーが発生しました: {file_to_delete}"
                    )
                    print(f"[Error] エラー: {e}")

        print("[Info] 処理が完了しました！")
