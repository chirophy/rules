"""Generate platform templates and synchronize the existing browser converter.

Requires PyYAML: python -m pip install --target .tools PyYAML
"""
from pathlib import Path
import copy
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools'))
import yaml


def build(platform):
    source = yaml.safe_load((ROOT / 'rules-baseline.yaml').read_text(encoding='utf-8-sig'))
    cfg = copy.deepcopy(source)
    cfg['dns'].pop('follow-rule')
    # +.msftconnecttest.com covers the old *.msftconnecttest.com entry.
    cfg['dns']['fake-ip-filter'].remove('*.msftconnecttest.com')
    cfg['proxies'] = '__PROXIES__'
    groups = cfg['proxy-groups']
    groups.insert(5, {'name': '🤖 AI', 'type': 'select',
                      'proxies': ['LA-VMRack-三网', 'LA-DMIT', 'LA-Zgo']})
    cfg['rules'] = ['RULE-SET,ai,🤖 AI' if rule == 'RULE-SET,ai,LA-VMRack-三网' else rule
                    for rule in cfg['rules']]
    # Keep defaults and access to individual nodes via the main selection group.
    for g in groups:
        if g['name'] == '🚀 节点选择':
            g['proxies'] = g['proxies'][:5] + ['__NODES__']
        elif g['name'] == '♻️ 自动选择':
            g['proxies'] = ['__NODES__']
        elif g['name'] == '🇯🇵 日本-最优':
            g['proxies'] = ['__JP__']
        elif g['name'] == '🇭🇰 港澳台-最优':
            g['proxies'] = ['__HK__']
        elif g['name'] == '🇺🇸 美国-最优':
            g['proxies'] = ['__US__']
        elif g['name'] in ('🌍 国外媒体', '📲 电报信息'):
            g['proxies'] = g['proxies'][:3] + ['__NODES__']
        elif g['name'] == '🎵 TikTok':
            g['proxies'] = g['proxies'][:3] + ['__TT__']
    # Deliberate coverage tradeoff, not a claim that BanAD fully replaces reject.
    del cfg['rule-providers']['reject']
    cfg['rules'].remove('RULE-SET,reject,🆎 AdBlock')
    groups[:] = [g for g in groups if g['name'] != '🆎 AdBlock']

    if platform == 'stash':
        cfg = {k: cfg[k] for k in ('mixed-port', 'allow-lan', 'mode', 'log-level', 'ipv6', 'external-controller', 'unified-delay', 'tcp-concurrent', 'dns', 'proxies', 'proxy-groups', 'rule-providers', 'rules')}
        cfg['mixed-port'] = 7890
        cfg['allow-lan'] = True
        cfg['external-controller'] = '0.0.0.0:9090'
        cfg['unified-delay'] = True
        cfg['tcp-concurrent'] = True
        old = cfg['dns']
        # Keep platform-specific DNS fields separate.
        cfg['dns'] = {
            'follow-rule': True,
            'default-nameserver': ['223.5.5.5', '119.29.29.29'],
            'nameserver': ['https://dns.alidns.com/dns-query', 'https://doh.pub/dns-query'],
            'fake-ip-filter': old['fake-ip-filter'],
        }
        for g in groups:
            if g['type'] == 'url-test':
                g.pop('url', None)
                g.pop('tolerance', None)
        for p in cfg['rule-providers'].values():
            p['type'] = 'http'
            p.setdefault('format', 'yaml')
            p.pop('path', None)
    cfg['ipv6'] = True
    dns = cfg['dns']
    dns['ipv6'] = True
    dns['follow-rule' if platform == 'stash' else 'respect-rules'] = True
    dns['default-nameserver'] = ['223.5.5.5', '119.29.29.29']
    dns['nameserver'] = ['https://dns.alidns.com/dns-query', 'https://doh.pub/dns-query']
    dns['proxy-server-nameserver'] = list(dns['nameserver'])
    dns['nameserver-policy'] = {'geosite:geolocation-!cn': [
        'https://1.1.1.1/dns-query#🚀 节点选择',
        'https://8.8.8.8/dns-query#🚀 节点选择',
    ]}
    dns.pop('fallback', None)
    dns.pop('fallback-filter', None)
    server_keys = ('default-nameserver', 'nameserver', 'proxy-server-nameserver', 'nameserver-policy')
    if platform == 'mihomo':
        dns['direct-nameserver'] = list(dns['nameserver'])
        dns['direct-nameserver-follow-policy'] = False
        server_keys += ('direct-nameserver', 'direct-nameserver-follow-policy')
    cfg['dns'] = {k: v for k, v in dns.items() if k not in (*server_keys, 'fake-ip-filter')}
    cfg['dns'].update((k, dns[k]) for k in server_keys)
    cfg['dns']['fake-ip-filter'] = dns['fake-ip-filter']
    class Dumper(yaml.SafeDumper):
        def ignore_aliases(self, data):
            # Expand every group so exported configurations can be inspected directly.
            return True

        def increase_indent(self, flow=False, indentless=False):
            return super().increase_indent(flow, False)
    text = yaml.dump(cfg, Dumper=Dumper, allow_unicode=True, sort_keys=False, width=160)
    for address in dns['nameserver-policy']['geosite:geolocation-!cn']:
        text = text.replace('- ' + address, '- ' + json.dumps(address, ensure_ascii=False))
    text = text.replace('proxies: __PROXIES__', 'proxies:\n{{proxies}}')
    for token, name in [('__NODES__', 'nodeList'), ('__JP__', 'jpNodeList'), ('__HK__', 'hkNodeList'), ('__US__', 'usNodeList'), ('__TT__', 'ttNodeList')]:
        text = re.sub(r'^\s+- ' + token + r'$', '{{' + name + '}}', text, flags=re.M)
    header = '# ' + platform + ' 专用模板；请通过 HTML 转换器填入节点，不要直接导入占位符。\n'
    header += '# 分流顺序与固定出口以 rules-baseline.yaml 为准；说明及官方来源见 README.md。\n'
    if platform == 'stash':
        header += '# 适用 iOS/tvOS 3.6+、macOS 4.3+；iOS/tvOS 不支持进程规则。\n'
        header += '# 共享代理：Stash iOS/Mac 默认在 7890 提供 HTTP/SOCKS；请在客户端开启「允许局域网连接」。\n'
        header += '# 按用户要求显式输出 mixed-port: 7890 / allow-lan: true；客户端实际监听和共享开关仍需确认。\n'
        header += '# iOS 减负版：DNS 跟随规则、按 geosite 分流；移除 reject 及其独立广告组，广告覆盖减少。\n'
    text = header + text
    return text


def main():
    (ROOT / 'templates').mkdir(exist_ok=True)
    html_path = ROOT / 'index.html'
    html = html_path.read_text(encoding='utf-8')
    for platform, variable in [('mihomo', 'CLASH_TEMPLATE'), ('stash', 'STASH_TEMPLATE')]:
        text = build(platform)
        (ROOT / 'templates' / f'{platform}.yaml').write_text(text, encoding='utf-8')
        pattern = r'const ' + variable + r' = (?:`[\s\S]*?`|"(?:\\.|[^"\\])*");'
        html, n = re.subn(pattern, lambda _: 'const ' + variable + ' = ' + json.dumps(text, ensure_ascii=False) + ';', html, count=1)
        assert n == 1, variable
    html = html.replace('Template: rules-baseline.yaml', 'Templates: mihomo.yaml / stash.yaml')
    html = html.replace('Stash / Clash Premium', 'Stash')
    html_path.write_text(html, encoding='utf-8')
    print('Generated both templates; index.html synchronized.')


if __name__ == '__main__':
    main()
