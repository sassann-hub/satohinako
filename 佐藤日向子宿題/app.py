from http.server import SimpleHTTPRequestHandler, HTTPServer
import webbrowser

HTML_CONTENT = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>おやこでかけ</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Hiragino Sans", Meiryo, sans-serif; }
    body { background-color: #e5e5e5; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
    
    .mobile-container {
      width: 100%;
      max-width: 390px;
      height: 844px;
      background-color: #faf5ee;
      border-radius: 36px;
      box-shadow: 0 12px 30px rgba(0,0,0,0.15);
      display: flex;
      flex-direction: column;
      position: relative;
      overflow: hidden;
      border: 8px solid #333;
    }

    .app-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 20px 10px; }
    .logo { font-size: 20px; color: #dd7a53; font-weight: 800; }
    .bell-btn { width: 36px; height: 36px; background: #fff; border: 1px solid #eee; border-radius: 50%; color: #777; cursor: pointer; display: flex; align-items: center; justify-content: center; }

    /* 地域と学年選択のピル */
    .filter-selector-row {
      display: flex;
      gap: 8px;
      padding: 0 20px 10px;
    }
    .select-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #fff;
      border: 1px solid #e0dad0;
      border-radius: 20px;
      padding: 6px 14px;
      font-size: 12px;
      font-weight: 700;
      color: #333;
      cursor: pointer;
    }
    .select-pill i:first-child { color: #dd7a53; }
    .select-pill .arrow { font-size: 10px; color: #888; }

    .search-bar {
      margin: 0 20px 12px;
      background: #fff;
      border-radius: 12px;
      padding: 9px 14px;
      display: flex;
      align-items: center;
      gap: 10px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .search-bar input { border: none; outline: none; width: 100%; font-size: 13px; background: transparent; }

    /* 水平スクロールタブ */
    .pill-scroll {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding: 0 20px 8px;
      scrollbar-width: none;
    }
    .pill-scroll::-webkit-scrollbar { display: none; }

    .tab-pill, .category-pill, .age-pill {
      white-space: nowrap;
      border: 1px solid #e2ddd6;
      background: #fff;
      border-radius: 20px;
      padding: 5px 14px;
      font-size: 12px;
      font-weight: 600;
      color: #666;
      cursor: pointer;
    }
    /* 学年タブ（緑系アクセント） */
    .age-tabs .age-pill.active { background-color: #3d7a5a; color: #fff; border-color: #3d7a5a; }
    /* 日付タブ（オレンジ系アクセント） */
    .date-tabs .tab-pill.active { background-color: #dd7a53; color: #fff; border-color: #dd7a53; }
    /* カテゴリタブ（深緑系アクセント） */
    .category-tags .category-pill.active { background-color: #2b5e58; color: #fff; border-color: #2b5e58; }

    .content-area { flex: 1; overflow-y: auto; padding: 6px 20px 80px; }
    .list-summary { font-size: 12px; color: #777; margin-bottom: 10px; font-weight: 600; }
    
    .cards-list { display: flex; flex-direction: column; gap: 12px; }
    .event-card {
      background: #fff;
      border-radius: 16px;
      padding: 12px;
      display: flex;
      gap: 12px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .card-thumb {
      width: 72px;
      height: 72px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      flex-shrink: 0;
    }
    .thumb-cyan { background-color: #cce9e4; }
    .thumb-purple { background-color: #e5daf3; }
    .thumb-orange { background-color: #fce1d4; }

    .card-body { display: flex; flex-direction: column; gap: 4px; flex: 1; }
    .card-title { font-size: 13px; font-weight: 700; color: #222; line-height: 1.35; }
    .card-info { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #777; }
    
    .tag-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
    .badge {
      background-color: #f7e6cd;
      color: #8c6031;
      font-size: 10px;
      font-weight: 600;
      padding: 2px 7px;
      border-radius: 6px;
    }
    /* 学年バッジ */
    .badge-grade {
      background-color: #e3f2e9;
      color: #2a6d45;
    }

    .floating-action { position: absolute; bottom: 20px; left: 0; right: 0; display: flex; justify-content: center; }
    .filter-action-btn {
      background: #2f2a26;
      color: #fff;
      border: none;
      border-radius: 30px;
      padding: 11px 26px;
      font-size: 13px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }
  </style>
</head>
<body>
  <div class="mobile-container">
    <header class="app-header">
      <h1 class="logo">おやこでかけ</h1>
      <button class="bell-btn"><i class="fa-regular fa-bell"></i></button>
    </header>

    <!-- 地域と学年の選択ボタン -->
    <div class="filter-selector-row">
      <button class="select-pill">
        <i class="fa-solid fa-location-dot"></i>
        <span>長崎市</span>
        <i class="fa-solid fa-chevron-down arrow"></i>
      </button>
      <button class="select-pill">
        <i class="fa-solid fa-graduation-cap"></i>
        <span>小学1〜4年生</span>
        <i class="fa-solid fa-chevron-down arrow"></i>
      </button>
    </div>

    <!-- 検索バー -->
    <div class="search-bar">
      <i class="fa-solid fa-magnifying-glass" style="color: #999;"></i>
      <input type="text" placeholder="エリア・キーワードで探す" />
    </div>

    <!-- 小学生1〜4年の学年別切り替えタブ -->
    <div class="pill-scroll age-tabs">
      <button class="age-pill active">小1〜小4すべて</button>
      <button class="age-pill">小学1年生</button>
      <button class="age-pill">小学2年生</button>
      <button class="age-pill">小学3年生</button>
      <button class="age-pill">小学4年生</button>
    </div>

    <!-- 日付フィルター -->
    <div class="pill-scroll date-tabs">
      <button class="tab-pill active">今日</button>
      <button class="tab-pill">明日</button>
      <button class="tab-pill">今週末</button>
      <button class="tab-pill">来週</button>
    </div>

    <!-- カテゴリフィルター -->
    <div class="pill-scroll category-tags">
      <button class="category-pill active">自由研究</button>
      <button class="category-pill">花火大会</button>
      <button class="category-pill">ヒーロー・特撮</button>
      <button class="category-pill">お化け屋敷</button>
    </div>

    <main class="content-area">
      <div class="list-summary">今週末・小1〜小4対象のイベント 3件</div>

      <div class="cards-list">
        <!-- カード 1 -->
        <article class="event-card">
          <div class="card-thumb thumb-cyan">🧊</div>
          <div class="card-body">
            <h2 class="card-title">液体窒素で冷熱実験!バナナで釘打ちに挑戦</h2>
            <div class="card-info">
              <i class="fa-regular fa-calendar"></i>
              <span>8/23(土) 10:00〜16:00</span>
            </div>
            <div class="card-info">
              <i class="fa-solid fa-location-dot"></i>
              <span>セブン-イレブン記念館 ・ 1.2km</span>
            </div>
            <div class="tag-row">
              <span class="badge badge-grade">小2〜小4おすすめ</span>
              <span class="badge">自由研究</span>
              <span class="badge">屋内</span>
            </div>
          </div>
        </article>

        <!-- カード 2 -->
        <article class="event-card">
          <div class="card-thumb thumb-purple">👻</div>
          <div class="card-body">
            <h2 class="card-title">きもだめしナイト 〜両国 江戸怪談ミュージアム〜</h2>
            <div class="card-info">
              <i class="fa-regular fa-calendar"></i>
              <span>8/13(水)〜8/15(金) 18:00〜21:00</span>
            </div>
            <div class="card-info">
              <i class="fa-solid fa-location-dot"></i>
              <span>すみだ江戸怪談ミュージアム ・ 3.4km</span>
            </div>
            <div class="tag-row">
              <span class="badge badge-grade">小1から参加OK</span>
              <span class="badge">お化け屋敷</span>
              <span class="badge">期間限定</span>
            </div>
          </div>
        </article>

        <!-- カード 3 -->
        <article class="event-card">
          <div class="card-thumb thumb-orange">🎆</div>
          <div class="card-body">
            <h2 class="card-title">アミュプラザ長崎 夏まつり花火</h2>
            <div class="card-info">
              <i class="fa-regular fa-calendar"></i>
              <span>8/20(木) 19:30〜19:50</span>
            </div>
            <div class="card-info">
              <i class="fa-solid fa-location-dot"></i>
              <span>アミュプラザ長崎 ・ 2.5km</span>
            </div>
            <div class="tag-row">
              <span class="badge badge-grade">全学年対象</span>
              <span class="badge">花火</span>
              <span class="badge">屋外</span>
            </div>
          </div>
        </article>
      </div>
    </main>

    <div class="floating-action">
      <button class="filter-action-btn">
        <i class="fa-solid fa-sliders"></i>
        <span>絞り込む</span>
      </button>
    </div>
  </div>

  <script>
    // タブの選択切り替え
    document.querySelectorAll('.pill-scroll').forEach(container => {
      const buttons = container.querySelectorAll('button');
      buttons.forEach(btn => {
        btn.addEventListener('click', () => {
          buttons.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
        });
      });
    });
  </script>
</body>
</html>
"""

class CustomHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode("utf-8"))

if __name__ == "__main__":
    port = 8000
    server = HTTPServer(("localhost", port), CustomHandler)
    print(f"サーバーを起動しました: http://localhost:{port}")
    webbrowser.open(f"http://localhost:{port}")
    server.serve_forever()