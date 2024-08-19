import zipfile
import os

# 1. ファイルパスの入力とファイルの存在確認
file_path = input('ファイルパスを入力してください: ')

# ファイルの存在確認
if not os.path.exists(file_path):
    print("エラー: 指定されたファイルが存在しません。")
else:   # ファイルが存在する場合
    # 圧縮後のZIPファイルの名前を指定
    zip_file_name = os.path.splitext(file_path)[0] + ".zip" # os.path.splitext()で拡張子以外のファイル名を取得
    
    try:    # エラーが出るかもしれないため、try-exceptでエラー処理を行う
        # 2. ZIPファイルの作成
        with zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, os.path.basename(file_path))  # ファイルをZIPに追加
        
        print(f"ZIPファイルの作成が完了しました: {zip_file_name}")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
