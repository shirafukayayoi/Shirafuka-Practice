import io
import re
from collections import defaultdict


def parse_line_history(content):
    """
    LINE のトーク履歴テキストをパースし、
    日付・時刻・送信者・内容を抽出して辞書リストで返す
    """
    date_pattern = re.compile(r"^(\d{4}/\d{1,2}/\d{1,2})")
    msg_pattern = re.compile(r"^(\d{1,2}:\d{2})\t(.+?)\t(.*)$")
    current_date = None
    messages = []

    # BytesIOまたは文字列から処理
    if isinstance(content, bytes):
        lines = content.decode("utf-8").split("\n")
    else:
        lines = content.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        m_date = date_pattern.match(line)
        if m_date:
            current_date = line.split()[0]
            continue
        m_msg = msg_pattern.match(line)
        if m_msg and current_date:
            time, sender, content = m_msg.groups()
            messages.append(
                {
                    "date": current_date,
                    "time": time,
                    "sender": sender,
                    "content": content,
                }
            )
    return messages


def count_chars(messages):
    """送信者ごとに送った文字数をカウント"""
    char_count = defaultdict(int)
    for m in messages:
        char_count[m["sender"]] += len(m["content"])
    return char_count


def count_messages(messages):
    """送信者ごとのメッセージ数をカウント"""
    msg_count = defaultdict(int)
    for m in messages:
        msg_count[m["sender"]] += 1
    return msg_count


def most_active_day(messages):
    """日付ごとの文字数を集計し、最も多い日を返す"""
    day_count = defaultdict(int)
    for m in messages:
        day_count[m["date"]] += len(m["content"])
    return (
        max(day_count.items(), key=lambda x: x[1]) if day_count else ("データなし", 0)
    )


def count_keyword(messages, keyword):
    """指定したキーワードの出現回数をカウント"""
    sender_counts = defaultdict(int)
    for m in messages:
        count = m["content"].count(keyword)
        if count > 0:
            sender_counts[m["sender"]] += count
    return sender_counts
