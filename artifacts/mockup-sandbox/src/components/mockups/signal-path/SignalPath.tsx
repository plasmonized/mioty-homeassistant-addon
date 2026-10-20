import { useState } from 'react';
import { Radio, ArrowRight, Plus, Search, Settings2, X, Check, Activity, Thermometer, Droplets, Cpu, House, Antenna, ChevronRight, Battery, AlertTriangle, Cable, ShieldCheck, CheckCircle2 } from 'lucide-react';
import './signalpath.css';

type Device = { id: string; name: string; location: string; value: string; unit: string; ago: string; battery: string; signal: string; warning?: boolean };
const startingDevices: Device[] = [
  { id: 'fca84a090000002b', name: 'Temperatur Büro', location: 'Sentinum · Juno-TH', value: '22.4', unit: '°C', ago: 'vor 12 s', battery: '94 %', signal: '−87 dBm' },
  { id: 'fca84a090000003e', name: 'Luftfeuchte Lager', location: 'Sentinum · Juno-TH', value: '48.7', unit: '%', ago: 'vor 34 s', battery: '87 %', signal: '−92 dBm' },
  { id: 'fca84a090000004a', name: 'Temperatur Außen', location: 'Sentinum · Juno-TH', value: '16.8', unit: '°C', ago: 'vor 1 min', battery: '76 %', signal: '−103 dBm' },
  { id: 'fca84a090000001c', name: 'Füllstand Keller', location: 'Sentinum · Febris', value: '—', unit: '', ago: 'vor 3 Std.', battery: '18 %', signal: '−114 dBm', warning: true },
];
const stages = [
  { label: 'Sensoren', sub: '3 von 4 aktiv', icon: Radio },
  { label: 'Basisstation', sub: '1 verbunden', icon: Antenna },
  { label: 'Decoder', sub: '2 einsatzbereit', icon: Cpu },
  { label: 'Home Assistant', sub: 'MQTT verbunden', icon: House },
];

export function SignalPath() {
  const [stage, setStage] = useState(0);
  const [devices, setDevices] = useState(startingDevices);
  const [selectedId, setSelectedId] = useState(startingDevices[0].id);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('Alle');
  const [dialog, setDialog] = useState<'add' | 'settings' | null>(null);
  const [step, setStep] = useState(1);
  const [name, setName] = useState('');
  const [eui, setEui] = useState('');
  const [error, setError] = useState('');
  const [resolved, setResolved] = useState(false);
  const [autoDiscovery, setAutoDiscovery] = useState(true);
  const [diagnosed, setDiagnosed] = useState(false);
  const selected = devices.find(d => d.id === selectedId) || devices[0];
  const visible = devices.filter(d => (d.name + d.id).toLowerCase().includes(query.toLowerCase()) && (filter === 'Alle' || (filter === 'Aktiv' ? !d.warning : d.warning)));
  const showWarning = !resolved && devices.some(d => d.warning);

  function addDevice() {
    if (step === 1) {
      if (!name.trim() || !/^[a-fA-F0-9]{16}$/.test(eui)) { setError('Name und eine gültige EUI mit 16 Hex-Zeichen eingeben.'); return; }
      if (devices.some(d => d.id === eui)) { setError('Diese EUI ist bereits registriert.'); return; }
      setError(''); setStep(2); return;
    }
    setDevices(d => [...d, { id: eui, name, location: 'Sentinum · Juno-TH', value: '—', unit: '', ago: 'Warte auf Daten', battery: '—', signal: '—' }]);
    setSelectedId(eui); setDialog(null); setStage(0); setFilter('Alle'); setQuery('');
  }
  function openAdd() { setName(''); setEui(''); setStep(1); setError(''); setDialog('add'); }

  return <div className="sp-app">
    <header className="sp-top">
      <div className="sp-brand"><Radio size={23} strokeWidth={1.8} /> mioty<span>APPLICATION CENTER</span></div>
      <div className="sp-top-right"><span className="sp-demo">DEMO-WORKSPACE</span><span><i className="sp-dot" />System online</span><button aria-label="Einstellungen öffnen" className="sp-icon-btn" onClick={() => setDialog('settings')}><Settings2 size={15} /></button></div>
    </header>
    <main className="sp-main">
      <div className="sp-heading">
        <div><div className="sp-overline">BETRIEBSÜBERSICHT / 01</div><h1>Vom Signal zum Zuhause.</h1><p>Dein Sensornetz. Ein durchgängiger Datenweg.</p></div>
        <button className="sp-primary" onClick={openAdd}><Plus size={13} /> Sensor verbinden</button>
      </div>

      <section className="sp-map" aria-label="Interaktiver Datenweg">
        {stages.map((item, index) => <button key={item.label} className={`sp-stage ${stage === index ? 'active' : ''}`} aria-pressed={stage === index} onClick={() => { setStage(index); setDiagnosed(false); }}>
          <span className="sp-stage-icon"><item.icon size={21} strokeWidth={1.4} /></span>
          {index === 0 && showWarning && <span className="sp-stage-number">1</span>}
          <strong>{item.label}</strong><small>{index === 0 ? `${devices.filter(d => !d.warning).length} von ${devices.length} aktiv` : item.sub}</small>
        </button>)}
      </section>

      {showWarning ? <div className="sp-attention"><AlertTriangle size={13} /><span><strong>Ein Sensor braucht Aufmerksamkeit.</strong> Seit 3 Stunden kein Signal.</span><button onClick={() => { setStage(0); setSelectedId(startingDevices[3].id); setFilter('Prüfen'); }}>Prüfen <ArrowRight size={12} /></button></div>
      : <div className="sp-attention" style={{ background: '#e3eddb', borderColor: '#c8d8bf', color: '#4b7455' }}><ShieldCheck size={14} /><span>Alle Sensoren senden. Dein Datenweg ist vollständig.</span><Check size={13} /></div>}

      {stage === 0 ? <div className="sp-workspace">
        <section>
          <div className="sp-section-head"><h2>Deine Sensoren</h2><span className="sp-count">{devices.length.toString().padStart(2, '0')}</span></div>
          <label className="sp-search"><Search size={13} /><input aria-label="Sensoren durchsuchen" placeholder="Name oder EUI suchen" value={query} onChange={e => setQuery(e.target.value)} /><span style={{ fontSize: 8 }}>⌕</span></label>
          <div className="sp-filters">{['Alle', 'Aktiv', 'Prüfen'].map(f => <button key={f} onClick={() => setFilter(f)} className={`sp-filter ${filter === f ? 'active' : ''}`}>{f}{f === 'Prüfen' && showWarning ? ' · 1' : ''}</button>)}</div>
          <div>{visible.map(d => <button key={d.id} className={`sp-device ${selectedId === d.id ? 'active' : ''}`} onClick={() => { setSelectedId(d.id); setDiagnosed(false); }}>
            <span className="sp-device-icon">{d.warning ? <Battery size={14} color="#aa7142" /> : d.unit === '%' ? <Droplets size={14} /> : <Thermometer size={14} />}</span>
            <span className="sp-device-info"><strong>{d.name}</strong><small>{d.location}</small></span>
            <span className="sp-device-value">{d.value}<span style={{ fontSize: 8 }}> {d.unit}</span><small>{d.warning ? <i className="sp-dot" style={{ background: '#bb8751' }} /> : <i className="sp-dot" />}{d.ago}</small></span><ChevronRight size={11} color="#8fa08f" />
          </button>)}{!visible.length && <div className="sp-empty"><Search size={22} style={{ margin: '0 auto 8px' }} />Keine passenden Sensoren.<br /><button className="sp-text-btn" onClick={() => { setQuery(''); setFilter('Alle'); }}>Filter zurücksetzen</button></div>}</div>
        </section>
        <aside className="sp-detail" key={selected.id}>
          <div className="sp-detail-head"><div><h3>{selected.name}</h3><div className="sp-mono">{selected.id}</div></div><span className="sp-online" style={selected.warning ? { background: '#eee0c6', color: '#966f38' } : {}}>{selected.warning ? 'Kein Signal' : 'Verbunden'}</span></div>
          <div className="sp-reading"><strong>{selected.value}<small>{selected.unit}</small></strong><span>{selected.warning ? 'Letzter Empfang vor 3 Std.' : '↗ +0.3 seit 08:00'}</span></div>
          <svg className="sp-chart" viewBox="0 0 270 50" preserveAspectRatio="none" aria-label="Messwertverlauf der letzten 6 Stunden"><defs><linearGradient id="sp-fill" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#bdd1ad" stopOpacity=".5" /><stop offset="1" stopColor="#bdd1ad" stopOpacity="0" /></linearGradient></defs><path d="M0 39L12 35L23 36L35 28L47 30L59 24L70 30L82 28L94 32L106 20L118 23L130 21L142 26L154 17L166 19L178 11L190 15L202 9L214 15L226 9L238 13L251 5L270 8V50H0Z" fill="url(#sp-fill)" /><path d="M0 39L12 35L23 36L35 28L47 30L59 24L70 30L82 28L94 32L106 20L118 23L130 21L142 26L154 17L166 19L178 11L190 15L202 9L214 15L226 9L238 13L251 5L270 8" fill="none" stroke={selected.warning ? '#b78b55' : '#62876c'} strokeWidth="1.6" strokeDasharray={selected.warning ? '3 3' : undefined} /></svg>
          <div className="sp-chart-labels"><span>08:00</span><span>11:00</span><span>14:00</span></div>
          <div className="sp-detail-meta"><div><small>BATTERIE</small><strong>{selected.battery}</strong></div><div><small>SIGNALSTÄRKE</small><strong>{selected.signal}</strong></div><div><small>BASISSTATION</small><strong>Gateway Dach</strong></div><div><small>DECODER</small><strong>{selected.location.split(' · ')[1]}</strong></div></div>
          {selected.warning ? <div style={{ marginTop: 13 }}><p style={{ color: '#9b7244', fontSize: 10, lineHeight: 1.5 }}>Batterie schwach. Prüfe die Stromversorgung und sende ein Testsignal.</p><button className="sp-primary" style={{ width: '100%' }} onClick={() => { setDevices(ds => ds.map(d => d.id === selected.id ? { ...d, warning: false, value: '63.2', unit: '%', ago: 'gerade eben', battery: '98 %' } : d)); setResolved(true); setFilter('Alle'); }}>Testsignal simulieren <ArrowRight size={12} /></button></div> : <div className="sp-path"><CheckCircle2 size={12} /><span>Empfangen</span><ArrowRight size={9} /><span>Decodiert</span><ArrowRight size={9} /><House size={11} /><span>Übertragen</span></div>}
        </aside>
      </div> : <div className="sp-workspace">
        <section>
          <div className="sp-section-head"><h2>{stages[stage].label}</h2><span className="sp-count">{stage === 2 ? '02' : '01'}</span></div>
          {(stage === 1 ? [{ title: 'Gateway Dach', subtitle: 'BSSCI · fca84a00000192bd', value: 'Online' }] : stage === 2 ? [{ title: 'Juno-TH', subtitle: 'Temperatur & Luftfeuchte · 3 Sensoren', value: 'Aktiv' }, { title: 'Febris', subtitle: 'Füllstand · 1 Sensor', value: 'Aktiv' }] : [{ title: 'MQTT Broker', subtitle: 'homeassistant.local:1883', value: 'Online' }, { title: 'Auto Discovery', subtitle: 'Sensoren automatisch registrieren', value: autoDiscovery ? 'Aktiv' : 'Pausiert' }]).map((item, i) => <div className="sp-device" key={item.title}><span className="sp-device-icon">{stage === 1 ? <Antenna size={15} /> : stage === 2 ? <Cpu size={15} /> : <Cable size={15} />}</span><span className="sp-device-info"><strong>{item.title}</strong><small>{item.subtitle}</small></span><span className="sp-online">{item.value}</span>{stage === 3 && i === 1 && <button className="sp-icon-btn" aria-label="Auto Discovery umschalten" onClick={() => setAutoDiscovery(!autoDiscovery)}><Settings2 size={13} /></button>}</div>)}
          <p style={{ color: '#7b8b80', fontSize: 10, lineHeight: 1.7, marginTop: 17 }}>Wähle einen anderen Schritt im Datenweg, um Sensoren, Empfang und Verarbeitung zusammen zu prüfen.</p>
        </section>
        <aside className="sp-detail"><div className="sp-overline">VERBINDUNGSDIAGNOSE</div><h3>{stage === 1 ? 'Empfang steht.' : stage === 2 ? 'Jedes Byte lesbar.' : 'Zu Hause angekommen.'}</h3><p style={{ color: '#738582', fontSize: 11, lineHeight: 1.7, margin: '12px 0 20px' }}>{stage === 1 ? 'Deine Basisstation empfängt mioty-Nachrichten und leitet sie an das Service Center weiter.' : stage === 2 ? 'Die passenden Decoder übersetzen Payloads in Messwerte für Home Assistant.' : 'Messwerte werden über MQTT veröffentlicht und als Entitäten in Home Assistant erkannt.'}</p><div className="sp-path"><CheckCircle2 size={14} />{diagnosed ? 'Test erfolgreich · alle Prüfungen bestanden' : 'Letzte Prüfung heute um 14:03'}</div><button className="sp-primary" style={{ marginTop: 15 }} onClick={() => setDiagnosed(true)}><Activity size={13} />{diagnosed ? 'Erneut testen' : 'Verbindung testen'}</button></aside>
      </div>}
      <footer className="sp-footer"><span><Activity size={10} />Live-Ansicht · Beispieldaten</span><span>mioty Application Center <span style={{ color: '#486d5e', marginLeft: 8 }}>by sentinum</span></span></footer>
    </main>

    {dialog && <div className="sp-dialog-backdrop" onClick={() => setDialog(null)}><section role="dialog" aria-modal="true" aria-label={dialog === 'add' ? 'Sensor verbinden' : 'Einstellungen'} className="sp-dialog" onClick={e => e.stopPropagation()}>
      <div className="sp-dialog-title"><span className="sp-overline">{dialog === 'add' ? `SENSOR VERBINDEN / 0${step}` : 'WORKSPACE'}</span><button className="sp-icon-btn" aria-label="Schließen" onClick={() => setDialog(null)}><X size={17} /></button></div>
      {dialog === 'settings' ? <><h2>Dein Datenweg.</h2><p>Einstellungen für diesen Demo-Workspace. Deine produktive Konfiguration bleibt unverändert.</p><div className="sp-settings-row"><span>MQTT Auto Discovery</span><input aria-label="Auto Discovery" type="checkbox" checked={autoDiscovery} onChange={e => setAutoDiscovery(e.target.checked)} style={{ width: 16, margin: 0 }} /></div><div className="sp-settings-row"><span>Service Center</span><span className="sp-online">Verbunden</span></div><button className="sp-primary" onClick={() => setDialog(null)}>Einstellungen übernehmen <Check size={13} /></button></> :
      <form onSubmit={e => { e.preventDefault(); addDevice(); }}>
        <h2>{step === 1 ? 'Ein neues Signal.' : 'Bereit für dein Zuhause.'}</h2>
        <p>{step === 1 ? 'Verbinde einen mioty-Sensor mit deinem Datenweg.' : 'Prüfe die Zuordnung. Der Sensor wird lokal zum Demo-Workspace hinzugefügt.'}</p>
        {step === 1 ? <><label>Sensorname<input autoFocus value={name} onChange={e => setName(e.target.value)} placeholder="z. B. Temperatur Werkstatt" /></label><label>Geräte-EUI<input value={eui} onChange={e => setEui(e.target.value)} maxLength={16} placeholder="fca84a090000005f" style={{ fontFamily: "'Space Mono',monospace" }} /></label><label>Decoder<select><option>Sentinum · Juno-TH</option></select></label></> : <><div className="sp-settings-row"><span>Sensor</span><strong>{name}</strong></div><div className="sp-settings-row"><span>EUI</span><span className="sp-mono">{eui}</span></div><div className="sp-settings-row"><span>Datenweg</span><span>Gateway Dach → Home Assistant</span></div></>}
        {error && <div className="sp-error" role="alert">{error}</div>}
        <button type="submit" className="sp-primary">{step === 1 ? 'Weiter zur Zuordnung' : 'Sensor im Demo-Workspace verbinden'}<ArrowRight size={13} /></button>{step === 2 && <button type="button" className="sp-text-btn" onClick={() => setStep(1)}>Zurück</button>}
      </form>}
    </section></div>}
  </div>;
}
