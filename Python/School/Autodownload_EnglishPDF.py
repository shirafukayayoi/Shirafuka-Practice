import os

import requests
from bs4 import BeautifulSoup

# 3級のページURL
url = "https://zensho.or.jp/examination/pastexams/english/"

try:
    # HTTPリクエストを送信してページの内容を取得
    response = requests.get(url)
    response.raise_for_status()

    # BeautifulSoupを使ってHTMLを解析
    soup = BeautifulSoup(response.text, "html.parser")

    # PDFリンクを探す
    pdf_links = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.endswith(".pdf") and "3_exa" in href:
            href_url = "https://zensho.or.jp" + href
            pdf_links.append(href_url)

    # PDFをダウンロードするディレクトリを作成
    os.makedirs("pdfs", exist_ok=True)

    # PDFをダウンロード
    for pdf_link in pdf_links:
        try:
            pdf_response = requests.get(pdf_link)
            pdf_response.raise_for_status()

            # ファイル名から回数を抽出してファイル名を作成
            file_name = pdf_link.split("/")[-1]
            times = file_name.split("_")[1]
            pdf_name = os.path.join("pdfs", f"第{times}回.pdf")

            with open(pdf_name, "wb") as pdf_file:
                pdf_file.write(pdf_response.content)
            print(f"Downloaded: {pdf_name}")
        except requests.RequestException as e:
            print(f"Failed to download {pdf_link}: {e}")

except requests.RequestException as e:
    print(f"Failed to retrieve the page: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
