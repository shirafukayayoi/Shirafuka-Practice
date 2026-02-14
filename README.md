# Shirafuka_Practice

## Explanation

これは白深やよいが練習で作ったプログラムを置いておく場所です。  
PythonやNode.jsを使っているので、そのプログラムを置いておきます。  
自分が少しずつ覚えながら作っているコードなので、コメントが沢山ありますが注意してください。  
**Change Log:**

- `2025/01/07`:Googleスプレッドシート関係の認証を変更(サービスアカウントを使用しない形に変えた)
- `2025/05/31`:tokenのパスを変更。
- `2025/05/31`:Pythonのprint文に[Info][Error]を追加

## Links

- Twitter [@shirafukayayoi](https://x.com/shirafukayayoi)

## Shirafuka_Programs

## Node.js

### Node_fb2kRichPresence.js

`Add 2024/06/11`  
foobar2000とYoutubeSourceを組み合わせて、DiscordRichPresenceに再生バーと動画のURLボタンを付けるやつ。  
実行結果はこんな感じ。  
![image](./image/Node_fb2kRichPresence.png)  
詳しくはこのレポジトリを見てください。  
[https://github.com/shirafukayayoi/Node_fb2kRichPresence](https://github.com/shirafukayayoi/Node_fb2kRichPresence)

### PuppeteerDocs.js

`Add 2024/07/21`  
Puppeteerの基本的な使い方をまとめたNode.js。  
詳しくはコード内のコメントを見てください。

## Python

### AutoFolderUnzip.py

`Add 2024/07/17`  
フォルダ内のzipファイルを解凍するPython。  
詳しくはこのレポジトリを見てください。  
[https://github.com/shirafukayayoi/AutoFolderUnzip](https://github.com/shirafukayayoi/AutoFolderUnzip)

### AutoScreenshot.py

`Add 2025/04/18`  
Tkinterを使用した簡単なスクリーンショットツール。指定した領域のスクリーンショットを撮影し、ファイルとして保存します。  
ボタン一つで簡単に画面の特定領域をキャプチャできます。

### Base64Decode.py

`Add 2024/10/26`  
Base64でデコードされた文字列と、元の文字列を使って複合キーを取得するPython

### BOOK-WALKER_NewBookCalendarPush.py

`Add 2024/11/10`  
[BOOK☆WALKER](https://bookwalker.jp/top/)の新刊情報のURLからタイトル等を取得しGoogleカレンダーに追加するPython。

### BOOK-WALKER_Sale_Information.py

`Add 2024/08/02`  
BOOK-WALKERのセール情報を取得するPython。  
Googleスプレットシートに出力されます。

```csv
タイトル,著者,価格,レーベル,終了日
```

詳しくはこのレポジトリを見てください。  
[https://github.com/shirafukayayoi/BOOK-WALKER_Sale_Information](https://github.com/shirafukayayoi/BOOK-WALKER_Sale_Information)

**Change Log:**

- `2024/08/02`:金額を数値として取得できるようにした。

### Bookmeter_LoadBookList.py

`Add 2024/09/08`  
[読書メーター](https://bookmeter.com/)に登録されている、積読本、または読んだ本をcsv形式で出力するpython。  
使い方はこのレポジトリを見てください。  
[https://github.com/shirafukayayoi/Bookmeter_LoadBookList](https://github.com/shirafukayayoi/Bookmeter_LoadBookList)

### Bookmeter_link.py

`Add 2025/07/03`  
[読書メーター](https://bookmeter.com/)のユーザーページから読んだ本と積読本の情報を取得し、[BOOK☆WALKER](https://bookwalker.jp/)の該当ページで「持っている本として登録する」を自動実行するPython。  
PlaywrightとBOOK☆WALKERのアカウント情報が必要です。

**機能:**

- 読書メーターから読んだ本と積読本のリンクを自動取得
- 各本のページからBOOK☆WALKERのリンクを抽出（UUID形式のみ対象）
- キャンペーン・特集・サンプルページのリンクを自動除外
- BOOK☆WALKERに自動ログイン
- 各書籍で「持っている本として登録する」→「紙書籍を書店で」を自動クリック
- 既に登録済みの場合は自動的にスキップ
- リトライ機能とエラーハンドリング

**必要な環境変数:**

```
BOOKWALKER_EMAIL=your_email@example.com
BOOKWALKER_PASSWORD=your_password
```

**注意事項:**

- スクリプト内のユーザーID（`1291485`）を自分のIDに変更する必要があります
- 大量の書籍がある場合、処理に時間がかかります
- 現在はヘッドレスモードが無効（`headless=False`）になっています

**Change Log:**

- `2025/07/10`:サンプルページ（`?sample=1`等）の除外機能を追加、デバッグ出力を削除して本番用に最適化
- `2025/01/15`:デバッグモード機能を追加。デバッグモード時はブラウザを閉じずに処理完了後も待機し、手動確認が可能

### DirectoryText.py

`Add 2024/06/03`  
ディレクトリの構成を出力してくれるPython。  
~~`python ImportOS_DirectoryText,py <ディレクトリパス>`~~  
実行してからディレクトリを入れるようにしました。

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

**Change Log:**

- `2024/07/17`:cmdからディレクトリを入力できるようにした。
- `2025/01/07`:`ImportOS_DirectoryText.py`から`DirectoryText.py`に変更
- `2025/01/02`:cmdからテキストファイルとして出力するか指定できるようにした
- `2025/01/02`:cmdでフォルダーだけ出力するか指定できるようにした

### DMM_PurchhaseList.py

`Add 2024/07/27`  
DMMの購入履歴を取得するPython。  
csvファイルに出力されます。  
詳しくはこのレポジトリを見てください。  
[https://github.com/shirafukayayoi/DMM_PurchaseList](https://github.com/shirafukayayoi/DMM_PurchaseList)  
実行結果はこんな感じ。

```csv
タイトル,サークル名,ジャンル
タイトル,サークル名,ジャンル
タイトル,サークル名,ジャンル
```

**Change Log:**

- `2024/07/28`:GoogleSheetに出力するようにした。
- `2025/02/01`:seleniumからplaywrightに移行、Cookieがあれば使用しログインするようにした。

### DMMGAMEsCalendarPush.py

`Add 2024/11/10`  
DMMのゲーム新作情報をGoogleカレンダーに登録するためのPython。

### fb2k_generate_playlist.py

`Add 2025/04/25`  
foobar2000用.m3u8プレイリストをYouTubeプレイリストURLから自動生成するPythonスクリプト。  
動画URLのみを抽出してプレイリストに出力します。  
yt-dlpが必要になります。

### FileRenames.py

`Add 2025/01/12`  
特定のフォルダーの中身を全て、全角から半角にするPython。  
全角スペースと半角スペースは`_`に変更される。

### Gboard_FormatText.py

`Add 2024/08/19`  
PC版のGboardをスマホでも使えるようにするためのPython。  
詳しくはこのレポジトリを見てください。  
[https://github.com/shirafukayayoi/Gboard_FomatText](https://github.com/shirafukayayoi/Gboard_FomatText)

### GigaFile.py

`Add 2024/10/02`  
指定したファイルを自動的に[GigaFile便](https://gigafile.nu)にアップロードするPython。  
実行したらURLが出力されます。

### GithubRepository_downloader.py

`Add 2025/06/19`  
指定したGitHubユーザーの全リポジトリを自動的にダウンロード・解凍するPython。  
パブリックリポジトリとプライベートリポジトリの両方に対応しています。

**機能:**

- 指定ユーザーの全リポジトリを一括ダウンロード
- ZIPファイルの自動解凍とフォルダ整理
- プライベートリポジトリへの対応（Personal Access Token使用）
- Windowsでのファイルアクセスエラー対策
- GitHub APIレート制限への配慮
- 既存フォルダのスキップ機能

**必要な設定:**
`.env`ファイルに以下を設定：

```
GITHUB_TOKEN=your_personal_access_token_here
```

**Personal Access Tokenの権限:**

- `repo` (Full control of private repositories)
- `public_repo` (Access public repositories)

### LightNovel_CSV.py

`Add 2024/10/02/`  
楽天のブックスから指定した月のラノベの情報を読み取り、csvを作成するPython。

```csv
名前,詳細,日付
```

詳細の部分は空白になっている、

### LightNovel_GoogleCalendarPush.py

`Add 2024/07/11`  
楽天のブックスから指定した月のラノベの情報を読み取り、Googleカレンダーに予定を追加させるPython。  
`year`と`month`、`calendar_id`を入れ、`target_media`にGoogleカレンダーに追加したい出版社を入れ実行。  
実行結果はこんな感じ。
![image](./image/LightNovel_GoogleCalendarPush.png)
詳しくは、このレポジトリと、Zennを見てください。  
[https://github.com/shirafukayayoi/LightNovel_GoogleCalendarPush](https://github.com/shirafukayayoi/LightNovel_GoogleCalendarPush)  
[https://zenn.dev/shirafukayayoi/articles/3d89539bf26c3d](https://zenn.dev/shirafukayayoi/articles/3d89539bf26c3d)

### LINE_analysis.py

`Add 2025/04/18`  
LINEのトーク履歴を解析し、メッセージの頻度やトークの傾向を可視化するPythonスクリプト。
ユーザーごとの発言数、時間帯別のメッセージ頻度、よく使われる単語などを分析します。

### MouseChanger.py

`Add 2025/01/27`  
Windowsのマウスカーソルを変更するPython。指定フォルダー内の`.ani`や`.cur`ファイルを検出し、カーソルスキームとして登録します。  
`<名前> 移動.ani`、`<名前> テキスト.ani`などの日本語ファイル名に対応。  
使用方法：

```bash
python MouseChanger.py "C:\path\to\cursor\folder"  # フォルダー指定
python MouseChanger.py                              # 対話型モード
```

既存のカーソルを上書きせず、新しいスキームとしてWindowsのマウス設定に登録されます。  
Windows設定の「ポインター」タブから選択・切り替えが可能で、不要になったスキームは簡単に削除できます。

### MouseChangerGUI.py

`Add 2025/01/27`  
MouseChanger.pyのGUI版。Tkinterを使用してマウスカーソル変更を視覚的に操作できるPython。  
フォルダー選択、カーソルファイルの自動検出・マッピング、プレビュー機能、カーソルスキームの登録・削除がGUIで行えます。  
exe化にも対応しており、PyInstallerでビルドすることでスタンドアロンアプリケーションとして配布可能です。

### merged_image.py

`Add 2025/02/07`  
1枚目に指定した画像の上に、2枚目に指定した画像を合成させるPython。

### PDF_PasswordCancellation.py

`Add 2024/06/28`  
鍵がかかっているPDFを総当たりで調べるためのコード。  
自分が昔作ったPDFのパスワードがわからなくなってしまったので作りました。  
置いたPDFのディレクトリと同じ場所にパスワードが解除されたPDFが出力されます。  
~~コード内の`characters`と`count`を書き換えて使います。~~  
コードを実行してから選択できるようにしました。  
**実行結果:**

```text
0000 は一致しませんでした
0001 は一致しませんでした
0002 は一致しませんでした
------------------------------------（省略）
パスワードは????でした。
```

**Change Log:**

- `2024/07/17`:cmdからPDFのディレクトリとcountを入力できるようにした。

### PDF_ShirafukaToolCLI.py

`Add 2025/10/04`  
指定したPDFを1ページずつ分割するためのCLIツール。  
`--split_pdf`フラグを付けて起動すると、各ページを個別のPDFとして同じディレクトリに出力します。

**主な機能:**

- PDFをページ単位で切り出し、`<元ファイル名>_page_<番号>.pdf`として保存
- 既存ファイルを上書きしないようファイル名を自動生成
- エラー時に`[Error]`形式でメッセージを出力

**現在の引数:**

- `input_pdf` : 分割対象のPDFファイルのパス（必須）
- `--split_pdf` : このフラグを付けるとページ単位で分割を実行

今後は引数リストに項目を追加するだけでオプションを増やせるよう、順次拡張予定です。

**使い方（PowerShell）:**

```powershell
python Python/PDF_ShirafukaToolCLI.py .\sample.pdf --split_pdf
```

**使い方（コマンドプロンプト）:**

```cmd
python Python\PDF_ShirafukaToolCLI.py sample.pdf --split_pdf
```

### Process_Moniter.py

`Add 2024/12/05`  
特定のソフトのメモリ、CPU、GPU等の使用率を出力するPython。  
**例:**

```text
2024-12-08 15:24:57 - プロセス: foobar2000.exe (PID: 15156)
CPU使用率: 0.0%
メモリ使用量: 101.1 MB
GPU使用率: GPU 0: 7.0% 使用中
--------------------------------------------------
```

**Change Log:**

- `2025/01/04`:上書き表示した。

### RandamNumber.py

`Add 2024/07/16`  
簡単な数あてゲーム。  
実行結果はこんな感じ。  
![image](./image/RandamNumber.png)

### RSS_Notification.py

`Add 2024/08/18`  
RSSフィードを取得して、新しい記事があれば通知するPython。  
最新のtitleとURLを取得します。

```text
title,URL
```

### savedata_copy.py

`Add 2025/01/05`  
特定のフォルダーのセーブデータのフォルダーをバックアップするためのPython。  
www/saveにも対応している。  
Google Driveの`G:`を使い、実装している。

**Change Log:**

- `2025/01/06` セーブデータをGoogle Driveに直接移動するようにした。
- `2025/07/13` セーブデータが存在するフォルダのみをバックアップ先から削除する効率的な処理に変更。重複した例外処理を修正し、ログ出力を改善。

### Tesseract_OCR.py

`Add 2024/08/28`  
Tesseractを使って画像から文字を取得するPython。

### Update_InstagramNote.py

`Add 2025/02/01`  
InstagramのNoteを`playwright`を使い更新させるPython。

### URLChecker.py

`Add 2024/10/26`  
指定しれたURLの隠しURLを探すPython

### USB_FileCopyChecker.py

`Add 2024/10/04`  
指定したファイルをUSBが認識されたときにコピーするPython。

### VideoSpeedChange.py

`Add 2024/11/14`  
指定した動画の再生スピードを変更するPython。  
ディレクトリに`output.mp4`が出力される。

### Vertical_converter.py

`Add 2025/09/28`  
横動画を縦動画（ショート動画形式）に変換するPython。  
元の動画を前景として中央に配置し、背景には元の動画を拡大・暗化・ぼかししたバージョンを使用します。

**主な機能:**

- MoviePyとOpenCVを使用した高品質な動画変換
- 横幅を画面いっぱいに使用した前景動画
- OpenCVのGaussianBlurを使用したぼかし背景効果
- デフォルト解像度: 1080×1920（カスタマイズ可能）
- 音声も含めた完全な動画変換

**必要なライブラリ:** moviepy, opencv-python, numpy

### Youtube_PlayListChange.py

`Add 2024/10/10`  
Youtubeのプレイリストの中身を消し、特定のGoogleスプレッドシートからvideoidを取り出しプレイリストに追加していくPython。  
スプレッドシートは、

```csv
名前,URL
```

という形式になっていなければいけない。

### YoutubeLrcConverter.py

`Add 2026/01/10`  
YouTube動画の英語字幕(VTT)を取得し、LRC形式に変換するPythonスクリプト。  
yt-dlpで字幕だけをダウンロードし、タイムスタンプをLRC形式に変換して保存します。

### Youtube_PlayListGetCSV

`Add 2024/10/10`  
特定のプレイリストを、Googleスプレッドシートで出力するPython。  
出力結果：

```csv
名前,URL
名前,URL
```

### YoutubeDownloaderTools.py

`Add 2026/01/23`  
yt-dlpでダウンロードした動画を縦型の動画にし、GoogleドライブにアップロードするPython。  
YouTube URLまたはローカルファイルのパスを指定可能。

**主な機能:**

- yt-dlpを使用したYouTube動画の自動ダウンロード
- 横動画を縦型（ショート動画形式）に自動変換
  - **GPU高速化対応**: NVIDIA CUDA（scale_cuda, hwupload_cuda）を使用した高速処理
  - CPUフォールバック機能搭載（GPU処理失敗時に自動切替）
  - 処理速度: GPU使用時は従来比5-10倍高速
- Google Driveへの自動アップロード
- 処理完了後の不要ファイルの自動削除（変換後の動画とダウンロードした元動画）
- ローカルファイル使用時は元ファイルを保護

**動作環境:**

- **推奨**: NVIDIA GPU搭載PC（CUDA対応ffmpeg）
- **最低**: CPU処理でも動作可能（moviepy使用）
- ffmpegのCUDAフィルター（scale_cuda, hwupload_cuda, overlay_cuda）が利用可能な場合にGPU処理が有効化

**Change Log:**

- `2026/02/14`: 動画変換時に前景と背景の間に緑色の線が表示される問題を修正。YUV420pフォーマットのアライメント要件に対応するため、すべてのサイズ計算と位置計算を偶数に丸める処理を追加。
- `2026/02/07`: GPU処理による大幅高速化を実装。NVIDIA CUDAを活用したffmpeg直接処理により5-10倍の性能向上。GPU非対応環境でも動作するCPUフォールバック機能を搭載。
- `2026/01/26`: Google Driveアップロード後に不要なファイル（変換後の動画とダウンロードした元動画）を自動削除する機能を追加。ローカルファイルは削除せず保護。
- `2026/01/26`: yt-dlpのエンコーディングエラー（UTF-8デコードエラー）を修正。

### YoutubeVideoClipper.py

`Add 2026/02/01`  
YouTube動画をプレビューしながら時間範囲を指定して切り出し、縦型動画に変換してGoogle Driveにアップロードするツール。  
GUIで操作でき、動画を再生・確認しながら開始点と終了点を設定できます。

**主な機能:**

- 動画プレビュー表示（VLC音声付き、またはOpenCVフォールバック）
- 動画を見ながら開始点・終了点を視覚的に設定
- シークバー上に範囲マーカーを可視化（緑=開始、赤=終了、オレンジ=現在位置）
- 再生コントロール（再生/一時停止、±5秒シーク、音量調整）
- 指定範囲の切り出し、またはフル動画のダウンロード（1080p固定）
- 横動画を縦型（1080×1920）に自動変換
- Google Driveへの自動アップロード
- 一時ファイルの自動削除（スクリプトと同じディレクトリに一時保存）
- 処理完了後のGUI自動クローズ

**必要なライブラリ:**

- python-vlc（音声付きプレビュー用、VLC本体のインストールも必要）
- opencv-python（フォールバック用）
- moviepy（動画変換用）
- yt-dlp（動画ダウンロード用）
- その他: tkinter, PIL, google-api-python-client

**使い方:**

1. YouTube URLを入力
2. 「プレビュー読込」で動画をプレビュー
3. 再生しながら開始点・終了点をボタンで設定
4. 「範囲を切り出してダウンロード」または「フル動画をダウンロード」
5. 自動的に縦型動画に変換→Google Driveにアップロード→GUI終了

**注意事項:**

- VLC本体がインストールされていない場合、音声なしのOpenCVプレーヤーにフォールバックします
- プレビュー用動画は低画質でダウンロードされ、本ダウンロードは1080p固定です
- 環境変数に`YT-DLP_PATH`と`VIDEO_OUTPUT_FOLDER_ID`の設定が必要です

### yt-dlp_dowroad.py

`Add 2024/08/31`  
yt-dlpを使って動画をダウンロードするPython。  
今のオプションは最高画質&最高音質。

### YuchoMailOutput.py

`Add 2024/12/17`  
ゆうちょデビットのメールを取得し、使用したお金を特定のGoogleスプレッドシートに出力するPythonコード。  
詳しくはこのレポジトリを見てください。  
[https://github.com/shirafukayayoi/YuchoMailOutput](https://github.com/shirafukayayoi/YuchoMailOutput)

**Change Log:**

- `2024/12/18`:メッセージを古い順から取得するようにした。
- `2025/01/04`:金額が全て202円になってしまう問題を解消、ファイルのダブルクリックで実行できるようにした。
- `2025/02/01`:関数の更新、ショップごとに使った金額がわかるようにした。
- `2026/01/22`:三井住友カードの「ご利用のお知らせ」メールも読み取り、日付・金額・利用先をゆうちょ分とまとめてスプレッドシートに出力するようにした。
- `2026/01/23`: 重複防止、月別合計・日別最大日/最大額、店舗別TOP、全体高額TOP5、金額の通貨書式、パース失敗時の警告出力を追加し、シートに各集計を出力するようにした。

### YuchoMailOutputCSV.py

`Add 2024/12/17`  
ゆうちょデビットのメールを取得し、使用したお金をCSVファイルとして出力するPythonコード。  
GoogleスプレッドシートではなくローカルのCSVファイルに出力したい場合に使用します。  
基本的な機能は`YuchoMailOutput.py`と同じですが、出力先がCSVファイルになっています。

## PyAutoGui

PyAutoGuiで作成した自動化プログラム一覧

### CoreKeeper_AutoFish.py

`Add 2024/12/5`  
[Core Keeper](https://store.steampowered.com/app/1621690/Core_Keeper/)の魚釣りを自動化するPython。  
実行中は他のことができないのが難点。

## School-Python

学校生活を送るうえで使ったPythonコード。

### Autodownload_EnglishPDF.py

[全国商業高校協会/全商英検](https://zensho.or.jp/examination/pastexams/english/)の3級の問題文を全てダウンロードするPython。

## Template-Python

様々なプログラムの元となるテンプレート。

### GoogleCalendarTemplate.py

`Add 2024/07/29`  
GoogleCalendarに接続するためのテンプレート。  
必要になるのは、`credentials.json`とカレンダーID。  
**TemplateList:**

- イベントを追加する
- イベントを取得する
- CSVファイルからイベントを追加する

**Change Log:**

- `2024/12/08`:場所も追加できるようにした。

### GoogleDriveTemplate.py

`Add 2024/12/16`  
GoogleDriveに接続するためのテンプレート。
**TemplateList:**

- ファイル一覧の取得（特定フォルダも可能）
- ファイルのアップロード（特定フォルダも可能）

### GoogleGmailTemplate.py

`Add 2024/12/16`  
GoogleGmailに接続するためのテンプレート  
**TempletList:**

- 最新のメールを取得する
- 特定のメールアドレスのメールを指定した回数取得する。

### GoogleSheetTemplate.py

`Add 2024/07/28`  
GoogleSheetに接続するためのテンプレート。  
必要になるのは、`credentials.json`とスプレットシートID。  
**TemplateList:**

- スプレットシートのデータを読み込む
- スプレットシートのすべてのデータを消す
- スプレットシートにデータを書き込む
- スプレットシートに1行目だけ書き込む
- フィルターを設定する

### YoutubeTemplate.py

`Add 2024/08/24`  
Youtubeに接続するためのテンプレート。  
必要になるのはAPIキー。  
**TemplateList:**

- ライブ動画の配信開始時間の取得

### ToolsUpdater.py

`Add 2026/02/01`  
Toolsフォルダー内のツール（yt-dlpなど）を自動更新するスクリプト。  
GitHub Releases APIを使用して最新版をチェックし、安全に更新を行います。  
**機能:**

- バージョン確認（`--check`）
- 特定ツールの更新（`--update --tool ツール名`）
- 全ツールの更新（`--update-all`）
- プロセス実行中の検出とスキップ
- ダウンロード失敗時の自動ロールバック
- GitHub認証（オプション）でAPIレート制限を緩和

**使用例:**

```bash
# 全ツールのバージョンを確認
python ToolsUpdater.py --check

# yt-dlpを更新
python ToolsUpdater.py --update --tool yt-dlp

# 全ツールを更新
python ToolsUpdater.py --update-all
```

**設定:**

- 設定ファイル: [settings/tools_config.json](settings/tools_config.json)
- GitHub認証（オプション）: [Python/.env](Python/.env) に `GITHUB_TOKEN` を設定
