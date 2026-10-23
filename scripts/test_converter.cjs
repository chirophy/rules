// Execute the actual browser conversion code with synthetic node links only.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
assert.ok(!html.includes('FIXED_V6_PROXIES'));
assert.ok(!/<script\b[^>]*\bsrc\s*=/i.test(html));
const code = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
const elements = new Map();
let created = 0;
function element(id) {
  if (!elements.has(id)) {
    const el = { value:'', style:{}, children:[], listeners:{},
      classList:{ add(){}, remove(){} },
      addEventListener(type, fn){ this.listeners[type] = fn; },
      appendChild(child){ this.children.push(child); },
      replaceChildren(...children){ this.children = children; this._content = ''; },
      remove(){}, contains(){return false;}, scrollIntoView(){} };
    el._content = '';
    for (const field of ['textContent', 'innerHTML']) Object.defineProperty(el, field, {
      get() { return this._content; }, set(value) { this._content = value; this.children = []; }, configurable:true
    });
    Object.defineProperty(el, 'id', { set(value){ elements.set(value, this); }, configurable:true });
    el.parentElement = el;
    elements.set(id, el);
  }
  return elements.get(id);
}
const context = vm.createContext({ console, URL, Set, Map, atob: s => Buffer.from(s, 'base64').toString('binary'),
  setTimeout: fn => fn(), document: { getElementById: element,
    createElement: () => element('created:' + created++),
    querySelectorAll: () => [], body: element('body') }, navigator: {} });
vm.runInContext(code, context);
assert.ok(!vm.runInContext("highlightYaml('<img src=x onerror=alert(1)>')", context).includes('<img'));
const realHighlightYaml = vm.runInContext('highlightYaml', context);
vm.runInContext('showToast = () => {}; highlightYaml = value => value;', context);
fs.mkdirSync(path.join(root, '.cache'), {recursive: true});
const policy = vm.runInContext('CONVERTER_POLICY', context);
const sourceNames = [...new Set(policy.groups.flatMap(g => g.proxies))]
  .filter(n => !policy.groups.some(g => g.name === n) && !['DIRECT', 'REJECT'].includes(n));
function generate(names, kernel) {
  element('inputArea').value = names.map(n =>
    `trojan://test-only@192.0.2.1:443#${encodeURIComponent(n)}`).join('\n');
  vm.runInContext(`setKernel('${kernel}'); process();`, context);
  return element('outputArea');
}
const minimal = ['LA-VMRack', 'LA-DMIT', 'LA-Zgo', 'JP-KFCHost', 'HK-HKC', 'JP-DMIT'];
assert.equal(vm.runInContext('relayEnabled', context), false);
for (const kernel of ['mihomo', 'stash']) {
  // No editor refresh, no HK/JP relay members, no SJC-V.PS: direct generation must work.
  const output = generate(['LA-VMRack', 'LA-DMIT', 'LA-Zgo', 'JP-KFCHost', 'LA-RN'], kernel).textContent;
  assert.ok(!output.startsWith('等待'));
  assert.ok(!output.includes('dialer-proxy:'));
  assert.ok(!output.includes('HK Route'));
  assert.ok(!output.includes('JP Route'));
  fs.writeFileSync(path.join(root, '.cache', `test-${kernel}-no-relay.yaml`), output);
}
vm.runInContext('setRelayEnabled(true)', context);

for (const kernel of ['mihomo', 'stash']) {
  for (const [scenario, names] of [['full', sourceNames], ['minimal', minimal],
    ['extra', [...minimal, 'toString', 'true', 'custom $& <tag> "quote"\\path\nline']]]) {
    const output = generate(names, kernel).innerHTML;
    assert.ok(!output.startsWith('等待'), 'Generation unexpectedly blocked');
    assert.ok(output.includes('DOMAIN,rfc.uhdnow.com,JP-KFCHost'));
    assert.ok(!output.includes('{{'));
    assert.equal((output.match(/    udp: true/g) || []).length, names.length);
    fs.writeFileSync(path.join(root, '.cache', `test-${kernel}-${scenario}.yaml`), output);
  }
  const mixed = [...minimal.map(n => `trojan://test-only@192.0.2.1:443#${encodeURIComponent(n)}`),
    ...['HK-BWL', 'JP-100TB', 'LA-RN'].map(n =>
      `ss://${Buffer.from('aes-128-gcm:test-only').toString('base64')}@192.0.2.1:443#${encodeURIComponent(n)}`),
    ...['SJC-V.PS', 'HK-Mhyidc-V6'].map(n =>
      `vless://test-only-id@192.0.2.1:443?security=reality&sni=example.com&pbk=test-only-public-key#${encodeURIComponent(n)}`),
    'vmess://' + Buffer.from(JSON.stringify({ps:'VMESS-TEST',add:'192.0.2.1',port:443,id:'test-only-id',net:'tcp'})).toString('base64')];
  element('inputArea').value = mixed.join('\n');
  vm.runInContext(`setKernel('${kernel}'); process();`, context);
  assert.ok(!element('outputArea').innerHTML.startsWith('等待'));
  fs.writeFileSync(path.join(root, '.cache', `test-${kernel}-mixed.yaml`), element('outputArea').innerHTML);
  generate(minimal.filter(n => n !== 'LA-VMRack'), kernel);
  assert.equal(element('outputArea').textContent, '等待补齐或修正链路节点');
  assert.match(element('statusBar').textContent, /LA-VMRack/);
  generate(minimal.filter(n => n !== 'HK-HKC'), kernel);
  assert.match(element('statusBar').textContent, /HK Route/);
  generate(minimal.filter(n => n !== 'JP-DMIT'), kernel);
  assert.match(element('statusBar').textContent, /JP Route/);
  generate([...minimal, 'LA-RN'], kernel);
  assert.match(element('statusBar').textContent, /SJC-V.PS/);
  generate([...minimal, 'SJC-VmShell'], kernel);
  assert.match(element('statusBar').textContent, /SJC-V.PS/);
  generate([...minimal, 'DIRECT'], kernel);
  assert.match(element('statusBar').textContent, /重名/);
  generate([...minimal, '🚀 节点选择'], kernel);
  assert.match(element('statusBar').textContent, /重名/);
  vm.runInContext("dialerOverrides.set('HK-HKC', 'HK-BWL')", context);
  generate([...minimal, 'HK-BWL'], kernel);
  assert.match(element('statusBar').textContent, /循环/);
  vm.runInContext("dialerOverrides.delete('HK-HKC')", context);
}
console.log('Both platforms: full/minimal/extra outputs, missing fixed and route nodes, missing dialers, reserved names, cycle guards PASS');

// Exercise the actual selectors and their change handlers, not just a configuration map.
function choose(name, target) {
  const row = element('chainRows').children.find(row => row.children[0].textContent === name);
  assert.ok(row, 'Missing chain row');
  const select = row.children[1];
  assert.ok(!select.children.some(option => option.value === 'target:' + name), 'Self-dialer offered');
  select.value = target;
  select.listeners.change();
  assert.equal(element('outputArea').textContent, '等待重新生成配置');
}
const customNames = [...minimal, 'HK-BWL', 'LA-RN', 'CUSTOM-A', 'CUSTOM-B'];
for (const kernel of ['mihomo', 'stash']) {
  vm.runInContext('dialerOverrides.clear()', context);
  generate(customNames, kernel); // Default LA-RN lacks SJC; editor must remain usable.
  choose('LA-RN', 'none');
  choose('HK-BWL', 'target:LA-DMIT');
  choose('CUSTOM-A', 'target:CUSTOM-B');
  choose('CUSTOM-B', 'target:HK-HKC');
  const output = generate(customNames, kernel).textContent;
  assert.ok(!output.startsWith('等待'));
  fs.writeFileSync(path.join(root, '.cache', `test-${kernel}-custom.yaml`), output);
  // Regeneration keeps selections, even with re-parsing and client switching.
  assert.equal(element('chainRows').children.find(r => r.children[0].textContent === 'HK-BWL').children[1].value,
    'target:LA-DMIT');
  choose('CUSTOM-B', 'target:CUSTOM-A');
  generate(customNames, kernel);
  assert.match(element('statusBar').textContent, /循环/);
  choose('CUSTOM-B', 'none');
  choose('CUSTOM-A', 'target:CUSTOM-B');
  generate(customNames.filter(n => n !== 'CUSTOM-B'), kernel);
  assert.match(element('statusBar').textContent, /缺少中转出口/);
  vm.runInContext('resetChainChoices()', context);
  assert.equal(vm.runInContext('dialerOverrides.size', context), 0);
  generate(minimal, kernel);
  choose('HK-HKC', 'target:🇭🇰 HK Route');
  generate(minimal, kernel);
  assert.match(element('statusBar').textContent, /循环/);
  vm.runInContext('dialerOverrides.clear()', context);
  generate([...minimal, 'CUSTOM-A'], kernel);
  choose('CUSTOM-A', 'target:🇭🇰 HK Route');
  const groupOutput = generate([...minimal, 'CUSTOM-A'], kernel).textContent;
  assert.ok(!groupOutput.startsWith('等待'));
  fs.writeFileSync(path.join(root, '.cache', `test-${kernel}-custom-group.yaml`), groupOutput);
  vm.runInContext('dialerOverrides.clear()', context);
  generate([...minimal, '<img src=x onerror=alert(1)>'], kernel);
  const row = element('chainRows').children.at(-1);
  assert.equal(row.children[0].textContent, '<img src=x onerror=alert(1)>');
  assert.equal(row.children[0].children.length, 1); // Plain text label plus the static note only.
}
console.log('Selector UI: custom node/group upstreams, removal, multi-hop chains, stale-output invalidation, missing targets, cycle guards, reset, safe labels PASS');

function member(groupName, nodeName, checked) {
  const fieldset = element('routeGroupRows').children.find(row => row.children[0].textContent === groupName);
  assert.ok(fieldset, 'Missing group member editor');
  const checkbox = fieldset.children[2].children.map(label => label.children[0]).find(input => input.value === nodeName);
  assert.ok(checkbox, 'Missing member checkbox');
  checkbox.checked = checked;
  checkbox.listeners.change();
  assert.equal(element('outputArea').textContent, '等待重新生成配置');
}
for (const kernel of ['mihomo', 'stash']) {
  vm.runInContext('dialerOverrides.clear(); routeMemberOverrides.clear()', context);
  const names = [...minimal, 'HK-BWL', 'HK-NEW', 'JP-NEW', 'CUSTOM-HK-EXIT'];
  generate(names, kernel);
  member('🇭🇰 HK Route', 'HK-BWL', true);
  member('🇭🇰 HK Route', 'HK-HKC', false);
  const output = generate(names, kernel).textContent;
  assert.ok(!output.startsWith('等待'));
  fs.writeFileSync(path.join(root, '.cache', `test-${kernel}-members.yaml`), output);
  const hkMember = element('chainRows').children.find(r => r.children[0].textContent === 'HK-BWL').children[1];
  assert.match(hkMember.children[0].textContent, /不使用中转/);
  // Keep explicit dialers when membership changes, but reject the resulting cycle.
  choose('HK-BWL', 'target:🇭🇰 HK Route');
  generate(names, kernel);
  assert.match(element('statusBar').textContent, /循环/);
  choose('HK-BWL', 'template');
  generate(names.filter(n => n !== 'HK-BWL'), kernel);
  assert.match(element('statusBar').textContent, /已移除的成员/);
  member('🇭🇰 HK Route', 'HK-BWL', false);
  generate(names.filter(n => n !== 'HK-BWL'), kernel);
  assert.match(element('statusBar').textContent, /HK Route/); // Deliberately empty must not fall back.
  vm.runInContext('resetChainChoices()', context);
  assert.equal(vm.runInContext('routeMemberOverrides.size', context), 0);
  generate(names, kernel);
  // Region-matching input nodes can be members even when old candidate lists are absent.
  const arbitrary = ['LA-VMRack', 'LA-DMIT', 'LA-Zgo', 'JP-KFCHost', 'RELAY-HK', 'RELAY-JP', 'HK-NEW', 'JP-NEW'];
  generate(arbitrary, kernel);
  member('🇭🇰 HK Route', 'RELAY-HK', true);
  member('🇯🇵 JP Route', 'RELAY-JP', true);
  const arbitraryOutput = generate(arbitrary, kernel).textContent;
  assert.ok(!arbitraryOutput.startsWith('等待'));
  fs.writeFileSync(path.join(root, '.cache', `test-${kernel}-arbitrary-members.yaml`), arbitraryOutput);
  vm.runInContext('routeMemberOverrides.clear(); dialerOverrides.clear()', context);
}
console.log('Route membership UI: regional defaults, arbitrary members, member direct defaults, explicit-cycle rejection, removed/empty members, reset PASS');

for (const kernel of ['mihomo', 'stash']) {
  vm.runInContext('routeMemberOverrides.clear(); dialerOverrides.clear()', context);
  generate([...minimal, 'HK-NEW', 'JP-NEW', 'US-NEW'], kernel);
  for (const [group, region] of [['🇭🇰 HK Route', 'HK'], ['🇯🇵 JP Route', 'JP']]) {
    const field = element('routeGroupRows').children.find(row => row.children[0].textContent === group);
    const values = field.children[2].children.map(label => label.children[0].value);
    assert.ok(values.includes(region + '-NEW'));
    assert.ok(values.every(name => name.toUpperCase().includes(region)), 'Wrong region in checkbox candidates');
  }
  vm.runInContext("routeMemberOverrides.set('🇭🇰 HK Route', ['JP-DMIT'])", context);
  generate(minimal, kernel);
  assert.match(element('statusBar').textContent, /只能包含名称带 HK/);
  vm.runInContext("routeMemberOverrides.clear(); routeMemberOverrides.set('🇯🇵 JP Route', ['HK-HKC'])", context);
  generate(minimal, kernel);
  assert.match(element('statusBar').textContent, /只能包含名称带 JP/);
  vm.runInContext('routeMemberOverrides.clear()', context);
}
console.log('HK/JP Route: region-filtered member controls and generation-time region guards PASS');

// Stale invalid relay choices must not prevent generation after disabling relay mode.
for (const kernel of ['mihomo', 'stash']) {
  vm.runInContext("setRelayEnabled(true); routeMemberOverrides.set('🇭🇰 HK Route', ['JP-DMIT']); dialerOverrides.set('LA-DMIT', 'missing-relay')", context);
  generate(minimal, kernel);
  assert.ok(element('outputArea').textContent.startsWith('等待'));
  vm.runInContext('setRelayEnabled(false)', context);
  const output = generate(minimal, kernel).textContent;
  assert.ok(!output.startsWith('等待'));
  assert.ok(!output.includes('dialer-proxy:'));
  vm.runInContext('setRelayEnabled(true)', context);
  generate(minimal, kernel);
  assert.match(element('statusBar').textContent, /只能包含名称带 HK/);
  vm.runInContext('routeMemberOverrides.clear(); dialerOverrides.clear()', context);
}
console.log('Optional relay mode: default direct generation, no relay requirements, disabling ignores stale relay errors, re-enabling preserves settings PASS');

assert.ok(!html.includes('id="relayEnabled"'), 'Redundant enable switch remains');
assert.ok(html.includes('onclick="openChainEditor()"'));
assert.ok(html.includes('id="chainPanel" hidden'));
vm.runInContext('setRelayEnabled(false)', context);
generate(minimal, 'mihomo');
assert.ok(!element('outputArea').textContent.includes('dialer-proxy:'));
vm.runInContext('openChainEditor()', context);
assert.equal(vm.runInContext('relayEnabled', context), true);
assert.equal(element('chainPanel').hidden, false);
assert.equal(element('outputArea').textContent, '等待重新生成配置');
const configured = generate(minimal, 'mihomo').textContent;
assert.ok(configured.includes('dialer-proxy:'));
vm.runInContext('setRelayEnabled(false)', context);
assert.equal(element('chainPanel').hidden, true);
const cancelled = generate(minimal, 'mihomo').textContent;
assert.ok(!cancelled.includes('dialer-proxy:'));
console.log('Single entry: setting relays enables mode, cancelling hides editor and restores direct generation PASS');

// Exercise real parsing and serialization for encoded credentials, Unicode and IPv6.
const encodedPassword = 'test:@密码%';
const ssAuth = Buffer.from('aes-128-gcm:' + encodedPassword).toString('base64url');
const parserCases = [
  ...minimal.map(n => `trojan://test-only@192.0.2.1:443#${encodeURIComponent(n)}`),
  'vmess://' + Buffer.from(JSON.stringify({ps:'中文节点',add:'192.0.2.1',port:443,id:'test-only-id',net:'tcp'})).toString('base64'),
  `trojan://${encodeURIComponent(encodedPassword)}@[2001:db8::1]:443#ENCODED-TROJAN`,
  `ss://${ssAuth}@[2001:db8::2]:8443#SS-IPV6`,
  `ss://aes-128-gcm:${encodeURIComponent(encodedPassword)}@192.0.2.1:443#SS-PLAIN`,
  'ss://' + Buffer.from('aes-128-gcm:' + encodedPassword + '@[2001:db8::3]:443').toString('base64') + '#SS-LEGACY',
  `vless://test-only-id@192.0.2.1:443?security=reality&sni=example.com&pbk=test-only-public-key#VLESS-SNI`,
  'vmess://' + Buffer.from(JSON.stringify({ps:'SCALAR',add:'192.0.2.1',port:443,id:'test-only\n    injected: true',net:'tcp'})).toString('base64'),
];
for (const kernel of ['mihomo', 'stash']) {
  element('inputArea').value = parserCases.join('\n');
  vm.runInContext(`setRelayEnabled(false); setKernel('${kernel}'); process()`, context);
  const output = element('outputArea').textContent;
  assert.ok(!output.startsWith('等待'));
  assert.ok(output.includes('中文节点'));
  fs.writeFileSync(path.join(root, '.cache', `test-${kernel}-encoding.yaml`), output);
  fs.writeFileSync(path.join(root, '.cache', `test-${kernel}-encoding.html`), realHighlightYaml(output));
}
for (const bad of [
  'ss://' + ssAuth + '@192.0.2.1:443/?plugin=obfs-local',
  'ss://' + ssAuth + '@192.0.2.1:0',
  'vless://test-only-id@192.0.2.1:0',
  'trojan://test-only@192.0.2.1:0',
  'vmess://' + Buffer.from(JSON.stringify({ps:'BAD',add:'192.0.2.1',port:'443bad',id:'test-only-id'})).toString('base64'),
  'vless://test-only-id@192.0.2.1:443?type=grpc&serviceName=test',
]) {
  element('inputArea').value = bad;
  const parsed = vm.runInContext('readInputNodes()', context);
  assert.equal(parsed.nodes.length, 0);
  assert.equal(parsed.errors.length, 1);
  assert.ok(!parsed.errors[0].message.includes('test-only'));
}
console.log('Parsing: UTF-8, encoded passwords, SS IPv6/plain/legacy, invalid ports, unsupported transports and safe error messages PASS');
