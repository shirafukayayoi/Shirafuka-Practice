# CTF_Docs

## よく使うコマンドLinux一覧

| command | 詳細                            |
| :------ | ------------------------------- |
| ls      | ディレクトリの中身を表示        |
| -l      | 詳細情報を表示                  |
| -a      | 隠しファイルも表示              |
| cd      | ディレクトリの移動              |
| cp      | ファイルのコピー                |
| mv      | ファイルの移動                  |
| rm      | ファイルの削除                  |
| cat     | ファイルの中身全体を表示        |
| less    | ファイルの内容を1ページずつ表示 |
| head    | ファイルの数行を表示            |
| tail    | ファイルの末行を表示            |

## ZIPファイルの解析方法

[John the Ripper](https://www.openwall.com/john/)を使う。  
使い方:

1. `cd`コマンドを使い、ディレクトリに入る。
1. ディレクトリにzipファイルを入れる。
1. ディレクトリの中で`zip2john.exe <zip名> ><zip名>.hash`と実行する
1. ハッシュが作られているため、それを使うために`john.exe --pot=<zip名>.pot --incremental=ASCII <zip名>.hash`とコマンドを打つ

これででてきたパスワードを打ち込んだら終わり！！!  
![image](/image/zip2john.png)

## Base64で暗号化されたデータから複合キーの取得

Base64でできたコードは、元のデータがあれば複合キーを取得することができる。  
以下Pythonコード：

```python
import base64

encoded_data = input("Base64でエンコードされた文字列を入力してください: ")

plain = input("元のデータを入力してください: ").encode()

decoded_data = base64.b64decode(encoded_data)

data = []

for i in range(len(decoded_data)):
    dec = decoded_data[i] ^ plain[i]
    dec_char = chr(dec)
    data.append(dec_char)

print("デコードされたデータ: " + "".join(data))
```

## APIとの通信からメールアドレスやパスワードを取得

1. `DebugMode`を開く
1. `Network`タブへ
1. `ALL`を選択
1. 一度適当にログイン
1. わんちゃんパスワードもでてくる（クライアント側で認証の場合）

## URLから隠されたURLを探す

`/admin`などのURLを探してみる。
以下Pythonコード:

```python
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

```
