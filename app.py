from flask import Flask, request, jsonify, render_template_string
import psycopg2
import psycopg2.pool
from urllib.parse import unquote, quote

app = Flask(__name__)

COCKROACH_CONN = 'postgresql://atharva:S6_SVxa9zMtqQifpCajH5Q@coupang-sitemap-24437.j77.aws-ap-south-1.cockroachlabs.cloud:26257/custom_urls?sslmode=require'

connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, COCKROACH_CONN)

def normalize_url(url):
    """Generate multiple URL variants to match against DB"""
    url = url.strip()
    variants = set()
    variants.add(url)
    try:
        decoded = unquote(url)
        variants.add(decoded)
        re_encoded = quote(decoded, safe=':/?=&%-.~_@!$&\'()*+,;')
        variants.add(re_encoded)
        re_encoded_upper = re_encoded.upper()
        variants.add(re_encoded_upper)
    except Exception:
        pass
    return list(variants)

HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Coupang TW · Sitemap URL Checker</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --red: #E52027;
    --red-dark: #C41A20;
    --red-light: #FFF0F0;
    --green: #00A650;
    --green-light: #F0FFF7;
    --gray-50: #F8F8F8;
    --gray-100: #F0F0F0;
    --gray-200: #E0E0E0;
    --gray-400: #AAAAAA;
    --gray-600: #767676;
    --gray-900: #111111;
    --white: #FFFFFF;
    --border: #EEEEEE;
    --shadow: 0 2px 8px rgba(0,0,0,0.08);
  }

  body {
    background: var(--gray-50);
    color: var(--gray-900);
    font-family: 'Noto Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px;
    line-height: 1.5;
    min-height: 100vh;
  }

  .site-header { background: var(--red); padding: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.15); }
  .header-inner { max-width: 1200px; margin: 0 auto; padding: 12px 24px; display: flex; align-items: center; gap: 16px; }
  .logo-text { font-size: 22px; font-weight: 700; color: var(--white); letter-spacing: -0.5px; }
  .logo-divider { width: 1px; height: 20px; background: rgba(255,255,255,0.4); }
  .logo-subtitle { font-size: 13px; color: rgba(255,255,255,0.85); font-weight: 500; }

  .breadcrumb { background: var(--white); border-bottom: 1px solid var(--border); padding: 8px 0; }
  .breadcrumb-inner { max-width: 1200px; margin: 0 auto; padding: 0 24px; display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--gray-600); }
  .breadcrumb-inner span { color: var(--gray-400); }

  .main { max-width: 1200px; margin: 0 auto; padding: 24px; }

  .page-title { margin-bottom: 20px; }
  .page-title h1 { font-size: 20px; font-weight: 700; color: var(--gray-900); margin-bottom: 4px; }
  .page-title p { font-size: 13px; color: var(--gray-600); }

  .card { background: var(--white); border: 1px solid var(--border); border-radius: 4px; padding: 24px; margin-bottom: 16px; box-shadow: var(--shadow); }
  .card-title { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--gray-600); margin-bottom: 12px; }

  textarea {
    width: 100%; background: var(--white); border: 1px solid var(--gray-200); border-radius: 4px;
    color: var(--gray-900); font-family: 'Noto Sans', monospace; font-size: 13px; padding: 12px;
    resize: vertical; min-height: 140px; outline: none; transition: border-color 0.15s; line-height: 1.6;
  }
  textarea:focus { border-color: var(--red); box-shadow: 0 0 0 2px rgba(229,32,39,0.1); }
  textarea::placeholder { color: var(--gray-400); }

  .actions { display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap; align-items: center; }

  .btn { font-family: 'Noto Sans', sans-serif; font-weight: 600; font-size: 14px; padding: 10px 24px; border-radius: 4px; border: none; cursor: pointer; transition: all 0.15s; display: inline-flex; align-items: center; gap: 6px; }
  .btn-primary { background: var(--red); color: var(--white); }
  .btn-primary:hover { background: var(--red-dark); }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-secondary { background: var(--white); border: 1px solid var(--gray-200); color: var(--gray-600); }
  .btn-secondary:hover { border-color: var(--gray-400); color: var(--gray-900); }
  .btn-outline-red { background: var(--white); border: 1px solid var(--red); color: var(--red); }
  .btn-outline-red:hover { background: var(--red-light); }

  .stats-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
  .stat { background: var(--white); border: 1px solid var(--border); border-radius: 4px; padding: 20px 24px; display: flex; align-items: center; gap: 16px; box-shadow: var(--shadow); }
  .stat-icon { width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
  .stat.total .stat-icon { background: var(--gray-100); }
  .stat.found .stat-icon { background: var(--green-light); }
  .stat.notfound .stat-icon { background: var(--red-light); }
  .stat-number { font-size: 28px; font-weight: 700; line-height: 1; margin-bottom: 2px; }
  .stat.total .stat-number { color: var(--gray-900); }
  .stat.found .stat-number { color: var(--green); }
  .stat.notfound .stat-number { color: var(--red); }
  .stat-label { font-size: 12px; color: var(--gray-600); font-weight: 500; }

  .results-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 10px; }
  .filter-tabs { display: flex; border: 1px solid var(--border); border-radius: 4px; overflow: hidden; }
  .tab { font-family: 'Noto Sans', sans-serif; font-size: 13px; font-weight: 500; padding: 7px 16px; border: none; background: var(--white); color: var(--gray-600); cursor: pointer; transition: all 0.15s; border-right: 1px solid var(--border); }
  .tab:last-child { border-right: none; }
  .tab.active { background: var(--red); color: var(--white); font-weight: 600; }
  .tab:hover:not(.active) { background: var(--gray-50); color: var(--gray-900); }

  .result-item { border: 1px solid var(--border); border-radius: 4px; padding: 14px 16px; margin-bottom: 8px; display: flex; align-items: center; gap: 14px; background: var(--white); }
  .result-item.found { border-left: 3px solid var(--green); }
  .result-item.notfound { border-left: 3px solid var(--red); }
  .status-badge { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 2px; flex-shrink: 0; text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap; }
  .found .status-badge { background: var(--green-light); color: var(--green); border: 1px solid rgba(0,166,80,0.2); }
  .notfound .status-badge { background: var(--red-light); color: var(--red); border: 1px solid rgba(229,32,39,0.2); }
  .result-content { flex: 1; min-width: 0; }
  .result-url { font-size: 13px; color: var(--gray-900); word-break: break-all; margin-bottom: 3px; font-family: monospace; }
  .result-meta { font-size: 12px; color: var(--gray-600); }
  .result-meta.found-meta { color: var(--green); }

  .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.4); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }

  #results-section { display: none; }
  .empty-state { text-align: center; padding: 40px; color: var(--gray-400); font-size: 14px; }

  .site-footer { background: var(--white); border-top: 1px solid var(--border); padding: 16px 24px; text-align: center; font-size: 12px; color: var(--gray-600); margin-top: 40px; }

  @media (max-width: 600px) {
    .stats-row { grid-template-columns: 1fr; }
    .main { padding: 16px; }
  }
</style>
</head>
<body>

<header class="site-header">
  <div class="header-inner">
    <span class="logo-text">coupang</span>
    <div class="logo-divider"></div>
    <span class="logo-subtitle">Sitemap URL Checker</span>
  </div>
</header>

<div class="breadcrumb">
  <div class="breadcrumb-inner">
    KuPeng Homepage <span>›</span> Tools <span>›</span> Sitemap URL Checker
  </div>
</div>

<main class="main">
  <div class="page-title">
    <h1>Sitemap URL Checker</h1>
    <p>Check if URLs exist across all 297 Coupang Taiwan sitemaps — 14.3M+ URLs indexed</p>
  </div>

  <div class="card">
    <div class="card-title">Paste URLs to check — one per line</div>
    <textarea id="url-input" placeholder="https://www.tw.coupang.com/categories/example&#10;https://www.tw.coupang.com/products/example&#10;..."></textarea>
    <div class="actions">
      <button class="btn btn-primary" id="check-btn" onclick="checkURLs()">Check URLs</button>
      <button class="btn btn-secondary" onclick="clearAll()">Clear</button>
      <button class="btn btn-outline-red" id="export-btn" onclick="exportCSV()" style="display:none">Export CSV</button>
    </div>
  </div>

  <div id="results-section">
    <div class="stats-row">
      <div class="stat total">
        <div class="stat-icon">🔍</div>
        <div class="stat-info">
          <div class="stat-number" id="stat-total">0</div>
          <div class="stat-label">Total Checked</div>
        </div>
      </div>
      <div class="stat found">
        <div class="stat-icon">✅</div>
        <div class="stat-info">
          <div class="stat-number" id="stat-found">0</div>
          <div class="stat-label">Found in Sitemap</div>
        </div>
      </div>
      <div class="stat notfound">
        <div class="stat-icon">❌</div>
        <div class="stat-info">
          <div class="stat-number" id="stat-notfound">0</div>
          <div class="stat-label">Not Found</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="results-header">
        <div class="card-title" style="margin:0">Results</div>
        <div class="filter-tabs">
          <button class="tab active" onclick="filterResults('all', this)">All</button>
          <button class="tab" onclick="filterResults('found', this)">Found</button>
          <button class="tab" onclick="filterResults('notfound', this)">Not Found</button>
        </div>
      </div>
      <div id="results-list"></div>
    </div>
  </div>
</main>

<footer class="site-footer">
  Coupang TW · Sitemap URL Checker · 297 Sitemaps · 14.3M+ URLs · Powered by Botpresso
</footer>

<script>
  let allResults = [];

  async function checkURLs() {
    const raw = document.getElementById('url-input').value.trim();
    if (!raw) return;
    const urls = raw.split('\\n').map(u => u.trim()).filter(u => u.length > 0);
    if (urls.length === 0) return;
    const btn = document.getElementById('check-btn');
    btn.innerHTML = '<span class="spinner"></span> Checking...';
    btn.disabled = true;
    try {
      const res = await fetch('/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls })
      });
      const data = await res.json();
      allResults = data.results;
      renderResults(allResults);
    } catch(e) {
      alert('Error: ' + e.message);
    } finally {
      btn.innerHTML = 'Check URLs';
      btn.disabled = false;
    }
  }

  function renderResults(results) {
    const found = results.filter(r => r.found).length;
    document.getElementById('stat-total').textContent = results.length;
    document.getElementById('stat-found').textContent = found;
    document.getElementById('stat-notfound').textContent = results.length - found;
    document.getElementById('results-section').style.display = 'block';
    document.getElementById('export-btn').style.display = 'inline-flex';
    const list = document.getElementById('results-list');
    if (results.length === 0) { list.innerHTML = '<div class="empty-state">No results</div>'; return; }
    list.innerHTML = results.map(r => `
      <div class="result-item ${r.found ? 'found' : 'notfound'}" data-status="${r.found ? 'found' : 'notfound'}">
        <div class="status-badge">${r.found ? 'Found' : 'Not Found'}</div>
        <div class="result-content">
          <div class="result-url">${escapeHtml(r.url)}</div>
          <div class="result-meta ${r.found ? 'found-meta' : ''}">${r.found ? '📁 ' + r.sitemap_source : 'Not found in any of the 297 sitemaps'}</div>
        </div>
      </div>
    `).join('');
  }

  function filterResults(type, tabEl) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tabEl.classList.add('active');
    const filtered = type === 'all' ? allResults : type === 'found' ? allResults.filter(r => r.found) : allResults.filter(r => !r.found);
    const list = document.getElementById('results-list');
    if (filtered.length === 0) { list.innerHTML = '<div class="empty-state">No results for this filter</div>'; return; }
    list.innerHTML = filtered.map(r => `
      <div class="result-item ${r.found ? 'found' : 'notfound'}">
        <div class="status-badge">${r.found ? 'Found' : 'Not Found'}</div>
        <div class="result-content">
          <div class="result-url">${escapeHtml(r.url)}</div>
          <div class="result-meta ${r.found ? 'found-meta' : ''}">${r.found ? '📁 ' + r.sitemap_source : 'Not found in any of the 297 sitemaps'}</div>
        </div>
      </div>
    `).join('');
  }

  function exportCSV() {
    if (!allResults.length) return;
    const rows = [['URL', 'Status', 'Sitemap Source']];
    allResults.forEach(r => rows.push([r.url, r.found ? 'Found' : 'Not Found', r.sitemap_source || '']));
    const csv = rows.map(r => r.map(c => `"${c}"`).join(',')).join('\\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'sitemap_check_results.csv';
    a.click();
  }

  function clearAll() {
    document.getElementById('url-input').value = '';
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('export-btn').style.display = 'none';
    allResults = [];
  }

  function escapeHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/check', methods=['POST'])
def check():
    data = request.get_json()
    urls = data.get('urls', [])
    if not urls:
        return jsonify({'results': []})

    conn = connection_pool.getconn()
    try:
        cur = conn.cursor()
        results = []
        for url in urls:
            url = url.strip()
            if not url:
                continue

            variants = normalize_url(url)
            found_row = None

            for variant in variants:
                cur.execute(
                    'SELECT sitemap_source FROM sitemap_urls WHERE url = %s LIMIT 1',
                    (variant,)
                )
                row = cur.fetchone()
                if row:
                    found_row = row
                    break

            if found_row:
                results.append({'url': url, 'found': True, 'sitemap_source': found_row[0]})
            else:
                results.append({'url': url, 'found': False, 'sitemap_source': ''})

        cur.close()
    finally:
        connection_pool.putconn(conn)

    return jsonify({'results': results})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
