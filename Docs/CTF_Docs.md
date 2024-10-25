# CTF_Docs

## よく使うコマンドLinux一覧

| command | 詳細                            |
| :------ | ------------------------------- |
| ls      | ディレクトリの中身を表示        |
| -l      | 詳細情報を表示                  |
| -a      | 隠しファイルも表示              |
| cd      | ディレクトリの移動              |
| cp      | ファイルのコピー                |
| mv      | ファイルの移動                  |
| rm      | ファイルの削除                  |
| cat     | ファイルの中身全体を表示        |
| less    | ファイルの内容を1ページずつ表示 |
| head    | ファイルの数行を表示            |
| tail    | ファイルの末行を表示            |

## ZIPファイルの解析方法

[John the Ripper](https://www.openwall.com/john/)を使う。  
使い方:  

1. `cd`コマンドを使い、ディレクトリに入る。
1. ディレクトリにzipファイルを入れる。
1. ディレクトリの中で`zip2john.exe <zip名> ><zip名>.hash`と実行する
1. ハッシュが作られているため、それを使うために`john.exe --pot=<zip名>.pot --incremental=ASCII <zip名>.hash`とコマンドを打つ

これででてきたパスワードを打ち込んだら終わり！！!  
![image](/image/zip2john.png)