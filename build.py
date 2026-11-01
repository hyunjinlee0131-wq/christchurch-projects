import json, glob, collections, sys
feats = [x for g in sorted(glob.glob('items_*.json')) for x in json.load(open(g, encoding='utf-8')).get('features', [])]
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
       f'Source: https://opendata-christchurchcity.hub.arcgis.com (Hub search API, pulled 2026-11-01). '
       f'{len(seen)} datasets. Datasets tagged with more than one category appear under each one.', '']
order = sorted(groups, key=lambda c: (c == 'Uncategorised', c))
out.append('## Summary\n\n| Category | Datasets |\n|---|---|')
out += [f'| {c} | {len(groups[c])} |' for c in order]
for c in order:
    out += ['', f'## {c} ({len(groups[c])})', '', '| Dataset | Type | Description |', '|---|---|---|']
    for t, ty, i, s in sorted(groups[c], key=lambda r: r[0].lower()):
        out.append(f'| [{t}](https://opendata-christchurchcity.hub.arcgis.com/datasets/{i}) | {ty} | {s.replace("|", "/")} |')
open(sys.argv[1], 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print(len(seen), len(groups))
