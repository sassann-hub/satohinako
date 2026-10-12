"""
app.py — おやこでかけ（福岡版）の画面（Streamlit）

【起動方法】
  streamlit run app.py
  → ブラウザで画面が開く

【Streamlit のしくみ（これだけ知っておくと読みやすい）】
  Streamlit は、ボタンを押す・日付を変えるなど「画面で何か操作するたびに、
  このファイルを上から下まで全部もう一度実行」して、画面を作り直す。
  なので、このファイルは「上から順に画面に並べるもの」を書いていくだけでよい。

【画面の流れ】
  1. 上部：アプリ名 → その下に「福岡市」と「家族設定」ボタン → 今の家族設定
  2. 日付を入力
  3. 家族に合うイベントを最大5件表示（絞り込みは filter.py が行う）
"""

from datetime import datetime     # 日付・時刻を扱う
from html import escape           # 文字を安全に HTML に埋め込むための関数（後述）
from textwrap import dedent       # 文字列の先頭の空白（字下げ）を取る
from zoneinfo import ZoneInfo     # 「日本時間」を指定するため

import streamlit as st            # 画面を作るライブラリ。以降 st.〇〇 で使う

# 自分たちのファイルから、使う関数・値を読み込む
from filter import find_events    # 絞り込み
from database import init_db       # さっさんの database.py：テーブルを作る
from family_profile import GENRE_LABELS, MEMBER_LABELS, load_profile, save_profile, summarize  # 家族設定

# ---------------------------------------------------------------
# データベースの値（英語のコード） → 画面に出す日本語（schema.sql の CHECK と同じ値）
# ---------------------------------------------------------------
INDOOR_LABELS = {"indoor": "屋内", "outdoor": "屋外", "both": "屋内・屋外"}

WEEKDAYS = "月火水木金土日"  # 曜日の表示用。weekday() は 月曜=0 … 日曜=6 なので、その番号で1文字取り出す

# ブラウザのタブに出るタイトルとアイコン。layout="centered"：画面の中央に寄せて表示
st.set_page_config(page_title="おやこでかけ（福岡版）", page_icon="🎈", layout="centered")

# ---------------------------------------------------------------
# 見た目（CSS）
#   スマホ画面くらいの幅・クリーム色の背景・オレンジのアクセントにする。
#   st.markdown(..., unsafe_allow_html=True) で、HTML/CSS を画面に直接入れられる。
#   dedent()：字下げがあると Streamlit が「コード」として表示してしまうので、字下げを取る
# ---------------------------------------------------------------
st.markdown(
    dedent("""
    <style>
    .stApp { background: #FAF6EF; }
    .block-container { max-width: 480px; padding-top: 2rem; }
    .app-title { color: #E8743B; font-weight: 800; font-size: 1.6rem; margin: 0; }
    .area-chip {
        display: inline-block; padding: 2px 12px; border-radius: 999px;
        border: 1px solid #E8743B; color: #E8743B; font-size: .85rem; font-weight: 700;
    }
    .family-line { color: #555; font-size: .9rem; margin: .25rem 0 .75rem; }
    .card {
        background: #fff; border-radius: 16px; padding: 1rem 1.1rem;
        border: 1px solid #EADFCF; margin-bottom: .8rem;
    }
    .card h4 { margin: 0 0 .35rem; font-size: 1.05rem; color: #333; }
    .card .meta { color: #555; font-size: .88rem; line-height: 1.7; }
    .tag {
        display: inline-block; padding: 1px 9px; margin-right: 4px; border-radius: 999px;
        font-size: .78rem; font-weight: 700; background: #F3ECE1; color: #6B5B45;
    }
    .card a { color: #E8743B; font-weight: 700; text-decoration: none; }
    /* 家族設定の窓：クリーム色の背景 */
    div[role="dialog"] { background: #FAF6EF; }
    /* 年齢の選択欄：オレンジの太い枠（画像の「3歳」の欄） */
    div[role="dialog"] [data-baseweb="select"] > div {
        border: 2px solid #E8743B; border-radius: 999px; font-weight: 700;
    }
    .age-hint { color: #E8743B; font-weight: 700; font-size: .9rem; margin: -.4rem 0 .6rem; }
    </style>
    """),
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------
# 家族設定の画面（「家族設定」ボタンを押すと、画面の上に小さな窓が開く。保存したら閉じる）
@st.dialog("家族設定")
def family_dialog(current):
    st.caption("保存してあとから変更OK")  # 小さめの文字で説明を出す

    # まだ家族設定がない（None）ときは、よくある形を最初の値にしておく
    current = current or {"members": ["papa", "mama", "child"], "child_ages": [3], "has_car": True,
                          "favorite_character": "", "favorite_genres": []}

    # 子どもの人数は st.session_state（画面を作り直しても消えないメモ帳）に覚えておく。
    #   「＋追加」を押すと1人増える。窓を開いた最初の1回だけ、保存済みの人数を入れる
    if "child_count" not in st.session_state:
        st.session_state["child_count"] = max(len(current["child_ages"]), 1)

    # ---- メンバー：丸いボタンを複数選べる（selection_mode="multi"）＋「＋追加」 ----
    #   options はデータベースに入れる英語のコード（papa など）、
    #   format_func で画面には日本語（パパ など）を見せる
    col_members, col_add = st.columns([3, 1], vertical_alignment="bottom")
    with col_members:
        members = st.pills(
            "メンバー", list(MEMBER_LABELS), selection_mode="multi",
            default=current["members"], format_func=lambda m: MEMBER_LABELS[m],
        )
    with col_add:
        # 「＋追加」：子どもを1人増やす（最大5人）。押すと窓の中だけ作り直され、年齢の欄が1つ増える
        if st.button("＋追加", help="子どもを追加"):
            st.session_state["child_count"] = min(st.session_state["child_count"] + 1, 5)

    members = members or []  # 何も選ばないと None になるので [] にする

    # ---- 子どもの年齢：「子ども」を選んでいるときだけ出す ----
    ages = []
    if "child" in members:
        count = st.session_state["child_count"]
        for i in range(count):  # i = 0, 1, 2, ...
            # 保存済みの年齢があればそれを、なければ 3歳 を最初の値にする
            saved = current["child_ages"][i] if i < len(current["child_ages"]) else 3
            label = "子どもの年齢" if count == 1 else f"子どもの年齢（{i + 1}人目）"
            ages.append(
                st.selectbox(
                    label,
                    options=list(range(0, 13)),            # 0〜12歳から選ぶ
                    index=saved,                           # 最初に選ばれている年齢（0歳が0番目なので年齢＝番号）
                    format_func=lambda a: f"{a}歳",         # 画面には「3歳」の形で見せる
                    key=f"age_{i}",                        # 同じ見た目の欄が複数あるので名前で区別
                )
            )
        st.markdown('<p class="age-hint">▲ ここに年齢を入れる</p>', unsafe_allow_html=True)

    # ---- 車：あり／なし のどちらか1つ。horizontal=True で横並び ----
    car = st.radio("車", ["あり", "なし"], horizontal=True, index=0 if current["has_car"] else 1)

    # ---- 好きなキャラ：自由に入力（空でもよい） ----
    character = st.text_input("好きなキャラ", value=current["favorite_character"],
                              placeholder="例：仮面ライダー")

    # ---- 好きなジャンル：複数選べる（空でもよい）。メンバーと同じく、保存は英語のコード ----
    genres = st.pills(
        "好きなジャンル", list(GENRE_LABELS), selection_mode="multi",
        default=current["favorite_genres"], format_func=lambda g: GENRE_LABELS[g],
    )

    # ---- 保存ボタン。押されたときだけ True になって、中の処理が動く ----
    if st.button("保存", type="primary", use_container_width=True):
        # family_profile.py の save_profile() で保存（中で database.py の save_family() を使う）
        save_profile(
            {
                "members": members,
                "child_ages": [int(a) for a in ages],  # 「子ども」を選んでいなければ空のリスト
                "has_car": car == "あり",               # "あり" なら True
                "favorite_character": character.strip(),  # 前後の空白を取る
                "favorite_genres": genres or [],
            }
        )
        del st.session_state["child_count"]  # 次に窓を開いたとき、保存した人数から始めるため消す
        st.rerun()  # 画面を最初から作り直す → 窓が閉じて、保存した設定で表示される


# ---------------------------------------------------------------
# 表示用の小さな関数
# ---------------------------------------------------------------
def format_date(iso_text):
    """'2026-10-17' → '10月17日(土)' に変える"""
    d = datetime.strptime(iso_text, "%Y-%m-%d").date()  # 文字 → 日付 に変換
    return f"{d.month}月{d.day}日({WEEKDAYS[d.weekday()]})"


def format_period(event):
    """開催日の表示を作る。

      1日だけ（end_date が start_date と同じ）  → 「10月17日(土)」
      期間あり                                  → 「10月17日(土)〜10月18日(日)」
      終わりなし（end_date が空 ＝ 毎日など）    → 「10月17日(土)〜」
      time_text（時間）があれば後ろに付ける      → 「10月17日(土)　10:00〜12:00」
    """
    start = format_date(event["start_date"])
    end = event["end_date"]
    if end is None or end == "":
        text = f"{start}〜"
    elif end == event["start_date"]:
        text = start
    else:
        text = f"{start}〜{format_date(end)}"

    if event["time_text"]:
        text += "　" + escape(event["time_text"])
    return text


def format_fee(fee):
    """料金（数字・円）を表示用の文字にする。0 → 「無料」、1500 → 「1,500円」"""
    if fee == 0:
        return "無料"
    return f"{fee:,}円"  # :, は3けたごとにカンマを入れる書き方


def reservation_flags(reservation):
    """予約区分（3択）を、画像の「予約 有・無」「チケット 有・無」の2つに分ける。

    データベースの reservation  →  予約      チケット
      'required'（予約が必要）  →  あり      なし
      'ticket'（チケットが必要）→  なし      あり
      'none'（どちらも不要）    →  なし      なし
    空(NULL＝わからない)のときは None を返し、画面には出さない。
    """
    if not reservation:
        return None
    return {
        "予約": "あり" if reservation == "required" else "なし",
        "チケット": "あり" if reservation == "ticket" else "なし",
    }


def event_card(event):
    """イベント1件分のカード（HTML）を作る。

    表示する項目（画像の順番）：名前 → 会場名 → 屋内・屋外 → チケット有・無 → 予約有・無 → 料金 → URL
    escape()：データベースの文字に < や > が入っていても、HTML として動かないように変換する。
              （サイトから取ってきた文字をそのまま画面に入れると、表示が崩れたり危険なことがあるため）
    """
    lines = []

    # 会場名（会場内の場所があれば後ろに付ける。例：「福岡市科学館（1F ○○エリア）」）と日付
    venue = escape(event["venue"])
    if event["place_detail"]:
        venue += f"（{escape(event['place_detail'])}）"
    lines.append(f"📍 {venue}")
    lines.append(f"📅 {format_period(event)}")

    # 屋内・屋外
    if event["indoor"]:
        lines.append(f"🏠 {INDOOR_LABELS.get(event['indoor'], '')}")

    # チケット有・無、予約有・無
    flags = reservation_flags(event["reservation"])
    if flags:
        lines.append(f"🎫 チケット：{flags['チケット']}")
        lines.append(f"📝 予約：{flags['予約']}")

    # 料金：予約やチケットが必要なときだけ出す（打ち合わせで決定）。fee が空(NULL)なら出さない
    if event["reservation"] in ("required", "ticket") and event["fee"] is not None:
        lines.append(f"💴 料金：{format_fee(event['fee'])}")

    # URL：http(s) で始まるちゃんとしたURLのときだけリンクにする
    link = ""
    url = event["url"] or ""
    if url.startswith(("http://", "https://")):
        # target="_blank"：新しいタブで開く
        link = f'<div style="margin-top:.4rem"><a href="{escape(url)}" target="_blank">くわしく見る（URL）→</a></div>'

    # 部品をつなげて1枚のカードにする（"<br>".join：リストの文字を改行でつなぐ）
    return (
        '<div class="card">'
        f"<h4>{escape(event['title'])}</h4>"
        f'<div class="meta">{"<br>".join(lines)}</div>'
        f"{link}"
        "</div>"
    )


# ===============================================================
# ここから下が、実際に画面に並べる部分（上から順に表示される）
# ===============================================================

# データベースの準備：schema.sql からテーブルを作る（すでにあれば何もしない）
#   @st.cache_resource を付けた関数は、アプリを起動している間に1回だけ実行される
@st.cache_resource
def prepare_db():
    init_db()


prepare_db()

# 保存済みの家族設定を読み込む（まだなければ None）
profile = load_profile()

# 初めて開いたとき（家族設定がまだない）は、設定画面を自動で1回だけ開く
#   st.session_state：画面を作り直しても消えずに残る「メモ帳」。
#   "asked_family" を書いておくことで、2回目以降は自動で開かないようにしている
if profile is None and not st.session_state.get("asked_family"):
    st.session_state["asked_family"] = True
    family_dialog(None)

# ---- 1. 上部 ----
# 1行目：アプリ名
st.markdown('<p class="app-title">おやこでかけ</p>', unsafe_allow_html=True)

# 2行目：左に「福岡市」、その右に「家族設定」ボタン（横に2列。幅の比率 1:2）
col_area, col_family = st.columns([1, 2], vertical_alignment="center")
with col_area:
    st.markdown('<span class="area-chip">福岡市</span>', unsafe_allow_html=True)
with col_family:
    if st.button("👪 家族設定"):  # 押されたら家族設定の窓を開く
        family_dialog(profile)

# 今の家族設定を一行で表示（例：パパ・ママ・子ども3歳 ／ 車あり）
st.markdown(f'<div class="family-line">{escape(summarize(profile))}</div>', unsafe_allow_html=True)

# ---- 2. 日付を入力 ----
today = datetime.now(ZoneInfo("Asia/Tokyo")).date()  # 日本時間の今日
# 日付の入力欄。最初は今日、今日より前は選べない（min_value）
target_date = st.date_input("日付を入力", value=today, min_value=today, format="YYYY/MM/DD")

# ---- 3. 結果 ----
# filter.py で、日付と家族設定に合うイベントを最大5件もらう
events = find_events(target_date, profile)

if profile is None:
    # 家族設定がないときは、日付だけで絞った結果になることを伝える
    st.info("家族設定を保存すると、家族に合うイベントだけに絞り込みます。")

if not events:
    # 0件のとき
    st.write("この日に合うイベントは見つかりませんでした。別の日付を選んでみてください。")
else:
    st.caption(f"{format_date(target_date.isoformat())}　家族に合うイベント {len(events)}件")
    # 1件ずつカードにして表示
    for event in events:
        st.markdown(event_card(event), unsafe_allow_html=True)