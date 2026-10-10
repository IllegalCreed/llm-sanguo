#!/usr/bin/env python3
"""从 AA 数据重建快照 CSV。

两种用法:
  python3 scripts/rebuild_snapshot.py --leaderboard <leaderboard.html> <out_csv>
      解析 https://artificialanalysis.ai/leaderboards/models 页面内嵌的
      全库 JSON（推荐：一次 curl 即全量，含 II/成本/速度/延迟）
  python3 scripts/rebuild_snapshot.py --pages <pages_dir> <out_csv>
      解析 sitemap 抓取的模型页本地 HTML（备选：无榜单页时）

数值一律取页面内嵌 JSON 的 authority 值：II 为浮点，估算加 *；
成本/速度/延迟/总耗时分别对应 intelligenceIndexCostPerTask /
medianOutputTokensPerSecond / medianTimeToFirstTokenSeconds /
medianEndToEndResponseTimeSeconds。人工手填一律作废。
"""
import csv
import glob
import os
import re
import sys


def esc(key):
    return key


def get(span, key):
    m = re.search(
        r'\\?"%s\\?"\s*:\s*(\\?"(?:[^"\\]|\\.)*?\\?"|[0-9.eE+-]+|true|false|null)' % key,
        span)
    if not m:
        return None
    v = m.group(1)
    if v.endswith('"'):
        return v.strip('\\"').replace('\\"', '"')
    return v


def iter_objects(html, start_pos):
    """按 '{\\"slug\\":' 边界切分对象，返回各对象文本片段。"""
    pat = re.compile(r'\{\\"slug\\":')
    starts = [m.start() for m in pat.finditer(html, start_pos)]
    # 数组结束于首个 '}]' 结构处
    objs = []
    for i, s in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else s + 20000
        objs.append(html[s:end])
    return objs


def parse_leaderboard(html):
    """解析榜单页两个内嵌数组：注册表（含 creator）与评测表（含全部指标）。"""
    # 找到带 intelligenceIndex 的 models 数组（评测表）
    metrics_pos = None
    for m in re.finditer(r'\\?"models\\?"\s*:\s*\[', html):
        if 'intelligenceIndex' in html[m.start():m.start() + 6000]:
            metrics_pos = m.end()
            break
    if metrics_pos is None:
        sys.exit("未找到评测表数组")

    rows = []
    for obj in iter_objects(html, metrics_pos):
        slug = get(obj, 'slug')
        name = get(obj, 'name')
        if not slug or not name or '\\"]' in name:
            continue
        # 数组尾部会带上下文残留，遇到 releaseSlug 之类的注册表对象则跳过
        rows.append({
            'slug': slug, 'name': name,
            'creator': get(obj, 'modelCreatorName'),
            'deprecated': get(obj, 'deprecated') == 'true',
            'ctx': get(obj, 'contextWindowTokens'),
            'ii': get(obj, 'intelligenceIndex'),
            'est': get(obj, 'intelligenceIndexIsEstimated') == 'true',
            'cost': get(obj, 'intelligenceIndexCostPerTask'),
            'speed': get(obj, 'medianOutputTokensPerSecond'),
            'ttft': get(obj, 'medianTimeToFirstTokenSeconds'),
            'total': get(obj, 'medianEndToEndResponseTimeSeconds'),
        })
        if slug and name and get(obj, 'contextWindowTokens') is None and \
                get(obj, 'intelligenceIndex') is None and get(obj, 'releaseSlug'):
            rows.pop()  # 注册表残留对象
    return rows


def fmt_ctx(v):
    if not v or v in ('null', '--'):
        return '--'
    n = float(v)
    for div, suf in [(1e6, 'M'), (1e3, 'k')]:
        if n >= div and n % div == 0:
            return f"{int(n // div)}{suf}"
    return v


def fmt_num(v, digits=1, prefix=''):
    if v is None or v in ('null', ''):
        return '--'
    try:
        return f"{prefix}{float(v):.{digits}f}"
    except ValueError:
        return '--'


def main():
    args = sys.argv[1:]
    if args and args[0] == '--leaderboard':
        html = open(args[1], encoding='utf-8', errors='ignore').read()
        records = parse_leaderboard(html)
    elif args and args[0] == '--pages':
        records = [parse_page(p) for p in sorted(glob.glob(os.path.join(args[1], '*.html')))]
        records = [r for r in records if r]
        for r in records:
            r.setdefault('creator', None)
            r.setdefault('cost', None)
            r.setdefault('speed', None)
            r.setdefault('ttft', None)
            r.setdefault('total', None)
    else:
        sys.exit(__doc__)

    out_csv = args[-1]
    header = ['model', 'context_window', 'creator', 'intelligence_index',
              'cost_per_task_usd', 'median_tokens_per_s',
              'latency_first_chunk_s', 'total_response_s', 'further_analysis', 'source']

    def ii_str(r):
        if r['ii'] is None or r['ii'] == 'null':
            return '--'
        return fmt_num(r['ii'], 1) + ('*' if r['est'] else '')

    rows = []
    for r in sorted(records, key=lambda r: -(float(r['ii']) if r['ii'] not in (None, 'null') else -1)):
        rows.append({
            'model': r['name'],
            'context_window': fmt_ctx(r['ctx']),
            'creator': r.get('creator') or '--',
            'intelligence_index': ii_str(r),
            'cost_per_task_usd': fmt_num(r.get('cost'), 2, '$'),
            'median_tokens_per_s': fmt_num(r.get('speed'), 1),
            'latency_first_chunk_s': fmt_num(r.get('ttft'), 2),
            'total_response_s': fmt_num(r.get('total'), 2),
            'further_analysis': 'Model Providers',
            'source': f"https://artificialanalysis.ai/models/{r['slug']}",
        })

    with open(out_csv, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    scored = sum(1 for r in rows if r['intelligence_index'] != '--')
    print(f"models: {len(rows)} (scored {scored}) -> {out_csv}")


# ---- 页面模式（备选）的解析，保留原实现 ----

def nearest_before(window, key):
    ms = list(re.finditer(
        r'\\?"%s\\?"\s*:\s*("(?:[^"\\]|\\.)*"|true|false|null|[0-9.eE+-]+)' % key,
        window))
    if not ms:
        return None
    return ms[-1].group(1).strip('"').replace('\\"', '"')


def parse_page(path):
    html = open(path, encoding='utf-8', errors='ignore').read()
    m = re.search(r'\\?"intelligenceIndex\\?"\s*:\s*([0-9.eE+-]+|null)', html)
    if not m:
        return None
    ii = None if m.group(1) == 'null' else float(m.group(1))
    sm = re.search(r'\\?"slug\\?"\s*:\s*\\?"%s\\?"' % re.escape(os.path.basename(path)[:-5]), html)
    if sm:
        after = html[sm.end():sm.end() + 12000]
        m2 = re.search(r'\\?"intelligenceIndex\\?"\s*:\s*([0-9.eE+-]+|null)', after)
        if m2:
            ii = None if m2.group(1) == 'null' else float(m2.group(1))
    t = re.search(r'<title>([^<]+)</title>', html)
    name = t.group(1).split(' - Intelligence')[0] if t else ''
    return {'slug': os.path.basename(path)[:-5], 'name': name or None,
            'ii': ii, 'est': False, 'ctx': None}


if __name__ == '__main__':
    main()
