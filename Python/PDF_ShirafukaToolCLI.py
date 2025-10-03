import argparse
import os

from pypdf import PdfReader, PdfWriter

def main():
    # 1. ArgumentParserオブジェクトを作成
    parser = argparse.ArgumentParser(
        description="指定されたPDFファイルをページごとに分割します。"
    )

    # 2. 引数（オプション）を定義

    # 位置引数（必須の引数）。--をつけずに指定するもの。
    # 'input_pdf'という名前で取得できるようにする
    parser.add_argument(
        "input_pdf",
        type=str,
        help="分割するPDFファイルのパスを指定します。"
    )

    parser.add_argument(
        "--split_pdf",
        action="store_true",
        help="PDFをページごとに分割します。"
    )

    # 3. コマンドライン引数を解析
    args = parser.parse_args()

    # 4. 取得した引数の値に基づいて処理を実行
    if args.split_pdf:
        split_pdf_to_pages(args.input_pdf)


def split_pdf_to_pages(input_pdf_path):
    # 入力されたPDFファイル名から拡張子とベース名を取得
    base_name, ext = os.path.splitext(os.path.basename(input_pdf_path))

    try:
        # PDF全体を読み込み、総ページ数を取得
        reader = PdfReader(input_pdf_path)
        num_pages = len(reader.pages)

        for i in range(num_pages):
            # 1ページ分のPDFを作成するためにWriterを生成
            writer = PdfWriter()
            writer.add_page(reader.pages[i])

            # ページ番号付きのファイル名を作成して出力
            output_pdf_path = f"{base_name}_page_{i + 1}{ext}"
            with open(output_pdf_path, "wb") as output_pdf_file:
                writer.write(output_pdf_file)

            # 分割結果をログとして表示
            print(f"[Info] Created: {output_pdf_path}")
    except FileNotFoundError:
        # 対象ファイルが存在しない場合のエラーメッセージ
        print("[Error] 指定されたPDFファイルが見つかりません")
    except Exception as error:
        # 想定外の例外が発生した場合のエラーメッセージ
        print(f"[Error] 予期しないエラーが発生しました: {error}")
        
if __name__ == "__main__":
    main()