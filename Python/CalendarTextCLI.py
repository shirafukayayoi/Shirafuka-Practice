import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pytz
import requests
from dotenv import load_dotenv
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL_NAME = "gemini-flash-latest"
CALENDAR_SCOPE = ["https://www.googleapis.com/auth/calendar.events"]
MAX_GEMINI_RETRIES = 5
BASE_RETRY_SECONDS = 1.5


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_env() -> None:
    root = repo_root()
    load_dotenv(root / ".env")
    load_dotenv(root / "Python" / ".env")


def load_calendar_config() -> dict[str, Any]:
    config_path = repo_root() / "tokens" / "calendar_ids.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"カレンダー設定ファイルが見つかりません: {config_path}"
        )

    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("calendar_ids.json の形式が不正です。")
    return data


def select_calendar_id(config: dict[str, Any], category: str | None) -> tuple[str, str]:
    calendar_map = (
        config.get("calendar_map")
        if isinstance(config.get("calendar_map"), dict)
        else {}
    )
    if category:
        cal_id = calendar_map.get(category)
        if not cal_id:
            raise KeyError(
                f"calendar_map にカテゴリ '{category}' がありません。利用可能: {', '.join(calendar_map.keys())}"
            )
        return cal_id, category

    default_id = config.get("default_calendar_id")
    if default_id:
        return default_id, "default"

    if calendar_map:
        first_category = next(iter(calendar_map.keys()))
        return calendar_map[first_category], first_category

    legacy_default = config.get("default")
    if legacy_default:
        return legacy_default, "default"

    raise KeyError("calendar_ids.json に有効な calendar_id がありません。")


def authenticate_google() -> Any:
    root = repo_root()
    token_path = root / "tokens" / "calendar_token.json"
    credentials_path = root / "tokens" / "credentials.json"

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), CALENDAR_SCOPE)

    if not creds or not creds.valid:
        needs_reauth = True

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                needs_reauth = False
            except RefreshError as e:
                print(f"[Warning] 既存トークンの更新に失敗したため再認証します: {e}")
                creds = None

        if needs_reauth:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"OAuthクライアント情報が見つかりません: {credentials_path}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), CALENDAR_SCOPE
            )
            creds = flow.run_local_server(port=0)

        token_path.parent.mkdir(parents=True, exist_ok=True)
        with token_path.open("w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def gemini_generate(prompt: str, model: str, api_key: str) -> str:
    url = f"{GEMINI_API_BASE}/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.2},
    }

    body = None
    last_error: Exception | None = None

    for attempt in range(1, MAX_GEMINI_RETRIES + 1):
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            body = response.json()
            break
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code not in (429, 500, 502, 503, 504):
                raise

            last_error = e
            if attempt == MAX_GEMINI_RETRIES:
                break

            retry_after = None
            if e.response is not None:
                retry_after_header = e.response.headers.get("Retry-After")
                if retry_after_header:
                    try:
                        retry_after = float(retry_after_header)
                    except ValueError:
                        retry_after = None

            wait_seconds = retry_after
            if wait_seconds is None:
                wait_seconds = BASE_RETRY_SECONDS * (
                    2 ** (attempt - 1)
                ) + random.uniform(0, 0.8)

            print(
                f"[Warning] Gemini API一時エラー ({status_code})。{wait_seconds:.1f}秒後に再試行します ({attempt}/{MAX_GEMINI_RETRIES})"
            )
            time.sleep(wait_seconds)
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt == MAX_GEMINI_RETRIES:
                break
            wait_seconds = BASE_RETRY_SECONDS * (2 ** (attempt - 1)) + random.uniform(
                0, 0.8
            )
            print(
                f"[Warning] Gemini API通信エラー。{wait_seconds:.1f}秒後に再試行します ({attempt}/{MAX_GEMINI_RETRIES})"
            )
            time.sleep(wait_seconds)

    if body is None:
        if isinstance(last_error, requests.exceptions.HTTPError):
            status_code = (
                last_error.response.status_code
                if last_error.response is not None
                else "unknown"
            )
            raise RuntimeError(
                f"Gemini API呼び出しに失敗しました（HTTP {status_code}）。しばらく待って再実行してください。"
            ) from last_error
        raise RuntimeError(
            "Gemini API呼び出しに失敗しました。ネットワーク状態を確認して再実行してください。"
        ) from last_error

    candidates = body.get("candidates", [])
    if not candidates:
        raise ValueError(f"Gemini応答に候補がありません: {body}")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(
        part.get("text", "") for part in parts if isinstance(part, dict)
    ).strip()
    if not text:
        raise ValueError(f"Gemini応答テキストが空です: {body}")
    return text


def parse_json_block(text: str) -> Any:
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    candidate = code_block.group(1) if code_block else text
    return json.loads(candidate)


def normalize_events(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        raise ValueError("イベント解析結果は配列である必要があります。")

    normalized = []
    for item in raw:
        if not isinstance(item, dict):
            continue

        title = str(item.get("title", "")).strip()
        if not title:
            continue

        description = str(item.get("description", "")).strip()
        location = str(item.get("location", "")).strip()

        all_day = bool(item.get("all_day", False))
        start = str(item.get("start", "")).strip()
        end = str(item.get("end", "")).strip()

        if not start:
            continue
        if not end:
            end = start

        normalized.append(
            {
                "title": title,
                "description": description,
                "location": location,
                "start": start,
                "end": end,
                "all_day": all_day,
            }
        )

    if not normalized:
        raise ValueError("有効な予定を抽出できませんでした。")
    return normalized


def parse_events_with_gemini(
    text: str, model: str, api_key: str
) -> list[dict[str, Any]]:
    jst = pytz.timezone("Asia/Tokyo")
    today = datetime.now(jst).strftime("%Y-%m-%d")

    prompt = (
        "以下の日本語テキストからGoogleカレンダー予定を抽出して、JSON配列のみ返してください。"
        "各要素は title,start,end,all_day,description,location を持つこと。"
        "description,location は不明なら空文字。"
        "all_day は true/false。"
        "all_day=true の場合 start/end は YYYY-MM-DD。"
        "all_day=false の場合 start/end は ISO8601 (例: 2026-02-21T19:00:00+09:00)。"
        "時刻指定がない予定は all_day=true。"
        "複数予定があれば配列に複数要素を入れる。"
        f"今日は {today} (JST) です。\n\n"
        f"入力テキスト:\n{text}"
    )

    raw_text = gemini_generate(prompt, model, api_key)
    parsed = parse_json_block(raw_text)
    return normalize_events(parsed)


def classify_category_with_gemini(
    text: str,
    categories: list[str],
    model: str,
    api_key: str,
) -> str | None:
    if not categories:
        return None

    prompt = (
        "次の予定文を最も適切なカテゴリ1つに分類してください。"
        "カテゴリ名のみ返してください。説明不要。\n"
        f"カテゴリ候補: {', '.join(categories)}\n"
        f"予定文: {text}"
    )
    result = gemini_generate(prompt, model, api_key)
    for category in categories:
        if category in result:
            return category
    return None


def build_event_payload(event: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "summary": event["title"],
        "description": event.get("description", ""),
    }

    if event.get("location"):
        payload["location"] = event["location"]

    if event.get("all_day"):
        payload["start"] = {"date": event["start"]}
        payload["end"] = {"date": event["end"]}
    else:
        payload["start"] = {"dateTime": event["start"], "timeZone": "Asia/Tokyo"}
        payload["end"] = {"dateTime": event["end"], "timeZone": "Asia/Tokyo"}

    return payload


def print_suggestions(events: list[dict[str, Any]], category: str | None) -> None:
    print("\n=== 予定提案 ===")
    if category:
        print(f"カテゴリ: {category}")

    for idx, event in enumerate(events, start=1):
        print(f"\n[{idx}] {event['title']}")
        if event.get("all_day"):
            print(f"  日付: {event['start']} (終日)")
        else:
            print(f"  日時: {event['start']} ~ {event['end']}")

        if event.get("location"):
            print(f"  場所: {event['location']}")
        if event.get("description"):
            print(f"  詳細: {event['description']}")


def confirm() -> bool:
    answer = input("\nこの内容で追加しますか？ [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def add_events(
    service: Any, calendar_id: str, events: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    created = []
    for event in events:
        payload = build_event_payload(event)
        response = (
            service.events().insert(calendarId=calendar_id, body=payload).execute()
        )
        created.append(response)
    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="テキストからGoogleカレンダー予定を作成するCLI"
    )
    parser.add_argument("text", nargs="+", help="予定テキスト")
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="提案だけ表示して、承認後に追加する",
    )
    parser.add_argument(
        "--category",
        help="calendar_map のカテゴリ名を指定して追加先カレンダーを固定する",
    )
    parser.add_argument(
        "--model",
        default=GEMINI_MODEL_NAME,
        help=f"Geminiモデル名 (default: {GEMINI_MODEL_NAME})",
    )
    parser.add_argument(
        "--api-key-env",
        default="GEMINI_API_KEY",
        help="Gemini APIキーを読む環境変数名 (default: GEMINI_API_KEY)",
    )
    return parser.parse_args()


def main() -> int:
    load_env()
    args = parse_args()
    text = " ".join(args.text).strip()

    api_key = os.getenv(args.api_key_env, "").strip()
    if not api_key:
        print(
            f"[Error] 環境変数 {args.api_key_env} が未設定です。Gemini APIキーを設定してください。"
        )
        return 1

    try:
        config = load_calendar_config()

        chosen_category = args.category
        calendar_map = (
            config.get("calendar_map")
            if isinstance(config.get("calendar_map"), dict)
            else {}
        )
        if not chosen_category and calendar_map:
            auto_category = classify_category_with_gemini(
                text, list(calendar_map.keys()), args.model, api_key
            )
            if auto_category:
                chosen_category = auto_category

        calendar_id, resolved_category = select_calendar_id(config, chosen_category)

        events = parse_events_with_gemini(text, args.model, api_key)

        if args.suggest:
            print_suggestions(events, resolved_category)
            if not confirm():
                print("[Info] 予定は追加しませんでした。")
                return 0

        service = authenticate_google()
        created = add_events(service, calendar_id, events)

        print(f"[Info] {len(created)} 件の予定を追加しました。")
        for idx, event in enumerate(created, start=1):
            print(
                f"  {idx}. {event.get('summary', '(無題)')} -> {event.get('htmlLink', '-')}"
            )
        return 0
    except Exception as e:
        print(f"[Error] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
