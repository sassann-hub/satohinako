-- schema.sql
-- おやこでかけ データベース設計
-- 値が分からない場合はNULL

-- eventsテーブル（メイン）
-- UNIQUE 制約：同じ URL は重複して登録できない
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL,
    start_date   TEXT NOT NULL,
    end_date     TEXT,                   -- NULL = 終わりなし（毎日など）
    time_text    TEXT,
    venue        TEXT NOT NULL,          -- 会場の正式名に固定（取得元ごとに決まる）
    place_detail TEXT,                   -- 会場内の場所（1F ○○エリア）
    city         TEXT,
    age_min      INTEGER,
    age_max      INTEGER,
    reservation  TEXT CHECK (reservation IN ('required', 'ticket', 'none')),
    deadline     TEXT,                    -- YYYY-MM-DD
    fee          INTEGER,
    indoor       TEXT CHECK (indoor IN ('indoor', 'outdoor', 'both')),
    character    TEXT,
    genre        TEXT CHECK (genre IN ('character', 'experience', 'show', 'seasonal', 'play')),
    url          TEXT NOT NULL UNIQUE,
    source       TEXT NOT NULL,           -- kagakukan / aeon_fukuoka
    raw_text     TEXT,                    -- 抜き出す前の告知分すべて
    fetched_at   TEXT NOT NULL            -- YYYY-MM-DD HH:MM
);

-- familiesテーブル
CREATE TABLE IF NOT EXISTS families (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    members               TEXT NOT NULL,
    child_ages             TEXT NOT NULL,
    has_car               INTEGER NOT NULL DEFAULT 0,
    favorite_character    TEXT,
    favorite_genres       TEXT,
    updated_at             TEXT NOT NULL
);

-- インデックス作成（検索を高速化する）
CREATE INDEX IF NOT EXISTS idx_events  ON events (start_date, end_date);