import os
import shutil
import time

import psutil


# 既存のディスク一覧を取得
def get_existing_drives():
    return set(psutil.disk_partitions(all=False))


# 新しいUSBが接続されたかを確認する
def detect_usb_connection():
    initial_drives = get_existing_drives()
    while True:
        time.sleep(2)  # 2秒ごとに確認
        current_drives = get_existing_drives()

        # 新しいディスクが追加されたか確認
        if len(current_drives) > len(initial_drives):
            new_drive = list(current_drives - initial_drives)[0]
            print(f"新しいドライブが検出されました: {new_drive.device}")
            return new_drive.device


# ファイルをUSBにコピーする
def copy_file_to_usb(usb_path, source_file):
    destination = os.path.join(usb_path, os.path.basename(source_file))
    shutil.copy2(source_file, destination)
    print(f"ファイルが {usb_path} にコピーされました")


# メイン処理
if __name__ == "__main__":
    while True:
        source_file_path = input("コピーするファイルのパスを入力してください: ")
        source_file_path = source_file_path.strip('"')  # 余分な引用符を削除
        print("USBの接続を待機しています...")
        usb_drive = detect_usb_connection()

        # USBにファイルをコピー
        copy_file_to_usb(usb_drive, source_file_path)

        # 処理が終わったら再度ループ
        print("処理が完了しました。次のファイルをコピーする準備ができました。")
