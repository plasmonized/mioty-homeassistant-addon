import { useState } from 'react';
import { Radio, Plus, ArrowUpRight, ArrowRight, Settings2, X, Check, BatteryLow, Thermometer, Droplets, Search, ChevronRight, Antenna, Cpu, House, CircleCheck, Activity } from 'lucide-react';
import './networkdesk.css';

type Sensor = { id: string; name: string; room: string; value: string; unit: string; battery: string; signal: string; ago: string; warning?: boolean };
const initial: Sensor[] = [
  { id: 'fca84a090000001c', name: 'Füllstand Keller', room: 'Keller', value: '—', unit: '', battery: '18 %', signal: '−114', ago: 'vor 3 Std.', warning: true },
  { id: 'fca84a090000002b', name: 'Temperatur Büro', room: 'Büro', value: '22.4', unit: '°C', battery: '94 %', signal: '−87', ago: 'vor 12 s' },
  { id: 'fca84a090000003e', name: 'Luftfeuchte Lager', room: 'Lager', value: '48.7', unit: '%', battery: '87 %', signal: '−92', ago: 'vor 34 s' },
  { id: 'fca84a090000004a', name: 'Temperatur Außen', room: 'Außen', value: '16.8', unit: '°C', battery: '76 %', signal: '−103', ago: 'vor 1 Min.' },
];

export function NetworkDesk() {
  const [sensors, setSensors] = useState(initial);
  const [panel, setPanel] = useState<'diagnose' | 'add' | 'network' | 'settings' | 'sensor' | null>(null);
  const [selected, setSelected] = useState(initial[0]);
  const [tab, setTab] = useState('Alle');
  const [search, setSearch] = useState('');
  const [checked, setChecked] = useState(false);
  const [tested, setTested] = useState(false);
  const [discovery, setDiscovery] = useState(true);
  const [name, setName] = useState('');
  const [eui, setEui] = useState('');
  const [error, setError] = useState('');
  const warning = sensors.some(s => s.warning);
  const visible = sensors.filter(s => (tab !== 'Prüfen' || s.warning) && (tab !== 'Aktiv' || !s.warning) && (s.name + s.id).toLowerCase().includes(search.toLowerCase()));
  function resolve() {
    setSensors(items => items.map(s => s.warning ? { ...s, warning: false, value: '63.2', unit: '%', battery: '98 %', ago: 'gerade eben' } : s));
    setPanel(null); setTab('Alle');
  }
  function add() {
    if (!name.trim() || !/^[a-f0-9]{16}$/i.test(eui)) { setError('Bitte einen Namen und eine EUI mit 16 Hex-Zeichen eingeben.'); return; }
    if (sensors.some(s => s.id.toLowerCase() === eui.toLowerCase())) { setError('Diese EUI ist bereits verbunden.'); return; }
    setSensors(items => [...items, { id: eui, name, room: 'Neu', value: '—', unit: '', battery: '—', signal: '—', ago: 'Warte auf Daten' }]);
    setPanel(null); setSearch(''); setTab('Alle');
  }
  return <div className="nd">
    <header><div className="nd-brand"><Radio size={27} strokeWidth={1.6} />mioty<small>APPLICATION<br />CENTER</small></div><div className="nd-header-right"><span className="nd-status"><i className="nd-dot" /> Workspace verbunden</span><span className="nd-kicker">DEMO / 01</span><button className="nd-icon" aria-label="Einstellungen" onClick={() => setPanel('settings')}><Settings2 size={15} /></button></div></header>
    <main>
      <div className="nd-heading"><div><div className="nd-kicker">Dein Netzwerk · Mittwoch, 18. Juni</div><h1>Alles im Empfang.</h1><p>Ein Blick aufs Ganze. Ein klarer nächster Schritt.</p></div><button className="nd-btn" onClick={() => { setName(''); setEui(''); setError(''); setPanel('add'); }}><Plus size={15} />Sensor verbinden</button></div>
      <section className="nd-summary" aria-label="Netzwerkstatus"><div><strong>{sensors.filter(s => !s.warning).length}<span> / {sensors.length}</span></strong><span>Sensoren aktiv</span></div><div><strong>{warning ? '01' : '00'}</strong><span>Hinweis{warning ? '' : 'e'}</span></div><button className="nd-connection" onClick={() => setPanel('network')}><i className="nd-dot" /> Gateway → Decoder → Zuhause <ArrowUpRight size={14} /></button></section>
      <div className="nd-focus">
        <section className="nd-incident" style={!warning ? { background: '#e0e8dc' } : undefined}>
          <div className="nd-kicker">{warning ? <BatteryLow size={14} /> : <CircleCheck size={14} />}{warning ? 'Braucht Aufmerksamkeit / 01' : 'Netzwerk in Ordnung'}</div>
          <div className="nd-radar">{warning ? <BatteryLow /> : <Radio />}</div>
          <h2>{warning ? <>Ein Signal fehlt.<br />Der Rest läuft.</> : <>Alle Signale da.<br />Alles läuft.</>}</h2>
          <p>{warning ? 'Füllstand Keller sendet seit 3 Stunden nicht mehr. Die letzte Batteriemeldung lag bei 18 %.' : 'Deine Sensoren senden wieder. Alle Messwerte erreichen Home Assistant über deinen Datenweg.'}</p>
          <div className="nd-incident-bottom"><button className="nd-btn" onClick={() => { if (warning) { setChecked(false); setPanel('diagnose'); } else setPanel('network'); }}>{warning ? 'Ursache prüfen' : 'Datenweg ansehen'}<ArrowRight size={14} /></button><span>{warning ? 'KELLER · FEBRIS' : 'ZU LETZT GERADE EBEN'}</span></div>
        </section>
        <section className="nd-feed"><div className="nd-section-title"><h3>Was gerade ankommt</h3><span className="nd-live"><i className="nd-dot" />LIVE</span></div>
          {(!warning ? [{ time: '14:09', title: 'Füllstand Keller ist zurück', sub: '63.2 % · an Home Assistant übertragen' }] : []).concat([{ time: '14:08', title: 'Temperatur Büro aktualisiert', sub: '22.4 °C · an Home Assistant übertragen' }, { time: '14:08', title: 'Luftfeuchte Lager aktualisiert', sub: '48.7 % · an Home Assistant übertragen' }, { time: '14:07', title: 'Gateway Dach verbunden', sub: 'Empfang stabil · 2 Decoder einsatzbereit' }]).slice(0,3).map(event => <div className="nd-event" key={event.title}><time>{event.time}</time><div><strong><CircleCheck size={13} color="#698471" />{event.title}</strong><p>{event.sub}</p></div></div>)}
        </section>
      </div>
      <section className="nd-fleet"><div className="nd-fleet-head"><h3>Deine Sensoren <span style={{ color: '#8d9697', marginLeft: 7 }}>{sensors.length.toString().padStart(2, '0')}</span></h3><div className="nd-tabs">{['Alle', 'Aktiv', 'Prüfen'].map(t => <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>{t}{t === 'Prüfen' && warning ? ' · 1' : ''}</button>)}</div><label className="nd-search"><Search size={14} /><input aria-label="Sensor suchen" placeholder="Name oder EUI suchen" value={search} onChange={e => setSearch(e.target.value)} /></label></div>
        <table className="nd-table"><thead><tr><th>Sensor / EUI</th><th>Messwert</th><th>Batterie</th><th>Empfang</th><th>Zuletzt</th><th /></tr></thead><tbody>{visible.map(s => <tr key={s.id} tabIndex={0} role="button" aria-label={`${s.name} ansehen`} onClick={() => { setSelected(s); setPanel('sensor'); }} onKeyDown={e => { if (e.key === 'Enter') { setSelected(s); setPanel('sensor'); } }}><td><div className="nd-device">{s.warning ? <BatteryLow size={17} color="#b5754d" /> : s.unit === '%' ? <Droplets size={17} /> : <Thermometer size={17} />}<div><strong>{s.name}</strong><small>{s.id}</small></div></div></td><td className="nd-reading">{s.value} <small>{s.unit}</small></td><td className="nd-mono">{s.battery}</td><td><span className={`nd-pill ${s.warning ? 'warn' : ''}`}><i className="nd-dot" />{s.warning ? 'Kein Signal' : 'Verbunden'}</span></td><td style={{ color: '#78828a' }}>{s.ago}</td><td><ChevronRight size={14} /></td></tr>)}</tbody></table>
        {!visible.length && <div className="nd-empty"><Search size={23} style={{ margin: '0 auto 10px' }} /><p>Hier gibt es keine passenden Sensoren.</p><button className="nd-btn light" style={{ marginTop: 15 }} onClick={() => { setSearch(''); setTab('Alle'); }}>Alle Sensoren anzeigen</button></div>}
      </section>
      <footer><span>LIVE-ANSICHT · BEISPIELDATEN · LOKALER DEMO-WORKSPACE</span><span>mioty Application Center / by sentinum</span></footer>
    </main>
    {panel && <div className="nd-overlay" onClick={() => setPanel(null)}><aside className="nd-drawer" role="dialog" aria-modal="true" aria-label={panel === 'diagnose' ? 'Sensordiagnose' : panel === 'add' ? 'Sensor verbinden' : 'Netzwerkdetails'} onClick={e => e.stopPropagation()}><div className="nd-drawer-top"><span className="nd-kicker">{panel === 'diagnose' ? 'AUFMERKSAMKEIT / 01' : 'DEIN WORKSPACE'}</span><button className="nd-icon" aria-label="Schließen" onClick={() => setPanel(null)}><X size={16} /></button></div>
      {panel === 'diagnose' && <><h2>Das Signal<br />zurückholen.</h2><p>Füllstand Keller · Sentinum Febris<br />Die Batterie ist die wahrscheinlichste Ursache. Dein Gateway und der Decoder funktionieren.</p><div className="nd-check"><span><Check size={15} /> Gateway empfängt</span><span className="nd-pill">In Ordnung</span></div><div className="nd-check"><span><Check size={15} /> Febris-Decoder</span><span className="nd-pill">Bereit</span></div><div className="nd-check"><span><BatteryLow size={15} /> Sensorbatterie</span><span className="nd-pill warn">18 % · prüfen</span></div><label style={{ display: 'flex', gap: 10, alignItems: 'center', lineHeight: 1.6 }}><input type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)} /> Stromversorgung am Sensor geprüft</label><p>Demo: Nach der Prüfung kannst du ein neues Testsignal simulieren. Es werden keine echten Geräte verändert.</p><button className="nd-btn" disabled={!checked} style={{ opacity: checked ? 1 : .4 }} onClick={resolve}>Testsignal simulieren <Radio size={15} /></button></>}
      {panel === 'add' && <form onSubmit={e => { e.preventDefault(); add(); }}><h2>Ein neues Signal.</h2><p>Verbinde einen Sensor mit deinem Demo-Netzwerk. Die Zuordnung übernehmen wir.</p><label>Sensorname<input autoFocus value={name} onChange={e => setName(e.target.value)} placeholder="z. B. Temperatur Werkstatt" /></label><label>Geräte-EUI<input value={eui} onChange={e => setEui(e.target.value)} maxLength={16} placeholder="fca84a090000005f" /></label><label>Decoder<select><option>Sentinum · Juno-TH</option></select></label><div className="nd-check"><span>Gateway Dach</span><ArrowRight size={14} /><span>Home Assistant</span></div>{error && <div role="alert" className="nd-error">{error}</div>}<button className="nd-btn" type="submit">Im Demo-Workspace verbinden <Plus size={15} /></button></form>}
      {panel === 'network' && <><h2>Der Weg nach Hause.</h2><p>Jede Nachricht durchläuft drei Stationen. Hier siehst du, ob die Verbindungen stehen.</p>{[{ icon: Antenna, title: 'Gateway Dach', sub: 'BSSCI · Empfang aktiv' }, { icon: Cpu, title: 'Juno-TH & Febris', sub: '2 Decoder · einsatzbereit' }, { icon: House, title: 'Home Assistant', sub: 'MQTT · homeassistant.local:1883' }].map(s => <div key={s.title} className="nd-check"><span><s.icon size={21} /><span style={{ display: 'block' }}>{s.title}<small style={{ display: 'block', color: '#78828a', marginTop: 6 }}>{s.sub}</small></span></span><Check size={15} color="#527b68" /></div>)}<button className="nd-btn" onClick={() => setTested(true)}><Activity size={15} />{tested ? 'Erneut prüfen' : 'Verbindungen prüfen'}</button>{tested && <p style={{ color: '#527b68', marginTop: 17 }} role="status">Alle drei Stationen erreichbar. Test erfolgreich.</p>}</>}
      {panel === 'settings' && <><h2>Dein Netzwerk.<br />Deine Regeln.</h2><p>Einstellungen für den lokalen Demo-Workspace. Deine produktive Konfiguration bleibt unverändert.</p><div className="nd-check"><span>MQTT Auto Discovery</span><input aria-label="MQTT Auto Discovery" type="checkbox" checked={discovery} onChange={e => setDiscovery(e.target.checked)} /></div><div className="nd-check"><span>Service Center</span><span className="nd-pill">Verbunden</span></div><button className="nd-btn" onClick={() => setPanel(null)}>Einstellungen übernehmen <Check size={15} /></button></>}
      {panel === 'sensor' && <><div className="nd-kicker" style={{ marginBottom: 12 }}>{selected.room} / SENTINUM</div><h2>{selected.name}</h2><div className="nd-mono" style={{ color: '#78828a' }}>{selected.id}</div><div className="nd-bigvalue">{selected.value}<span style={{ fontSize: 24 }}>{selected.unit}</span></div>{!selected.warning && selected.value !== '—' && <svg className="nd-graph" viewBox="0 0 340 90" preserveAspectRatio="none" aria-label="Messwertverlauf"><path d="M0 74L15 62L30 67L45 52L60 60L75 45L90 50L105 39L120 46L135 31L150 36L165 22L180 29L195 18L210 24L225 15L240 22L255 13L270 19L285 9L300 16L320 6L340 11" stroke="#72918c" strokeWidth="2" fill="none" /></svg>}<div className="nd-check"><span>Letzter Empfang</span><strong>{selected.ago}</strong></div><div className="nd-check"><span>Batterie</span><strong>{selected.battery}</strong></div><div className="nd-check"><span>Signalstärke</span><strong>{selected.signal} dBm</strong></div><div className="nd-check"><span>Basisstation</span><strong>Gateway Dach</strong></div><button className="nd-btn" onClick={() => { if (selected.warning) { setChecked(false); setPanel('diagnose'); } else setPanel('network'); }}>{selected.warning ? 'Ursache prüfen' : 'Datenweg überprüfen'}<ArrowRight size={15} /></button></>}
    </aside></div>}
  </div>;
}
