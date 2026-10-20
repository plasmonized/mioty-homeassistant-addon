// Offline rendering checks for the existing inline sensor-page JavaScript.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../app/templates/sensors.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map(match => match[1].replace('{{ ingress_path|tojson }}', '""')).join('\n');
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, {
    innerHTML: '', value: '', style: {}, addEventListener() {}, reset() {},
  });
  return elements.get(id);
};
let sensors = [
  { eui: 'C1', protocol_type: 'cellular', source: 'sentinum_cloud', device_name: '<script>bad</script>' },
  { eui: 'L1', protocol_type: 'lora' },
  { eui: 'M2', protocol_type: 'mioty', device_name: 'Sensor 10' },
  { eui: 'M1', protocol_type: 'mioty', device_name: 'Sensor 2' },
  { eui: 'O1', protocol_type: 'oms' },
  { eui: 'U1', protocol_type: 'future_radio' },
  { eui: 'LEGACY' },
];
const context = vm.createContext({
  document: { getElementById: element },
  window: {}, console, Date, Intl, setInterval() {}, alert() {}, confirm() { return false; },
  fetch: async () => ({ ok: true, json: async () => sensors }),
});
vm.runInContext(scripts, context);

(async () => {
  await vm.runInContext('loadSensors()', context);
  const rendered = element('sensors-list').innerHTML;
  const labels = ['mioty', 'LoRaWAN', 'OMS / Wireless M-Bus', 'Mobilfunk', 'Unbekannt'];
  let previous = -1;
  for (const label of labels) {
    const position = rendered.indexOf(`<h3>${label}</h3>`);
    assert(position > previous, `Missing or incorrectly ordered group: ${label}`);
    previous = position;
  }
  assert(rendered.indexOf('Sensor 2') < rendered.indexOf('Sensor 10'));
  assert(rendered.includes('IMEI: C1'));
  assert(rendered.includes('Sentinum Cloud'));
  assert(rendered.includes('&lt;script&gt;bad&lt;/script&gt;'));
  assert(!rendered.includes('<script>bad</script>'));
  assert.equal((rendered.match(/data-action="reregister"/g) || []).length, 3);
  assert.deepEqual(Array.from(vm.runInContext('allSensorEuis', context)).sort(), ['LEGACY', 'M1', 'M2']);
  const cellular = rendered.slice(rendered.indexOf('<section class="technology-group" aria-label="Mobilfunk"'));
  assert(!cellular.includes('Network Key:'));
  assert(!cellular.includes('Short Address:'));
  sensors = [{ eui: 'M1', protocol_type: 'mioty' }];
  await vm.runInContext('loadSensors()', context);
  assert(!element('sensors-list').innerHTML.includes('<h3>Mobilfunk</h3>'));
  sensors = [];
  await vm.runInContext('loadSensors()', context);
  assert(element('sensors-list').innerHTML.includes('Keine Sensoren registriert.'));
  console.log('Sensor grouping rendering checks passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
