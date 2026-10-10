"""Bounded domain-only witnesses using cached public provider snapshots.

Assumes TCP, no process match, no already-known private/Telegram destination IP.
Does not simulate GEOSITE/GEOIP, DNS, wildcard dialects, or a complete client.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def matches(host, entry, behavior):
    if behavior == 'domain':
        if entry.startswith('+.'):
            domain = entry[2:]
            return host == domain or host.endswith('.' + domain)
        if entry.startswith('.'):
            return host.endswith(entry)
        return host == entry
    if behavior == 'classical':
        kind, _, value = entry.partition(',')
        value = value.split(',')[0]
        if kind == 'DOMAIN':
            return host == value
        if kind == 'DOMAIN-SUFFIX':
            return host == value or host.endswith('.' + value)
        if kind == 'DOMAIN-KEYWORD':
            return value in host
    return False


def main():
    snapshot = json.loads((ROOT / 'reports/current-rule-snapshot.json').read_text(encoding='utf-8'))
    providers = {name: json.loads((ROOT / '.cache/rule-review' / (name+'.json')).read_text(encoding='utf-8'))
                 for name, meta in snapshot['providers'].items() if 'error' not in meta}
    hosts = ['chatgpt.com', 'api.openai.com', 'claude.ai', 'gemini.google.com',
        'challenges.cloudflare.com', 'auth0.com', 'js.stripe.com', 'apps.mzstatic.com',
        'guzzoni.apple.com', 'www.bing.com', 'cn.bing.com', 'byteoversea.com', 'trae.ai',
        'marscode.com', 'tiktok.com', 'capcut.com', 'telegram.org', 'web.telegram.org',
        't.me', 'api.telegram.org', 'linux.do', 'open.cd', 'clash.razord.top',
        'yacd.haishan.me', 'rfc.uhdnow.com', 'dl.google.com', 'mtalk.google.com',
        'app-measurement.com', 'googletagmanager.com', 'steamcontent.com',
        'store.steampowered.com', 'steamcommunity.com', 'bilibili.com', 'apple.com',
        'icloud.com', 'youtube.com', 'netflix.com', 'alibabacloud.com', 'qoder.com',
        'minimax.io', 'cdn.example.edgesuite.net', 'router.asus.com', 'doh.pub', 'dns.alidns.com',
        'fonts.googleapis.com', 'fonts.gstatic.com', 'www.apple.com', 'api.smoot.apple.com',
        'gateway.icloud.com', 'appleid.apple.com']
    witnesses = []
    for host in hosts:
        hits = []
        for index, rule in enumerate(snapshot['rules'], 1):
            parts = rule.split(',')
            evidence = []
            if parts[0] == 'RULE-SET' and parts[1] in providers:
                evidence = [entry for entry in providers[parts[1]] if matches(host, entry, snapshot['providers'][parts[1]]['behavior'])]
            elif parts[0] in ('DOMAIN', 'DOMAIN-SUFFIX') and matches(host, ','.join(parts[:2]), 'classical'):
                evidence = [','.join(parts[:2])]
            if evidence:
                hits.append(dict(position=index, rule=rule, evidence=evidence))
        witnesses.append(dict(domain=host, first_domain_match=hits[0] if hits else None, all_domain_matches=hits))
    # Semantic intersections between AI suffixes and classical TikTok rules.
    ai_tiktok = [e for e in providers['ai'] if e.startswith('+.') and any(
        matches(e[2:], t, 'classical') for t in providers['TikTok'])]
    result = dict(snapshot_time=snapshot['checked_at'],
        scope=__doc__, ai_tiktok_domain_witnesses=ai_tiktok, witnesses=witnesses)
    (ROOT / 'reports/domain-witnesses.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for witness in witnesses:
        hit = witness['first_domain_match']
        print(witness['domain'], '=>', str(hit['position']) if hit else '?',
              hit['evidence'] if hit else 'No supported domain match')
    print('AI/TikTok:', ai_tiktok)


if __name__ == '__main__':
    main()
