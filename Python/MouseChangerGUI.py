import ctypes
import glob
import os
import shutil
import sys
import time
import winreg
from ctypes import wintypes
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading


class MouseCursorChanger:
    def __init__(self):
        # Windowsのカーソル設定で使用されるレジストリキー
        self.cursor_registry_path = r"Control Panel\Cursors"
        self.cursor_schemes_path = r"Control Panel\Cursors\Schemes"

        # カーソルの種類とレジストリでの名前のマッピング
        self.cursor_types = {
            "Arrow": "Arrow",  # 通常の選択
            "Help": "Help",  # ヘルプ選択
            "AppStarting": "AppStarting",  # バックグラウンドで作業中
            "Wait": "Wait",  # 待機中
            "Crosshair": "Crosshair",  # 精密選択
            "IBeam": "IBeam",  # テキスト選択
            "NWPen": "NWPen",  # 手書き
            "No": "No",  # 利用不可
            "SizeNS": "SizeNS",  # 垂直方向のサイズ変更
            "SizeWE": "SizeWE",  # 水平方向のサイズ変更
            "SizeNWSE": "SizeNWSE",  # 対角線のサイズ変更（左上-右下）
            "SizeNESW": "SizeNESW",  # 対角線のサイズ変更（右上-左下）
            "SizeAll": "SizeAll",  # 移動
            "UpArrow": "UpArrow",  # 代替選択
            "Hand": "Hand",  # リンク選択
        }

        # システムカーソルフォルダー
        self.system_cursors_dir = os.path.join(os.environ["WINDIR"], "Cursors")

    def find_cursor_files(self, directory):
        """指定されたディレクトリ内のカーソルファイルを検索"""
        cursor_files = {}

        # .aniファイルと.curファイルを検索
        for ext in ["*.ani", "*.cur"]:
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
            elif (
                "テキスト" in filename or "text" in lower_name or "ibeam" in lower_name
            ):
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

    def copy_cursors_to_system(self, cursor_mapping, scheme_name, target_dir=None):
        """カーソルファイルを専用ディレクトリにコピー"""
        if target_dir is None:
            # スキーム専用のディレクトリを作成
            target_dir = os.path.join(self.system_cursors_dir, f"Custom_{scheme_name}")

        copied_files = {}

        try:
            # ターゲットディレクトリが存在しない場合は作成
            os.makedirs(target_dir, exist_ok=True)

            for cursor_type, source_path in cursor_mapping.items():
                # ファイル名を生成（例：custom_arrow.ani）
                ext = os.path.splitext(source_path)[1]
                target_filename = f"{scheme_name.lower()}_{cursor_type.lower()}{ext}"
                target_path = os.path.join(target_dir, target_filename)

                # ファイルをコピー
                shutil.copy2(source_path, target_path)
                copied_files[cursor_type] = target_path

        except PermissionError:
            raise PermissionError("システムディレクトリへの書き込み権限がありません。管理者権限で実行してください。")
        except Exception as e:
            raise Exception(f"コピー中にエラーが発生しました: {e}")

        return copied_files

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
            ctypes.windll.user32.SendMessageW(
                HWND_BROADCAST, WM_SETTINGCHANGE, SPI_SETCURSORS, 0
            )

            return True

        except Exception as e:
            raise Exception(f"カーソル適用中にエラーが発生しました: {e}")

    def get_current_cursor_scheme(self):
        """現在のカーソル設定を取得してスキーム文字列を作成"""
        current_cursors = {}
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self.cursor_registry_path
            ) as key:
                for cursor_type in self.cursor_types:
                    try:
                        value, _ = winreg.QueryValueEx(key, cursor_type)
                        current_cursors[cursor_type] = value if value else ""
                    except FileNotFoundError:
                        current_cursors[cursor_type] = ""

        except Exception as e:
            raise Exception(f"現在のカーソル設定取得中にエラーが発生しました: {e}")

        # スキーム文字列を作成（Windowsの形式に合わせる）
        scheme_values = []
        for cursor_type in self.cursor_types.keys():
            scheme_values.append(current_cursors.get(cursor_type, ""))

        return ",".join(scheme_values)

    def create_cursor_scheme(self, scheme_name, cursor_mapping):
        """新しいカーソルスキームを作成"""
        try:
            # 現在のカーソル設定を取得
            current_scheme = self.get_current_cursor_scheme()

            # 新しいスキーム用のカーソル設定を作成
            new_scheme_cursors = {}

            # まず現在の設定をベースにする
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self.cursor_registry_path
            ) as key:
                for cursor_type in self.cursor_types:
                    try:
                        value, _ = winreg.QueryValueEx(key, cursor_type)
                        new_scheme_cursors[cursor_type] = value if value else ""
                    except FileNotFoundError:
                        new_scheme_cursors[cursor_type] = ""

            # 新しいカーソルファイルで上書き
            for cursor_type, file_path in cursor_mapping.items():
                if cursor_type in self.cursor_types:
                    new_scheme_cursors[cursor_type] = file_path

            # スキーム文字列を作成
            scheme_values = []
            for cursor_type in self.cursor_types.keys():
                scheme_values.append(new_scheme_cursors.get(cursor_type, ""))

            scheme_string = ",".join(scheme_values)

            # スキームをレジストリに登録
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, self.cursor_schemes_path
            ) as schemes_key:
                winreg.SetValueEx(
                    schemes_key, scheme_name, 0, winreg.REG_SZ, scheme_string
                )

            return True

        except Exception as e:
            raise Exception(f"スキーム作成中にエラーが発生しました: {e}")

    def apply_cursor_scheme(self, scheme_name):
        """指定したスキームを適用"""
        try:
            # スキームを取得
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self.cursor_schemes_path
            ) as schemes_key:
                scheme_string, _ = winreg.QueryValueEx(schemes_key, scheme_name)

            # スキーム文字列をパース
            cursor_paths = scheme_string.split(",")
            if len(cursor_paths) != len(self.cursor_types):
                raise ValueError("スキームデータが無効です。")

            # カーソル設定を更新
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.cursor_registry_path,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                for i, cursor_type in enumerate(self.cursor_types.keys()):
                    if i < len(cursor_paths):
                        reg_name = self.cursor_types[cursor_type]
                        winreg.SetValueEx(
                            key, reg_name, 0, winreg.REG_EXPAND_SZ, cursor_paths[i]
                        )

            # 変更を適用
            self.apply_cursor_changes()
            return True

        except FileNotFoundError:
            raise FileNotFoundError(f"スキーム '{scheme_name}' が見つかりません。")
        except Exception as e:
            raise Exception(f"スキーム適用中にエラーが発生しました: {e}")

    def list_cursor_schemes(self):
        """利用可能なカーソルスキームを一覧表示"""
        try:
            schemes = []
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self.cursor_schemes_path
            ) as schemes_key:
                i = 0
                while True:
                    try:
                        scheme_name = winreg.EnumValue(schemes_key, i)[0]
                        schemes.append(scheme_name)
                        i += 1
                    except OSError:
                        break

            return schemes

        except FileNotFoundError:
            return []
        except Exception as e:
            raise Exception(f"スキーム一覧取得中にエラーが発生しました: {e}")

    def reset_to_default(self):
        """カーソルをデフォルトに戻す"""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.cursor_registry_path,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                # 各カーソルタイプを空文字列に設定（デフォルトに戻す）
                for cursor_type in self.cursor_types.keys():
                    winreg.SetValueEx(key, cursor_type, 0, winreg.REG_EXPAND_SZ, "")

            # 変更を適用
            self.apply_cursor_changes()
            return True

        except Exception as e:
            raise Exception(f"デフォルト復元中にエラーが発生しました: {e}")

    def change_cursors(self, directory, scheme_name=None):
        """メイン関数：指定ディレクトリのカーソルをスキームとして登録"""
        # ディレクトリの存在確認
        if not os.path.exists(directory):
            raise FileNotFoundError(f"ディレクトリが見つかりません: {directory}")

        # スキーム名が指定されていない場合は自動生成
        if scheme_name is None:
            dir_name = os.path.basename(directory.rstrip(os.sep))
            scheme_name = f"Custom_{dir_name}_{int(time.time())}"

        # カーソルファイルを検索
        cursor_files = self.find_cursor_files(directory)
        if not cursor_files:
            raise ValueError("カーソルファイル(.ani/.cur)が見つかりませんでした。")

        # カーソルタイプを分析
        cursor_mapping = self.analyze_cursor_files(cursor_files)
        if not cursor_mapping:
            raise ValueError("適用可能なカーソルファイルが見つかりませんでした。")

        # カーソルファイルをコピー
        copied_files = self.copy_cursors_to_system(cursor_mapping, scheme_name)

        # カーソルスキームを作成
        self.create_cursor_scheme(scheme_name, copied_files)

        return scheme_name, cursor_mapping


class MouseCursorChangerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("マウスカーソル変更ツール - GUI版")
        self.root.geometry("800x600")
        self.root.configure(bg="#f0f0f0")
        
        # カーソル変更器のインスタンスを作成
        self.cursor_changer = MouseCursorChanger()
        
        # スタイルを設定
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # カラーテーマを設定
        self.style.configure('Title.TLabel', font=('Arial', 16, 'bold'), background="#f0f0f0")
        self.style.configure('Heading.TLabel', font=('Arial', 12, 'bold'), background="#f0f0f0")
        
        self.create_widgets()
        
    def create_widgets(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # タイトル
        title_label = ttk.Label(main_frame, text="マウスカーソル変更ツール", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 現在のフォルダー情報フレーム
        current_folder_frame = ttk.LabelFrame(main_frame, text="現在のフォルダー", padding="10")
        current_folder_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.current_folder_var = tk.StringVar(value=os.getcwd())
        current_folder_label = ttk.Label(current_folder_frame, textvariable=self.current_folder_var, 
                                       font=('Arial', 9), foreground='blue')
        current_folder_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        use_current_btn = ttk.Button(current_folder_frame, text="現在のフォルダーを使用", 
                                   command=self.use_current_folder)
        use_current_btn.grid(row=0, column=1)
        
        # フォルダー選択フレーム
        folder_frame = ttk.LabelFrame(main_frame, text="カーソルフォルダー選択", padding="10")
        folder_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.folder_path = tk.StringVar()
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_path, width=60)
        folder_entry.grid(row=0, column=0, padx=(0, 10))
        
        browse_btn = ttk.Button(folder_frame, text="フォルダーを選択", command=self.browse_folder)
        browse_btn.grid(row=0, column=1)
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(0, 10))
        
        scan_btn = ttk.Button(button_frame, text="フォルダーをスキャン", command=self.scan_folder)
        scan_btn.grid(row=0, column=0, padx=(0, 10))
        
        change_btn = ttk.Button(button_frame, text="カーソルを変更", command=self.change_cursor)
        change_btn.grid(row=0, column=1, padx=(0, 10))
        
        reset_btn = ttk.Button(button_frame, text="デフォルトに戻す", command=self.reset_cursor)
        reset_btn.grid(row=0, column=2)
        
        # 検出されたファイル一覧
        files_frame = ttk.LabelFrame(main_frame, text="検出されたカーソルファイル", padding="10")
        files_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ツリービューを作成
        self.files_tree = ttk.Treeview(files_frame, columns=("Type", "File"), show="tree headings", height=8)
        self.files_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ヘッダーを設定
        self.files_tree.heading("#0", text="カーソルタイプ")
        self.files_tree.heading("Type", text="ファイルタイプ")
        self.files_tree.heading("File", text="ファイル名")
        
        # スクロールバーを追加
        scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.files_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.files_tree.configure(yscrollcommand=scrollbar.set)
        
        # ログエリア
        log_frame = ttk.LabelFrame(main_frame, text="ログ", padding="10")
        log_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, width=70)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ログクリアボタン
        clear_log_btn = ttk.Button(log_frame, text="ログクリア", command=self.clear_log)
        clear_log_btn.grid(row=1, column=0, pady=(5, 0), sticky=tk.W)
        
        # グリッドの重みを設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        main_frame.rowconfigure(5, weight=1)
        current_folder_frame.columnconfigure(0, weight=1)
        folder_frame.columnconfigure(0, weight=1)
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

    def use_current_folder(self):
        """現在のフォルダーをカーソルフォルダーとして設定"""
        current_folder = os.getcwd()
        self.folder_path.set(current_folder)
        self.log(f"現在のフォルダーを設定: {current_folder}")
        # 自動的にスキャンを実行
        self.scan_folder()

    def log(self, message):
        """ログメッセージを表示"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_log(self):
        """ログをクリア"""
        self.log_text.delete(1.0, tk.END)

    def browse_folder(self):
        """フォルダー選択ダイアログを開く"""
        folder_selected = filedialog.askdirectory(title="カーソルファイルがあるフォルダーを選択")
        if folder_selected:
            self.folder_path.set(folder_selected)
            self.log(f"フォルダーを選択: {folder_selected}")

    def scan_folder(self):
        """フォルダーをスキャンしてカーソルファイルを検出"""
        folder = self.folder_path.get()
        if not folder:
            messagebox.showerror("エラー", "フォルダーを選択してください。")
            return
        
        try:
            # ツリービューをクリア
            for item in self.files_tree.get_children():
                self.files_tree.delete(item)
            
            # カーソルファイルを検索
            cursor_files = self.cursor_changer.find_cursor_files(folder)
            if not cursor_files:
                self.log("カーソルファイルが見つかりませんでした。")
                return
            
            self.log(f"カーソルファイルを {len(cursor_files)} 個発見しました。")
            
            # ファイルを分析
            cursor_mapping = self.cursor_changer.analyze_cursor_files(cursor_files)
            
            # 結果をツリービューに表示
            for cursor_type, filepath in cursor_mapping.items():
                filename = os.path.basename(filepath)
                ext = os.path.splitext(filename)[1]
                self.files_tree.insert("", tk.END, text=cursor_type, values=(ext, filename))
            
            # 未分類のファイルも表示
            mapped_files = set(cursor_mapping.values())
            for filename, filepath in cursor_files.items():
                if filepath not in mapped_files:
                    ext = os.path.splitext(filename)[1]
                    self.files_tree.insert("", tk.END, text="未分類", values=(ext, filename))
            
            self.log("フォルダーのスキャンが完了しました。")
            
        except Exception as e:
            self.log(f"エラー: {str(e)}")
            messagebox.showerror("エラー", f"スキャン中にエラーが発生しました:\n{str(e)}")

    def change_cursor(self):
        """カーソルを変更"""
        folder = self.folder_path.get()
        
        if not folder:
            messagebox.showerror("エラー", "フォルダーを選択してください。")
            return
        
        try:
            # バックグラウンドで実行
            def change_task():
                try:
                    self.log("カーソル変更を開始します...")
                    created_scheme_name, cursor_mapping = self.cursor_changer.change_cursors(folder)
                    
                    self.log(f"スキーム '{created_scheme_name}' を作成しました。")
                    self.log(f"マッピングされたカーソル: {len(cursor_mapping)} 個")
                    
                    self.log("スキームを適用中...")
                    self.cursor_changer.apply_cursor_scheme(created_scheme_name)
                    self.log(f"スキーム '{created_scheme_name}' を適用しました。")
                    
                    # UIスレッドで完了メッセージを表示
                    self.root.after(0, lambda: messagebox.showinfo("完了", 
                        f"カーソルテーマ '{created_scheme_name}' を適用しました。\n\n"
                        "変更が反映されない場合は、一度ログオフ/ログインするか、\n"
                        "コントロールパネル→マウス→ポインタータブを開いてください。"))
                    
                except Exception as e:
                    self.log(f"エラー: {str(e)}")
                    self.root.after(0, lambda: messagebox.showerror("エラー", f"カーソル変更中にエラーが発生しました:\n{str(e)}"))
            
            # バックグラウンドスレッドで実行
            thread = threading.Thread(target=change_task, daemon=True)
            thread.start()
            
        except Exception as e:
            self.log(f"エラー: {str(e)}")
            messagebox.showerror("エラー", f"カーソル変更中にエラーが発生しました:\n{str(e)}")

    def reset_cursor(self):
        """カーソルをデフォルトに戻す"""
        result = messagebox.askyesno("確認", "カーソルをデフォルトに戻しますか？")
        if not result:
            return
            
        try:
            def reset_task():
                try:
                    self.log("カーソルをデフォルトに戻しています...")
                    self.cursor_changer.reset_to_default()
                    self.log("カーソルをデフォルトに戻しました。")
                    
                    self.root.after(0, lambda: messagebox.showinfo("完了", 
                        "カーソルをデフォルトに戻しました。\n\n"
                        "変更が反映されない場合は、一度ログオフ/ログインするか、\n"
                        "コントロールパネル→マウス→ポインターを開いてください。"))
                    
                except Exception as e:
                    self.log(f"エラー: {str(e)}")
                    self.root.after(0, lambda: messagebox.showerror("エラー", f"デフォルト復元中にエラーが発生しました:\n{str(e)}"))
            
            # バックグラウンドスレッドで実行
            thread = threading.Thread(target=reset_task, daemon=True)
            thread.start()
            
        except Exception as e:
            self.log(f"エラー: {str(e)}")
            messagebox.showerror("エラー", f"デフォルト復元中にエラーが発生しました:\n{str(e)}")


def main():
    # exe版の場合は常にGUI版を起動
    if getattr(sys, 'frozen', False):
        # PyInstallerでexe化されている場合
        root = tk.Tk()
        app = MouseCursorChangerGUI(root)
        root.mainloop()
        return
    
    if len(sys.argv) >= 2 and sys.argv[1] == "--gui":
        # GUI版を起動
        root = tk.Tk()
        app = MouseCursorChangerGUI(root)
        root.mainloop()
        return
    
    if len(sys.argv) < 2:
        # コンソールがない場合（stdin使用不可）はGUIモードにフォールバック
        try:
            # stdin が利用可能かテスト
            sys.stdin.read(0)
            print("=== マウスカーソル変更ツール ===")
            print("引数なしで実行されました。GUIモードを開始します。")
            print("GUI版を起動しています...")
            root = tk.Tk()
            app = MouseCursorChangerGUI(root)
            root.mainloop()
        except (OSError, RuntimeError):
            # stdinが利用できない場合はGUIモードで起動
            root = tk.Tk()
            app = MouseCursorChangerGUI(root)
            root.mainloop()
        return

    # コマンドライン引数処理
    directory = sys.argv[1]
    changer = MouseCursorChanger()

    try:
        # カーソルを変更
        scheme_name, cursor_mapping = changer.change_cursors(directory)
        print(f"\n✅ カーソルスキーム '{scheme_name}' が正常に作成されました！")
        print(f"マッピングされたカーソル: {len(cursor_mapping)} 個")
        
        print("\n📋 使用方法:")
        print("1. Windows設定 → デバイス → マウス → その他のマウス オプション")
        print("2. 「ポインター」タブを選択")
        print(f"3. 配色で '{scheme_name}' を選択")
        print("4. 「OK」をクリックして適用")

        # GUIモードで確認
        root = tk.Tk()
        result = messagebox.askyesno("確認", f"今すぐ '{scheme_name}' スキームを適用しますか？")
        root.destroy()
        
        if result:
            changer.apply_cursor_scheme(scheme_name)
            print("✅ スキームが適用されました！")

        print("\n💡 元に戻したい場合は、Windows設定から「マウス」→「その他のマウス オプション」→「ポインター」タブで変更できます。")
        
    except Exception as e:
        print(f"\n❌ カーソルの変更に失敗しました: {e}")


if __name__ == "__main__":
    main()
