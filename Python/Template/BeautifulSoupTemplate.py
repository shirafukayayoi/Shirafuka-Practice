import requests
from bs4 import BeautifulSoup

def main():
    url = input("urlを入力してください: ")
    BsT = BuautifulSoupTemplate()
    BsT.get_html(url)

class BuautifulSoupTemplate:
    def __init__(self):
        pass

if __name__ == "__main__":
    main()