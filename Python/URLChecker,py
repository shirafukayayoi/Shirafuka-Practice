import queue
import socket
import threading
import time
import urllib.error
import urllib.request

WORKER = 4
BASE = input("Enter the base URL: ")
ADMIN_URL = "https://raw.githubusercontent.com/zaproxy/zap-extensions/main/addOns/svndigger/src/main/svndigger/context/admin.txt"

socket.setdefaulttimeout(3)


# admin.txtを取得して内容をリストとして返す関数
def fetch_admin_txt(url: str):
    try:
        response = urllib.request.urlopen(url)
        return response.read().decode("utf-8").splitlines()  # 各行をリストとして返す
    except Exception as e:
        print(f"Error fetching admin.txt: {e}")
        return []


collected = []
q = queue.Queue()


def collect() -> None:
    while True:
        path = q.get()
        try:
            response = urllib.request.urlopen(f"{BASE}/{path}")
        except urllib.error.HTTPError:
            continue
        if 200 <= response.status < 300:
            collected.append(response.url)


# admin.txtを取得してキューに追加
admin_paths = fetch_admin_txt(ADMIN_URL)
for path in admin_paths:
    q.put(path.strip())  # 各パスの前後の空白を削除して追加

# ワーカーを開始
for _ in range(WORKER):
    th = threading.Thread(target=collect)
    th.daemon = True
    th.start()

# キューの処理が終わるまで待機
while q.qsize() != 0:
    print(f"\rRemaining: {q.qsize()}\033[K", end="")
    time.sleep(1)

# 結果を表示
print("\rCollected:\033[K")
print(collected)
