// Test just the live summary renderer, without a browser or MQTT connection.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../app/templates/index.html'), 'utf8');
const summary = html.slice(html.indexOf('let dashboardRequestInFlight = false;'),
  html.indexOf('// Auto-refresh mit verbessertem Error-Handling'));
assert(summary.includes('async function loadStatus()'));
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, { innerHTML: '', textContent: '' });
  return elements.get(id);
};
let response = {
  ok: true, json: async () => ({
    generated_at: 1800000000, sensor_activity_window_seconds: 3600,
    basestation_activity_window_seconds: 300, sensors: { active: 5, total: 7 },
    technologies: [
      { key: 'mioty', label: 'mioty', sensors: { active: 2, total: 3 }, basestations: { active: 1, total: 2 } },
      { key: 'lora', label: 'LoRaWAN', sensors: { active: 2, total: 3 }, basestations: { active: 1, total: 1 } },
      { key: 'cellular', label: '<b>Mobilfunk</b>', sensors: { active: 1, total: 1 }, basestations: null },
    ],
    connections: [
      { label: 'Service Center', state: 'connected', detail: 'MQTT: verbunden' },
      { label: 'Home Assistant MQTT', state: 'disconnected', detail: 'Messwerte weitergeben' },
      { label: 'Sentinum Cloud', state: 'disabled', detail: '<script>unsafe</script>' },
    ],
  }),
};
let requests = 0;
const context = vm.createContext({
  document: { getElementById: element }, console: { error() {} }, Date,
  escapeHtml: value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;'),
  getCacheBusterURL: url => url,
  fetch: async url => { assert.equal(url, '/api/dashboard'); requests++; return response; },
});
vm.runInContext(summary, context);
(async () => {
  await vm.runInContext('loadStatus()', context);
  assert(element('dashboard-activity').innerHTML.includes('>5</span>'));
  assert(element('dashboard-activity').innerHTML.includes('von 7 Sensoren'));
  assert(element('dashboard-window').textContent.includes('1 Std.'));
  assert(element('dashboard-window').textContent.includes('5 Min.'));
  assert(element('dashboard-technologies').innerHTML.includes('LoRaWAN'));
  assert(element('dashboard-technologies').innerHTML.includes('<strong>1</strong>/2 Basisstationen'));
  assert(element('dashboard-technologies').innerHTML.includes('&lt;b&gt;Mobilfunk&lt;/b&gt;'));
  const connections = element('dashboard-connections').innerHTML;
  for (const label of ['Verbunden', 'Getrennt', 'Deaktiviert']) assert(connections.includes(label));
  assert(connections.includes('&lt;script&gt;unsafe&lt;/script&gt;'));
  const before = requests;
  await Promise.all([vm.runInContext('loadStatus()', context), vm.runInContext('loadStatus()', context)]);
  assert.equal(requests, before + 1);
  response = { ok: false, status: 503 };
  await vm.runInContext('loadStatus()', context);
  assert(element('dashboard-activity').innerHTML.includes('nicht verfügbar'));
  assert(!element('dashboard-connections').innerHTML.includes('state-connected'));
  assert.equal(element('dashboard-updated').textContent, '');
  response = { ok: true, json: async () => ({}) };
  await vm.runInContext('loadStatus()', context);
  assert(element('dashboard-connections').innerHTML.includes('nicht verfügbar'));
  console.log('Dashboard rendering checks passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
