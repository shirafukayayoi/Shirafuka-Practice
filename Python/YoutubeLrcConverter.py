import ctypes
import html
import glob
import os
import re
import subprocess
import time
import uuid


def download_vtt(video_url, ytdlp_path, output_name="subtitle"):
    """yt-dlpを使って字幕(VTT)をダウンロードする"""
    command = [
        ytdlp_path,
        "--write-subs",           # 字幕を書き込む
        "--skip-download",        # 動画本体はダウンロードしない
        "--sub-lang", "ja",       # 言語指定（日本語固定）
        "--sub-format", "vtt",    # 取得形式を明示
        "--output", output_name,
        video_url
    ]
    
    print(f"字幕を取得中...: {video_url}")
    subprocess.run(command, check=True)
    
    # yt-dlpは output_name.ja.vtt / output_name.ja-orig.vtt のような名前で保存することがある
    # 古い同名ファイルを拾わないよう、更新日時が最も新しいものを採用する
    candidates = [path for path in glob.glob(f"{output_name}*.vtt") if os.path.exists(path)]
    if candidates:
        return max(candidates, key=os.path.getmtime)
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


def copy_to_clipboard(text: str):
    """生成したLRCをクリップボードへコピーする"""
    GMEM_MOVEABLE = 0x0002
    CF_UNICODETEXT = 13

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_int
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = ctypes.c_int
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.c_int

    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_int
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.restype = ctypes.c_void_p

    data = text.replace("\n", "\r\n")
    buffer = ctypes.create_unicode_buffer(data)
    size = ctypes.sizeof(buffer)

    for _ in range(5):
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
        if not handle:
            raise OSError("GlobalAlloc failed")

        locked = kernel32.GlobalLock(handle)
        if not locked:
            kernel32.GlobalFree(handle)
            raise OSError("GlobalLock failed")

        ctypes.memmove(locked, ctypes.addressof(buffer), size)
        kernel32.GlobalUnlock(handle)

        if user32.OpenClipboard(None):
            try:
                if not user32.EmptyClipboard():
                    raise OSError("EmptyClipboard failed")
                if not user32.SetClipboardData(CF_UNICODETEXT, handle):
                    raise OSError("SetClipboardData failed")
                handle = None
                return
            finally:
                user32.CloseClipboard()

        kernel32.GlobalFree(handle)
        time.sleep(0.1)

    raise OSError("クリップボードを開けませんでした")


def vtt_to_lrc(vtt_file):
    """VTT形式をLRC形式 [mm:ss.xx] の文字列へ変換する"""
    with open(vtt_file, "r", encoding="utf-8-sig") as f:
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

    return "\n".join(lrc_lines)

def main():
    # 設定
    # yt-dlpのパスを指定してください (例: "C:/tools/yt-dlp.exe" や "/usr/local/bin/yt-dlp")
    default_ytdlp = "yt-dlp" 
    
    url = input("YouTubeのURLを入力してください: ")
    path = input(f"yt-dlpのパスを入力してください (空欄で '{default_ytdlp}'): ") or default_ytdlp
    copy_mode = input("クリップボードにもコピーしますか？ (y/N): ").strip().lower() == "y"
    
    output_base = f"lyrics_output_{uuid.uuid4().hex}"
    vtt_path = download_vtt(url, path, output_base)
    
    if vtt_path:
        lrc_text = vtt_to_lrc(vtt_path)
        try:
            if copy_mode:
                copy_to_clipboard(lrc_text)
                print("クリップボードにコピーしました。")
            else:
                lrc_path = "lyrics_output.lrc"
                with open(lrc_path, "w", encoding="utf-8") as f:
                    f.write(lrc_text)
                print(f"保存完了: {lrc_path}")
        finally:
            if os.path.exists(vtt_path):
                os.remove(vtt_path)
    else:
        print("字幕の取得に失敗しました。字幕設定がオフの動画かもしれません。")

if __name__ == "__main__":
    main()
