"""Read current rendered policy and snapshot public providers for a bounded audit.

Domain examples are witnesses, not a replacement for a client routing engine.
No user proxy configuration or credentials are copied to the report.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import datetime
import hashlib
import ipaddress
import json
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools'))
import yaml


def main():
    cfg = yaml.safe_load((ROOT / '.cache/test-mihomo.yaml').read_text(encoding='utf-8'))
    folder = ROOT / '.cache/rule-review'
    folder.mkdir(exist_ok=True)

    def fetch(item):
        name, provider = item
        try:
            with urllib.request.urlopen(provider['url'], timeout=40) as response:
                raw = response.read()
            text = raw.decode('utf-8-sig')
            entries = yaml.safe_load(text)['payload'] if provider.get('format', 'yaml') == 'yaml' else [
                x.strip() for x in text.splitlines() if x.strip() and not x.lstrip().startswith(('#', '//'))]
            assert isinstance(entries, list) and all(isinstance(e, str) for e in entries)
            invalid = []
            if provider['behavior'] == 'ipcidr':
                for entry in entries:
                    try:
                        ipaddress.ip_network(entry, strict=False)
                    except ValueError:
                        invalid.append(entry)
            (folder / (name + '.json')).write_text(json.dumps(entries, ensure_ascii=False), encoding='utf-8')
            return name, entries, dict(url=provider['url'], behavior=provider['behavior'],
                entries=len(entries), unique=len(set(entries)), duplicates=len(entries)-len(set(entries)),
                invalid_cidrs=invalid, sha256=hashlib.sha256(raw).hexdigest())
        except Exception as exc:
            return name, [], {'error': str(exc), 'url': provider['url']}

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(fetch, cfg['rule-providers'].items()))
    sets = {name: set(entries) for name, entries, meta in results if 'error' not in meta}
    overlaps = []
    for i, a in enumerate(sets):
        for b in list(sets)[i+1:]:
            common = sets[a] & sets[b]
            if common:
                overlaps.append(dict(a=a, b=b, count=len(common), examples=sorted(common)[:12]))
    report = dict(checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Current Mihomo/Stash providers, exact text intersections only; no semantic equivalence inferred.',
        rules=cfg['rules'], providers={n: m for n, e, m in results}, overlaps=overlaps)
    (ROOT / 'reports/current-rule-snapshot.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
