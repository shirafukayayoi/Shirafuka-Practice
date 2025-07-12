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
            print(f"[Error] An error occurred: {e}")
            return None
        
        # セーブデータが存在するフォルダを特定
        folders_with_savedata = []
        
        for folder in folders:
            has_savedata = False
            
            # 通常のターゲットフォルダをチェック
            for target in self.target_folders:
                target_path = os.path.join(self.src_dir, folder, target)
                if os.path.exists(target_path) and os.path.isdir(target_path):
                    print(f"[Info] '{target}' folder found in: {target_path}")
                    has_savedata = True
            
            # www/save フォルダをチェック
            www_save_path = os.path.join(self.src_dir, folder, "www", "save")
            if os.path.exists(www_save_path) and os.path.isdir(www_save_path):
                print(f"[Info] 'www/save' folder found in: {www_save_path}")
                has_savedata = True
            
            if has_savedata:
                folders_with_savedata.append(folder)
        
        try:
            backup_folder = "G:\\マイドライブ\\バッグアップ\\ノベルゲーセーブデータ"
            
            # セーブデータがあるフォルダのみをバックアップ先から削除
            if os.path.exists(backup_folder):
                for folder in folders_with_savedata:
                    folder_backup_path = os.path.join(backup_folder, folder)
                    if os.path.exists(folder_backup_path) and os.path.isdir(folder_backup_path):
                        print(f"[Info] Removing existing backup folder: {folder_backup_path}")
                        shutil.rmtree(folder_backup_path)
            
            # バックアップフォルダを作成
            os.makedirs(backup_folder, exist_ok=True)
            print(f"[Info] Created folder: {backup_folder}")
            
            # セーブデータをコピー
            for folder in folders_with_savedata:
                # 通常のターゲットフォルダをコピー
                for target in self.target_folders:
                    src_target_path = os.path.join(self.src_dir, folder, target)
                    if os.path.exists(src_target_path) and os.path.isdir(src_target_path):
                        dest_folder_path = os.path.join(backup_folder, folder, target)
                        os.makedirs(dest_folder_path, exist_ok=True)
                        print(f"[Info] Copying {src_target_path} to {dest_folder_path}")
                        
                        for item in os.listdir(src_target_path):
                            src_item_path = os.path.join(src_target_path, item)
                            dest_item_path = os.path.join(dest_folder_path, item)
                            if os.path.isdir(src_item_path):
                                shutil.copytree(src_item_path, dest_item_path, dirs_exist_ok=True)
                            else:
                                shutil.copy2(src_item_path, dest_item_path)
                
                # www/save フォルダをコピー
                www_save_path = os.path.join(self.src_dir, folder, "www", "save")
                if os.path.exists(www_save_path) and os.path.isdir(www_save_path):
                    dest_folder_path = os.path.join(backup_folder, folder, "www", "save")
                    os.makedirs(dest_folder_path, exist_ok=True)
                    print(f"[Info] Copying {www_save_path} to {dest_folder_path}")
                    
                    for item in os.listdir(www_save_path):
                        src_item_path = os.path.join(www_save_path, item)
                        dest_item_path = os.path.join(dest_folder_path, item)
                        if os.path.isdir(src_item_path):
                            shutil.copytree(src_item_path, dest_item_path, dirs_exist_ok=True)
                        else:
                            shutil.copy2(src_item_path, dest_item_path)
            
            print(f"[Info] Backup completed successfully. {len(folders_with_savedata)} folders processed.")
            return backup_folder
            
        except Exception as e:
            print(f"[Error] An error occurred during backup: {e}")
            return None


if __name__ == "__main__":
    src_dir = input("Enter the source directory: ")
    copy = SavedataCopy(src_dir)
    copy.copy_savedata()
