#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BPM同期スライドショー動画作成ツール
音源のBPMを自動検出し、ビートに同期した写真スライドショー動画を生成します。
"""

import os
import sys
import random
import glob
from pathlib import Path
from datetime import datetime
import cv2
import numpy as np
import librosa
from PIL import Image, ImageFont, ImageDraw
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_SUPPORT = True
except ImportError:
    HEIF_SUPPORT = False
import subprocess
import tempfile
import shutil


# ========================================
# 定数定義
# ========================================
TITLE_FONT_SIZE = 40  # タイトルフォントサイズ（小さめ）
DATE_FONT_SIZE = 30   # 日付フォントサイズ
TEXT_COLOR = (255, 255, 255)  # 白色
BG_COLOR = (0, 0, 0)  # 黒色
OPENING_BEATS = 4  # オープニング画面の拍数
MIN_BEATS = 0.5  # 写真表示の最小拍数
MAX_BEATS = 4  # 写真表示の最大拍数
BEAT_OPTIONS = [0.5, 1, 2, 3, 4]  # 選択可能な拍数

VIDEO_FORMATS = {
    '1': {'name': '横', 'width': 1920, 'height': 1080},
    '2': {'name': '縦', 'width': 1080, 'height': 1920}
}

SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']
if HEIF_SUPPORT:
    SUPPORTED_IMAGE_FORMATS.extend(['.heic', '.heif'])


# ========================================
# ユーティリティ関数
# ========================================
def print_header(text):
    """ヘッダーテキストを表示"""
    print(f"\n{'='*50}")
    print(f"  {text}")
    print(f"{'='*50}\n")


def print_progress(text):
    """進捗メッセージを表示"""
    print(f"▶ {text}")


def print_success(text):
    """成功メッセージを表示"""
    print(f"✓ {text}")


def print_error(text):
    """エラーメッセージを表示"""
    print(f"✗ エラー: {text}", file=sys.stderr)


def parse_time(time_str):
    """時間文字列をパース（MM:SS または SS 形式）"""
    time_str = time_str.strip()
    if not time_str:
        return None
    
    try:
        # MM:SS形式
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            elif len(parts) == 3:
                # HH:MM:SS形式
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        else:
            # 秒のみ
            return float(time_str)
    except ValueError:
        return None


def format_time(seconds):
    """秒数を MM:SS 形式に変換"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


# ========================================
# 対話形式の入力機能
# ========================================
def get_user_input():
    """対話形式でユーザー入力を取得"""
    print_header("BPM同期スライドショー動画作成ツール")
    
    # 写真フォルダ
    while True:
        photo_folder = input("写真フォルダのパスを入力: ").strip().strip('"')
        if os.path.isdir(photo_folder):
            break
        print_error("フォルダが存在しません。もう一度入力してください。")
    
    # 音源ファイル
    while True:
        audio_file = input("音源ファイルのパスを入力: ").strip().strip('"')
        if os.path.isfile(audio_file):
            break
        print_error("ファイルが存在しません。もう一度入力してください。")
    
    # 音源の長さを取得
    try:
        total_audio_duration = librosa.get_duration(path=audio_file)
        print(f"\n音源の総時間: {format_time(total_audio_duration)} ({total_audio_duration:.1f}秒)")
    except Exception as e:
        print_error(f"音源ファイルの読み込みに失敗しました: {e}")
        sys.exit(1)
    
    # 音源の開始時間
    print("\n音源の使用範囲を指定（空白で全体を使用）:")
    print("  形式: MM:SS または 秒数（例: 1:30 または 90）")
    while True:
        start_time_str = input(f"開始時間 [0:00]: ").strip()
        if not start_time_str:
            audio_start = 0.0
            break
        audio_start = parse_time(start_time_str)
        if audio_start is not None and 0 <= audio_start < total_audio_duration:
            break
        print_error(f"0〜{format_time(total_audio_duration)}の範囲で入力してください。")
    
    # 音源の終了時間
    while True:
        end_time_str = input(f"終了時間 [{format_time(total_audio_duration)}]: ").strip()
        if not end_time_str:
            audio_end = total_audio_duration
            break
        audio_end = parse_time(end_time_str)
        if audio_end is not None and audio_start < audio_end <= total_audio_duration:
            break
        print_error(f"{format_time(audio_start)}〜{format_time(total_audio_duration)}の範囲で入力してください。")
    
    audio_duration = audio_end - audio_start
    print(f"  → 使用する音源: {format_time(audio_start)} 〜 {format_time(audio_end)} (長さ: {format_time(audio_duration)})")
    
    # 動画形式
    while True:
        print("\n動画形式を選択:")
        print("  1: 横 (1920x1080)")
        print("  2: 縦 (1080x1920)")
        video_format = input("選択 (1 or 2): ").strip()
        if video_format in VIDEO_FORMATS:
            break
        print_error("1または2を入力してください。")
    
    # タイトル
    title = input("\nタイトルを入力: ").strip()
    
    # 開始日付
    while True:
        start_date = input("開始日付 (YYYY/MM/DD): ").strip()
        try:
            datetime.strptime(start_date, "%Y/%m/%d")
            break
        except ValueError:
            print_error("日付形式が正しくありません。YYYY/MM/DD形式で入力してください。")
    
    # 終了日付
    while True:
        end_date = input("終了日付 (YYYY/MM/DD): ").strip()
        try:
            datetime.strptime(end_date, "%Y/%m/%d")
            break
        except ValueError:
            print_error("日付形式が正しくありません。YYYY/MM/DD形式で入力してください。")
    
    # フォントファイル（オプション）
    font_path = input("\nフォントファイルパス (.ttf) [空白でシステムフォント]: ").strip().strip('"')
    if font_path and not os.path.isfile(font_path):
        print_error("フォントファイルが見つかりません。システムフォントを使用します。")
        font_path = ""
    
    # 写真切り替えモード
    while True:
        print("\n写真の切り替えモードを選択:")
        print("  1: ランダム（1〜4拍でランダムに切り替え）")
        print("  2: 自動調整（音源の激しさに応じて切り替え速度を変更）")
        switch_mode = input("選択 (1 or 2) [2]: ").strip()
        if not switch_mode:
            switch_mode = '2'
        if switch_mode in ['1', '2']:
            break
        print_error("1または2を入力してください。")
    
    use_intensity_analysis = (switch_mode == '2')
    
    return {
        'photo_folder': photo_folder,
        'audio_file': audio_file,
        'audio_start': audio_start,
        'audio_end': audio_end,
        'audio_duration': audio_duration,
        'video_format': VIDEO_FORMATS[video_format],
        'title': title,
        'start_date': start_date,
        'end_date': end_date,
        'font_path': font_path,
        'use_intensity_analysis': use_intensity_analysis
    }


# ========================================
# BPM検出機能
# ========================================
def detect_bpm(audio_file):
    """音源ファイルからBPMを検出"""
    print_progress("BPMを検出中...")
    try:
        y, sr = librosa.load(audio_file)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        # tempoがarrayの場合は最初の要素を取得
        if isinstance(tempo, np.ndarray):
            tempo = tempo[0]
        bpm = float(tempo)
        print_success(f"検出されたBPM: {bpm:.1f}")
        return bpm
    except Exception as e:
        print_error(f"BPM検出に失敗しました: {e}")
        sys.exit(1)


def get_beat_duration(bpm):
    """BPMから1拍の時間（秒）を計算"""
    return 60.0 / bpm


# ========================================
# 音響特徴量分析機能
# ========================================
def analyze_intensity(audio_file, audio_start, audio_end, sr=22050):
    """音源の激しさを時系列で分析
    
    Returns:
        times: 時間軸の配列（秒）
        intensity_scores: 激しさスコアの配列（0.0〜1.0）
    """
    print_progress("音源の激しさを分析中...")
    
    try:
        # 指定範囲の音源を読み込み
        y, sr = librosa.load(audio_file, sr=sr, offset=audio_start, duration=audio_end - audio_start)
        
        # 1. RMSエネルギー（音量）
        rms = librosa.feature.rms(y=y)[0]
        
        # 2. スペクトル重心（音の明るさ）
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        
        # 3. ゼロ交差率（音の粗さ）
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        
        # 各特徴量を正規化（0〜1）
        rms_norm = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-8)
        centroid_norm = (spectral_centroid - np.min(spectral_centroid)) / (np.max(spectral_centroid) - np.min(spectral_centroid) + 1e-8)
        zcr_norm = (zcr - np.min(zcr)) / (np.max(zcr) - np.min(zcr) + 1e-8)
        
        # 重み付き平均で激しさスコアを計算
        # RMS（音量）: 50%, スペクトル重心（明るさ）: 30%, ゼロ交差率（粗さ）: 20%
        intensity = 0.5 * rms_norm + 0.3 * centroid_norm + 0.2 * zcr_norm
        
        # 時間軸を計算
        hop_length = 512
        times = librosa.frames_to_time(np.arange(len(intensity)), sr=sr, hop_length=hop_length)
        
        print_success(f"激しさ分析完了！（{len(intensity)}サンプル）")
        
        return times, intensity
        
    except Exception as e:
        print_error(f"音響分析に失敗しました: {e}")
        sys.exit(1)


def determine_beat_intervals(intensity_times, intensity_scores, beat_times, min_beats=0.5, max_beats=4):
    """各ビート位置での写真表示拍数を決定
    
    Args:
        intensity_times: 激しさスコアの時間軸
        intensity_scores: 激しさスコアの配列
        beat_times: ビート位置の時間配列
        min_beats: 最小拍数
        max_beats: 最大拍数
    
    Returns:
        beat_intervals: 各写真の表示拍数のリスト
    """
    print_progress("ビート間隔を計算中...")
    
    beat_intervals = []
    
    for i in range(len(beat_times) - 1):
        beat_start = beat_times[i]
        beat_end = beat_times[i + 1]
        
        # このビート区間の激しさの平均を計算
        mask = (intensity_times >= beat_start) & (intensity_times < beat_end)
        if np.sum(mask) > 0:
            avg_intensity = np.mean(intensity_scores[mask])
        else:
            # データがない場合は中間値
            avg_intensity = 0.5
        
        # 激しさスコアに基づいて拍数を決定
        # スコアが高い（激しい）→ 少ない拍数（速い切り替え）
        # スコアが低い（穏やか）→ 多い拍数（ゆっくり切り替え）
        if avg_intensity >= 0.8:
            beats = 0.5  # 0.5拍（非常に激しい）
        elif avg_intensity >= 0.65:
            beats = 1  # 1拍（激しい）
        elif avg_intensity >= 0.5:
            beats = 2  # 2拍（中程度）
        elif avg_intensity >= 0.35:
            beats = 3  # 3拍（やや穏やか）
        else:
            beats = 4  # 4拍（穏やか）
        
        beat_intervals.append(beats)
    
    # 統計情報を表示
    if beat_intervals:
        from collections import Counter
        counter = Counter(beat_intervals)
        print_success(f"拍数分布: {dict(counter)}")
    
    return beat_intervals


# ========================================
# 日本語フォント検出機能
# ========================================
def find_system_font():
    """Windowsのシステムフォントから日本語対応フォントを検索"""
    font_candidates = [
        r"C:\Windows\Fonts\meiryo.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
        r"C:\Windows\Fonts\YuGothM.ttc",
        r"C:\Windows\Fonts\YuGothR.ttc",
        r"C:\Windows\Fonts\msmincho.ttc",
    ]
    
    for font_path in font_candidates:
        if os.path.exists(font_path):
            return font_path
    
    return None


def get_font(font_path, size):
    """フォントオブジェクトを取得"""
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception as e:
            print_error(f"フォントの読み込みに失敗: {e}")
    
    # システムフォントを検索
    system_font = find_system_font()
    if system_font:
        try:
            return ImageFont.truetype(system_font, size)
        except Exception:
            pass
    
    # デフォルトフォントを使用
    return ImageFont.load_default()


# ========================================
# 画像読み込み・処理機能
# ========================================
def load_images(folder_path):
    """フォルダ内の画像ファイルを読み込む"""
    print_progress("画像を読み込み中...")
    
    image_files = []
    for ext in SUPPORTED_IMAGE_FORMATS:
        image_files.extend(glob.glob(os.path.join(folder_path, f"*{ext}")))
        image_files.extend(glob.glob(os.path.join(folder_path, f"*{ext.upper()}")))
    
    if not image_files:
        print_error("画像ファイルが見つかりません。")
        sys.exit(1)
    
    # シャッフル
    random.shuffle(image_files)
    
    print_success(f"画像を読み込み完了！（{len(image_files)}枚）")
    return image_files


def resize_with_letterbox(image, target_width, target_height):
    """アスペクト比を維持しながら黒帯付きでリサイズ"""
    h, w = image.shape[:2]
    target_aspect = target_width / target_height
    image_aspect = w / h
    
    if image_aspect > target_aspect:
        # 横長画像: 幅を基準にリサイズ
        new_w = target_width
        new_h = int(target_width / image_aspect)
    else:
        # 縦長画像: 高さを基準にリサイズ
        new_h = target_height
        new_w = int(target_height * image_aspect)
    
    # リサイズ
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # 黒背景に配置
    result = np.zeros((target_height, target_width, 3), dtype=np.uint8)
    y_offset = (target_height - new_h) // 2
    x_offset = (target_width - new_w) // 2
    result[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
    
    return result


def load_image_file(image_path):
    """画像ファイルを読み込み（HEIC対応、日本語パス対応、EXIF回転対応）"""
    ext = os.path.splitext(image_path)[1].lower()
    
    # 常にPILを使用して読み込み（日本語パス対応のため）
    try:
        pil_image = Image.open(image_path)
        
        # EXIF情報から回転情報を取得して自動回転
        try:
            # ExifタグのOrientationを確認
            exif = pil_image.getexif()
            if exif:
                orientation = exif.get(0x0112)  # 0x0112 = Orientation tag
                
                # Orientationに基づいて回転・反転
                if orientation == 2:
                    pil_image = pil_image.transpose(Image.FLIP_LEFT_RIGHT)
                elif orientation == 3:
                    pil_image = pil_image.rotate(180, expand=True)
                elif orientation == 4:
                    pil_image = pil_image.transpose(Image.FLIP_TOP_BOTTOM)
                elif orientation == 5:
                    pil_image = pil_image.transpose(Image.FLIP_LEFT_RIGHT).rotate(90, expand=True)
                elif orientation == 6:
                    pil_image = pil_image.rotate(270, expand=True)
                elif orientation == 7:
                    pil_image = pil_image.transpose(Image.FLIP_LEFT_RIGHT).rotate(270, expand=True)
                elif orientation == 8:
                    pil_image = pil_image.rotate(90, expand=True)
        except Exception:
            # EXIF情報がない、または読み込めない場合はそのまま
            pass
        
        pil_image = pil_image.convert('RGB')
        # PIL画像をOpenCV形式に変換
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    except Exception as e:
        # 読み込み失敗時はNoneを返す
        return None


# ========================================
# テキスト描画機能
# ========================================
def draw_text_on_image(image, title, date_range, font_path, is_opening=False):
    """画像にテキストをオーバーレイ（PIL使用で日本語対応）"""
    # OpenCV画像をPIL画像に変換
    pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_image)
    
    # フォントを取得
    title_font = get_font(font_path, TITLE_FONT_SIZE)
    date_font = get_font(font_path, DATE_FONT_SIZE)
    
    # 画像サイズ
    width, height = pil_image.size
    
    # テキストのバウンディングボックスを取得
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    date_bbox = draw.textbbox((0, 0), date_range, font=date_font)
    
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    date_w = date_bbox[2] - date_bbox[0]
    date_h = date_bbox[3] - date_bbox[1]
    
    # 中央配置の座標計算
    title_x = (width - title_w) // 2
    date_x = (width - date_w) // 2
    
    # Y座標（中央に配置）
    total_h = title_h + date_h + 10  # 10pxの間隔
    start_y = (height - total_h) // 2
    
    title_y = start_y
    date_y = start_y + title_h + 10
    
    # テキストを描画
    draw.text((title_x, title_y), title, font=title_font, fill=TEXT_COLOR)
    draw.text((date_x, date_y), date_range, font=date_font, fill=TEXT_COLOR)
    
    # PIL画像をOpenCV画像に変換
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)


# ========================================
# オープニング画面生成
# ========================================
def create_opening_frame(width, height, title, date_range, font_path):
    """オープニング用の黒背景フレームを生成"""
    # 黒背景
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # テキストを追加
    frame = draw_text_on_image(frame, title, date_range, font_path, is_opening=True)
    
    return frame


# ========================================
# ffmpeg実行関数
# ========================================
def check_ffmpeg():
    """ffmpegがインストールされているか確認"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def create_video_with_ffmpeg(frames_folder, fps, width, height, output_file, audio_file, opening_duration, audio_start, audio_end):
    """ffmpegを使って動画を生成"""
    print_progress("ffmpegで動画を生成中...")
    
    # 一時的な無音動画を作成
    temp_silent_video = "temp_silent_video.mp4"
    temp_trimmed_audio = "temp_trimmed_audio.m4a"
    
    # 日本語パス対策: 音源ファイルを一時的にコピー
    temp_audio_copy = None
    if any(ord(c) > 127 for c in audio_file):
        # 日本語などの非ASCII文字が含まれている場合
        import tempfile
        temp_audio_copy = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
        print_progress(f"日本語パスを検出。一時ファイルにコピー中...")
        shutil.copy2(audio_file, temp_audio_copy)
        audio_file_to_use = temp_audio_copy
    else:
        audio_file_to_use = audio_file
    
    # フレーム画像から動画を生成
    ffmpeg_cmd = [
        'ffmpeg',
        '-y',  # 上書き
        '-framerate', str(fps),
        '-i', os.path.join(frames_folder, 'frame_%05d.png'),
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-pix_fmt', 'yuv420p',
        temp_silent_video
    ]
    
    try:
        result = subprocess.run(ffmpeg_cmd, capture_output=True)
        if result.returncode != 0:
            print_error(f"動画生成に失敗しました:")
            try:
                stderr_text = result.stderr.decode('utf-8', errors='replace')
            except:
                stderr_text = result.stderr.decode('cp932', errors='replace')
            print(f"STDERR: {stderr_text}")
            raise subprocess.CalledProcessError(result.returncode, ffmpeg_cmd)
    except subprocess.CalledProcessError as e:
        # 一時ファイルをクリーンアップ
        if temp_audio_copy and os.path.exists(temp_audio_copy):
            os.remove(temp_audio_copy)
        raise
    
    print_success("無音動画生成完了！")
    
    # 音源をトリミング
    print_progress(f"音源をトリミング中... ({format_time(audio_start)} 〜 {format_time(audio_end)})")
    
    # 音源の長さを計算
    trim_duration = audio_end - audio_start
    
    ffmpeg_trim_cmd = [
        'ffmpeg',
        '-y',
        '-i', audio_file_to_use,
        '-ss', str(audio_start),
        '-t', str(trim_duration),
        '-vn',  # 動画ストリームを無視（アルバムアート対策）
        '-c:a', 'aac',
        '-b:a', '192k',
        temp_trimmed_audio
    ]
    
    try:
        # エンコーディングエラーを回避するためにバイナリモードで取得
        result = subprocess.run(ffmpeg_trim_cmd, capture_output=True)
        if result.returncode != 0:
            print_error(f"音源のトリミングに失敗しました:")
            # UTF-8でデコードを試みる
            try:
                stderr_text = result.stderr.decode('utf-8', errors='replace')
            except:
                stderr_text = result.stderr.decode('cp932', errors='replace')
            print(f"STDERR: {stderr_text}")
            raise subprocess.CalledProcessError(result.returncode, ffmpeg_trim_cmd)
    except subprocess.CalledProcessError as e:
        # 一時ファイルをクリーンアップ
        if temp_audio_copy and os.path.exists(temp_audio_copy):
            os.remove(temp_audio_copy)
        raise
    
    print_success("音源トリミング完了！")
    
    # 音声を結合（オープニング後から開始）
    print_progress("音声を結合中...")
    
    ffmpeg_audio_cmd = [
        'ffmpeg',
        '-y',
        '-i', temp_silent_video,
        '-i', temp_trimmed_audio,
        '-filter_complex', f'[1:a]adelay={int(opening_duration * 1000)}|{int(opening_duration * 1000)}[delayed]',
        '-map', '0:v',
        '-map', '[delayed]',
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        output_file
    ]
    
    try:
        result = subprocess.run(ffmpeg_audio_cmd, capture_output=True)
        if result.returncode != 0:
            print_error(f"音声結合に失敗しました:")
            try:
                stderr_text = result.stderr.decode('utf-8', errors='replace')
            except:
                stderr_text = result.stderr.decode('cp932', errors='replace')
            print(f"STDERR: {stderr_text}")
            # 音声なしの動画をリネームして返す
            if os.path.exists(temp_silent_video):
                shutil.move(temp_silent_video, output_file)
                print(f"音声なしの動画を保存: {output_file}")
            # 一時ファイルをクリーンアップ
            if temp_audio_copy and os.path.exists(temp_audio_copy):
                os.remove(temp_audio_copy)
            return
    except subprocess.CalledProcessError as e:
        # 音声なしの動画をリネームして返す
        if os.path.exists(temp_silent_video):
            shutil.move(temp_silent_video, output_file)
            print(f"音声なしの動画を保存: {output_file}")
        # 一時ファイルをクリーンアップ
        if temp_audio_copy and os.path.exists(temp_audio_copy):
            os.remove(temp_audio_copy)
        return
    
    # 一時ファイル削除
    if os.path.exists(temp_silent_video):
        os.remove(temp_silent_video)
    if os.path.exists(temp_trimmed_audio):
        os.remove(temp_trimmed_audio)
    if temp_audio_copy and os.path.exists(temp_audio_copy):
        os.remove(temp_audio_copy)
    
    print_success("音声結合完了！")


# ========================================
# 動画生成機能
# ========================================
def generate_slideshow(config, bpm, image_files):
    """スライドショー動画を生成"""
    
    # ffmpegの確認
    if not check_ffmpeg():
        print_error("ffmpegがインストールされていません。")
        print("ffmpegをインストールしてから再度実行してください。")
        print("ダウンロード: https://ffmpeg.org/download.html")
        sys.exit(1)
    
    print_progress("動画フレームを生成中...")
    
    # パラメータ取得
    width = config['video_format']['width']
    height = config['video_format']['height']
    format_name = config['video_format']['name']
    title = config['title']
    date_range = f"{config['start_date']} - {config['end_date']}"
    font_path = config['font_path']
    audio_file = config['audio_file']
    audio_start = config['audio_start']
    audio_end = config['audio_end']
    audio_duration = config['audio_duration']
    
    # FPS設定
    fps = 30
    
    # 拍の長さ計算
    beat_duration = get_beat_duration(bpm)
    opening_duration = beat_duration * OPENING_BEATS
    
    print(f"  - 1拍の時間: {beat_duration:.2f}秒")
    print(f"  - オープニング時間: {opening_duration:.2f}秒（{OPENING_BEATS}拍分）")
    print(f"  - 使用する音源: {format_time(audio_start)} 〜 {format_time(audio_end)} (長さ: {format_time(audio_duration)})")
    
    # 激しさ分析モードの場合
    use_intensity = config.get('use_intensity_analysis', False)
    beat_intervals = []
    
    if use_intensity:
        # 音源を分析
        intensity_times, intensity_scores = analyze_intensity(audio_file, audio_start, audio_end)
        
        # ビート位置を計算
        num_beats = int(audio_duration / beat_duration)
        beat_times = np.arange(num_beats) * beat_duration
        
        # 各ビートでの表示拍数を決定
        beat_intervals = determine_beat_intervals(intensity_times, intensity_scores, beat_times, MIN_BEATS, MAX_BEATS)
        
        print(f"  - モード: 自動調整（激しさ分析）")
    else:
        print(f"  - モード: ランダム")
    
    # 出力ファイル名
    timestamp = datetime.now().strftime("%Y-%m-%d")
    mode_suffix = "auto" if use_intensity else "random"
    output_file = f"slideshow_{format_name}_{width}x{height}_{int(bpm)}bpm_{mode_suffix}_{timestamp}.mp4"
    
    # 一時フレーム保存用ディレクトリ
    frames_dir = tempfile.mkdtemp(prefix='slideshow_frames_')
    
    try:
        # オープニング画面を生成
        opening_frame = create_opening_frame(width, height, title, date_range, font_path)
        opening_frames = int(opening_duration * fps)
        
        frame_number = 0
        
        # オープニングフレームを保存
        for _ in range(opening_frames):
            frame_path = os.path.join(frames_dir, f'frame_{frame_number:05d}.png')
            cv2.imwrite(frame_path, opening_frame)
            frame_number += 1
        
        # スライドショー部分を生成
        remaining_duration = audio_duration
        current_time = 0
        image_index = 0
        total_images = len(image_files)
        beat_index = 0
        
        while current_time < remaining_duration:
            # 拍数を決定
            if use_intensity and beat_index < len(beat_intervals):
                # 激しさ分析に基づく拍数
                beats = beat_intervals[beat_index]
                beat_index += 1
            else:
                # ランダムな拍数（0.5, 1, 2, 3, 4拍）
                beats = random.choice(BEAT_OPTIONS)
            
            duration = beat_duration * beats
            
            # 画像を読み込み
            image_path = image_files[image_index % total_images]
            image = load_image_file(image_path)
            
            if image is None:
                print_error(f"画像の読み込みに失敗: {image_path}")
                image_index += 1
                continue
            
            # リサイズ
            resized_image = resize_with_letterbox(image, width, height)
            
            # テキストをオーバーレイ
            frame = draw_text_on_image(resized_image, title, date_range, font_path)
            
            # フレームを保存
            frame_count = int(duration * fps)
            for _ in range(frame_count):
                frame_path = os.path.join(frames_dir, f'frame_{frame_number:05d}.png')
                cv2.imwrite(frame_path, frame)
                frame_number += 1
            
            current_time += duration
            image_index += 1
            
            # 進捗表示
            progress = (current_time / remaining_duration) * 100
            print(f"\r  フレーム生成進捗: {progress:.1f}% ({image_index}枚目の画像, {beats}拍)", end='')
        
        print()  # 改行
        print_success(f"全{frame_number}フレームを生成完了！")
        
        # ffmpegで動画を生成・音声結合
        create_video_with_ffmpeg(frames_dir, fps, width, height, output_file, audio_file, opening_duration, audio_start, audio_end)
        
    finally:
        # 一時フレームディレクトリを削除
        if os.path.exists(frames_dir):
            shutil.rmtree(frames_dir)
            print_progress("一時ファイルを削除しました")
    
    return output_file


# ========================================
# メイン処理
# ========================================
def main():
    """メイン処理"""
    try:
        # ユーザー入力を取得
        config = get_user_input()
        
        # BPMを検出
        bpm = detect_bpm(config['audio_file'])
        
        # 画像を読み込み
        image_files = load_images(config['photo_folder'])
        
        # 動画を生成
        output_file = generate_slideshow(config, bpm, image_files)
        
        # 完了メッセージ
        print_header("完成！")
        print(f"ファイル名: {output_file}")
        
        # 動画の総時間を表示（ffprobeで取得）
        if os.path.exists(output_file):
            try:
                result = subprocess.run(
                    ['ffprobe', '-v', 'error', '-show_entries', 
                     'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', 
                     output_file],
                    capture_output=True,
                    text=True,
                    check=True
                )
                total_time = float(result.stdout.strip())
                minutes = int(total_time // 60)
                seconds = int(total_time % 60)
                print(f"総時間: {minutes}分{seconds}秒")
            except (subprocess.CalledProcessError, FileNotFoundError):
                # ffprobeが使えない場合はスキップ
                pass
        
    except KeyboardInterrupt:
        print("\n\n処理が中断されました。")
        sys.exit(1)
    except Exception as e:
        print_error(f"予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
