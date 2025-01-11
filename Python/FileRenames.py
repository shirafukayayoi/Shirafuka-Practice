import os
import unicodedata


def normalize_filename(filename):
    # 半角および全角スペースをアンダースコアに変更
    filename = filename.replace(" ", "_").replace("　", "_")
    # 全角文字を半角に変更
    filename = unicodedata.normalize("NFKC", filename)
    # Windowsで使用できない文字をアンダースコアに変更
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    return filename


def rename_files_in_directory(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        # ファイルのリネーム
        for filename in files:
            new_filename = normalize_filename(filename)
            if new_filename != filename:
                old_path = os.path.join(root, filename)
                new_path = os.path.join(root, new_filename)
                if os.path.exists(new_path):
                    os.remove(new_path)  # 既に存在するファイルを削除
                os.rename(old_path, new_path)
                print(f"Renamed file: {old_path} -> {new_path}")

        # ディレクトリのリネーム
        for dirname in dirs:
            new_dirname = normalize_filename(dirname)
            if new_dirname != dirname:
                old_path = os.path.join(root, dirname)
                new_path = os.path.join(root, new_dirname)
                if os.path.exists(new_path):
                    os.rmdir(new_path)  # 既に存在するディレクトリを削除
                os.rename(old_path, new_path)
                print(f"Renamed directory: {old_path} -> {new_path}")


if __name__ == "__main__":
    target_directory = input("対象ディレクトリのパスを入力してください: ")
    rename_files_in_directory(target_directory)
