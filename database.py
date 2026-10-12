# =============================================================
# database.py — DB操作の一元管理（おやこでかけ）
# W3 のdatabase.py をベースに、eventsとfamily用に作り替えたもの
# =============================================================
import sqlite3
from pathlib import Path
from datetime import datetime

# このファイルがあるフォルダを基準にする(どこから実行しても同じDBを使うため)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "oyako.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def get_connection():
    """DB への接続を取得する（data/ フォルダが無ければ自動作成）"""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row        # 行データを辞書のように扱う
    return conn


def init_db():
    """schema.sql を読み込んで DB を初期化する"""
    conn = get_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# -------------------------------------------------------------
# events(イベント)
# -------------------------------------------------------------

def upsert_event(event: dict) -> int:
    """ページ情報を DB に登録する（同じURLは上書き）
    
    event にない項目は NULL(不明)として保存する。
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO events
            (title, start_date, end_date, time_text, venue, place_detail, city,
             age_min, age_max, reservation, deadline, fee, indoor, character, genre,
             url, source, raw_text, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? ,?, ? ,?)
        """, (
            event["title"],
            event["start_date"],
            event.get("end_date"),
            event.get("time_text"),
            event.get("venue"),
            event.get("place_detail"),
            event.get("city"),
            event.get("age_min"),
            event.get("age_max"),
            event.get("reservation"),
            event.get("deadline"),
            event.get("fee"),
            event.get("indoor"),
            event.get("character"),
            event.get("genre"),
            event["url"],
            event["source"],
            event.get("raw_text"),
            event.get("fetched_at") or _now(),
        ))
        event_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()
    return event_id


def get_events_on(date: str) -> list:
    """その日に開催中のイベントを、開始日の早い順で取得する
    
    date: "YYYY-MM-DD"
    end_date が NULLのイベントも含める。
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM events
        WHERE start_date <= ?
        AND (end_date IS NULL OR end_date >= ?)
        ORDER BY start_date
    """, (date, date))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def count_events() -> int:
    """登録済みのイベント件数を返す(確認用)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM events")
    count = cursor.fetchone()[0]
    conn.close()
    return count


# -------------------------------------------------------------
# families(家族)
# -------------------------------------------------------------

def _list_to_text(items) -> str:
    """リスト(or 文字列)を DB 保存用のカンマ区切り文字列にする  例: [3, 6] → "3,6" """
    if not items:
        return ""
    if isinstance(items, str):
        return items
    return ",".join(str(i) for i in items)


def _text_to_list(text) -> list:
    """カンマ区切り文字列をリストに戻す  例: "papa,mama" → ["papa", "mama"]"""
    return [t.strip() for t in (text or "").split(",") if t.strip()]


def save_family(family: dict, family_id: int = None) -> int:
    """家族設定を保存して family_id を返す
 
    family の例:
        {"members": ["papa", "mama", "child"], "child_ages": [3],
         "has_car": True, "favorite_character": "仮面ライダー",
         "favorite_genres": ["character", "show"]}
    リストはカンマ区切りの文字列にして保存する。
    family_id を渡すと、その家族を上書きする(あとから変更する時用)。
    """
    values = (
        _list_to_text(family.get("members")),          # ["papa","mama"] → "papa,mama"
        _list_to_text(family.get("child_ages")),       # [3, 6] → "3,6"
        1 if family.get("has_car") else 0,
        family.get("favorite_character") or None,
        _list_to_text(family.get("favorite_genres")),
        _now(),
    )
    conn = get_connection()
    try:                                  # 失敗しても必ず接続を閉じる
        cursor = conn.cursor()
        if family_id is None:
            cursor.execute("""
                INSERT INTO families
                    (members, child_ages, has_car, favorite_character, favorite_genres, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, values)
            family_id = cursor.lastrowid     
        else:
            cursor.execute("""
                UPDATE families
                SET members = ?, child_ages = ?, has_car = ?, favorite_character = ?,
                    favorite_genres = ?, updated_at = ?
                WHERE id = ?
            """, values + (family_id,))
        conn.commit()
    finally:
        conn.close()
    return family_id


def get_family(family_id: int):
    """家族設定を取得する(見つからなければ None)
 
    カンマ区切りで保存した項目はリストに戻して返す。child_ages は数値のリストになる。
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM families WHERE id = ?", (family_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    f = dict(row)
    f["members"] = _text_to_list(f["members"])
    f["child_ages"] = [int(a) for a in _text_to_list(f["child_ages"])]   # "3,6" → [3, 6]
    f["favorite_genres"] = _text_to_list(f["favorite_genres"])
    f["has_car"] = bool(f["has_car"])
    return f