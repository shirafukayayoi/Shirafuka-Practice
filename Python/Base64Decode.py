import base64

# Base64でエンコードされた文字列（例）
encoded_data = input("Base64でエンコードされた文字列を入力してください: ")

# 元のデータ
plain = input("元のデータを入力してください: ").encode()

# Base64デコード
decoded_data = base64.b64decode(encoded_data)

data = []

# decoded_data の長さを使ってループする（plainの長さではなく）
for i in range(len(decoded_data)):
    # decoded_data[i] はバイトなので、直接整数として扱うことができる
    dec = decoded_data[i] ^ plain[i]
    dec_char = chr(dec)  # 整数を文字に戻す
    data.append(dec_char)

print("デコードされたデータ: " + "".join(data))
