import os
import pytesseract
from PIL import Image

class charRec:
    def __init__(self):
        # 画像のパスを指定 (絶対パス)
        image_path = input("画像ファイルのパスを入力してください: ")
        
        # 画像ファイルの存在を確認
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"指定されたファイルが見つかりません: {image_path}")
        
        # 画像の読み込み
        self.img = Image.open(image_path).convert("RGB")

    def imgText(self):
        # Tesseract-OCRの実行
        return pytesseract.image_to_string(self.img, lang="jpn")

# 現在の作業ディレクトリを確認
print("現在の作業ディレクトリ:", os.getcwd())

img = charRec()
result = img.imgText()
print(result)
