"""Strict YAML and complete selectable chain checks; does not start a client."""
from pathlib import Path
from html.parser import HTMLParser
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools'))
import yaml
from build_templates import build, policy


class StrictLoader(yaml.SafeLoader):
    pass


def mapping(loader, node, deep=False):
    keys = [loader.construct_object(k, deep=deep) for k, v in node.value]
    assert len(keys) == len(set(keys)), 'Duplicate YAML key'
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def load(text):
    return yaml.load(text, Loader=StrictLoader)


class HighlightedText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        assert tag == 'span' and all(key == 'class' for key, value in attrs), 'Unsafe highlight markup'

    def handle_data(self, data):
        self.parts.append(data)


def validate(cfg, baseline, platform, scenario):
    assert cfg['rules'] == baseline['rules'], 'Rule order or target drift'
    assert cfg['rule-providers'] == baseline['rule-providers'], 'Provider drift'
    assert 'x-converter' not in cfg
    assert cfg['ipv6'] is True and cfg['dns']['ipv6'] is True
    assert cfg['mixed-port'] == 7890 and cfg['allow-lan'] is True
    assert cfg['unified-delay'] is True and cfg['tcp-concurrent'] is True
    expected_dns = dict(baseline['dns'])
    if platform == 'mihomo':
        expected_dns.pop('follow-rule', None)
        expected_dns.update(enable=True, **{'respect-rules': True, 'enhanced-mode': 'fake-ip'})
    else:
        for key in ('enable', 'respect-rules', 'enhanced-mode'):
            expected_dns.pop(key, None)
        expected_dns['follow-rule'] = True
    assert cfg['dns'] == expected_dns, 'Platform DNS drift'
    proxies = cfg['proxies']; groups = cfg['proxy-groups']
    node_names = [n['name'] for n in proxies]
    names = node_names + [g['name'] for g in groups]
    assert len(names) == len(set(names)), 'Duplicate node/group name'
    assert all(n.get('udp') is True for n in proxies)
    assert all(n['server'] == '192.0.2.1' for n in proxies), 'Unexpected node parameters'
    known = set(names) | {'DIRECT', 'REJECT'}
    source_groups = [g for g in baseline['proxy-groups'] if scenario != 'no-relay' or not g['name'].endswith(' Route')]
    assert len(groups) == len(source_groups) == (13 if scenario == 'no-relay' else 15)
    expected_members = {g['name']: [n for n in g['proxies'] if n in node_names]
                        for g in baseline['proxy-groups'] if g['name'].endswith(' Route')}
    if scenario == 'members':
        expected_members['🇭🇰 HK Route'] = ['HK-BWL']
    if scenario == 'arbitrary-members':
        expected_members = {'🇭🇰 HK Route': ['RELAY-HK'], '🇯🇵 JP Route': ['RELAY-JP']}
    for name, members in expected_members.items():
        region = 'HK' if name == '🇭🇰 HK Route' else 'JP'
        assert all(region in member.upper() for member in members), 'Wrong region in Route group'
    for actual, source in zip(groups, source_groups):
        assert actual['name'] == source['name']
        assert actual['type'] == source['type']
        assert actual['proxies'] and set(actual['proxies']) <= known
        if source['name'] == '🚀 节点选择':
            assert actual['proxies'] == ['♻️ 自动选择', 'DIRECT'] + node_names
        elif source['name'] == '♻️ 自动选择':
            assert actual['proxies'] == node_names
            if platform == 'mihomo':
                assert actual['url'].startswith('https://')
        elif source['name'] in expected_members:
            assert actual['proxies'] == expected_members[source['name']]
        else:
            assert actual['proxies'] == [n for n in source['proxies'] if n in known]
    expected_dialers = dict(baseline['x-converter']['dialer-proxies'])
    members = set(n for values in expected_members.values() for n in values)
    for name in node_names:
        if name in members:
            expected_dialers.pop(name, None)
        elif 'HK' in name.upper():
            expected_dialers[name] = '🇭🇰 HK Route'
        elif 'JP' in name.upper():
            expected_dialers[name] = '🇯🇵 JP Route' 
    if scenario == 'custom':
        expected_dialers.update({'HK-BWL': 'LA-DMIT', 'CUSTOM-A': 'CUSTOM-B', 'CUSTOM-B': 'HK-HKC'})
        expected_dialers.pop('LA-RN')
    if scenario == 'custom-group':
        expected_dialers['CUSTOM-A'] = '🇭🇰 HK Route' 
    if scenario == 'no-relay':
        expected_dialers = {}
        assert not any(g['name'].endswith(' Route') for g in groups)
    edges = {g['name']: g['proxies'] for g in groups}
    for node in proxies:
        expected = expected_dialers.get(node['name'])
        assert node.get('dialer-proxy') == expected, 'Dialer lost or injected'
        assert not expected or expected in known, 'Missing dialer'
        edges[node['name']] = [expected] if expected else []
    for rule in cfg['rules']:
        parts = rule.split(',')
        target = parts[-2] if parts[-1] == 'no-resolve' else parts[-1]
        assert target in known, 'Missing rule target'
        if parts[0] == 'RULE-SET':
            assert parts[1] in cfg['rule-providers']
    visited = set()
    def visit(name, parents):
        assert name not in parents, 'Node/group/dialer cycle'
        if name in visited:
            return
        for child in edges.get(name, []):
            visit(child, parents | {name})
        visited.add(name)
    for name in edges:
        visit(name, set())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rules-source', type=Path, help='Compare rule-providers and ordered rules against the latest YAML/TXT')
    args = parser.parse_args()
    baseline = load((ROOT / 'rules-baseline.yaml').read_text(encoding='utf-8-sig'))
    assert baseline['proxies'] == []
    assert len(baseline['rules']) == 30 and len(baseline['rule-providers']) == 19
    assert baseline['x-converter']['dialer-proxies'] == {
        'HK-BWL': '🇭🇰 HK Route', 'HK-100TB': '🇭🇰 HK Route',
        'JP-100TB': '🇯🇵 JP Route', 'JP-KFCHost': '🇯🇵 JP Route',
        'LA-RN': 'SJC-V.PS', 'SJC-VmShell': 'SJC-V.PS',
        'HK-Mhyidc-V6': '🇭🇰 HK Route', 'JP-Mhyidc-V6': '🇭🇰 HK Route',
        'MO-Mhyidc-V6': '🇭🇰 HK Route'}
    assert 'GoogleCN' not in baseline['rule-providers']
    assert baseline['rules'][14] == 'GEOSITE,google-cn,🎯 全球直连'
    replacements = {'BanAD': 'AdvertisingLite', 'BanProgramAD': 'Privacy',
                    'SteamCN': 'SteamCN', 'Microsoft': 'Microsoft', 'ProxyMedia': 'GlobalMedia'}
    for name, collection in replacements.items():
        entry = baseline['rule-providers'][name]
        assert entry['format'] == 'yaml' and entry['behavior'] == 'classical'
        assert entry['url'] == 'https://cdn.jsdelivr.net/gh/blackmatrix7/ios_rule_script@master/rule/Clash/' + collection + '/' + collection + '.yaml'
    if args.rules_source:
        updates = load(args.rules_source.read_text(encoding='utf-8-sig'))
        for key in ('rule-providers', 'rules'):
            assert baseline[key] == updates[key], 'Latest TXT rule policy drift: ' + key
    # Old local YAML still describes DNS/groups, but its rule snapshot is superseded by the TXT.
    source_path = ROOT / '已脱敏.yaml'
    if source_path.exists():
        source = load(source_path.read_text(encoding='utf-8-sig'))
        for key in ('dns', 'proxy-groups'):
            assert baseline[key] == source[key], 'Local source policy drift: ' + key
        assert baseline['x-converter']['dialer-proxies'] == {
            n['name']: n['dialer-proxy'] for n in source['proxies'] if n.get('dialer-proxy')}
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    embedded_policy = re.search(r'const CONVERTER_POLICY = (\{[^\n]*\});', html).group(1)
    assert json.loads(embedded_policy) == policy(baseline)
    for platform, variable in [('mihomo', 'CLASH_TEMPLATE'), ('stash', 'STASH_TEMPLATE')]:
        template = (ROOT / 'templates' / f'{platform}.yaml').read_text(encoding='utf-8')
        embedded = json.loads(re.search(r'const ' + variable + r' = ("(?:\\.|[^"\\])*");', html).group(1))
        assert template == embedded == build(baseline, platform), 'Generated/embedded template drift'
        encoded = load((ROOT / '.cache' / f'test-{platform}-encoding.yaml').read_text(encoding='utf-8'))
        highlighted = HighlightedText()
        highlighted.feed((ROOT / '.cache' / f'test-{platform}-encoding.html').read_text(encoding='utf-8'))
        assert ''.join(highlighted.parts) == (ROOT / '.cache' / f'test-{platform}-encoding.yaml').read_text(encoding='utf-8'), 'Highlighting changed downloadable YAML'
        by_name = {node['name']: node for node in encoded['proxies']}
        assert '中文节点' in by_name
        for name in ('ENCODED-TROJAN', 'SS-IPV6', 'SS-PLAIN', 'SS-LEGACY'):
            assert by_name[name]['password'] == 'test:@密码%'
        assert by_name['SS-IPV6']['server'] == '2001:db8::2'
        assert by_name['SS-IPV6']['port'] == 8443
        assert by_name['SS-LEGACY']['server'] == '2001:db8::3'
        assert by_name['SCALAR']['uuid'] == 'test-only\n    injected: true'
        assert 'injected' not in by_name['SCALAR']
        assert by_name['VLESS-SNI']['sni' if platform == 'stash' else 'servername'] == 'example.com'
        assert ('servername' if platform == 'stash' else 'sni') not in by_name['VLESS-SNI']
        for scenario in ('full', 'minimal', 'extra', 'mixed', 'custom', 'custom-group', 'members', 'arbitrary-members', 'no-relay'):
            text = (ROOT / '.cache' / f'test-{platform}-{scenario}.yaml').read_text(encoding='utf-8')
            assert '{{' not in text, 'Placeholder remaining'
            cfg = load(text)
            validate(cfg, baseline, platform, scenario)
            if scenario == 'full':
                assert next(n for n in cfg['proxies'] if n['name'] == 'JP-Mhyidc-V6')['dialer-proxy'] == '🇯🇵 JP Route'
            if scenario == 'extra':
                assert cfg['proxies'][-1]['name'] == 'custom $& <tag> "quote"\\path\nline'
        print(f'{platform}: strict YAML, source parity, full chain references/cycles, DNS, template parity PASS')


if __name__ == '__main__':
    main()
