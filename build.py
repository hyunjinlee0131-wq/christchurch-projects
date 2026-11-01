"""Build datasets.md: every CCC open dataset, grouped by portal category. Usage: build.py [out.md]"""
import collections, sys
from datetime import date

from ccc_data import catalog

feats = catalog()
fix = {'Utilties': 'Utilities', 'Green Assets': 'Green Asset'}
def norm(c):
    parts = [p.strip() for p in c.split('/') if p.strip() and p.strip() != 'Categories']
    return ' / '.join(fix.get(p, p) for p in parts)
groups = collections.defaultdict(list)
seen = set()
for f in feats:
    p = f['properties']
    key = (p['title'], f['id'])
    if key in seen: continue
    seen.add(key)
    cats = {norm(c) for c in (p.get('categories') or [])} or {'Uncategorised'}
    cats = {c for c in cats if not any(o != c and o.startswith(c + ' / ') for o in cats)}  # keep most specific
    snip = ' '.join((p.get('snippet') or '').split())
    if len(snip) > 110: snip = snip[:107] + '...'
    for c in cats:
        groups[c].append((p['title'], p['type'], f['id'], snip))
out = ['# CCC Spatial Open Data: Datasets by Category', '',
       f'Source: https://opendata-christchurchcity.hub.arcgis.com (Hub search API, pulled {date.today()}). '
       f'{len(seen)} datasets. Datasets tagged with more than one category appear under each one.', '']
order = sorted(groups, key=lambda c: (c == 'Uncategorised', c))
out.append('## Summary\n\n| Category | Datasets |\n|---|---|')
out += [f'| {c} | {len(groups[c])} |' for c in order]
for c in order:
    out += ['', f'## {c} ({len(groups[c])})', '', '| Dataset | Type | Description |', '|---|---|---|']
    for t, ty, i, s in sorted(groups[c], key=lambda r: r[0].lower()):
        out.append(f'| [{t}](https://opendata-christchurchcity.hub.arcgis.com/datasets/{i}) | {ty} | {s.replace("|", "/")} |')
open(sys.argv[1] if len(sys.argv) > 1 else 'datasets.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
print(len(seen), len(groups))
