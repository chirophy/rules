"""Read public provider contents; report exact textual overlap, never rewrite policy."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import datetime
import hashlib
import json
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools'))
import yaml


def main():
    cfg = yaml.safe_load((ROOT / 'rules-baseline.yaml').read_text(encoding='utf-8-sig'))
    def fetch(item):
        name, p = item
        try:
            for attempt in range(2):
                try:
                    with urllib.request.urlopen(p['url'], timeout=25) as response:
                        raw = response.read()
                    break
                except Exception:
                    if attempt == 1:
                        raise
            text = raw.decode('utf-8-sig')
            if p.get('format', 'yaml') == 'yaml':
                entries = yaml.safe_load(text)['payload']
            else:
                entries = [s.strip() for s in text.splitlines() if s.strip() and not s.lstrip().startswith(('#', '//'))]
            unique = set(entries)
            return name, {'entries': len(entries), 'unique': len(unique), 'duplicates': len(entries) - len(unique),
                          'sha256': hashlib.sha256(raw).hexdigest(), 'behavior': p['behavior']}, unique
        except Exception as e:
            return name, {'error': str(e)}, set()
    with ThreadPoolExecutor(max_workers=6) as pool:
        data = list(pool.map(fetch, cfg['rule-providers'].items()))
    sets = {n: s for n, m, s in data if 'error' not in m}
    overlaps = []
    for a, b in [('google', 'proxy'), ('gfw', 'proxy'), ('icloud', 'apple'), ('BanAD', 'BanProgramAD'), ('private', 'direct')]:
        if a in sets and b in sets:
            overlaps.append({'a': a, 'b': b, 'exact_intersection': len(sets[a] & sets[b]),
                             'a_only': len(sets[a] - sets[b]), 'b_only': len(sets[b] - sets[a])})
    report = {'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'method': 'Exact payload string equality only; suffix/wildcard/CIDR semantic coverage is not inferred. Remote snapshots do not prove permanent redundancy.',
              'local_rules': len(cfg['rules']), 'local_unique_rules': len(set(cfg['rules'])),
              'providers': {n: m for n, m, s in data}, 'overlaps': overlaps}
    (ROOT / 'reports').mkdir(exist_ok=True)
    (ROOT / 'reports' / 'rule-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'providers_ok': len(sets), 'providers_total': len(data), 'overlaps': overlaps}, ensure_ascii=False))


if __name__ == '__main__':
    main()
