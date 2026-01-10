import os
import re
import subprocess


def download_vtt(video_url, ytdlp_path, output_name="subtitle"):
    """yt-dlpを使って字幕(VTT)をダウンロードする"""
    command = [
        ytdlp_path,
        "--write-subs",           # 字幕を書き込む
        "--skip-download",        # 動画本体はダウンロードしない
        "--sub-lang", "en",       # 言語指定（英語の場合。適宜変更可）
        "--output", output_name,
        video_url
    ]
    
    print(f"字幕を取得中...: {video_url}")
    subprocess.run(command, check=True)
    
    # 実際に保存されたファイル名を探す (yt-dlpは拡張子の前に言語コードを付けるため)
    expected_file = f"{output_name}.en.vtt"
    if os.path.exists(expected_file):
        return expected_file
    return None

def vtt_to_lrc(vtt_file, lrc_file):
    """VTT形式をLRC形式 [mm:ss.xx] に変換する"""
    with open(vtt_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    lrc_content = []
    # タイムスタンプの正規表現 (例: 00:00:02.123 --> 00:00:02.12)
    time_re = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})")

    for i, line in enumerate(lines):
        if "-->" in line:
            match = time_re.search(line)
            if match:
                hh, mm, ss, mmm = match.groups()
                # LRCは分:秒.ミリ秒[mm:ss.xx]が一般的。時間は分に合算
                total_mm = int(hh) * 60 + int(mm)
                lrc_time = f"[{total_mm:02}:{ss}.{mmm[:2]}]"
                
                # 次の行が歌詞テキスト
                if i + 1 < len(lines):
                    text = lines[i+1].strip()
                    # HTMLタグ（♪やカラーコード）を除去
                    text = re.sub(r'<[^>]+>', '', text)
                    if text:
                        lrc_content.append(f"{lrc_time}{text}")

    with open(lrc_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lrc_content))
    print(f"保存完了: {lrc_file}")

def main():
    # 設定
    # yt-dlpのパスを指定してください (例: "C:/tools/yt-dlp.exe" や "/usr/local/bin/yt-dlp")
    default_ytdlp = "yt-dlp" 
    
    url = input("YouTubeのURLを入力してください: ")
    path = input(f"yt-dlpのパスを入力してください (空欄で '{default_ytdlp}'): ") or default_ytdlp
    
    output_base = "lyrics_output"
    vtt_path = download_vtt(url, path, output_base)
    
    if vtt_path:
        lrc_path = f"{output_base}.lrc"
        vtt_to_lrc(vtt_path, lrc_path)
        # 一時ファイル(VTT)を削除したい場合は以下を有効化
        # os.remove(vtt_path)
    else:
        print("字幕の取得に失敗しました。字幕設定がオフの動画かもしれません。")

if __name__ == "__main__":
    main()