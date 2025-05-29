import ctypes
import glob
import os
import shutil
import sys
import time
import winreg
from ctypes import wintypes
from pathlib import Path


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
                print(f"コピー完了: {cursor_type} -> {target_path}")

        except PermissionError:
            print("エラー: システムディレクトリへの書き込み権限がありません。")
            print("管理者権限で実行するか、別のディレクトリを指定してください。")
            return None
        except Exception as e:
            print(f"コピー中にエラーが発生しました: {e}")
            return None

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

            print("カーソルの変更が適用されました。")
            return True

        except Exception as e:
            print(f"カーソル適用中にエラーが発生しました: {e}")
            return False

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
            print(f"現在のカーソル設定取得中にエラーが発生しました: {e}")
            return None

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
            if current_scheme is None:
                print("現在のカーソル設定の取得に失敗しました。")
                return False

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
            try:
                with winreg.CreateKeyEx(
                    winreg.HKEY_CURRENT_USER, self.cursor_schemes_path
                ) as schemes_key:
                    winreg.SetValueEx(
                        schemes_key, scheme_name, 0, winreg.REG_SZ, scheme_string
                    )
                    print(f"カーソルスキーム '{scheme_name}' を登録しました。")

            except Exception as e:
                print(f"スキーム登録中にエラーが発生しました: {e}")
                return False

            return True

        except Exception as e:
            print(f"スキーム作成中にエラーが発生しました: {e}")
            return False

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
                print("スキームデータが無効です。")
                return False

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
                        print(f"カーソル更新: {reg_name} -> {cursor_paths[i]}")

            # 変更を適用
            self.apply_cursor_changes()
            print(f"カーソルスキーム '{scheme_name}' が適用されました。")
            return True

        except FileNotFoundError:
            print(f"スキーム '{scheme_name}' が見つかりません。")
            return False
        except Exception as e:
            print(f"スキーム適用中にエラーが発生しました: {e}")
            return False

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
            print("カーソルスキームが見つかりません。")
            return []
        except Exception as e:
            print(f"スキーム一覧取得中にエラーが発生しました: {e}")
            return []

    def change_cursors(self, directory, scheme_name=None):
        """メイン関数：指定ディレクトリのカーソルをスキームとして登録"""
        print(f"カーソルファイルを検索中: {directory}")

        # ディレクトリの存在確認
        if not os.path.exists(directory):
            print(f"エラー: ディレクトリが見つかりません: {directory}")
            return False

        # スキーム名が指定されていない場合は自動生成
        if scheme_name is None:
            dir_name = os.path.basename(directory.rstrip(os.sep))
            scheme_name = f"Custom_{dir_name}_{int(time.time())}"

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

        # カーソルファイルをコピー
        print(f"\nカーソルファイルをコピー中...")
        copied_files = self.copy_cursors_to_system(cursor_mapping, scheme_name)
        if not copied_files:
            return False

        # カーソルスキームを作成
        print(f"\nカーソルスキーム '{scheme_name}' を作成中...")
        if not self.create_cursor_scheme(scheme_name, copied_files):
            return False

        print(f"\n✅ カーソルスキーム '{scheme_name}' が正常に作成されました！")
        print("\n📋 使用方法:")
        print("1. Windows設定 → デバイス → マウス → その他のマウス オプション")
        print("2. 「ポインター」タブを選択")
        print(f"3. 配色で '{scheme_name}' を選択")
        print("4. 「OK」をクリックして適用")

        # 今すぐ適用するか確認
        apply_now = (
            input(f"\n今すぐ '{scheme_name}' スキームを適用しますか？ (y/N): ")
            .strip()
            .lower()
        )
        if apply_now in ["y", "yes", "はい"]:
            if self.apply_cursor_scheme(scheme_name):
                print("✅ スキームが適用されました！")
            else:
                print("❌ スキームの適用に失敗しました。")

        return True


def interactive_mode():
    """対話型モードでカーソルを変更"""
    changer = MouseCursorChanger()

    print("=== マウスカーソル変更ツール ===")
    print()

    while True:
        print("オプションを選択してください：")
        print("1. 指定フォルダーのカーソルを適用")
        print("2. 現在のフォルダーのカーソルを適用")
        print("3. カーソルファイルを検索して表示")
        print("4. 登録済みスキーム一覧を表示")
        print("5. 登録済みスキームを適用")
        print("6. 終了")

        choice = input("\n選択 (1-6): ").strip()

        if choice == "1":
            directory = input(
                "カーソルファイルがあるフォルダーのパスを入力してください: "
            ).strip()
            scheme_name = input(
                "スキーム名を入力してください（空白で自動生成）: "
            ).strip()
            if directory:
                changer.change_cursors(directory, scheme_name if scheme_name else None)

        elif choice == "2":
            current_dir = os.getcwd()
            scheme_name = input(
                "スキーム名を入力してください（空白で自動生成）: "
            ).strip()
            changer.change_cursors(current_dir, scheme_name if scheme_name else None)

        elif choice == "3":
            directory = input(
                "検索するフォルダーのパスを入力してください (空白で現在のフォルダー): "
            ).strip()
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
            schemes = changer.list_cursor_schemes()
            if schemes:
                print("\n登録済みのカーソルスキーム:")
                for i, scheme in enumerate(schemes, 1):
                    print(f"  {i}. {scheme}")
            else:
                print("\n登録済みのスキームがありません。")

        elif choice == "5":
            schemes = changer.list_cursor_schemes()
            if schemes:
                print("\n登録済みのカーソルスキーム:")
                for i, scheme in enumerate(schemes, 1):
                    print(f"  {i}. {scheme}")

                try:
                    selection = (
                        int(input("\n適用するスキーム番号を入力してください: ")) - 1
                    )
                    if 0 <= selection < len(schemes):
                        selected_scheme = schemes[selection]
                        if changer.apply_cursor_scheme(selected_scheme):
                            print(f"✅ スキーム '{selected_scheme}' が適用されました！")
                        else:
                            print("❌ スキームの適用に失敗しました。")
                    else:
                        print("無効な番号です。")
                except ValueError:
                    print("数字を入力してください。")
            else:
                print("\n登録済みのスキームがありません。")

        elif choice == "6":
            print("ツールを終了します。")
            break

        else:
            print("無効な選択です。1-6の数字を入力してください。")

        print("\n" + "=" * 50 + "\n")


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
        print(
            "💡 元に戻したい場合は、Windows設定から「マウス」→「その他のマウス オプション」→「ポインター」タブで変更できます。"
        )
    else:
        print("\n❌ カーソルの変更に失敗しました。")


if __name__ == "__main__":
    main()
