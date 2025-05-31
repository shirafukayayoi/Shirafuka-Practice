import os
import zipfile


def replace_nouns_with_ja_jp(text):
    # 名詞部分を ja-jp に変換する処理
    chenged_text = [
        "人名",
        "名詞",
        "動詞",
        "形容詞",
        "副詞",
        "助詞",
        "助動詞",
        "連体詞",
        "感動詞",
        "接続詞",
        "接頭詞",
        "記号",
        "固有名詞",
    ]
    for i in chenged_text:
        text = text.replace(i, "ja-jp")
    return text  # 変換後のテキストを返す


def process_file(file_path):
    # ファイルの存在確認
    if not os.path.exists(file_path):
        print("[Error] エラー: 指定されたファイルが存在しません。")
        return

    try:
        # 元のファイルの内容を読み込む
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # 内容を変換する
        new_content = replace_nouns_with_ja_jp(content)

        # 変更後の内容を新しいファイルとして保存
        new_file_path = os.path.splitext(file_path)[0] + "_modified.txt"
        with open(new_file_path, "w", encoding="utf-8") as new_file:
            new_file.write(new_content)

        print(f"内容が変更された新しいファイルが作成されました: {new_file_path}")

        # 新しいファイルをZIPファイルに圧縮
        zip_file_name = os.path.splitext(file_path)[0] + ".zip"

        with zipfile.ZipFile(zip_file_name, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(new_file_path, os.path.basename(new_file_path))

        print(f"ZIPファイルの作成が完了しました: {zip_file_name}")

        # 作成した一時ファイルを削除（必要に応じて）
        os.remove(new_file_path)

    except Exception as e:
        print(f"エラーが発生しました: {e}")


# ファイルパスの入力
file_path = input("ファイルパスを入力してください: ")
process_file(file_path)
