"""Build public templates; optionally import a local configuration without its nodes."""
from pathlib import Path
import argparse
import copy
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools'))
import yaml


class Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def dump(cfg):
    return yaml.dump(cfg, Dumper=Dumper, allow_unicode=True, sort_keys=False, width=160)


def import_source(path):
    source = yaml.safe_load(path.read_text(encoding='utf-8-sig'))
    # Only public settings. Never copy node connection parameters or credentials.
    keys = ('mixed-port', 'allow-lan', 'mode', 'unified-delay', 'tcp-concurrent',
            'log-level', 'ipv6', 'external-controller', 'dns', 'proxy-groups',
            'rule-providers', 'rules')
    cfg = {key: copy.deepcopy(source[key]) for key in keys}
    cfg['proxies'] = []
    cfg['x-converter'] = {'dialer-proxies': {
        n['name']: n['dialer-proxy'] for n in source['proxies'] if n.get('dialer-proxy')
    }}
    (ROOT / 'rules-baseline.yaml').write_text(
        '# Public routing and chain blueprint; contains no node connection parameters.\n'
        + dump(cfg), encoding='utf-8')


def policy(source):
    names = {g['name'] for g in source['proxy-groups']} | {'DIRECT', 'REJECT'}
    required = []
    for rule in source['rules']:
        parts = rule.split(',')
        target = parts[-2] if parts[-1] == 'no-resolve' else parts[-1]
        if target not in names and target not in required:
            required.append(target)
    ai = next(g for g in source['proxy-groups'] if g['name'] == '🤖 AI')
    required = list(dict.fromkeys(ai['proxies'] + required))
    return {'groups': source['proxy-groups'], 'requiredNodes': required,
            'dialerProxies': source['x-converter']['dialer-proxies']}


def build(source, platform):
    cfg = copy.deepcopy(source)
    cfg.pop('x-converter')
    cfg['proxies'] = '__PROXIES__'
    cfg['proxy-groups'] = '__GROUPS__'
    dns = cfg['dns']
    if platform == 'mihomo':
        dns.pop('follow-rule', None)
        dns.update({'enable': True, 'respect-rules': True, 'enhanced-mode': 'fake-ip'})
    else:
        for key in ('enable', 'respect-rules', 'enhanced-mode'):
            dns.pop(key, None)
        dns['follow-rule'] = True
    text = dump(cfg).replace('proxies: __PROXIES__', 'proxies:\n{{proxies}}')
    text = text.replace('proxy-groups: __GROUPS__', 'proxy-groups:\n{{proxyGroups}}')
    for address in dns['nameserver-policy']['geosite:geolocation-!cn']:
        text = text.replace('- ' + address, '- ' + json.dumps(address, ensure_ascii=False))
    header = f'# {platform} 专用占位符模板；请通过 index.html 填入节点。\n'
    header += '# 分流、默认选择与中转关系来自 rules-baseline.yaml；不包含固定节点。\n'
    if platform == 'stash':
        header += '# 目标 iOS/tvOS 3.6+、macOS 4.3+；进程规则与 DNS 策略后缀的边界见 README。\n'
    return header + text


def js_json(value):
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Local source; import public routing settings and chain names only')
    parser.add_argument('--rules-source', type=Path, help='YAML/TXT containing rule-providers and rules only; leave DNS, nodes and groups unchanged')
    args = parser.parse_args()
    if args.source:
        import_source(args.source)
    source = yaml.safe_load((ROOT / 'rules-baseline.yaml').read_text(encoding='utf-8-sig'))
    if args.rules_source:
        updates = yaml.safe_load(args.rules_source.read_text(encoding='utf-8-sig'))
        assert isinstance(updates, dict) and set(updates) == {'rule-providers', 'rules'}, 'Rules source must contain only rule-providers and rules'
        assert isinstance(updates['rule-providers'], dict) and isinstance(updates['rules'], list)
        source.update(copy.deepcopy(updates))
        (ROOT / 'rules-baseline.yaml').write_text(
            '# Public routing and chain blueprint; contains no node connection parameters.\n' + dump(source), encoding='utf-8')
    html_path = ROOT / 'index.html'
    html = html_path.read_text(encoding='utf-8')
    for platform, variable in [('mihomo', 'CLASH_TEMPLATE'), ('stash', 'STASH_TEMPLATE'),
                               ('policy', 'CONVERTER_POLICY')]:
        value = policy(source) if platform == 'policy' else build(source, platform)
        if platform != 'policy':
            (ROOT / 'templates' / f'{platform}.yaml').write_text(value, encoding='utf-8')
        declaration = 'const ' + variable + ' = ' + js_json(value) + ';'
        pattern = r'const ' + variable + r' = (?:`[\s\S]*?`|"(?:\\.|[^"\\])*"|\{[^\n]*\});'
        if variable == 'CONVERTER_POLICY' and not re.search(pattern, html):
            html = html.replace('        const nodeNames = new Set();',
                                '        ' + declaration + '\n        const nodeNames = new Set();')
        else:
            html, count = re.subn(pattern, lambda _: declaration, html, count=1)
            assert count == 1, variable
    html_path.write_text(html, encoding='utf-8')
    print('Generated both templates and public chain policy; index.html synchronized.')


if __name__ == '__main__':
    main()
