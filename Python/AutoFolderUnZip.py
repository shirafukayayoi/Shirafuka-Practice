from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import zipfile
import time

class Watcher:      # フォルダの監視を行うものをわかりやすくするためにクラス化
    DIRECTORY_TO_WATCH = input("監視するフォルダのパスを入力してください：")

    def __init__(self):
        self.observer = Observer()  # Observerは監視を行うクラス

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=True)
        self.observer.start()
        print("監視中...")
        try:    # tryを使うことで監視。終了するまでループ
            while True:
                time.sleep(5)
        except:     # 例外が発生した場合は、監視を終了
            self.observer.stop()
            print("問題が発生したため、監視を終了します。")

        self.observer.join()    # 監視が終わるのを待つ

class Handler(FileSystemEventHandler):  # フォルダ内のファイルの変更を検知するため必要

    @staticmethod
    def on_created(event):
        if event.is_directory:  # フォルダーじゃない場合は何もしない
            return None

        elif event.src_path.endswith('.zip'):   # zipという単語が文字列の最後にある場合
            print(f"{event.src_path} ファイルが作成されました。")
            unzip_and_delete(event.src_path)    # 関数を呼び出す

def unzip_and_delete(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref: # rは読み込み専用、withを使うことで自動でファイルを閉じる、asの後に変数名
        unzip_path = os.path.splitext(zip_path)[0]  # 拡張子を取り除くことによって出力先を指定
        zip_ref.extractall(unzip_path)  # zipファイルを解凍
        print(f"{zip_path} を解凍しました。")
    os.remove(zip_path)     # zipファイルを削除
    print(f"{zip_path} を削除しました。")

# もし、このファイルが直接実行された場合は、Watcherクラスを実行
if __name__ == '__main__':
    w = Watcher()
    w.run()

# Watcherクラスで監視
# Handlerクラスでフォルダ内のファイルの変更を検知
# on_createdで作成されたファイルのフルパスを取得
# 取得したファイルがzipファイルかどうかを判定
# zipファイルの場合はunzip_and_delete関数を呼び出す