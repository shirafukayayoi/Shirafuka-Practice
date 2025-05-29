import os
import shutil
import winreg
import ctypes
from ctypes import wintypes
import glob
from pathlib import Path
import sys

class MouseCursorChanger:
    def __init__(self):
        # Windowsのカーソル設定で使用されるレジストリキー
        self.cursor_registry_path = r"Control Panel\Cursors"
        
        # カーソルの種類とレジストリでの名前のマッピング
        self.cursor_types = {
            "Arrow": "Arrow",           # 通常の選択
            "Help": "Help",             # ヘルプ選択
            "AppStarting": "AppStarting", # バックグラウンドで作業中
            "Wait": "Wait",             # 待機中
            "Crosshair": "Crosshair",   # 精密選択
            "IBeam": "IBeam",           # テキスト選択
            "NWPen": "NWPen",           # 手書き
            "No": "No",                 # 利用不可
            "SizeNS": "SizeNS",         # 垂直方向のサイズ変更
            "SizeWE": "SizeWE",         # 水平方向のサイズ変更
            "SizeNWSE": "SizeNWSE",     # 対角線のサイズ変更（左上-右下）
            "SizeNESW": "SizeNESW",     # 対角線のサイズ変更（右上-左下）
            "SizeAll": "SizeAll",       # 移動
            "UpArrow": "UpArrow",       # 代替選択
            "Hand": "Hand"              # リンク選択
        }
        
        # システムカーソルフォルダー
        self.system_cursors_dir = os.path.join(os.environ['WINDIR'], 'Cursors')
        
    def find_cursor_files(self, directory):
        """指定されたディレクトリ内のカーソルファイルを検索"""
        cursor_files = {}
        
        # .aniファイルと.curファイルを検索
        for ext in ['*.ani', '*.cur']:
            files = glob.glob(os.path.join(directory, ext))
            for file in files:
                filename = os.path.basename(file)
                cursor_files[filename] = file
                
        return cursor_files
    
    def analyze_cursor_files(self, cursor_files):
        """カーソルファイルを分析してタイプを推定"""
        cursor_mapping = {}
        
        for filename, filepath in cursor_files.items():
            lower_name = filename.lower()
            
            # ファイル名からカーソルタイプを推定
            if "移動" in filename or "move" in lower_name or "sizeall" in lower_name:
                cursor_mapping["SizeAll"] = filepath
            elif "テキスト" in filename or "text" in lower_name or "ibeam" in lower_name:
                cursor_mapping["IBeam"] = filepath
            elif "待機" in filename or "wait" in lower_name or "busy" in lower_name:
                cursor_mapping["Wait"] = filepath
            elif "選択" in filename or "arrow" in lower_name or "normal" in lower_name:
                cursor_mapping["Arrow"] = filepath
            elif "hand" in lower_name or "リンク" in filename:
                cursor_mapping["Hand"] = filepath
            elif "help" in lower_name or "ヘルプ" in filename:
                cursor_mapping["Help"] = filepath
            elif "no" in lower_name or "禁止" in filename:
                cursor_mapping["No"] = filepath
            elif "cross" in lower_name or "十字" in filename:
                cursor_mapping["Crosshair"] = filepath
            elif "sizens" in lower_name or "垂直" in filename:
                cursor_mapping["SizeNS"] = filepath
            elif "sizewe" in lower_name or "水平" in filename:
                cursor_mapping["SizeWE"] = filepath
            elif "sizenwse" in lower_name:
                cursor_mapping["SizeNWSE"] = filepath
            elif "sizenesw" in lower_name:
                cursor_mapping["SizeNESW"] = filepath
            elif "appstarting" in lower_name or "作業中" in filename:
                cursor_mapping["AppStarting"] = filepath
            elif "uparrow" in lower_name:
                cursor_mapping["UpArrow"] = filepath
            elif "pen" in lower_name or "ペン" in filename:
                cursor_mapping["NWPen"] = filepath
                
        return cursor_mapping
    
    def copy_cursors_to_system(self, cursor_mapping, target_dir=None):
        """カーソルファイルをシステムディレクトリまたは指定ディレクトリにコピー"""
        if target_dir is None:
            target_dir = self.system_cursors_dir
        
        copied_files = {}
        
        try:
            # ターゲットディレクトリが存在しない場合は作成
            os.makedirs(target_dir, exist_ok=True)
            
            for cursor_type, source_path in cursor_mapping.items():
                # ファイル名を生成（例：custom_arrow.ani）
                ext = os.path.splitext(source_path)[1]
                target_filename = f"custom_{cursor_type.lower()}{ext}"
                target_path = os.path.join(target_dir, target_filename)
                
                # ファイルをコピー
                shutil.copy2(source_path, target_path)
                copied_files[cursor_type] = target_path
                print(f"コピー完了: {cursor_type} -> {target_path}")
                
        except PermissionError:
            print("エラー: システムディレクトリへの書き込み権限がありません。")
            print("管理者権限で実行するか、別のディレクトリを指定してください。")
            return None
        except Exception as e:
            print(f"コピー中にエラーが発生しました: {e}")
            return None
            
        return copied_files
    
    def update_registry(self, cursor_mapping):
        """レジストリを更新してカーソルを変更"""
        try:
            # レジストリキーを開く
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.cursor_registry_path, 0, winreg.KEY_SET_VALUE) as key:
                for cursor_type, file_path in cursor_mapping.items():
                    if cursor_type in self.cursor_types:
                        reg_name = self.cursor_types[cursor_type]
                        winreg.SetValueEx(key, reg_name, 0, winreg.REG_EXPAND_SZ, file_path)
                        print(f"レジストリ更新: {reg_name} -> {file_path}")
                        
        except Exception as e:
            print(f"レジストリ更新中にエラーが発生しました: {e}")
            return False
            
        return True
    
    def apply_cursor_changes(self):
        """システムに変更を通知してカーソルを適用"""
        try:
            # システムパラメータを更新
            SPI_SETCURSORS = 0x0057
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            
            # カーソル変更を通知
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
            
            # 設定変更を全ウィンドウに通知
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SETTINGCHANGE, SPI_SETCURSORS, 0)
            
            print("カーソルの変更が適用されました。")
            return True
            
        except Exception as e:
            print(f"カーソル適用中にエラーが発生しました: {e}")
            return False
    
    def backup_current_cursors(self):
        """現在のカーソル設定をバックアップ"""
        backup = {}
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.cursor_registry_path) as key:
                for cursor_type in self.cursor_types:
                    try:
                        value, _ = winreg.QueryValueEx(key, cursor_type)
                        backup[cursor_type] = value
                    except FileNotFoundError:
                        pass  # そのカーソルタイプが設定されていない
                        
        except Exception as e:
            print(f"バックアップ中にエラーが発生しました: {e}")
            
        return backup
    
    def restore_cursors(self, backup_settings):
        """バックアップからカーソルを復元"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.cursor_registry_path, 0, winreg.KEY_SET_VALUE) as key:
                for cursor_type, file_path in backup_settings.items():
                    winreg.SetValueEx(key, cursor_type, 0, winreg.REG_EXPAND_SZ, file_path)
                    
            self.apply_cursor_changes()
            print("カーソルが復元されました。")
            return True
            
        except Exception as e:
            print(f"復元中にエラーが発生しました: {e}")
            return False
    
    def change_cursors(self, directory, backup=True):
        """メイン関数：指定ディレクトリのカーソルを適用"""
        print(f"カーソルファイルを検索中: {directory}")
        
        # ディレクトリの存在確認
        if not os.path.exists(directory):
            print(f"エラー: ディレクトリが見つかりません: {directory}")
            return False
        
        # カーソルファイルを検索
        cursor_files = self.find_cursor_files(directory)
        if not cursor_files:
            print("カーソルファイル(.ani/.cur)が見つかりませんでした。")
            return False
        
        print(f"発見されたカーソルファイル: {len(cursor_files)}個")
        for filename in cursor_files:
            print(f"  - {filename}")
        
        # カーソルタイプを分析
        cursor_mapping = self.analyze_cursor_files(cursor_files)
        if not cursor_mapping:
            print("適用可能なカーソルファイルが見つかりませんでした。")
            return False
        
        print("\nカーソルマッピング:")
        for cursor_type, filepath in cursor_mapping.items():
            print(f"  {cursor_type}: {os.path.basename(filepath)}")
        
        # 現在の設定をバックアップ
        if backup:
            backup_settings = self.backup_current_cursors()
            print(f"\n現在のカーソル設定をバックアップしました。")
        
        # カーソルファイルをコピー
        print("\nカーソルファイルをコピー中...")
        copied_files = self.copy_cursors_to_system(cursor_mapping)
        if not copied_files:
            return False
        
        # レジストリを更新
        print("\nレジストリを更新中...")
        if not self.update_registry(copied_files):
            return False
        
        # 変更を適用
        print("\nカーソル変更を適用中...")
        if not self.apply_cursor_changes():
            return False
        
        print(f"\nカーソルの変更が完了しました！")
        
        if backup:
            # バックアップ情報を保存
            backup_file = os.path.join(directory, "cursor_backup.txt")
            try:
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write("# カーソルバックアップ情報\n")
                    for cursor_type, filepath in backup_settings.items():
                        f.write(f"{cursor_type}={filepath}\n")
                print(f"バックアップ情報を保存しました: {backup_file}")
            except Exception as e:
                print(f"バックアップファイルの保存に失敗しました: {e}")
        
        return True

def change_cursors_current_directory():
    """現在のディレクトリのカーソルファイルを適用"""
    current_dir = os.getcwd()
    changer = MouseCursorChanger()
    
    print("=== 現在のディレクトリでマウスカーソル変更 ===")
    print(f"現在のディレクトリ: {current_dir}")
    print()
    
    # カーソルを変更
    success = changer.change_cursors(current_dir)
    
    if success:
        print("\n✅ カーソルの変更が正常に完了しました。")
        print("💡 元に戻したい場合は、Windows設定から「マウス」→「その他のマウス オプション」→「ポインター」タブで変更できます。")
    else:
        print("\n❌ カーソルの変更に失敗しました。")
    
    return success

def interactive_mode():
    """対話型モードでカーソルを変更"""
    changer = MouseCursorChanger()
    
    print("=== インタラクティブマウスカーソル変更ツール ===")
    print()
    
    while True:
        print("オプションを選択してください：")
        print("1. 指定フォルダーのカーソルを適用")
        print("2. 現在のフォルダーのカーソルを適用")
        print("3. カーソルファイルを検索して表示")
        print("4. 終了")
        
        choice = input("\n選択 (1-4): ").strip()
        
        if choice == "1":
            directory = input("カーソルファイルがあるフォルダーのパスを入力してください: ").strip()
            if directory:
                changer.change_cursors(directory)
        
        elif choice == "2":
            current_dir = os.getcwd()
            changer.change_cursors(current_dir)
        
        elif choice == "3":
            directory = input("検索するフォルダーのパスを入力してください (空白で現在のフォルダー): ").strip()
            if not directory:
                directory = os.getcwd()
            
            cursor_files = changer.find_cursor_files(directory)
            if cursor_files:
                print(f"\n{directory} で見つかったカーソルファイル:")
                for filename, filepath in cursor_files.items():
                    print(f"  - {filename} ({filepath})")
                
                cursor_mapping = changer.analyze_cursor_files(cursor_files)
                if cursor_mapping:
                    print("\n推定されたカーソルマッピング:")
                    for cursor_type, filepath in cursor_mapping.items():
                        print(f"  {cursor_type}: {os.path.basename(filepath)}")
            else:
                print(f"\n{directory} にカーソルファイルが見つかりませんでした。")
        
        elif choice == "4":
            print("ツールを終了します。")
            break
        
        else:
            print("無効な選択です。1-4の数字を入力してください。")
        
        print("\n" + "="*50 + "\n")

def main():
    if len(sys.argv) < 2:
        print("=== マウスカーソル変更ツール ===")
        print("引数なしで実行されました。対話型モードを開始します。")
        print()
        interactive_mode()
        return
    
    directory = sys.argv[1]
    changer = MouseCursorChanger()
    
    print("=== マウスカーソル変更ツール ===")
    print(f"対象ディレクトリ: {directory}")
    print()
    
    # カーソルを変更
    success = changer.change_cursors(directory)
    
    if success:
        print("\n✅ カーソルの変更が正常に完了しました。")
        print("💡 元に戻したい場合は、Windows設定から「マウス」→「その他のマウス オプション」→「ポインター」タブで変更できます。")
    else:
        print("\n❌ カーソルの変更に失敗しました。")

if __name__ == "__main__":
    main()