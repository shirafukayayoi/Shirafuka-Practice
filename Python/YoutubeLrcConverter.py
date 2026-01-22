import html
import os
import re
import subprocess


def download_vtt(video_url, ytdlp_path, output_name="subtitle"):
    """yt-dlpを使って字幕(VTT)をダウンロードする"""
    command = [
        ytdlp_path,
        "--write-subs",           # 字幕を書き込む
        "--skip-download",        # 動画本体はダウンロードしない
        "--sub-lang", "ja",       # 言語指定（日本語固定）
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

def _to_lrc_timestamp(raw_time: str) -> str | None:
    """VTT hh:mm:ss.mmm を LRC [mm:ss.xx] へ変換"""
    match = re.match(r"(\d+):(\d{2}):(\d{2})\.(\d{3})", raw_time)
    if not match:
        return None
    hh, mm, ss, mmm = match.groups()
    total_mm = int(hh) * 60 + int(mm)
    return f"[{total_mm:02}:{ss}.{mmm[:2]}]"


def _clean_text(text: str) -> str:
    # HTMLタグやスタイルを除去し、エンティティや不可視文字を掃除
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)  # zero-width 系
    text = re.sub(r"\s+", " ", text).strip()
    return text


def vtt_to_lrc(vtt_file, lrc_file):
    """VTT形式をLRC形式 [mm:ss.xx] に変換する"""
    with open(vtt_file, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.split("\n\n")
    lrc_lines = []
    seen_ts = set()  # 同一タイムスタンプは最初の1行だけ残す
    last_text = ""

    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue

        time_line = lines[0]
        if "-->" not in time_line:
            continue  # ヘッダやNOTEをスキップ

        start_raw = time_line.split("-->")[0].strip()
        lrc_time = _to_lrc_timestamp(start_raw)
        if not lrc_time:
            continue

        if lrc_time in seen_ts:
            continue

        text_body = _clean_text(" ".join(lines[1:]))
        if not text_body:
            continue

        if text_body == last_text:
            continue  # 連続同一行を抑制

        lrc_lines.append(f"{lrc_time}{text_body}")
        seen_ts.add(lrc_time)
        last_text = text_body

    with open(lrc_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lrc_lines))
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