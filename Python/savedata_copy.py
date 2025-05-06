import os
import shutil

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


class SavedataCopy:
    def __init__(self, src_dir):
        self.src_dir = src_dir
        self.target_folders = ["savedata", "UserData", "save", "Save"]

    def copy_savedata(self):
        try:
            folders = [f.name for f in os.scandir(self.src_dir) if f.is_dir()]
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        for folder in folders:
            for target in self.target_folders:
                # 通常のターゲットフォルダをチェック
                target_path = os.path.join(self.src_dir, folder, target)
                if os.path.exists(target_path) and os.path.isdir(target_path):
                    print(f"'{target}' folder found in: {target_path}")

                # www/save フォルダをチェック
                www_save_path = os.path.join(self.src_dir, folder, "www")
                if os.path.exists(www_save_path) and os.path.isdir(www_save_path):
                    print(f"'www/save' folder found in: {www_save_path}")
        try:
            backup_folder = "G:\\マイドライブ\\バッグアップ\\ノベルゲーセーブデータ"
            # 指定の組み合わせだけ削除
            if os.path.exists(backup_folder):
                for folder in folders:
                    for target in self.target_folders:
                        dest_folder_path = os.path.join(backup_folder, folder, target)
                        if os.path.exists(dest_folder_path) and os.path.isdir(dest_folder_path):
                            shutil.rmtree(dest_folder_path)
                # www/save も同様に削除
                for folder in folders:
                    www_save_path = os.path.join(backup_folder, folder, "www", "save")
                    if os.path.exists(www_save_path) and os.path.isdir(www_save_path):
                        shutil.rmtree(www_save_path)
            data_folder = os.makedirs(
                "G:\\マイドライブ\\バッグアップ\\ノベルゲーセーブデータ", exist_ok=True
            )
            print(
                f"Created folder: G:\\マイドライブ\\バッグアップ\\ノベルゲーセーブデータ"
            )
            for folder in folders:
                for target in self.target_folders:
                    src_target_path = os.path.join(self.src_dir, folder, target)
                    if os.path.exists(src_target_path) and os.path.isdir(
                        src_target_path
                    ):
                        dest_folder_path = os.path.join(
                            "G:\\マイドライブ\\バッグアップ\\ノベルゲーセーブデータ",
                            folder,
                            target,
                        )
                        os.makedirs(dest_folder_path, exist_ok=True)
                        for item in os.listdir(src_target_path):
                            src_item_path = os.path.join(src_target_path, item)
                            dest_item_path = os.path.join(dest_folder_path, item)
                            if os.path.isdir(src_item_path):
                                shutil.copytree(
                                    src_item_path, dest_item_path, dirs_exist_ok=True
                                )
                            else:
                                shutil.copy2(src_item_path, dest_item_path)
                    else:
                        www_save_path = os.path.join(
                            self.src_dir, folder, "www", "save"
                        )
                        if os.path.exists(www_save_path) and os.path.isdir(
                            www_save_path
                        ):
                            dest_folder_path = os.path.join(
                                "G:\\マイドライブ\\バッグアップ\\ノベルゲーセーブデータ",
                                folder,
                                "www",
                                "save",
                            )
                            os.makedirs(dest_folder_path, exist_ok=True)
                            for item in os.listdir(www_save_path):
                                src_item_path = os.path.join(www_save_path, item)
                                dest_item_path = os.path.join(dest_folder_path, item)
                                if os.path.isdir(src_item_path):
                                    shutil.copytree(
                                        src_item_path,
                                        dest_item_path,
                                        dirs_exist_ok=True,
                                    )
                                else:
                                    shutil.copy2(src_item_path, dest_item_path)
            return data_folder
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

        except Exception as e:
            print(f"An error occurred: {e}")
            return


if __name__ == "__main__":
    src_dir = input("Enter the source directory: ")
    copy = SavedataCopy(src_dir)
    copy.copy_savedata()
