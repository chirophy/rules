"""Static policy and reference checks; not a replacement for client import tests."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools'))
import yaml


class StrictLoader(yaml.SafeLoader):
    pass


def mapping(loader, node, deep=False):
    keys = [loader.construct_object(k, deep=deep) for k, v in node.value]
    assert len(keys) == len(set(keys)), 'Duplicate YAML key'
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def validate(cfg, baseline, platform):
    expected = ['RULE-SET,ai,🤖 AI' if r == 'RULE-SET,ai,LA-VMRack-三网' else r for r in baseline['rules']]
    expected.remove('RULE-SET,reject,🆎 AdBlock')
    assert set(cfg['rule-providers']) == set(baseline['rule-providers']) - {'reject'}
    assert all(g['name'] != '🆎 AdBlock' for g in cfg['proxy-groups'])
    if platform == 'stash':
        for name, provider in cfg['rule-providers'].items():
            assert provider['type'] == 'http', name
            assert provider['format'] == baseline['rule-providers'][name].get('format', 'yaml'), name
            assert provider['behavior'] == baseline['rule-providers'][name]['behavior'], name
            assert provider['url'] == baseline['rule-providers'][name]['url'], name
        assert cfg['dns']['follow-rule'] is True
        assert cfg['dns']['nameserver'] == ['https://dns.alidns.com/dns-query', 'https://doh.pub/dns-query']
        assert cfg['dns']['default-nameserver'] == ['223.5.5.5', '119.29.29.29']
        assert set(cfg['dns']) == {'follow-rule', 'default-nameserver', 'nameserver', 'fake-ip-filter', 'ipv6', 'proxy-server-nameserver', 'nameserver-policy'}
        assert cfg['dns']['fake-ip-filter'] == [v for v in baseline['dns']['fake-ip-filter'] if v != '*.msftconnecttest.com']
        assert cfg['mixed-port'] == 7890 and cfg['allow-lan'] is True
        assert cfg['external-controller'] == '0.0.0.0:9090'
        assert cfg['unified-delay'] is True and cfg['tcp-concurrent'] is True
    if platform == 'mihomo':
        assert cfg['dns']['direct-nameserver'] == ['https://dns.alidns.com/dns-query', 'https://doh.pub/dns-query']
        assert cfg['dns']['direct-nameserver-follow-policy'] is False
    assert cfg['ipv6'] is True and cfg['dns']['ipv6'] is True
    assert cfg['dns']['proxy-server-nameserver'] == cfg['dns']['nameserver'] == ['https://dns.alidns.com/dns-query', 'https://doh.pub/dns-query']
    assert cfg['dns']['nameserver-policy'] == {'geosite:geolocation-!cn': ['https://1.1.1.1/dns-query#🚀 节点选择', 'https://8.8.8.8/dns-query#🚀 节点选择']}
    assert not {'fallback', 'fallback-filter'} & cfg['dns'].keys()
    assert cfg['rules'] == expected, 'Routing policy changed'
    ai = next(g for g in cfg['proxy-groups'] if g['name'] == '🤖 AI')
    assert ai['type'] == 'select' and ai['proxies'] == ['LA-VMRack-三网', 'LA-DMIT', 'LA-Zgo']
    assert all(n.get('udp') is True for n in cfg['proxies']), 'Node UDP not enabled'
    names = [n['name'] for n in cfg['proxies']] + [g['name'] for g in cfg['proxy-groups']]
    assert len(names) == len(set(names)), 'Duplicate proxy/group name'
    known = set(names) | {'DIRECT', 'REJECT'}
    for g in cfg['proxy-groups']:
        assert g['proxies'], g['name']
        assert set(g['proxies']) <= known, g['name']
    for rule in cfg['rules']:
        parts = rule.split(',')
        target = parts[-2] if parts[-1] == 'no-resolve' else parts[-1]
        assert target in known, rule
        if parts[0] == 'RULE-SET':
            assert parts[1] in cfg['rule-providers'], rule
    groups = {g['name']: g for g in cfg['proxy-groups']}
    for name in ('🌍 国外媒体', '📲 电报信息'):
        assert groups[name]['proxies'] == ['🚀 节点选择', '♻️ 自动选择', '🎯 全球直连'] + [n['name'] for n in cfg['proxies']]
    tt = groups['🎵 TikTok']['proxies']
    assert tt[:3] == ['🇺🇸 美国-最优', '🇯🇵 日本-最优', '🚀 节点选择']
    assert tt[3:] and all(re.match(r'^(JP|LA|SJC|DLS)', n, re.I) for n in tt[3:])
    for name in ('Ⓜ️ 微软服务', '🍎 苹果服务', '🎮 Steam下载', '🎯 全球直连', '🐟 漏网之鱼'):
        original = next(g for g in baseline['proxy-groups'] if g['name'] == name)
        assert groups[name]['proxies'] == original['proxies']

    def visit(name, parents):
        assert name not in parents, 'Group cycle: ' + name
        for child in groups.get(name, {}).get('proxies', []):
            if child in groups:
                visit(child, parents | {name})
    for name in groups:
        visit(name, set())


def main():
    baseline = yaml.load((ROOT / 'rules-baseline.yaml').read_text(encoding='utf-8-sig'), Loader=StrictLoader)
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    names = ['LA-VMRack-三网', 'LA-DMIT', 'LA-Zgo', 'JP-RFCHost', 'HK-TEST']
    fake = [{'name': n, 'type': 'ss', 'server': '192.0.2.1', 'port': 443,
             'cipher': 'aes-128-gcm', 'password': 'TEST-ONLY', 'udp': True} for n in names]
    replacements = {'proxies': '\n'.join('  ' + line for line in yaml.safe_dump(fake, allow_unicode=True).splitlines()),
                    'nodeList': '\n'.join('      - ' + n for n in names),
                    'jpNodeList': '      - JP-RFCHost', 'hkNodeList': '      - HK-TEST', 'usNodeList': '      - LA-VMRack-三网', 'ttNodeList': '      - JP-RFCHost\n      - LA-VMRack-三网'}
    for platform, variable in [('mihomo', 'CLASH_TEMPLATE'), ('stash', 'STASH_TEMPLATE')]:
        text = (ROOT / 'templates' / f'{platform}.yaml').read_text(encoding='utf-8')
        embedded = json.loads(re.search(r'const ' + variable + r' = ("(?:\\.|[^"\\])*");', html).group(1))
        assert text == embedded, platform + ' HTML template drift'
        for key, value in replacements.items():
            text = text.replace('{{' + key + '}}', value)
        assert '{{' not in text
        cfg = yaml.load(text, Loader=StrictLoader)
        validate(cfg, baseline, platform)
        if platform == 'mihomo':
            assert 'follow-rule' not in cfg['dns'] and cfg['dns']['respect-rules']
        else:
            assert not ({'respect-rules', 'fallback', 'enhanced-mode', 'listen'} & cfg['dns'].keys())
            assert not ({'tun', 'sniffer', 'geox-url'} & cfg.keys())
        print(f'{platform}: YAML, references, no cycles, platform policy, embedded template parity PASS')
    for path in (ROOT / '.cache').glob('test-*.yaml'):
        validate(yaml.load(path.read_text(encoding='utf-8'), Loader=StrictLoader), baseline, path.stem.removeprefix('test-'))
        print(path.name + ': browser generation output PASS')


if __name__ == '__main__':
    main()
