import requests
from bs4 import BeautifulSoup

def main():
    url = input("urlを入力してください: ")
    BsT = BuautifulSoupTemplate()
    BsT.get_html(url)

class BuautifulSoupTemplate:
    def __init__(self):
        pass

    def first_get_html(self, url):
        try:
            req = requests.get(url)
            req.raise_for_status()
            return req.text

if __name__ == "__main__":
    main()