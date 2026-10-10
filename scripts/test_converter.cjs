// Execute browser generation logic with a small DOM stub and synthetic nodes.
// The public converter must only emit explicitly supplied nodes.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
assert.ok(!html.includes('FIXED_V6_PROXIES'));
let code = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, { value: '', textContent: '', innerHTML: '', style: {},
    classList: { add(){}, remove(){} }, addEventListener(){}, appendChild(){}, remove(){}, contains(){return false;} });
  const el = elements.get(id);
  el.parentElement = el;
  return el;
}
const context = vm.createContext({ console, URL, Set, atob: s => Buffer.from(s, 'base64').toString('binary'),
  setTimeout: fn => fn(), document: { getElementById: element, createElement: () => element('toast'),
    querySelectorAll: () => [], body: element('body') }, navigator: {} });
vm.runInContext(code, context);
assert.ok(!vm.runInContext("highlightYaml('<img src=x onerror=alert(1)>')", context).includes('<img'));
vm.runInContext('showToast = () => {}; highlightYaml = value => value;', context);
fs.mkdirSync(path.join(root, '.cache'), {recursive: true});
for (const kernel of ['mihomo', 'stash']) {
  element('inputArea').value = ['LA-VMRack-三网', 'LA-DMIT', 'LA-Zgo', 'JP-RFCHost', 'HK-TEST'].map(n =>
    `trojan://test-only@192.0.2.1:443#${encodeURIComponent(n)}`).join('\n');
  vm.runInContext(`setKernel('${kernel}'); process();`, context);
  const output = element('outputArea').innerHTML;
  assert.ok(output.includes('DOMAIN,rfc.uhdnow.com,JP-RFCHost'));
  assert.ok(!output.includes('{{'));
  assert.equal((output.match(/    udp: true/g) || []).length, 5);
  fs.writeFileSync(path.join(root, '.cache', `test-${kernel}.yaml`), output);
}
element('inputArea').value = 'trojan://test-only@192.0.2.1:443#HK-TEST';
vm.runInContext('process();', context);
assert.equal(element('outputArea').textContent, '等待补齐规则指定节点');
element('inputArea').value = ['LA-VMRack-三网', 'LA-DMIT', 'LA-Zgo', 'JP-RFCHost'].map(n =>
  `trojan://test-only@192.0.2.1:443#${encodeURIComponent(n)}`).join('\n');
vm.runInContext('process();', context);
assert.equal(element('outputArea').textContent, '等待补齐地区节点');
console.log('Both generation paths, exact node count, and missing-node guards PASS');
