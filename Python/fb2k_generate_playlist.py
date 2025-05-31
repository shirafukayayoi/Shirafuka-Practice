import json
import subprocess
import sys


def fetch_video_info(yt_dlp_path, video_url):
    """個別動画のメタデータを取得"""
    cmd = [yt_dlp_path, "--no-warnings", "--skip-download", "-j", video_url]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"[ERROR] メタデータ取得失敗: {video_url}")
        return None
    return json.loads(proc.stdout)

def generate_playlist(yt_dlp_path, url, output_file):
    # まず flat-playlist で ID リストのみ取得
    cmd_list = [
        yt_dlp_path,
        "--no-warnings",
        "--flat-playlist",
        "--dump-single-json",
        "-J",
        url
    ]
    proc_list = subprocess.run(cmd_list, capture_output=True, text=True)
    if proc_list.returncode != 0:
        print("[Error] Error fetching playlist IDs:", proc_list.stderr.strip())
        return

    data = json.loads(proc_list.stdout)
    entries = data.get("entries", [])

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for idx, e in enumerate(entries, 1):
            # 動画ID or URL からフルURLを組み立て
            raw = e.get("url", "")
            if raw.startswith("http"):
                full_url = raw
            else:
                full_url = f"https://www.youtube.com/watch?v={raw}"
            print(f"[{idx}/{len(entries)}] URL: {full_url}")
            # タイトル取得せず、URLのみ出力
            f.write(f"fy+{full_url}\n")

if __name__ == "__main__":
    yt_dlp_path  = input("yt-dlp 実行ファイルのパス: ").strip()
    url          = input("YouTube のプレイリスト URL: ").strip()
    output_file  = "fb2k_youtube_playlist.m3u8"

    if not yt_dlp_path or not url or not output_file:
        print("[Error] すべての項目を正しく入力してください。")
        sys.exit(1)

    generate_playlist(yt_dlp_path, url, output_file)
    print(f"生成完了: {output_file}")