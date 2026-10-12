# おやこでかけ（福岡版）

## ファイル（すべて同じフォルダに置く）

| ファイル | 担当 | 役割 |
|---|---|---|
| `app.py` | けーや | 画面（Streamlit）。家族設定ボタン → 保存、日付を入力 → 最大5件を表示 |
| `profile.py` | けーや | 家族設定の保存・読み込み（database.py の `save_family` / `get_family` を使う） |
| `filter.py` | けーや | 日付・子どもの年齢で絞り込み、好きなキャラ → 好きなジャンルの順に並べて最大5件（database.py の `get_events_on` を使う） |
| `weather.py` | けーや | 天気API（Open-Meteo、APIキー不要）。取れないときは天気なしで動く |
| `database.py` | さっさん | DB操作（※ 動かない箇所を修正済み。【修正】で検索） |
| `schema.sql` | さっさん | テーブル設計（※ families テーブルの名前・列名を修正済み） |
| `seed_sample.py` | — | 動作確認用のサンプルイベント登録（crawler.py ができたら不要） |

## 動かし方

```
pip install -r requirements.txt
python seed_sample.py              # サンプルを入れる（crawler.py で登録済みなら不要）
python -m streamlit run app.py     # ブラウザで http://localhost:8501 が開く
```

データベースは `data/oyako.db` に作られる。表の形を変えたときは `data` フォルダごと消してから実行し直す。

## さっさんの database.py / schema.sql の修正点

| ファイル | 場所 | 修正前 → 修正後 | 理由 |
|---|---|---|---|
| schema.sql | families の表 | `keywords` → `families` | database.py は families を使っている |
| schema.sql | 列名 | `child_age` → `child_ages`、`update_at` → `updated_at` | database.py の列名に合わせる |
| database.py | `init_db()` | `open("SCHEMA_PATH")` → `open(SCHEMA_PATH)` | "" があると SCHEMA_PATH という名前のファイルを探してしまう |
| database.py | `_now()` | `%Y-%M-%d` → `%Y-%m-%d` | %M は「分」。月は %m |
| database.py | `upsert_event()` | `event("venue", "")` → `event.get("venue", "")` | 辞書は () で呼べない（エラー） |
| database.py | `upsert_event()` | `event.get("end_date", "")` → `event.get("end_date")` | "" で保存すると、日付の比較で必ず外れてしまう |
| database.py | `get_events_on()` | `> =` → `>=` | 間に空白があると SQL のエラー |
| database.py | `save_family()` | 新規登録のとき `family_id = cursor.lastrowid` を追加 | 今までは None を返していた |

## crawler.py で登録するときの決めごと（filter.py / app.py が前提にしていること）

- 1日だけのイベントは `end_date` に `start_date` と同じ日付を入れる（空だと「終わりなし」として毎日出てしまう）
- `reservation`：`required`（予約あり）／ `ticket`（チケット要）／ `none`（不要）
- `indoor`：`indoor` ／ `outdoor` ／ `both`（雨の日は outdoor を後ろに並べる）
- `fee`：円の数字。0 は「無料」と表示。予約・チケットが必要なときだけ画面に出す
- `character`：キャラ名（家族設定の「好きなキャラ」と文字が含まれるかで比べる）
- `age_min` / `age_max` / `fee` / `character` などは空(NULL)でもよい（空なら外さない）

## 今回やっていないこと

- 車の有無：保存はするが、events に「車が必要か」の列がないので絞り込みには使っていない
