# google_tools_cli

Python の Google 系ツールを Rust CLI に寄せるための移行先です。

## 使い方（想定）

```bash
cargo run -- --help
```

> この環境では `cargo` 未インストールのため、実ビルド確認は未実施です。

## 共通オプション

- `--credentials tokens/credentials.json`
- `--token tokens/rust_google_token.json`

## サブコマンド

### 認証

```bash
google-tools-cli auth
```

実行後に表示されるURLをブラウザで開き、`http://127.0.0.1:8765/callback` へのリダイレクトで認証完了します。

`--scope` 省略時は以下をまとめて要求します。

- `https://www.googleapis.com/auth/calendar.events`
- `https://www.googleapis.com/auth/youtube`
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/spreadsheets`
- `https://www.googleapis.com/auth/drive.file`

個別に指定したい場合:

```bash
google-tools-cli auth --scope https://www.googleapis.com/auth/calendar.events
```

### Calendar

```bash
google-tools-cli calendar add-event --calendar-id <CAL_ID> --title "タイトル" --date 2026-03-20
google-tools-cli calendar add-events-json --calendar-id <CAL_ID> --file events.json
```

### YouTube

```bash
google-tools-cli youtube export-playlist --playlist-id <PLAYLIST_ID> --output-csv playlist.csv
google-tools-cli youtube import-playlist --playlist-id <PLAYLIST_ID> --input-csv playlist.csv --url-column URL
```

### Gmail

```bash
google-tools-cli gmail export-search --query "from:example@example.com newer_than:30d" --output-csv mails.csv
```

### Sheets

```bash
google-tools-cli sheets append-csv --spreadsheet-id <ID> --sheet-name Sheet1 --csv-path input.csv
```

### Drive

```bash
google-tools-cli drive upload-file --file-path ./sample.mp4 --folder-id <FOLDER_ID>
```

## Python からの移行対応（Google系）

- `BOOK-WALKER_NewBookCalendarPush.py` -> `calendar add-event / add-events-json`
- `DMMGAMEsCalendarPush.py` -> `calendar add-event / add-events-json`
- `LightNovel_GoogleCalendarPush.py` -> `calendar add-event / add-events-json`
- `CalendarTextCLI.py` -> 予定追加部分を `calendar add-events-json` で代替
- `Youtube_PlayListGetCSV.py` -> `youtube export-playlist`
- `Youtube_PlayListChange.py` -> `youtube import-playlist`
- `YuchoMailOutput.py` / `YuchoMailOutputCSV.py` -> `gmail export-search`
- `BOOK-WALKER_Sale_Information.py` / `Bookmeter_LoadBookList.py` -> `sheets append-csv` と `drive upload-file` を組み合わせて代替
- `Template/Google*.py` -> `auth`, `calendar`, `gmail`, `sheets`, `drive` で代替

## 非対応（今回除外）

- Playwright 依存ツール（`Bookmeter_link.py`, `DMM_PurchhaseList.py`, `Update_InstagramNote.py` など）は対象外。

## 補足

- Python 各スクリプトのスクレイピング処理そのものは移植していません。
- この Rust CLI は Google API 操作部分を共通化する「移行先の土台」です。
