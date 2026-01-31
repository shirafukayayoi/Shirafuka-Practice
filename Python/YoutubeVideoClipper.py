import glob
import os
import subprocess
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
from dotenv import load_dotenv
from moviepy.editor import CompositeVideoClip, VideoFileClip, vfx
from PIL import Image, ImageTk

load_dotenv()

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# スクリプトのディレクトリとプロジェクトルートを取得
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
TOKENS_DIR = os.path.join(PROJECT_ROOT, 'tokens')


class YoutubeDownloader:
    """YouTube動画のダウンロードを管理するクラス"""
    
    def __init__(self):
        self.ytdlp_path = os.getenv("YT-DLP_PATH")

    def download_video(self, url, output_path='.', quality='best', start_time=None, end_time=None):
        """
        指定されたURLから動画をMP4形式でダウンロードします。
        
        :param url: ダウンロードする動画のURL
        :param output_path: 保存先のディレクトリ
        :param quality: 'best', 'worst', または品質指定
        :param start_time: 開始時刻（秒）
        :param end_time: 終了時刻（秒）
        :return: ダウンロードされたファイルパス or None
        """
        before_files = set(glob.glob(os.path.join(output_path, "*.mp4")))
        
        output_template = os.path.join(output_path, "%(title)s.%(ext)s")
        
        # 品質設定
        if quality == 'worst':
            format_str = "worst[ext=mp4]/worst"
        elif quality == '1080p':
            format_str = "bestvideo[height=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height=1080]+bestaudio/best[height=1080]"
        else:
            format_str = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]"
        
        command = [
            self.ytdlp_path,
            "-f", format_str,
            "-o", output_template,
            "--no-playlist",
            "--print", "after_move:filepath",
        ]
        
        # 時間範囲指定がある場合
        if start_time is not None and end_time is not None:
            command.extend([
                "--download-sections", f"*{start_time}-{end_time}",
                "--force-keyframes-at-cuts"
            ])
        
        command.append(url)
        
        try:
            print(f"[Info] 動画をダウンロード中... ({quality})")
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # ファイルパスを取得
            output_lines = result.stdout.strip().split('\n')
            downloaded_filepath = None
            for line in reversed(output_lines):
                line = line.strip()
                if line.endswith('.mp4') and os.path.exists(line):
                    downloaded_filepath = line
                    break
            
            if not downloaded_filepath:
                after_files = set(glob.glob(os.path.join(output_path, "*.mp4")))
                new_files = after_files - before_files
                if new_files:
                    downloaded_filepath = list(new_files)[0]
                elif after_files:
                    downloaded_filepath = max(after_files, key=os.path.getmtime)
            
            if downloaded_filepath and os.path.exists(downloaded_filepath):
                print(f"[Info] ダウンロード完了: {downloaded_filepath}")
                return downloaded_filepath
            else:
                print("[Error] ダウンロードされたファイルが見つかりませんでした。")
                return None
                
        except subprocess.CalledProcessError as e:
            print(f"[Error] ダウンロードエラー: {e}")
            print(f"[Error] エラー出力: {e.stderr}")
            return None
        except Exception as e:
            print(f"[Error] 予期しないエラー: {e}")
            return None


class VideoVerticalConverter:
    """縦型動画変換クラス"""
    
    def __init__(self, input_path, output_path, resolution=(1080, 1920)):
        self.input_path = input_path
        self.output_path = output_path
        self.width, self.height = resolution

    def _blur_frame(self, frame, blur_strength=51):
        """フレームをぼかすための内部メソッド"""
        if blur_strength % 2 == 0:
            blur_strength += 1
        blurred = cv2.GaussianBlur(frame, (blur_strength, blur_strength), 0)
        return blurred

    def generate(self):
        """縦型動画を生成する"""
        if not os.path.exists(self.input_path):
            print(f"[Error] 入力ファイルが見つかりません -> {self.input_path}")
            return

        original_clip = VideoFileClip(self.input_path)
        
        W, H = self.width, self.height
        orig_W, orig_H = original_clip.size
        
        # 背景クリップの作成（解像度を下げてより荒く）
        scale_factor_bg = H / orig_H
        resized_bg_width = int(orig_W * scale_factor_bg)
        
        # まず解像度を1/3に縮小してから戻すことで荒い質感に
        temp_width = int(resized_bg_width / 3)
        temp_height = int(H / 3)
        
        background_clip = original_clip.copy() \
            .fx(vfx.resize, newsize=(temp_width, temp_height)) \
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
        try:
            # まずNVIDIA GPUを試す
            final_clip.write_videofile(
                self.output_path, 
                codec='h264_nvenc',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=original_clip.fps,
                preset='medium',
                logger='bar',
                ffmpeg_params=['-rc:v', 'vbr', '-cq:v', '19', '-b:v', '5M', '-maxrate:v', '10M']
            )
            print("[Info] GPU (NVIDIA NVENC) でエンコードしました")
        except Exception as e:
            print(f"[Info] GPU エンコードに失敗しました。CPUエンコードにフォールバックします: {e}")
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
        print(f"[Info] 縦型動画の生成が完了しました: {self.output_path}")


class GoogleDriveManager:
    """Google Drive APIを管理するクラス"""
    
    def __init__(self):
        self.SCOPES = [
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        
        credentials_path = os.path.join(TOKENS_DIR, 'credentials.json')
        token_path = os.path.join(TOKENS_DIR, 'drive_token.json')
        
        self.creds = None
        
        if os.path.exists(token_path):
            self.creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    print("[Info] トークンをリフレッシュしました")
                except Exception as e:
                    print(f"[Error] トークンのリフレッシュに失敗: {e}")
                    self.creds = None
            
            if not self.creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, self.SCOPES)
                    self.creds = flow.run_local_server(port=0)
                    print("[Info] 新しい認証を完了しました")
                except Exception as e:
                    print(f"[Error] 認証エラー: {e}")
                    raise
            
            try:
                with open(token_path, 'w') as token:
                    token.write(self.creds.to_json())
                print(f"[Info] トークンを保存しました: {token_path}")
            except Exception as e:
                print(f"[Error] トークンの保存に失敗: {e}")
        
        self.service = build("drive", "v3", credentials=self.creds)
    
    def check_connection(self):
        """Google Drive APIへの接続確認"""
        try:
            self.service.about().get(fields="user").execute()
            print("[Info] ✓ Google Drive API接続成功")
            return True
        except Exception as e:
            print(f"[Error] ✗ Google Drive API接続失敗: {e}")
            return False
    
    def check_folder_access(self, folder_id):
        """指定フォルダーへのアクセス確認"""
        if not folder_id:
            print("[Error] ✗ フォルダーIDが未指定")
            return False
        
        try:
            folder = self.service.files().get(fileId=folder_id, fields="id, name, capabilities").execute()
            folder_name = folder.get('name', '不明')
            can_add_children = folder.get('capabilities', {}).get('canAddChildren', False)
            
            if can_add_children:
                print(f"[Info] ✓ フォルダー '{folder_name}' へのアクセス成功")
                return True
            else:
                print(f"[Error] ✗ フォルダー '{folder_name}' へのアップロード権限なし")
                return False
                
        except Exception as e:
            print(f"[Error] ✗ フォルダーアクセス失敗: {e}")
            return False
    
    def upload_file(self, file_path, folder_id, file_name=None):
        """Google Driveにファイルをアップロード"""
        try:
            if folder_id:
                self.service.files().get(fileId=folder_id, fields="id").execute()
            
            upload_name = file_name if file_name else os.path.basename(file_path)
            
            file_metadata = {
                "name": upload_name,
                "parents": [folder_id] if folder_id else []
            }
            media = MediaFileUpload(file_path, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id"
            ).execute()
            print(f"[Info] Google Driveにアップロード完了 (ID: {file.get('id')})")
            return file.get('id')
        except Exception as e:
            print(f"[Error] アップロードエラー: {e}")
            return None


class VLCVideoPlayer:
    """VLCベースの動画プレーヤー（音声対応）"""
    
    def __init__(self, parent_frame):
        import vlc
        self.parent_frame = parent_frame
        self.instance = vlc.Instance('--no-xlib')
        self.player = self.instance.media_player_new()
        
        # Windows環境でウィンドウハンドルを設定
        import platform
        if platform.system() == 'Windows':
            self.player.set_hwnd(self.parent_frame.winfo_id())
        elif platform.system() == 'Linux':
            self.player.set_xwindow(self.parent_frame.winfo_id())
        elif platform.system() == 'Darwin':
            self.player.set_nsobject(self.parent_frame.winfo_id())
        
        self.duration = 0
        self.is_loaded = False
    
    def load_video(self, path):
        """動画を読み込む"""
        media = self.instance.media_new(path)
        self.player.set_media(media)
        self.player.audio_set_volume(100)
        self.player.play()
        time.sleep(0.5)  # メタデータの読み込み待機
        self.player.pause()
        self.duration = self.player.get_length() / 1000.0  # 秒に変換
        self.is_loaded = True
        return self.duration
    
    def play(self):
        """再生"""
        self.player.play()
    
    def pause(self):
        """一時停止"""
        self.player.pause()
    
    def is_playing(self):
        """再生中か確認"""
        return self.player.is_playing()
    
    def stop(self):
        """停止"""
        self.player.stop()
    
    def set_position(self, pos_ratio):
        """位置を設定（0.0～1.0）"""
        self.player.set_position(pos_ratio)
    
    def get_position(self):
        """現在位置を取得（0.0～1.0）"""
        return self.player.get_position()
    
    def get_time(self):
        """現在時刻を取得（秒）"""
        try:
            time_ms = self.player.get_time()
            if time_ms is not None and time_ms >= 0:
                return time_ms / 1000.0
            return 0.0
        except:
            return 0.0
    
    def set_volume(self, volume):
        """音量を設定（0～100）"""
        self.player.audio_set_volume(int(volume))
    
    def release(self):
        """リソースを解放"""
        self.player.stop()


class OpenCVVideoPlayer:
    """OpenCVベースの動画プレーヤー（音声なし・フォールバック用）"""
    
    def __init__(self, parent_canvas):
        self.canvas = parent_canvas
        self.cap = None
        self.duration = 0
        self.fps = 0
        self.total_frames = 0
        self.current_frame = 0
        self.is_loaded = False
        self.playing = False
        self.photo = None
    
    def load_video(self, path):
        """動画を読み込む"""
        self.cap = cv2.VideoCapture(path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0
        self.current_frame = 0
        self.is_loaded = True
        self.update_frame()
        return self.duration
    
    def update_frame(self):
        """現在のフレームを表示"""
        if not self.cap:
            return
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_resized = cv2.resize(frame_rgb, (800, 450))
            img = Image.fromarray(frame_resized)
            self.photo = ImageTk.PhotoImage(image=img)
            self.canvas.delete("all")
            self.canvas.create_image(400, 225, image=self.photo)
    
    def play(self):
        """再生"""
        self.playing = True
    
    def pause(self):
        """一時停止"""
        self.playing = False
    
    def is_playing(self):
        """再生中か確認"""
        return self.playing
    
    def stop(self):
        """停止"""
        self.playing = False
        self.current_frame = 0
        self.update_frame()
    
    def set_position(self, pos_ratio):
        """位置を設定（0.0～1.0）"""
        self.current_frame = int(pos_ratio * self.total_frames)
        self.current_frame = max(0, min(self.current_frame, self.total_frames - 1))
        if not self.playing:
            self.update_frame()
    
    def get_position(self):
        """現在位置を取得（0.0～1.0）"""
        if self.total_frames == 0:
            return 0.0
        return self.current_frame / self.total_frames
    
    def get_time(self):
        """現在時刻を取得（秒）"""
        try:
            if self.fps == 0 or self.fps is None:
                return 0.0
            return max(0.0, self.current_frame / self.fps)
        except:
            return 0.0
    
    def advance_frame(self):
        """次のフレームに進む（再生用）"""
        if self.playing and self.current_frame < self.total_frames - 1:
            self.current_frame += 1
            self.update_frame()
            return True
        elif self.current_frame >= self.total_frames - 1:
            self.playing = False
            return False
        return False
    
    def set_volume(self, volume):
        """音量設定（OpenCVでは音声なし）"""
        pass
    
    def release(self):
        """リソースを解放"""
        if self.cap:
            self.cap.release()


class RangeMarkerSeekbar(tk.Canvas):
    """開始/終了マーカー付きシークバー"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, height=50, bg='white', highlightthickness=1, 
                        highlightbackground='gray', **kwargs)
        self.duration = 100
        self.current_pos = 0
        self.start_marker = None
        self.end_marker = None
        self.on_seek_callback = None
        
        self.bind('<Button-1>', self._on_click)
        self.bind('<Configure>', lambda e: self.redraw())
    
    def set_duration(self, duration):
        """動画の長さを設定"""
        self.duration = max(1, duration)
        self.redraw()
    
    def set_start_marker(self, pos_sec):
        """開始マーカーを設定"""
        self.start_marker = pos_sec
        self.redraw()
    
    def set_end_marker(self, pos_sec):
        """終了マーカーを設定"""
        self.end_marker = pos_sec
        self.redraw()
    
    def set_current_position(self, pos_sec):
        """現在位置を設定"""
        self.current_pos = pos_sec
        self.redraw()
    
    def set_seek_callback(self, callback):
        """シーククリック時のコールバックを設定"""
        self.on_seek_callback = callback
    
    def redraw(self):
        """シークバーを再描画"""
        try:
            self.delete('all')
            width = self.winfo_width()
            height = self.winfo_height()
            
            if width <= 1:
                width = 800  # デフォルト幅を使用
            if height <= 1:
                height = 50
            
            # ベースライン
            base_y = height // 2
            self.create_rectangle(10, base_y - 4, width - 10, base_y + 4,
                                fill='lightgray', outline='gray', width=1)
            
            # 選択範囲のハイライト（青）
            if self.start_marker is not None and self.end_marker is not None:
                start_x = 10 + (width - 20) * (self.start_marker / self.duration)
                end_x = 10 + (width - 20) * (self.end_marker / self.duration)
                self.create_rectangle(start_x, base_y - 4, end_x, base_y + 4,
                                    fill='lightblue', outline='blue', width=2)
            
            # 開始マーカー（緑の三角形）
            if self.start_marker is not None:
                x = 10 + (width - 20) * (self.start_marker / self.duration)
                self.create_polygon(x, 8, x-6, 20, x+6, 20, fill='green', outline='darkgreen', width=2)
                # ラベル
                self.create_text(x, 5, text=self._format_time(self.start_marker), 
                               font=('Arial', 8), fill='darkgreen')
            
            # 終了マーカー（赤の三角形）
            if self.end_marker is not None:
                x = 10 + (width - 20) * (self.end_marker / self.duration)
                self.create_polygon(x, height-8, x-6, height-20, x+6, height-20,
                                  fill='red', outline='darkred', width=2)
                # ラベル
                self.create_text(x, height-5, text=self._format_time(self.end_marker),
                               font=('Arial', 8), fill='darkred')
            
            # 現在位置（黄色の縦線）
            current_x = 10 + (width - 20) * (self.current_pos / self.duration)
            self.create_line(current_x, 0, current_x, height, fill='orange', width=3)
        except Exception as e:
            # 描画エラーを無視
            pass
    
    def _format_time(self, seconds):
        """秒をMM:SS形式に変換"""
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"
    
    def _on_click(self, event):
        """クリックでシーク"""
        width = self.winfo_width()
        ratio = (event.x - 10) / (width - 20)
        ratio = max(0, min(1, ratio))
        pos_sec = ratio * self.duration
        
        if self.on_seek_callback:
            self.on_seek_callback(pos_sec)


class VideoClipperGUI:
    """YouTube動画クリッパーのメインGUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YouTube Video Clipper - 動画切り出しツール")
        self.root.geometry("950x750")
        
        # 変数初期化
        self.video_url = None
        self.preview_file = None
        self.temp_files = []  # 削除対象の一時ファイルリスト
        self.start_time = 0
        self.end_time = 0
        self.skip_preview_var = tk.BooleanVar(value=False)
        self.has_audio = False
        
        # 一時ファイルの保存先（スクリプトと同じディレクトリ）
        self.temp_dir = SCRIPT_DIR
        
        # Google Drive初期化
        self.drive_manager = None
        self.drive_folder_id = os.getenv("VIDEO_OUTPUT_FOLDER_ID")
        self._init_google_drive()
        
        # ダウンローダー初期化
        self.downloader = YoutubeDownloader()
        
        # UI構築
        self._build_ui()
        
        # ビデオプレーヤー初期化
        self.player = None
        self._init_video_player()
        
        # 更新ループ
        self.root.after(100, self._update_loop)
    
    def _init_google_drive(self):
        """Google Driveの初期化"""
        try:
            self.drive_manager = GoogleDriveManager()
            if self.drive_manager.check_connection():
                if self.drive_folder_id and self.drive_manager.check_folder_access(self.drive_folder_id):
                    print("[Info] ✓ Google Driveアップロード利用可能")
                else:
                    print("[Warning] フォルダーアクセス不可、アップロードはスキップされます")
                    self.drive_manager = None
            else:
                self.drive_manager = None
        except Exception as e:
            print(f"[Error] Google Drive初期化失敗: {e}")
            self.drive_manager = None
    
    def _init_video_player(self):
        """ビデオプレーヤーの初期化（VLC優先、OpenCVフォールバック）"""
        try:
            import vlc
            self.player = VLCVideoPlayer(self.video_frame)
            self.has_audio = True
            self.audio_control_frame.pack(fill=tk.X, padx=10, pady=5)
            print("[Info] ✓ VLCプレーヤーを使用（音声対応）")
        except Exception as e:
            print(f"[Info] VLC利用不可: {e}")
            print("[Info] → OpenCVプレーヤーを使用（音声なし）")
            
            # Canvasに切り替え
            for widget in self.video_frame.winfo_children():
                widget.destroy()
            
            self.video_canvas = tk.Canvas(self.video_frame, bg='black', width=800, height=450)
            self.video_canvas.pack(fill=tk.BOTH, expand=True)
            
            self.player = OpenCVVideoPlayer(self.video_canvas)
            self.has_audio = False
            self.audio_control_frame.pack_forget()
    
    def _build_ui(self):
        """UIコンポーネントの構築"""
        # URL入力エリア
        input_frame = ttk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(input_frame, text="YouTube URL:", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        self.url_entry = ttk.Entry(input_frame, font=('Arial', 10))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(input_frame, text="プレビュー読込", command=self._load_preview).pack(side=tk.LEFT, padx=5)
        
        # 動画表示エリア
        self.video_frame = tk.Frame(self.root, bg='black', width=800, height=450)
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.video_frame.pack_propagate(False)
        
        # 再生コントロール
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(control_frame, text="◀◀ -5秒", command=lambda: self._seek_relative(-5)).pack(side=tk.LEFT, padx=2)
        self.play_btn = ttk.Button(control_frame, text="▶ 再生", command=self._toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="■ 停止", command=self._stop).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="+5秒 ▶▶", command=lambda: self._seek_relative(5)).pack(side=tk.LEFT, padx=2)
        
        self.time_label = ttk.Label(control_frame, text="00:00 / 00:00", font=('Arial', 10))
        self.time_label.pack(side=tk.LEFT, padx=20)
        
        # 音声コントロール（VLC使用時のみ表示）
        self.audio_control_frame = ttk.Frame(self.root)
        
        ttk.Label(self.audio_control_frame, text="音量:").pack(side=tk.LEFT, padx=5)
        self.volume_var = tk.IntVar(value=100)
        self.volume_slider = ttk.Scale(
            self.audio_control_frame, from_=0, to=100, orient=tk.HORIZONTAL,
            variable=self.volume_var, command=self._on_volume_change, length=150
        )
        self.volume_slider.pack(side=tk.LEFT, padx=5)
        ttk.Label(self.audio_control_frame, textvariable=self.volume_var).pack(side=tk.LEFT)
        
        # シークバー（範囲マーカー付き）
        seekbar_frame = ttk.Frame(self.root)
        seekbar_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.seekbar = RangeMarkerSeekbar(seekbar_frame)
        self.seekbar.pack(fill=tk.X)
        self.seekbar.set_seek_callback(self._on_seekbar_click)
        
        # 範囲設定ボタン
        range_button_frame = ttk.Frame(self.root)
        range_button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(range_button_frame, text="開始点に設定", 
                  command=self._set_start_point, style='Green.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(range_button_frame, text="終了点に設定", 
                  command=self._set_end_point, style='Red.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(range_button_frame, text="範囲をリセット", 
                  command=self._reset_range).pack(side=tk.LEFT, padx=5)
        
        self.range_label = ttk.Label(range_button_frame, text="範囲: 未設定", font=('Arial', 10, 'bold'))
        self.range_label.pack(side=tk.LEFT, padx=20)
        
        # オプション
        option_frame = ttk.LabelFrame(self.root, text="オプション", padding=10)
        option_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Checkbutton(
            option_frame,
            text="プレビューをスキップ（直接フル画質でダウンロード）",
            variable=self.skip_preview_var
        ).pack(anchor=tk.W)
        
        # ダウンロードボタン
        download_frame = ttk.Frame(self.root)
        download_frame.pack(fill=tk.X, padx=10, pady=15)
        
        ttk.Button(
            download_frame, text="📥 フル動画をダウンロード → Google Drive",
            command=self._download_full, style='Blue.TButton'
        ).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(
            download_frame, text="✂ 範囲を切り出してダウンロード → Google Drive",
            command=self._download_range, style='Green.TButton'
        ).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # スタイル設定
        style = ttk.Style()
        style.configure('Blue.TButton', font=('Arial', 10, 'bold'))
        style.configure('Green.TButton', font=('Arial', 10, 'bold'))
        style.configure('Red.TButton', font=('Arial', 10, 'bold'))
    
    def _on_volume_change(self, value):
        """音量変更"""
        if self.player and self.has_audio:
            self.player.set_volume(int(float(value)))
    
    def _load_preview(self):
        """プレビュー動画を読み込む"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "YouTube URLを入力してください")
            return
        
        self.video_url = url
        
        if self.skip_preview_var.get():
            messagebox.showinfo("情報", "プレビューをスキップします。\nダウンロードボタンをクリックしてください。")
            return
        
        # 非同期でプレビューダウンロード
        self.play_btn.config(state='disabled', text="読込中...")
        threading.Thread(target=self._download_preview_thread, daemon=True).start()
    
    def _download_preview_thread(self):
        """プレビュー動画をダウンロード（バックグラウンド）"""
        try:
            print("[Info] プレビュー用動画をダウンロード中（低画質）...")
            
            preview_path = self.downloader.download_video(
                self.video_url,
                output_path=self.temp_dir,
                quality='worst'
            )
            
            if preview_path and os.path.exists(preview_path):
                self.preview_file = preview_path
                self.temp_files.append(preview_path)
                
                # UIスレッドで動画を読み込む
                self.root.after(0, self._load_video_to_player)
            else:
                self.root.after(0, lambda: messagebox.showerror("エラー", "プレビューのダウンロードに失敗しました"))
                self.root.after(0, lambda: self.play_btn.config(state='normal', text="▶ 再生"))
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("エラー", f"プレビュー読込エラー:\n{e}"))
            self.root.after(0, lambda: self.play_btn.config(state='normal', text="▶ 再生"))
    
    def _load_video_to_player(self):
        """プレーヤーに動画を読み込む"""
        try:
            duration = self.player.load_video(self.preview_file)
            self.seekbar.set_duration(duration)
            self.end_time = duration
            self.seekbar.set_end_marker(duration)
            self._update_time_display()
            self._update_range_label()
            print(f"[Info] プレビュー読込完了 ({duration:.1f}秒)")
            self.play_btn.config(state='normal', text="▶ 再生")
        except Exception as e:
            messagebox.showerror("エラー", f"動画の読み込みに失敗:\n{e}")
            self.play_btn.config(state='normal', text="▶ 再生")
    
    def _toggle_play(self):
        """再生/一時停止の切り替え"""
        if not self.player or not self.player.is_loaded:
            messagebox.showwarning("警告", "先にプレビューを読み込んでください")
            return
        
        if self.player.is_playing():
            self.player.pause()
            self.play_btn.config(text="▶ 再生")
        else:
            self.player.play()
            self.play_btn.config(text="❚❚ 一時停止")
    
    def _stop(self):
        """停止"""
        if self.player and self.player.is_loaded:
            self.player.stop()
            self.play_btn.config(text="▶ 再生")
    
    def _seek_relative(self, seconds):
        """相対シーク"""
        if not self.player or not self.player.is_loaded:
            return
        
        was_playing = self.player.is_playing()
        if was_playing:
            self.player.pause()
        
        current_time = self.player.get_time()
        new_time = max(0, min(current_time + seconds, self.seekbar.duration))
        self.player.set_position(new_time / self.seekbar.duration)
        
        # OpenCVの場合は手動でフレームを更新
        if isinstance(self.player, OpenCVVideoPlayer):
            self.player.update_frame()
        
        # 再生中だった場合は再開
        if was_playing:
            self.root.after(100, self.player.play)
    
    def _on_seekbar_click(self, pos_sec):
        """シークバークリック時の処理"""
        if self.player and self.player.is_loaded:
            # 再生中でも確実にシーク位置を設定
            was_playing = self.player.is_playing()
            if was_playing:
                self.player.pause()
            
            self.player.set_position(pos_sec / self.seekbar.duration)
            
            # OpenCVの場合は手動でフレームを更新
            if isinstance(self.player, OpenCVVideoPlayer):
                self.player.update_frame()
            
            # 再生中だった場合は再開
            if was_playing:
                # 少し待ってから再開（シーク処理を確実に完了させる）
                self.root.after(100, self.player.play)
    
    def _set_start_point(self):
        """現在位置を開始点に設定"""
        if not self.player or not self.player.is_loaded:
            messagebox.showwarning("警告", "先にプレビューを読み込んでください")
            return
        
        self.start_time = self.player.get_time()
        self.seekbar.set_start_marker(self.start_time)
        self._update_range_label()
        print(f"[Info] 開始点: {self._format_time(self.start_time)}")
    
    def _set_end_point(self):
        """現在位置を終了点に設定"""
        if not self.player or not self.player.is_loaded:
            messagebox.showwarning("警告", "先にプレビューを読み込んでください")
            return
        
        self.end_time = self.player.get_time()
        self.seekbar.set_end_marker(self.end_time)
        self._update_range_label()
        print(f"[Info] 終了点: {self._format_time(self.end_time)}")
    
    def _reset_range(self):
        """範囲をリセット"""
        if self.player and self.player.is_loaded:
            self.start_time = 0
            self.end_time = self.seekbar.duration
            self.seekbar.set_start_marker(0)
            self.seekbar.set_end_marker(self.seekbar.duration)
            self._update_range_label()
            print("[Info] 範囲をリセットしました")
    
    def _update_range_label(self):
        """範囲ラベルの更新"""
        start_str = self._format_time(self.start_time)
        end_str = self._format_time(self.end_time)
        duration = self.end_time - self.start_time
        self.range_label.config(text=f"範囲: {start_str} ～ {end_str} ({self._format_time(duration)})")
    
    def _update_time_display(self):
        """時間表示の更新"""
        if self.player and self.player.is_loaded:
            current = self.player.get_time()
            total = self.seekbar.duration
            self.time_label.config(text=f"{self._format_time(current)} / {self._format_time(total)}")
    
    def _format_time(self, seconds):
        """秒をMM:SS形式に変換"""
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"
    
    def _update_loop(self):
        """定期更新ループ"""
        if self.player and self.player.is_loaded:
            # OpenCVの場合はフレームを進める
            if isinstance(self.player, OpenCVVideoPlayer) and self.player.is_playing():
                self.player.advance_frame()
            
            # 現在位置を取得して更新
            try:
                current_time = self.player.get_time()
                if current_time is not None and current_time >= 0:
                    self.seekbar.set_current_position(current_time)
                    self._update_time_display()
            except Exception as e:
                pass  # エラーを無視して継続
        
        self.root.after(100, self._update_loop)
    
    def _download_full(self):
        """フル動画をダウンロードしてGoogle Driveにアップロード"""
        url = self.video_url if self.video_url else self.url_entry.get().strip()
        
        if not url:
            messagebox.showwarning("警告", "YouTube URLを入力してください")
            return
        
        if not self.drive_manager or not self.drive_folder_id:
            messagebox.showerror("エラー", "Google Driveが利用できません。\n環境変数を確認してください。")
            return
        
        # 非同期でダウンロード
        threading.Thread(target=self._download_full_thread, args=(url,), daemon=True).start()
    
    def _download_full_thread(self, url):
        """フル動画をダウンロード（バックグラウンド）"""
        try:
            print("[Info] フル動画をダウンロード中（1080p）...")
            
            # 1080p固定でダウンロード
            downloaded_file = self.downloader.download_video(url, output_path=self.temp_dir, quality='1080p')
            
            if downloaded_file and os.path.exists(downloaded_file):
                self.temp_files.append(downloaded_file)
                
                # 縦型動画に変換
                print("[Info] 縦型動画に変換中...")
                vertical_file = os.path.join(self.temp_dir, "output_vertical.mp4")
                converter = VideoVerticalConverter(input_path=downloaded_file, output_path=vertical_file)
                converter.generate()
                self.temp_files.append(vertical_file)
                
                # Google Driveにアップロード
                print("[Info] Google Driveにアップロード中...")
                # ファイル名に_verticalを追加
                base_name = os.path.splitext(os.path.basename(downloaded_file))[0]
                file_name = f"{base_name}_vertical.mp4"
                upload_result = self.drive_manager.upload_file(
                    vertical_file,
                    self.drive_folder_id,
                    file_name=file_name
                )
                
                if upload_result:
                    # 一時ファイル削除
                    self._cleanup_temp_files()
                    self.root.after(0, lambda: messagebox.showinfo(
                        "成功",
                        f"フル動画のダウンロードとアップロードが完了しました！\n\nファイル名: {file_name}\n\nGUIを閉じます。"
                    ))
                    # GUIを閉じる
                    self.root.after(100, self.root.destroy)
                else:
                    self.root.after(0, lambda: messagebox.showerror("エラー", "Google Driveへのアップロードに失敗しました"))
            else:
                self.root.after(0, lambda: messagebox.showerror("エラー", "動画のダウンロードに失敗しました"))
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("エラー", f"ダウンロードエラー:\n{e}"))
    
    def _download_range(self):
        """範囲を切り出してGoogle Driveにアップロード"""
        url = self.video_url if self.video_url else self.url_entry.get().strip()
        
        if not url:
            messagebox.showwarning("警告", "YouTube URLを入力してください")
            return
        
        if self.start_time >= self.end_time:
            messagebox.showwarning("警告", "開始点と終了点を正しく設定してください")
            return
        
        if not self.drive_manager or not self.drive_folder_id:
            messagebox.showerror("エラー", "Google Driveが利用できません。\n環境変数を確認してください。")
            return
        
        # 非同期でダウンロード
        threading.Thread(
            target=self._download_range_thread,
            args=(url, self.start_time, self.end_time),
            daemon=True
        ).start()
    
    def _download_range_thread(self, url, start_time, end_time):
        """範囲を切り出してダウンロード（バックグラウンド）"""
        try:
            print(f"[Info] 範囲を切り出し中 ({self._format_time(start_time)} ～ {self._format_time(end_time)}, 1080p)...")
            
            # 1080p固定でダウンロード
            downloaded_file = self.downloader.download_video(
                url,
                output_path=self.temp_dir,
                quality='1080p',
                start_time=start_time,
                end_time=end_time
            )
            
            if downloaded_file and os.path.exists(downloaded_file):
                self.temp_files.append(downloaded_file)
                
                # 縦型動画に変換
                print("[Info] 縦型動画に変換中...")
                vertical_file = os.path.join(self.temp_dir, "output_vertical_clip.mp4")
                converter = VideoVerticalConverter(input_path=downloaded_file, output_path=vertical_file)
                converter.generate()
                self.temp_files.append(vertical_file)
                
                # ファイル名に範囲情報を追加
                base_name = os.path.splitext(os.path.basename(downloaded_file))[0]
                new_name = f"{base_name}_{self._format_time(start_time).replace(':', '-')}～{self._format_time(end_time).replace(':', '-')}_vertical.mp4"
                
                # Google Driveにアップロード
                print("[Info] Google Driveにアップロード中...")
                upload_result = self.drive_manager.upload_file(
                    vertical_file,
                    self.drive_folder_id,
                    file_name=new_name
                )
                
                if upload_result:
                    # 一時ファイル削除
                    self._cleanup_temp_files()
                    self.root.after(0, lambda: messagebox.showinfo(
                        "成功",
                        f"動画の切り出しとアップロードが完了しました！\n\nファイル名: {new_name}\n\nGUIを閉じます。"
                    ))
                    # GUIを閉じる
                    self.root.after(100, self.root.destroy)
                else:
                    self.root.after(0, lambda: messagebox.showerror("エラー", "Google Driveへのアップロードに失敗しました"))
            else:
                self.root.after(0, lambda: messagebox.showerror("エラー", "動画の切り出しに失敗しました"))
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("エラー", f"処理エラー:\n{e}"))
    
    def _cleanup_temp_files(self):
        """一時ファイルを削除"""
        print("[Info] 一時ファイルを削除中...")
        time.sleep(1)  # ファイルハンドルの解放を待つ
        
        for file_path in self.temp_files:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"[Info] 削除: {file_path}")
                except PermissionError:
                    print(f"[Warning] 削除できませんでした（使用中）: {file_path}")
                except Exception as e:
                    print(f"[Error] 削除エラー: {file_path} - {e}")
        
        self.temp_files.clear()
    
    def run(self):
        """アプリケーションを実行"""
        try:
            self.root.mainloop()
        finally:
            # 終了時のクリーンアップ
            if self.player:
                self.player.release()
            self._cleanup_temp_files()


if __name__ == "__main__":
    print("=" * 60)
    print("YouTube Video Clipper - 動画切り出しツール")
    print("=" * 60)
    print()
    
    # VLCの利用可否チェック
    try:
        import vlc
        print("[Info] ✓ VLCライブラリが利用可能（音声付きプレビュー）")
    except ImportError:
        print("[Warning] python-vlcがインストールされていません")
        print("[Info] → OpenCVプレーヤーを使用します（音声なし）")
        print("[Info] 音声付きプレビューを使用する場合:")
        print("       1. VLC本体をインストール: https://www.videolan.org/vlc/")
        print("       2. pip install python-vlc")
    
    print()
    
    # アプリケーション起動
    app = VideoClipperGUI()
    app.run()
