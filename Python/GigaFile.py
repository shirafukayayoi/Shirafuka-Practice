from gfile import GFile

def main():
    file_name = input("ファイルパスを入力してください: ")
    if '"' in file_name:
        file_name = file_name.replace('"', '')
    giga = GigaFile(file_name)
    giga.update_file()

class GigaFile():
    def __init__(self, file_name):
        self.filename = file_name

    def update_file(self):
        update_file = GFile(self.filename, progress=True).upload().get_download_page()  # ログを出したくないならprogress=False
        print(f"GigaFile: {update_file}")

if __name__ == '__main__':
    main()
