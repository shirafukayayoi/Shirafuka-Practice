import os
import shutil


def copy_savedata(src_dir):
    target_folders = ["savedata", "UserData", "save", "Save"]

    try:
        folders = [f.name for f in os.scandir(src_dir) if f.is_dir()]
    except Exception as e:
        print(f"An error occurred: {e}")
        return

    for folder in folders:
        for target in target_folders:
            # 通常のターゲットフォルダをチェック
            target_path = os.path.join(src_dir, folder, target)
            if os.path.exists(target_path) and os.path.isdir(target_path):
                print(f"'{target}' folder found in: {target_path}")

            # www/save フォルダをチェック
            www_save_path = os.path.join(src_dir, folder, "www")
            if os.path.exists(www_save_path) and os.path.isdir(www_save_path):
                print(f"'www/save' folder found in: {www_save_path}")

    try:
        os.makedirs("savedata_folder", exist_ok=True)
        for folder in folders:
            for target in target_folders:
                src_target_path = os.path.join(src_dir, folder, target)
                if os.path.exists(src_target_path) and os.path.isdir(src_target_path):
                    dest_folder_path = os.path.join("savedata_folder", folder, target)
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
                    www_save_path = os.path.join(src_dir, folder, "www", "save")
                    if os.path.exists(www_save_path) and os.path.isdir(www_save_path):
                        dest_folder_path = os.path.join(
                            "savedata_folder", folder, "www", "save"
                        )
                        os.makedirs(dest_folder_path, exist_ok=True)
                        for item in os.listdir(www_save_path):
                            src_item_path = os.path.join(www_save_path, item)
                            dest_item_path = os.path.join(dest_folder_path, item)
                            if os.path.isdir(src_item_path):
                                shutil.copytree(
                                    src_item_path, dest_item_path, dirs_exist_ok=True
                                )
                            else:
                                shutil.copy2(src_item_path, dest_item_path)
    except Exception as e:
        print(f"An error occurred while copying: {e}")


if __name__ == "__main__":
    src_dir = input("コピー元のディレクトリパスを入力してください: ")
    copy_savedata(src_dir)
