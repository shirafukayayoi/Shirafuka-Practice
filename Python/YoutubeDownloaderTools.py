import glob
import os
import os.path
import pickle
import subprocess

import cv2
import numpy as np
from dotenv import load_dotenv
from moviepy.editor import CompositeVideoClip, VideoFileClip, vfx

load_dotenv()

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


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
            url
        ]
        
        try:
            print(f"動画をダウンロード中...: {url}")
            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            print(result.stdout)
            
            # ダウンロード後のファイルリストを取得
            after_files = set(glob.glob(os.path.join(output_path, "*.mp4")))
            new_files = after_files - before_files
            
            if new_files:
                filepath = list(new_files)[0]
                print(f"ダウンロードが完了しました: {filepath}")
                return {'filepath': filepath}
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
        self.SCOPES = [
            "https://www.googleapis.com/auth/drive.file",
        ]
        self.creds = service_account.Credentials.from_service_account_file(
            'tokens/service_token.json', scopes=self.SCOPES
        )
        self.service = build("drive", "v3", credentials=self.creds)
    
    def upload_file(self, file_path, folder_id):
        try:
            # フォルダーIDが指定されている場合、存在確認
            if folder_id:
                try:
                    self.service.files().get(fileId=folder_id, fields="id, name").execute()
                    print(f"アップロード先フォルダーを確認しました (ID: {folder_id})")
                except Exception as e:
                    print(f"エラー: 指定されたフォルダーID '{folder_id}' が見つかりません。")
                    print(f"フォルダーが存在するか、サービスアカウントに共有されているか確認してください。")
                    print(f"詳細: {e}")
                    return None
            
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
        drive_manager = GoogleDriveManager()
        folder_id = os.getenv("VIDEO_OUTPUT_FOLDER_ID")
        
        if not folder_id:
            print("\n警告: VIDEO_OUTPUT_FOLDER_ID が環境変数に設定されていません。")
            print("Google Driveへのアップロードをスキップします。")
        else:
            print(f"\nGoogle Driveにアップロード中... (フォルダーID: {folder_id})")
            result = drive_manager.upload_file(output_vertical_file, folder_id)
            if not result:
                print("Google Driveへのアップロードに失敗しました。ファイルはローカルに保持されます。")
        
        # --- ファイルのクリーンアップ ---
        print("\n不要なファイルを削除しています...")
        
        # 変換後の縦型動画ファイルは常に削除
        if os.path.exists(output_vertical_file):
            os.remove(output_vertical_file)
            print(f"削除しました: {output_vertical_file}")
        
        # YouTubeからダウンロードしたファイルの場合のみ削除（ローカルファイルは削除しない）
        if not is_local_file and os.path.exists(downloaded_file):
            os.remove(downloaded_file)
            print(f"削除しました: {downloaded_file}")
        
        print("\n処理が完了しました！")


