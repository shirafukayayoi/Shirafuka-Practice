import os

import cv2
import numpy as np
from moviepy.editor import CompositeVideoClip, VideoFileClip, vfx


def blur_frame(frame, blur_strength=23):
    """
    OpenCVを使用してフレームにガウシアンブラーを適用する関数
    
    Args:
        frame: 入力フレーム（numpy配列）
        blur_strength: ぼかしの強度（奇数である必要がある）
    
    Returns:
        ぼかしが適用されたフレーム
    """
    # blur_strengthが偶数の場合、奇数に変換
    if blur_strength % 2 == 0:
        blur_strength += 1
    
    # OpenCVのGaussianBlurでぼかし効果を適用
    blurred = cv2.GaussianBlur(frame, (blur_strength, blur_strength), 0)
    return blurred


def generate_vertical_video_with_background(input_path, output_path, vertical_resolution=(1080, 1920)):
    """
    横動画を縦動画に変換し、背景に元の動画の拡大・ぼかしバージョンを配置します。

    Args:
        input_path (str): 入力横動画のファイルパス
        output_path (str): 出力縦動画のファイルパス
        vertical_resolution (tuple): 目的の縦動画の解像度 (横, 縦)
    """
    if not os.path.exists(input_path):
        print(f"エラー: 入力ファイルが見つかりません -> {input_path}")
        return

    # 1. 元の動画を読み込む
    original_clip = VideoFileClip(input_path)
    
    W, H = vertical_resolution[0], vertical_resolution[1] # 縦動画の幅と高さ

    # 横動画のサイズ
    orig_W, orig_H = original_clip.size
    
    # --- 2. 縦画面の背景クリップを作成 (拡大 & ぼかし) ---
    
    # 縦画面いっぱいに広がるように拡大率を計算 (縦動画の高さ / 横動画の高さ)
    # 縦幅いっぱいに拡大することで、左右がはみ出るようにする
    scale_factor_bg = H / orig_H
    
    # リサイズ後の幅を計算
    resized_bg_width = orig_W * scale_factor_bg
    
    # 中央位置を計算
    x_center_bg = resized_bg_width / 2
    y_center_bg = H / 2
    
    background_clip = original_clip.copy() \
        .fx(vfx.resize, newsize=(resized_bg_width, H)) \
        .fx(vfx.crop, width=W, height=H, x_center=x_center_bg, y_center=y_center_bg) \
        .fx(vfx.colorx, 1.3) \
        .fl_image(blur_frame)

    # vfx.colorx(1.3) で明るさを少し上げ、前景を目立たせる
    # fl_image(blur_frame) でOpenCVを使用してガウシアンブラー効果を適用
    
    # --- 3. 前景のクリップを作成 (中央に配置) ---
    
    # 縦動画の幅 (W) に合わせて元の動画の幅を調整
    # 前景のサイズを縦動画の横幅ぎりぎりまで使用
    foreground_width = W
    
    # 新しい幅に基づいた高さ
    scale_factor_fg = foreground_width / orig_W
    foreground_height = int(orig_H * scale_factor_fg)
    
    foreground_clip = original_clip.copy() \
        .fx(vfx.resize, newsize=(foreground_width, foreground_height))
    
    # --- 4. クリップを合成 (コンポジット) ---

    # 前景を縦動画の中央に配置するための位置計算
    # 横幅は100%使用するためx_pos = 0、縦は中央に配置
    x_pos = (W - foreground_width) / 2  # = 0 (横ぎりぎりまで使用)
    y_pos = (H - foreground_height) / 2
    
    final_clip = CompositeVideoClip(
        [
            background_clip.set_position("center"), # 背景クリップを中央に配置 (縦動画の解像度にクロップされているためそのまま)
            foreground_clip.set_position((x_pos, y_pos)) # 前景クリップを計算した位置に配置
        ],
        size=vertical_resolution # 最終的な動画の解像度を設定
    ).set_duration(original_clip.duration)

    # 5. 書き出し
    print(f"\n動画の書き出しを開始します... (解像度: {W}x{H})")
    print("処理には時間がかかる場合があります。")

    final_clip.write_videofile(
        output_path, 
        codec='libx264', # 標準的なH.264コーデック
        audio_codec='aac', # 標準的なAACオーディオコーデック
        temp_audiofile='temp-audio.m4a',
        remove_temp=True,
        fps=original_clip.fps,
        threads=4, # 処理を高速化するためにスレッド数を設定
        logger='bar' # 進行状況をプログレスバーで表示
    )
    
    print(f"\n✅ 完了しました! 出力ファイル: {output_path}")

# --- 実行部分 ---
if __name__ == "__main__":
    # 【ここを編集してください】
    INPUT_FILE = "movie.mp4" # 横動画のファイル名
    OUTPUT_FILE = "output_vertical.mp4" # 出力する縦動画のファイル名
    
    generate_vertical_video_with_background(INPUT_FILE, OUTPUT_FILE)    
    generate_vertical_video_with_background(INPUT_FILE, OUTPUT_FILE)