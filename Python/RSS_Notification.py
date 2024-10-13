import feedparser

# RSSフィードのURLを指定
rss_url = input("RSSフィードのURLを入力してください: ")
# RSSフィードを取得して解析
feed = feedparser.parse(rss_url)

# RSSを配列として取得、最新の記事を取得
latest_article = feed.entries[0]
# 最新の記事のタイトルを取得
title = latest_article.title
# 最新の記事のURLを取得
link = latest_article.id

published = latest_article.published

# RSSのタイトルとURLを表示
print(feed)
print(f"----------------")
print(title)
print(link)
print(published)
