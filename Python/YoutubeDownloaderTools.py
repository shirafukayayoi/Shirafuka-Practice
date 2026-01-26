import glob
import os
import os.path
import subprocess

import cv2
from dotenv import load_dotenv
from moviepy.editor import CompositeVideoClip, VideoFileClip, vfx

load_dotenv()

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# スクリプトのディレクトリとプロジェクトルートを取得
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # Shirafuka-Practiceディレクトリ
TOKENS_DIR = os.path.join(PROJECT_ROOT, 'tokens')


class YoutubeDownloader:
    def __init__(self):
        self.ytdlp_path = os.getenv("YT-DLP_PATH")

    def download_video(self, url, output_path='.'):
        """
        指定されたURLから動画をMP4形式でダウンロードします。
        外部のyt-dlp.exeを使用してダウンロードします。
        成功した場合、ダウンロード情報を返します。

        :param url: ダウンロードする動画のURL
        :param output_path: 保存先のディレクトリ
        :return: ダウンロード情報 or None
        """
        # ダウンロード前のファイルリストを取得
        before_files = set(glob.glob(os.path.join(output_path, "*.mp4")))
        
        # yt-dlpコマンドを構築
        output_template = os.path.join(output_path, "%(title)s.%(ext)s")
        command = [
            self.ytdlp_path,
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", output_template,
            "--no-playlist",  # プレイリストの場合は最初の1件のみ
            "--print", "after_move:filepath",  # ダウンロード後のファイルパスを出力
            url
        ]
        
        try:
            print(f"動画をダウンロード中...: {url}")
            # Windows環境での文字化け対策: chcp 65001を使用してUTF-8モードで実行
            result = subprocess.run(
                command, 
                check=True, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace'
            )
            
            # 出力を表示
            print(result.stdout)
            
            # --print で出力されたファイルパスを取得
            output_lines = result.stdout.strip().split('\n')
            downloaded_filepath = None
            for line in reversed(output_lines):
                line = line.strip()
                if line.endswith('.mp4') and os.path.exists(line):
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
                print(f"ダウンロードが完了しました: {downloaded_filepath}")
                return {'filepath': downloaded_filepath}
            else:
                print("ダウンロードされたファイルが見つかりませんでした。")
                return None
                
        except subprocess.CalledProcessError as e:
            print(f"エラーが発生しました: {e}")
            print(f"エラー出力: {e.stderr}")
            return None
        except Exception as e:
            print(f"予期しないエラーが発生しました: {e}")
            return None

class VideoVerticalConverter:
    def __init__(self, input_path, output_path, resolution=(1080, 1920)):
        self.input_path = input_path
        self.output_path = output_path
        self.width, self.height = resolution

    def _blur_frame(self, frame, blur_strength=23):
        """フレームをぼかすための内部メソッド"""
        # ぼかしの強さが偶数なら奇数にする
        if blur_strength % 2 == 0:
            blur_strength += 1
        blurred = cv2.GaussianBlur(frame, (blur_strength, blur_strength), 0)
        return blurred

    def generate(self):
        """縦型動画を生成する"""
        if not os.path.exists(self.input_path):
            print(f"エラー: 入力ファイルが見つかりません -> {self.input_path}")
            return

        original_clip = VideoFileClip(self.input_path)
        
        W, H = self.width, self.height
        orig_W, orig_H = original_clip.size
        
        # 背景クリップの作成
        scale_factor_bg = H / orig_H
        resized_bg_width = int(orig_W * scale_factor_bg)
        
        background_clip = original_clip.copy() \
            .fx(vfx.resize, newsize=(resized_bg_width, H)) \
            .fx(vfx.crop, width=W, height=H, x_center=resized_bg_width / 2, y_center=H / 2) \
            .fx(vfx.colorx, 1.2) \
            .fl_image(self._blur_frame)

        # 前景クリップの作成
        foreground_width = W
        scale_factor_fg = foreground_width / orig_W
        foreground_height = int(orig_H * scale_factor_fg)
        
        foreground_clip = original_clip.copy() \
            .fx(vfx.resize, newsize=(foreground_width, foreground_height))
        
        # クリップを合成
        x_pos = (W - foreground_width) / 2
        y_pos = (H - foreground_height) / 2
        
        final_clip = CompositeVideoClip(
            [
                background_clip.set_position("center"),
                foreground_clip.set_position((x_pos, y_pos))
            ],
            size=(W, H)
        ).set_duration(original_clip.duration)

        # 動画ファイルとして書き出し（GPUアクセラレーション使用）
        # NVIDIA GPUの場合: h264_nvenc
        # AMD GPUの場合: h264_amf
        # Intel Quick Syncの場合: h264_qsv
        # GPUが利用できない場合は自動的にCPUにフォールバック
        try:
            # まずNVIDIA GPUを試す
            final_clip.write_videofile(
                self.output_path, 
                codec='h264_nvenc',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=original_clip.fps,
                preset='medium',  # NVENCプリセット: slow, medium, fast, hp, hq
                logger='bar',
                ffmpeg_params=['-rc:v', 'vbr', '-cq:v', '19', '-b:v', '5M', '-maxrate:v', '10M']
            )
            print("GPU (NVIDIA NVENC) でエンコードしました")
        except Exception as e:
            print(f"GPU エンコードに失敗しました。CPUエンコードにフォールバックします: {e}")
            # GPUが使えない場合はCPUエンコード
            final_clip.write_videofile(
                self.output_path, 
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=original_clip.fps,
                threads=4,
                logger='bar'
            )
        original_clip.close()
        final_clip.close()
        print(f"\n縦型動画の生成が完了しました: {self.output_path}")

class GoogleDriveManager:
    
    def __init__(self):
        """
        Google Drive APIマネージャーを初期化します（サービスアカウント認証）。
        """
        self.SCOPES = [
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        
        # サービスアカウント認証を使用
        token_path = os.path.join(TOKENS_DIR, 'service_token.json')
        self.creds = service_account.Credentials.from_service_account_file(
            token_path, scopes=self.SCOPES
        )
        
        self.service = build("drive", "v3", credentials=self.creds)
        print("認証方式: サービスアカウント")
    
    def check_connection(self):
        """
        Google Drive APIへの接続が可能かどうかを確認します。
        
        :return: 接続可能な場合True、それ以外False
        """
        try:
            # Google Drive APIへの簡単なクエリを実行して接続を確認
            self.service.about().get(fields="user").execute()
            print("✓ Google Drive APIへの接続に成功しました")
            return True
        except Exception as e:
            print(f"✗ Google Drive APIへの接続に失敗しました: {e}")
            return False
    
    def check_folder_access(self, folder_id):
        """
        指定されたフォルダーへのアクセスが可能かどうかを確認します。
        
        :param folder_id: 確認するフォルダーのID
        :return: アクセス可能な場合True、それ以外False
        """
        if not folder_id:
            print("✗ フォルダーIDが指定されていません")
            return False
        
        try:
            folder = self.service.files().get(fileId=folder_id, fields="id, name, capabilities").execute()
            folder_name = folder.get('name', '不明')
            can_add_children = folder.get('capabilities', {}).get('canAddChildren', False)
            
            if can_add_children:
                print(f"✓ フォルダー '{folder_name}' へのアクセスに成功しました")
                return True
            else:
                print(f"✗ フォルダー '{folder_name}' へのアップロード権限がありません")
                return False
                
        except Exception as e:
            print(f"✗ フォルダーへのアクセスに失敗しました: {e}")
            return False
    
    def upload_file(self, file_path, folder_id):
        try:
            if folder_id:
                self.service.files().get(fileId=folder_id, fields="id").execute()
                print(f"アップロード先フォルダーを確認しました")
            
            file_metadata = {
                "name": os.path.basename(file_path),
                "parents": [folder_id] if folder_id else []
            }
            media = MediaFileUpload(file_path, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id"
            ).execute()
            print(f"ファイルがGoogle Driveにアップロードされました。ファイルID: {file.get('id')}")
            return file.get('id')
        except Exception as e:
            print(f"アップロード中にエラーが発生しました: {e}")
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
        if drive_manager.check_connection() and folder_id and drive_manager.check_folder_access(folder_id):
            drive_available = True
            print("\n✓ Google Driveへのアップロードが利用可能です\n")
        else:
            print("\n✗ Google Driveへのアップロードはスキップされます\n")
    except Exception as e:
        print(f"✗ Google Drive接続に失敗しました: {e}")
        print("\n✗ Google Driveへのアップロードはスキップされます\n")
    
    print("=" * 60)
    print("動画処理開始")
    print("=" * 60)
    
    user_input = input("YouTube動画のURLまたはローカルファイルのパスを入力してください: ").strip()
    
    # ファイルパスかURLかを判定
    is_local_file = os.path.exists(user_input)
    
    if is_local_file:
        # ローカルファイルのパスが入力された場合
        print(f"\nローカルファイルを使用します: {user_input}")
        print("縦型動画の編集を開始します...")
        downloaded_file = user_input
    else:
        # YouTubeのURLとして処理
        print(f"\nYouTube動画をダウンロードします: {user_input}")
        downloader = YoutubeDownloader()
        info = downloader.download_video(user_input)
        
        if info:
            downloaded_file = info.get('filepath')
            if not (downloaded_file and os.path.exists(downloaded_file)):
                print("ダウンロードされたファイルが見つかりませんでした。")
                downloaded_file = None
        else:
            print("ダウンロードに失敗したため、動画編集は行いません。")
            downloaded_file = None
    
    # ダウンロード済みまたはローカルファイルが存在する場合に編集を実行
    if downloaded_file:
        print(f"\n動画ファイルを処理します: {downloaded_file}")
        print("縦型動画の編集を開始します...")

        # --- 縦型動画変換 ---
        output_vertical_file = "output_vertical.mp4"
        converter = VideoVerticalConverter(input_path=downloaded_file, output_path=output_vertical_file)
        converter.generate()

        # --- Google Driveアップロード ---
        if drive_available:
            print(f"\nGoogle Driveにアップロード中... (フォルダーID: {folder_id})")
            result = drive_manager.upload_file(output_vertical_file, folder_id)
            if not result:
                print("Google Driveへのアップロードに失敗しました。ファイルはローカルに保持されます。")
        else:
            print("\nGoogle Driveへのアップロードをスキップします（接続確認に失敗しました）")
        
        # --- ファイルのクリーンアップ ---
        print("\n不要なファイルを削除しています...")
        for file_to_delete in [output_vertical_file, downloaded_file if not is_local_file else None]:
            if file_to_delete and os.path.exists(file_to_delete):
                os.remove(file_to_delete)
                print(f"削除しました: {file_to_delete}")
        
        print("\n処理が完了しました！")


