# =============================================================
# extract.py — 文字から項目を読み取る(おやこでかけ)
# ルール: このファイルはネットにつながない。文字を受け取って、値を返すだけ
#         (ページを取ってきて、どこを読むかを決めるのは crawler.py)
# 試し方: python -c "from extract import find_ages; print(find_ages('5歳~小学6年生'))"  → (5, 12)
# =============================================================
import re
import unicodedata
from datetime import date, timedelta
 
 
# ---------- 言葉のリストと判定 ----------
 
# タイトルにこれがあれば対象外(お店の宣伝・もう申し込めないもの・終わった報告)
NOT_EVENT_WORDS = ["キャンペーン", "プレゼント", "チラシ", "セール", "クーポン", "ポイント", "割引",
                   "受付終了", "開催終了", "イベントレポート", "活動報告"]
# タイトルの言葉でジャンルを決める(上から順に調べる)
GENRE_WORDS = {
    "character": ["仮面ライダー", "スーパー戦隊", "プリキュア", "アンパンマン", "ウルトラマン", "ポケモン", "しまじろう"],
    "experience": ["体験", "工作", "実験", "講座", "教室", "ワークショップ"],
    "show": ["ショー", "ステージ", "上映", "プラネタリウム"],
    "seasonal": ["ハロウィン", "クリスマス", "まつり", "祭"],
    "play": ["遊び場", "あそび", "遊具"],
}
# タイトルと詳細にこれが1つもなければ、子ども向けではないとみなす(キャラクターものは子ども向けに入れる)
KIDS_WORDS = ["子ども", "こども", "子供", "お子さま", "キッズ", "親子", "家族", "小学", "幼児", "未就学",
              "ショー", "遊"] + GENRE_WORDS["character"]
 
 
def norm(text):
    """全角→半角(NFKC)にし、空白・改行を1つにまとめる。「［受付終了］」→「[受付終了]」、「～」→「~」"""
    text = unicodedata.normalize("NFKC", text).replace("〜", "~")
    return " ".join(text.split())
 
 
def is_excluded(title):
    """タイトルに対象外の言葉(NOT_EVENT_WORDS)が1つでもあれば True"""
    return any(w in title for w in NOT_EVENT_WORDS)
 
 
def is_for_kids(text):
    """子ども向けの言葉(KIDS_WORDS)が1つでもあれば True"""
    return any(w in text for w in KIDS_WORDS)
 
 
# ---------- 日付 ----------
 
def to_date(y, m, d):
    """数字から date を作る。ありえない日付(2/30 など)なら None"""
    try:
        return date(int(y), int(m), int(d))
    except ValueError:
        return None
 
 
def find_ymd(text):
    """文の中の最初の「2026.10.03」「2026/10/03」を date にする。なければ None"""
    m = re.search(r"(\d{4})[./](\d{1,2})[./](\d{1,2})", text)
    if m is None:
        return None
    return to_date(m.group(1), m.group(2), m.group(3))
 
 
def kagakukan_dates(title, text, today):
    """科学館の (開始日, 終了日)。
    ・タイトルの先頭に「10/25(日)」があれば、その日だけ。一覧の日付はシリーズ全体の期間で
      (おもちゃ病院なら 2026.04.26~2027.03.28)、毎日やっているわけではないため。
      月日だけなので今年とみなし、半年以上前になるなら来年とみなす
    ・一覧の日付: 「2026.11.28 土曜日」→ その日だけ / 「2026.10.03 ~10.31」→ 10/3~10/31 /
      「2026.10.01 ~ 毎日開催」→ 10/1から終わりなし / 「~ 毎日開催」→ 今日から終わりなし / 「~」→ 不明"""
    m = re.match(r"(\[[^\]]*\]\s*)*(\d{1,2})/(\d{1,2})", title)  # 先頭の[追加募集中]などは飛ばす
    if m:
        d = to_date(today.year, m.group(2), m.group(3))
        if d and d < today - timedelta(days=180):
            d = to_date(today.year + 1, m.group(2), m.group(3))
        return d, d
 
    if "~" not in text:  # 1日だけ
        start = find_ymd(text)
        return start, start
    left, right = text.split("~", 1)
    start = find_ymd(left)
    end = find_ymd(right)  # 「~2027.03.17」のように年つき
    if end is None and start is not None:  # 「~10.31」のように年なし → 開始日の年
        md = re.search(r"(\d{1,2})\.(\d{1,2})", right)
        if md:
            end = to_date(start.year, md.group(1), md.group(2))
            if end and end < start:  # 「2026.12.20 ~01.10」のように年をまたぐ
                end = to_date(start.year + 1, md.group(1), md.group(2))
    if start is None and "毎日" in right:
        start = today
    return start, end
 
 
def aeon_dates(text, today):
    """イオンの (開始日, 終了日)。
    「2026/10/06 (火) - 2026/10/12 (月)」→ 10/6~10/12 /
    「2026/10/31 (土) -」「2026/11/07 (土)」→ その日だけ / 「毎日」→ 今日から終わりなし"""
    if "毎日" in text:
        return today, None
    found = re.findall(r"\d{4}/\d{1,2}/\d{1,2}", text)
    if not found:
        return None, None
    return find_ymd(found[0]), find_ymd(found[-1])
 
 
# ---------- 年齢・料金・予約・ジャンル ----------
 
def find_ages(text):
    """対象年齢 (下限, 上限)。わからなければ (None, None)
    「5歳~小学6年生」→ (5, 12)、「小学生」→ (6, 12)、「3歳以上」→ (3, None)、「どなたでも」→ (None, None)
    小学○年生は ○+5 ~ ○+6 歳とみなす"""
    if "どなたでも" in text:  # 「どなたでも ※未就学児は要保護者同伴」を 3~6歳にしないため
        return None, None
    ages = [int(a) for a in re.findall(r"(\d{1,2})歳", text)]
    for g in re.findall(r"小学(\d)", text):
        ages += [int(g) + 5, int(g) + 6]
    for g in re.findall(r"~(\d)年", text):  # 「小学1~6年」の 6
        ages.append(int(g) + 6)
    if "未就学" in text or "幼児" in text:
        ages += [3, 6]
    if not ages and "小学生" in text:
        ages = [6, 12]
    if not ages:
        return None, None
    if "以上" in text:
        return min(ages), None
    return min(ages), max(ages)
 
 
def get_fee(fee_text, title):
    """料金(円)。「無料」→ 0、「2,000円」→ 2000、わからない → None
    「無料。ただし入場料が必要」は無料ではないので None。タイトルに「無料」があれば 0(無料屋外遊び場など)"""
    if "入場料" in fee_text:
        return None
    if "無料" in fee_text or "無料" in title:
        return 0
    m = re.search(r"(\d[\d,]*)円", fee_text)
    if m:
        return int(m.group(1).replace(",", ""))
    return None
 
 
def get_reservation(text):
    """予約区分。ticket=整理券 / none=不要 / required=必要 / None=書いていない
    「事前申込不要」は required の言葉も含むので、none を先に調べる"""
    text = text.replace("申し込み", "申込").replace("申込み", "申込")
    if "整理券" in text:
        return "ticket"
    if re.search(r"(申込|予約)(は)?不要|自由参加|直接お越し", text):
        return "none"
    if re.search(r"事前申込|要予約|予約制|抽選", text):
        return "required"
    return None
 
 
def get_genre(title):
    """タイトルの言葉でジャンルを決める。どれにも当たらなければ None"""
    for genre, words in GENRE_WORDS.items():
        for w in words:
            if w in title:
                return genre
    return None