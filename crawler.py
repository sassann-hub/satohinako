# =============================================================
# crawler.py — イベント情報の収集(おやこでかけ)
# ページの取得は W2 の fetch_page をそのまま使い、
# 2会場(福岡市科学館・イオンモール福岡)の「どこを読むか」と流れを足したもの
# 分担: ネットにつなぐのはこのファイルだけ。
#       文字から日付・年齢などを読み取る部分は extract.py(文字を受け取って値を返すだけ)
#
# 流れ: ① 一覧ページで「タイトル・日付・リンク」を読む
#       ② 終わったもの・対象外のものは、ここで落とす(詳細ページは取りに行かない)
#       ③ 残ったものだけ詳細ページを開き、「対象年齢・料金・予約」を読む
#       ④ DBに保存
# 実行: python crawler.py --dry-run   (DBに一切触らず、結果を表示するだけ)
#       python crawler.py             (本番)
#
# 空欄(None)の意味 ※filter.py と同じ意味で使うこと
#   end_date が None          … 終わりが決まっていない(毎日開催など)
#   age_min / age_max が None … 年齢の条件が書いていない → 年齢では除外しない
#   fee が None               … 料金がわからない(0 は無料)
#   reservation が None       … 予約について書いていない
# =============================================================
import argparse
import time
from datetime import date, datetime
from typing import Optional
from urllib.parse import urljoin
 
import requests
from bs4 import BeautifulSoup
 
import database
from extract import norm, is_excluded, is_for_kids, kagakukan_dates, aeon_dates
from extract import find_ages, get_fee, get_reservation, get_genre
 
HEADERS = {"User-Agent": "OyakoDekakeBot/0.1 (Tech0 Educational Purpose)"}
WAIT_SECONDS = 3  # 1ページごとに待つ秒数(相手のサーバーに負担をかけない)
 
KAGAKUKAN_LIST = "https://www.fukuokacity-kagakukan.jp/activity/inSession.html"
AEON_LIST = "https://fukuoka.aeonmall.jp/event"
 
 
# ---------- ① 取得(W2 の fetch_page をそのまま使う) ----------
 
def fetch_page(url: str, timeout: int = 10) -> Optional[str]:
    """指定URLのHTMLを取得する。失敗時は None"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return resp.text
    except requests.RequestException as e:
        print(f"  取得エラー: {e}")
        return None
 
 
def get_soup(url):
    """fetch_page で取ったHTMLを BeautifulSoup にする。失敗したら None
    (W2 の parse_html はページ全体を文字の行にするので、どの文字がどの欄かが分からなくなる。
     今回は欄ごとに値を取りたいので、BeautifulSoup のままタグを指定して読む)"""
    html = fetch_page(url)
    if html is None:
        return None
    return BeautifulSoup(html, "html.parser")
 
 
# ---------- ② 会場ごとの読み方(W2 に足した部分) ----------
 
def read_kagakukan_list(today):
    """科学館の一覧 → [(タイトル, 開始日, 終了日, URL), ...]
    1件ずつ <div class="articleList"> の中の <a>。タイトルは class="title"、日付は class="date" """
    soup = get_soup(KAGAKUKAN_LIST)
    if soup is None:
        return []
    box = soup.find("div", class_="articleList")
    if box is None:
        return []
    items = []
    for a in box.find_all("a", href=True):
        title = norm(a.find(class_="title").get_text())
        start, end = kagakukan_dates(title, norm(a.find(class_="date").get_text()), today)
        items.append((title, start, end, urljoin(KAGAKUKAN_LIST, a["href"])))
    return items
 
 
def read_aeon_list(today):
    """イオンの一覧 → [(タイトル, 開始日, 終了日, URL), ...]
    1件ずつ <li class="result-box event">。タイトルは <p class="name">、日付は <p class="info">"""
    soup = get_soup(AEON_LIST)
    if soup is None:
        return []
    items = []
    for li in soup.find_all("li", class_="result-box"):
        a = li.find("a", href=True)
        title = norm(li.find("p", class_="name").get_text())
        start, end = aeon_dates(norm(li.find("p", class_="info").get_text()), today)
        items.append((title, start, end, urljoin(AEON_LIST, a["href"])))
    return items
 
 
def read_kagakukan_detail(url):
    """科学館の詳細 → {"対象", "料金", "予約", "本文"}。失敗したら None
    「開催概要」は <dl><dt>見出し</dt><dd>中身</dd></dl> の並びなので、{見出し: 中身} の辞書にして引く"""
    soup = get_soup(url)
    if soup is None:
        return None
    table = {}
    box = soup.find("div", class_="table")
    if box is not None:
        for dl in box.find_all("dl"):
            dt, dd = dl.find("dt"), dl.find("dd")
            if dt and dd:
                table[norm(dt.get_text())] = norm(dd.get_text(" "))
    main = soup.find("main")
    article = main.find("article") if main else None
    return {"対象": table.get("対象", ""), "料金": table.get("料金", ""), "予約": table.get("参加方法", ""),
            "本文": norm(article.get_text(" ")) if article else ""}
 
 
def read_aeon_detail(url):
    """イオンの詳細 → {"対象", "料金", "予約", "本文"}。失敗したら None
    <section class="event-detail-specs"> だけを読む(下の「最新のイベント」欄はほかのイベントなので読まない)。
    対象・料金の決まった欄はないので、その言葉を含む行を探す"""
    soup = get_soup(url)
    if soup is None:
        return None
    section = soup.find("section", class_="event-detail-specs")
    if section is None:
        return None
    lines = [norm(l) for l in section.get_text("\n").splitlines() if l.strip()]
    target = [l for l in lines if "対象" in l]
    fee = [l for l in lines if "料金" in l or "参加費" in l]
    return {"対象": " ".join(target), "料金": fee[0] if fee else "", "予約": " ".join(lines), "本文": " ".join(lines)}
 
 
# ---------- ③ 実行 ----------
 
SOURCES = [
    {"source": "kagakukan", "venue": "福岡市科学館", "city": "福岡市中央区", "indoor": "indoor"},
    {"source": "aeon_fukuoka", "venue": "イオンモール福岡", "city": "糟屋郡粕屋町", "indoor": "indoor"},
]
 
 
def collect_source(src, today, limit=None, dry_run=False):
    """1会場ぶん: 一覧 → 落とす → 詳細 → 保存。拾えた件数を返す"""
    print(f"■ {src['venue']}")
    if src["source"] == "kagakukan":
        items = read_kagakukan_list(today)
    else:
        items = read_aeon_list(today)
    print(f"  一覧 {len(items)} 件")
 
    count = 0
    for title, start, end, url in items:
        if is_excluded(title):
            print(f"  - 対象外の言葉: {title}")
            continue
        if start is None:
            print(f"  - 日付不明: {title}")
            continue
        if end is not None and end < today:
            print(f"  - 終了: {title}")
            continue
        if end is None or (end - start).days >= 31:  # いつでも行けるもの(毎日開催・長期)は「その日のイベント」ではない
            print(f"  - 毎日・長期開催: {title}")
            continue
        if limit is not None and count >= limit:
            break
 
        time.sleep(WAIT_SECONDS)
        if src["source"] == "kagakukan":
            detail = read_kagakukan_detail(url)
        else:
            detail = read_aeon_detail(url)
        if detail is None:
            print(f"  × 取得失敗: {url}")
            continue
        if not is_for_kids(title + detail["本文"]):
            print(f"  - 子ども向けの言葉なし: {title}")
            continue
 
        age_min, age_max = find_ages(detail["対象"])
        event = {
            "title": title, "start_date": start.isoformat(), "end_date": end.isoformat() if end else None,
            "time_text": None, "venue": src["venue"], "city": src["city"],
            "age_min": age_min, "age_max": age_max,
            "reservation": get_reservation(detail["予約"]), "deadline": None,
            "fee": get_fee(detail["料金"], title),
            "indoor": "outdoor" if "屋外" in title else src["indoor"],
            "character": None, "genre": get_genre(title),
            "url": url, "source": src["source"], "raw_text": detail["本文"],
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        if not dry_run:
            database.upsert_event(event)
        print(f"  ○ {event['start_date']}~{event['end_date']} {title}"
              f"(年齢 {age_min}-{age_max} / 料金 {event['fee']} / 予約 {event['reservation']} / {event['genre']})")
        count += 1
    return count
 
 
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="各会場で○にする件数の上限(お試し用)")
    parser.add_argument("--dry-run", action="store_true", help="DBに一切触らない(お試し)")
    args = parser.parse_args()
 
    if not args.dry_run:
        database.init_db()
    today = date.today()
    total = 0
    for src in SOURCES:
        total += collect_source(src, today, args.limit, args.dry_run)
 
    if args.dry_run:
        print(f"完了(お試し・DBには触っていません): {total} 件")
    else:
        print(f"完了: {total} 件(DB全体 {database.count_events()} 件)")
 
 
if __name__ == "__main__":
    main()
