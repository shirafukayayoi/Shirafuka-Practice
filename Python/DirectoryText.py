import os


def print_directory_structure(root_dir, prefix=""):
    items = os.listdir(root_dir)
    for index, item in enumerate(items):
        item_path = os.path.join(root_dir, item)
        if index == len(items) - 1:
            connector = "└──"
        else:
            connector = "├──"
        print(prefix + connector + " " + item)
        if os.path.isdir(item_path):
            if index == len(items) - 1:
                new_prefix = prefix + "    "
            else:
                new_prefix = prefix + "|   "
            print_directory_structure(item_path, new_prefix)


if __name__ == "__main__":
    root_directory = input("ディレクトリパスを入力してください: ")
    print_directory_structure(root_directory)
