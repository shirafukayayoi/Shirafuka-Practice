import os
import sys

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
    if len(sys.argv) != 2:
        print("Usage: python <このファイル名>.py <ディレクトリパス>")
        sys.exit(1)
    
    root_directory = sys.argv[1]
    print_directory_structure(root_directory)
