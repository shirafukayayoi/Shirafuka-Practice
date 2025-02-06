import os

from PIL import Image

# 画像1のファイルを入力
image1_file = input("1つ目の画像ファイル名を入力してください：")
image1_file = image1_file.strip('"')  # 前後のダブルクォートを取り除く
image1_file = os.path.normpath(image1_file)  # パスを正規化

if not os.path.exists(image1_file):
    print(
        f"エラー: {image1_file} が見つかりません。正しいファイル名を入力してください。"
    )
    exit()

# 画像2のファイルを入力
image2_file = input("2つ目の画像ファイル名を入力してください：")
image2_file = image2_file.strip('"')  # 前後のダブルクォートを取り除く
image2_file = os.path.normpath(image2_file)  # パスを正規化

if not os.path.exists(image2_file):
    print(
        f"エラー: {image2_file} が見つかりません。正しいファイル名を入力してください。"
    )
    exit()

# 画像を開く
image1 = Image.open(image1_file).convert("RGBA")  # 背景画像
image2 = Image.open(image2_file).convert("RGBA")  # 重ねる画像

# 画像のサイズを合わせる（image1のサイズにimage2をリサイズ）
image2 = image2.resize(image1.size, Image.LANCZOS)

# 1枚目の画像に2枚目を重ねる（透過を考慮）
image1.paste(image2, (0, 0), image2)  # image2のアルファチャンネルを考慮して合成

# 保存または表示
output_file = "merged_output.png"
image1.save(output_file)
print(f"合成画像を {output_file} に保存しました。")
image1.show()
