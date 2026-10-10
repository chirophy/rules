"""Export an explicit public file list and scan without printing sensitive values."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools'))
import yaml

FILES = [
    '.gitignore', '.nojekyll', 'AGENTS.md', 'agent.md', 'README.md',
    'index.html', 'model_new_updated.html', 'rules-baseline.yaml',
    'requirements.txt', 'tailwind.config.cjs',
    'assets/tailwind-input.css', 'assets/tailwind.css',
    'templates/mihomo.yaml', 'templates/stash.yaml',
    'scripts/build_templates.py', 'scripts/validate_templates.py',
    'scripts/test_converter.cjs', 'scripts/prepare_public.py',
    'scripts/audit_rules.py', 'scripts/review_domain_witnesses.py',
    'scripts/review_rule_snapshot.py',
    'reports/rule-audit.json', 'reports/domain-witnesses.json',
    'reports/current-rule-snapshot.json', 'reports/规则合理性审查-2026-09-21.md',
]


def main():
    forbidden_values = set()
    private_html = ROOT / '.private' / 'model_new_updated.before-publication.html'
    if private_html.exists():
        text = private_html.read_text(encoding='utf-8')
        block = re.search(r'const FIXED_V6_PROXIES = `([\s\S]*?)`;', text)
        if block:
            for node in yaml.safe_load(block.group(1)):
                for key in ('password', 'uuid', 'server', 'public-key'):
                    if node.get(key):
                        forbidden_values.add(str(node[key]))
                for value in node.get('reality-opts', {}).values():
                    if value:
                        forbidden_values.add(str(value))
    patterns = {
        'UUID': r'\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b',
        'GitHub token': r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b',
        'private key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        'authenticated URL': r'https?://[^\s/]+:[^\s/]+@',
        'subscription token': r'https?://[^\s\"\']*[?&](?:token|key|secret|password|auth)=[^\s\"\']+',
        'local personal path': r'(?i)(?:[A-Z]:[\\/](?:Users|Code)[\\/]|/home/[A-Za-z0-9_.-]+/)',
    }
    contents = {}
    for relative in FILES:
        text = (ROOT / relative).read_text(encoding='utf-8-sig')
        assert not any(value in text for value in forbidden_values), f'Private parameter found: {relative}'
        for name, pattern in patterns.items():
            assert not re.search(pattern, text), f'{name} found: {relative}'
        contents[relative] = text
    html = contents['model_new_updated.html']
    assert html == contents['index.html'], 'Pages entry drift'
    assert not re.search(r'<script\b[^>]*\bsrc\s*=', html, re.I), 'External JavaScript'
    assert 'FIXED_V6_PROXIES' not in html
    assert not re.search(r'\b(?:fetch|XMLHttpRequest|localStorage|sessionStorage|sendBeacon|WebSocket)\s*[.(]', html)
    assert yaml.safe_load(contents['rules-baseline.yaml'])['proxies'] == []
    destination = ROOT / '.publish' / 'rules'
    destination.mkdir(parents=True, exist_ok=True)
    # A stale file must not silently join an upload from a previous run.
    expected = set(FILES)
    assert all(p.relative_to(destination).as_posix() in expected
               for p in destination.rglob('*') if p.is_file()), 'Unexpected export file'
    manifest = []
    for relative, text in contents.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8', newline='\n')
        manifest.append({'path': relative, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                         'bytes': target.stat().st_size})
    (ROOT / '.publish' / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    archive = shutil.make_archive(str(ROOT / '.publish' / 'rules-public'), 'zip', destination)
    print(f'Public export PASS: {len(manifest)} files; private-parameter and credential scans passed.')
    print('Prepared archive: .publish/rules-public.zip')


if __name__ == '__main__':
    main()
