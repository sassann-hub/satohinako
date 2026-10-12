"""
filter.py — 日付・家族の条件でイベントを絞り込む（担当：けーや）
  1. database.py の get_events_on() で、その日に開催しているイベントを取り出す
  2. 開催期間の短い順（その日だけのイベントを先）に並べる
  3. 子どもの年齢が対象年齢（age_min〜age_max）に入らないものを外す（空欄なら外さない）
  4. 好きなキャラ → 好きなジャンル → それ以外 の順に並べる
  5. 最大5件を返す
"""
from datetime import date
 
from database import get_events_on
 
MAX_RESULTS = 5
 
 
def find_events(target_date, profile, limit=MAX_RESULTS):
    events = get_events_on(target_date.isoformat())
    events.sort(key=_period_days)  # 期間の短いもの(その日だけ)を先に
    if profile is not None:
        events = [e for e in events if _fits_ages(e, profile["child_ages"])]
        events = _favorites_first(events, profile)
    return events[:limit]
 
 
def _period_days(event):
    """開催期間の日数。終わりなし(None)はいちばん後ろ"""
    if not event["end_date"]:
        return 99999
    return (date.fromisoformat(event["end_date"]) - date.fromisoformat(event["start_date"])).days
 
 
def _fits_ages(event, child_ages):
    """子ども全員が対象年齢に入っていれば True"""
    low = event["age_min"]
    high = event["age_max"]
    for age in child_ages:
        if low is not None and age < low:
            return False
        if high is not None and age > high:
            return False
    return True
 
 
def _favorites_first(events, profile):
    character = profile["favorite_character"]
    genres = profile["favorite_genres"]
 
    def is_favorite_character(e):
        if not character:
            return False
        return character in (e["character"] or "") or character in e["title"]
 
    def is_favorite_genre(e):
        return e["genre"] in genres
 
    first = [e for e in events if is_favorite_character(e)]
    second = [e for e in events if not is_favorite_character(e) and is_favorite_genre(e)]
    others = [e for e in events if not is_favorite_character(e) and not is_favorite_genre(e)]
    return first + second + others