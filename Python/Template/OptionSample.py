import argparse


def main():
    # 1. ArgumentParserオブジェクトを作成
    # descriptionはヘルプメッセージに表示されます
    parser = argparse.ArgumentParser(
        description="指定された名前で挨拶をします。"
    )

    # 2. 引数（オプション）を定義

    # 位置引数（必須の引数）。--をつけずに指定するもの。
    # 'name'という名前で取得できるようにする
    parser.add_argument(
        "name",
        type=str,
        help="挨拶をする相手の名前を指定します。"
    )

    # オプション引数（フラグ）。--をつけて指定するもの。
    # action='store_true'で、--formalが指定されたらTrue、されなかったらFalseになる
    parser.add_argument(
        "--formal",
        action="store_true",
        help="敬語を使った丁寧な形式で挨拶をします。"
    )

    # 3. コマンドライン引数を解析
    # argsオブジェクトに引数の値が格納されます
    args = parser.parse_args()

    # 4. 取得した引数の値に基づいて処理を実行
    if args.formal:
        greeting = f"皆様、{args.name}様。ご機嫌いかがでしょうか。"
    else:
        greeting = f"やあ、{args.name}！元気？"

    print(greeting)

if __name__ == "__main__":
    main()