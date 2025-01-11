import os


def print_directory_structure(
    root_dir, prefix="", output_file=None, folders_only=False
):
    items = os.listdir(root_dir)
    for index, item in enumerate(items):
        item_path = os.path.join(root_dir, item)
        if folders_only and not os.path.isdir(item_path):
            continue
        if index == len(items) - 1:
            connector = "└──"
        else:
            connector = "├──"
        line = prefix + connector + " " + item
        print(line)
        if output_file:
            output_file.write(line + "\n")
        if os.path.isdir(item_path):
            if index == len(items) - 1:
                new_prefix = prefix + "    "
            else:
                new_prefix = prefix + "|   "
            print_directory_structure(item_path, new_prefix, output_file, folders_only)


if __name__ == "__main__":
    root_directory = input("ディレクトリパスを入力してください: ")
    output_choice = (
        input("テキストファイルとして出力しますか？ (y/n): ").strip().lower()
    )
    folders_only_choice = (
        input("フォルダーのみを表示しますか？ (y/n): ").strip().lower()
    )
    folders_only = folders_only_choice == "y"
    if output_choice == "y":
        output_dir = input("出力するディレクトリのパスを入力してください: ")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file_path = os.path.join(output_dir, "directory_structure.txt")
        with open(output_file_path, "w", encoding="utf-8") as output_file:
            print_directory_structure(
                root_directory, output_file=output_file, folders_only=folders_only
            )
    else:
        print_directory_structure(root_directory, folders_only=folders_only)
