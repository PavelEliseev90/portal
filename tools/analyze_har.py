import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

har_path = Path(r'c:\Users\p.eliseev\Desktop\ah.kors-group.com.har')
with har_path.open(encoding='utf-8') as f:
    har = json.load(f)

entries = har['log']['entries']
pages = har['log'].get('pages', [])
print('entries', len(entries))
print('pages', len(pages))
for p in pages:
    print('PAGE', p.get('title'), p.get('startedDateTime'), p.get('id'))
    pt = p.get('pageTimings', {})
    print('  onContentLoad', pt.get('onContentLoad'), 'onLoad', pt.get('onLoad'))

rows = []
for e in entries:
    req = e['request']
    res = e['response']
    t = e.get('timings', {})
    url = req.get('url', '')
    u = urlparse(url)
    path = u.path
    host = u.netloc
    content = res.get('content', {}) or {}
    size = content.get('size') or res.get('bodySize') or 0
    transfer = res.get('bodySize')
    if transfer is None or transfer < 0:
        transfer = res.get('_transferSize') or size or 0
    wait = t.get('wait') or 0
    receive = t.get('receive') or 0
    blocked = t.get('blocked') or 0
    total = e.get('time') or 0
    status = res.get('status')
    mime = (content.get('mimeType') or '').split(';')[0][:40]
    headers = {h['name'].lower(): h['value'] for h in res.get('headers', [])}
    rows.append({
        'method': req.get('method'),
        'host': host,
        'path': path[:120],
        'url_short': (host + path)[:140],
        'status': status,
        'mime': mime,
        'total_ms': round(total, 1),
        'wait_ms': round(wait, 1),
        'receive_ms': round(receive, 1),
        'blocked_ms': round(max(blocked, 0), 1),
        'size': size,
        'transfer': transfer if transfer and transfer > 0 else 0,
        'cache': headers.get('cache-control', '')[:60],
        'started': e.get('startedDateTime'),
    })

print('\n=== TOP 25 by total time ===')
for r in sorted(rows, key=lambda x: -x['total_ms'])[:25]:
    print(
        f"{r['total_ms']:8.0f} wait={r['wait_ms']:7.0f} recv={r['receive_ms']:6.0f} "
        f"{r['status']} {r['method']} {r['size']/1024:7.1f}KB {r['mime']:20} {r['url_short']}"
    )

print('\n=== TOP 15 by wait (TTFB) ===')
for r in sorted(rows, key=lambda x: -x['wait_ms'])[:15]:
    print(f"{r['wait_ms']:8.0f} total={r['total_ms']:7.0f} {r['status']} {r['method']} {r['url_short']}")

print('\n=== TOP 15 by size ===')
for r in sorted(rows, key=lambda x: -x['size'])[:15]:
    print(f"{r['size']/1024:8.1f}KB {r['total_ms']:7.0f}ms {r['mime']:20} {r['url_short']}")

print('\n=== BY MIME type ===')
by_mime = defaultdict(lambda: {'n': 0, 'size': 0, 'time': 0})
for r in rows:
    m = r['mime'] or 'unknown'
    by_mime[m]['n'] += 1
    by_mime[m]['size'] += r['size']
    by_mime[m]['time'] += r['total_ms']
for m, v in sorted(by_mime.items(), key=lambda x: -x[1]['size']):
    print(f"{v['n']:4} {v['size']/1024/1024:7.2f}MB time_sum={v['time']/1000:6.1f}s {m}")

print('\n=== BY HOST ===')
by_host = defaultdict(lambda: {'n': 0, 'size': 0, 'time': 0})
for r in rows:
    by_host[r['host']]['n'] += 1
    by_host[r['host']]['size'] += r['size']
    by_host[r['host']]['time'] += r['total_ms']
for h, v in sorted(by_host.items(), key=lambda x: -x[1]['time']):
    print(f"{v['n']:4} size={v['size']/1024/1024:6.2f}MB time_sum={v['time']/1000:6.1f}s {h}")

print('\n=== HTML / document ===')
for r in rows:
    if 'html' in r['mime'] or r['mime'] == 'text/html':
        print(
            f"{r['total_ms']:8.0f} wait={r['wait_ms']:7.0f} "
            f"size={r['size']/1024:7.1f}KB {r['status']} {r['url_short']}"
        )

print('\n=== STATIC without cache-control max-age ===')
static_ext = ('.js', '.css', '.woff', '.woff2', '.ttf', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico')
bad = []
for r in rows:
    p = r['path'].lower()
    if any(p.endswith(ext) or ext + '?' in p for ext in static_ext):
        cc = (r['cache'] or '').lower()
        if 'max-age' not in cc and 'immutable' not in cc:
            bad.append(r)
for r in sorted(bad, key=lambda x: -x['size'])[:20]:
    print(f"{r['size']/1024:7.1f}KB cache='{r['cache']}' {r['url_short']}")
print('bad_cache_count', len(bad))

print('\n=== STATUS ===')
print(Counter(r['status'] for r in rows))

summary = {
    'n': len(rows),
    'pages': [
        {k: p.get(k) for k in ('id', 'title', 'startedDateTime')}
        | {'timings': p.get('pageTimings', {})}
        for p in pages
    ],
    'top_time': sorted(rows, key=lambda x: -x['total_ms'])[:20],
    'top_wait': sorted(rows, key=lambda x: -x['wait_ms'])[:15],
    'top_size': sorted(rows, key=lambda x: -x['size'])[:15],
    'by_mime': dict(by_mime),
    'by_host': dict(by_host),
    'bad_cache_n': len(bad),
    'status': dict(Counter(r['status'] for r in rows)),
}
Path(r'd:\portal\.har_summary.json').write_text(
    json.dumps(summary, ensure_ascii=False, indent=2),
    encoding='utf-8',
)
print('wrote summary')
