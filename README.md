# Shirafuka_Practice

## Explanation

これは白深やよいが練習で作ったプログラムを置いておく場所です。

## Links

- [白深やよいのTwitter](https://x.com/shirafuka_yayoi)

## Shirafuka_Programs

## Python

### ImportOS_DirectoryText.py

`python ImportOS_DirectoryText,py <ディレクトリパス>`  
ディレクトリの構成を出力してくれるスクリプト。

**実行結果:**  

```text
├── img
|   ├── dokusyome-ta-.png
|   ├── GitHub.png
|   ├── icon.jpg
|   ├── icon_2.png
|   ├── icon_3.jpg
|   ├── icon_4.jpg
|   ├── kakuyomu_icon.png
|   ├── ron_icon.png
|   ├── twitch-logo.jpg
|   ├── Twitter_icon.png
|   └── Youtube.png
├── index.html
└── main.css
```

### PDF_PasswordCancellation.py

鍵がかかっているPDFを総当たりで調べるためのコード。  
自分が昔作ったPDFのパスワードがわからなくなってしまったので作りました。  
コード内の`characters`と`count`を書き換えて使います。。  
**実行結果:**  

```text
0000 は一致しませんでした
0001 は一致しませんでした
0002 は一致しませんでした
------------------------------------（省略）
パスワードは????でした。
```

## Node.js

### Node_fb2kRichPresence.js

foobar2000とYoutubeSourceを組み合わせて、DiscordRichPresenceに再生バーと動画のURLボタンを付けるやつ。  
詳しくは[ここ](https://github.com/shirafukayayoi/Node_fb2kRichPresence)
