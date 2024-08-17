import feedparser

# RSSフィードのURLを指定
rss_url = "https://github.com/shirafukayayoi/Shirafuka_Practice/commits/main/.atom"
# RSSフィードを取得して解析
feed = feedparser.parse(rss_url)

# RSSを配列として取得、最新の記事を取得
latest_article = feed.entries[0]
# 最新の記事のタイトルを取得
title = latest_article.title
# 最新の記事のURLを取得
link = latest_article.link

# RSSのタイトルとURLを表示
print(title)
print(link)
