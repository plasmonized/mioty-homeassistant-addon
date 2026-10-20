import { useMemo, useState } from 'react';
import {
  Activity, AlertTriangle, ArrowRight, ArrowUpRight, Antenna, BatteryLow, Check,
  CheckCircle2, ChevronRight, Cpu, Droplets, House, Plus, Radio, Search,
  Settings2, ShieldCheck, Thermometer, X,
} from 'lucide-react';
import './signalpath.css';

type Sensor = {
  id: string; name: string; room: string; value: string; unit: string;
  battery: string; signal: string; ago: string; warning?: boolean;
};
const initialSensors: Sensor[] = [
  { id: 'fca84a090000001c', name: 'Füllstand Keller', room: 'Keller', value: '—', unit: '', battery: '18 %', signal: '−114 dBm', ago: 'vor 3 Std.', warning: true },
  { id: 'fca84a090000002b', name: 'Temperatur Büro', room: 'Büro', value: '22.4', unit: '°C', battery: '94 %', signal: '−87 dBm', ago: 'vor 12 s' },
  { id: 'fca84a090000003e', name: 'Luftfeuchte Lager', room: 'Lager', value: '48.7', unit: '%', battery: '87 %', signal: '−92 dBm', ago: 'vor 34 s' },
  { id: 'fca84a090000004a', name: 'Temperatur Außen', room: 'Außen', value: '16.8', unit: '°C', battery: '76 %', signal: '−103 dBm', ago: 'vor 1 Min.' },
];
const routeStages = [
  { label: 'Sensor', detail: 'mioty', Icon: Radio },
  { label: 'Basisstation', detail: 'Gateway Dach', Icon: Antenna },
  { label: 'Decoder', detail: 'Payload → Messwert', Icon: Cpu },
  { label: 'Zuhause', detail: 'Home Assistant', Icon: House },
];
type Panel = 'diagnose' | 'add' | 'network' | 'settings' | 'sensor' | null;

export function SignalPath() {
  const [sensors, setSensors] = useState(initialSensors);
  const [selectedId, setSelectedId] = useState(initialSensors[0].id);
  const [panel, setPanel] = useState<Panel>(null);
  const [search, setSearch] = useState('');
  const [tab, setTab] = useState('Alle');
  const [checked, setChecked] = useState(false);
  const [tested, setTested] = useState(false);
  const [discovery, setDiscovery] = useState(true);
  const [name, setName] = useState('');
  const [eui, setEui] = useState('');
  const [error, setError] = useState('');
  const [newSignal, setNewSignal] = useState(false);
  const selected = sensors.find(sensor => sensor.id === selectedId) ?? sensors[0];
  const warning = sensors.some(sensor => sensor.warning);
  const visibleSensors = useMemo(() => sensors.filter(sensor =>
    (tab === 'Alle' || (tab === 'Prüfen' ? sensor.warning : !sensor.warning))
    && `${sensor.name} ${sensor.id}`.toLowerCase().includes(search.toLowerCase())
  ), [sensors, tab, search]);

  function startAdd() {
    setName(''); setEui(''); setError(''); setPanel('add');
  }
  function addSensor(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !/^[a-fA-F0-9]{16}$/.test(eui)) {
      setError('Bitte einen Namen und eine EUI mit 16 Hex-Zeichen eingeben.');
      return;
    }
    if (sensors.some(sensor => sensor.id.toLowerCase() === eui.toLowerCase())) {
      setError('Diese EUI ist bereits verbunden.');
      return;
    }
    const sensor = { id: eui, name: name.trim(), room: 'Neu', value: '—', unit: '', battery: '—', signal: '—', ago: 'Warte auf Daten' };
    setSensors(current => [...current, sensor]);
    setSelectedId(eui); setTab('Alle'); setSearch(''); setPanel(null);
  }
  function resolveWarning() {
    setSensors(current => current.map(sensor => sensor.warning
      ? { ...sensor, warning: false, value: '63.2', unit: '%', battery: '98 %', ago: 'gerade eben' }
      : sensor));
    setTab('Alle'); setPanel(null); setChecked(false);
  }

  return <div className="sp-shell">
    <header className="sp-header">
      <div className="sp-brand"><Radio size={27} strokeWidth={1.7} /><span>mioty</span><small>APPLICATION<br />CENTER</small></div>
      <div className="sp-header-right"><span className="sp-workspace-state"><i className="sp-dot" />Workspace verbunden</span><span className="sp-kicker">DEMO / 01</span><button className="sp-icon" aria-label="Einstellungen öffnen" onClick={() => setPanel('settings')}><Settings2 size={16} /></button></div>
    </header>
    <main className="sp-main">
      <div className="sp-heading">
        <div><div className="sp-kicker">DEIN NETZWERK · LIVE-ÜBERSICHT</div><h1>Vom Signal zum Zuhause.</h1><p>Ein klarer Blick auf den Weg deiner Sensordaten.</p></div>
        <button className="sp-button" onClick={startAdd}><Plus size={15} />Sensor verbinden</button>
      </div>

      <section className="sp-summary" aria-label="Netzwerkübersicht">
        <div className="sp-stat"><strong>{sensors.filter(sensor => !sensor.warning).length}<span> / {sensors.length}</span></strong><small>Sensoren aktiv</small></div>
        <div className="sp-stat"><strong className={warning ? 'sp-warn-value' : ''}>{sensors.filter(sensor => sensor.warning).length.toString().padStart(2, '0')}</strong><small>Hinweise</small></div>
        <button className="sp-route-shortcut" onClick={() => setPanel('network')}><i className="sp-dot" />Sensor → Gateway → Decoder → Zuhause<ArrowUpRight size={14} /></button>
      </section>

      <section className="sp-route" aria-label="Datenweg vom Sensor nach Hause">
        {routeStages.map(({ label, detail, Icon }, index) => <div className="sp-route-step" key={label}>
          <span className={`sp-route-icon ${index === 3 ? 'home' : ''}`}><Icon size={18} strokeWidth={1.65} /></span>
          <span><strong>{label}</strong><small>{index === 0 ? `${sensors.length} Geräte · mioty` : detail}</small></span>
          {index < routeStages.length - 1 && <ArrowRight className="sp-route-arrow" size={15} />}
        </div>)}
        <button className="sp-route-open" aria-label="Datenweg im Detail öffnen" onClick={() => setPanel('network')}><ChevronRight size={16} /></button>
      </section>

      <div className="sp-focus">
        <section className={`sp-incident ${warning ? '' : 'healthy'}`}>
          <div className="sp-kicker">{warning ? <><AlertTriangle size={14} />BRAUCHT AUFMERKSAMKEIT / 01</> : <><ShieldCheck size={14} />DATENWEG IN ORDNUNG</>}</div>
          <div className="sp-radar" aria-hidden="true"><Radio size={25} /></div>
          <h2>{warning ? <>Ein Signal fehlt.<br />Der Rest läuft.</> : <>Alle Signale da.<br />Alles läuft.</>}</h2>
          <p>{warning
            ? 'Füllstand Keller meldet sich seit 3 Stunden nicht mehr. Gateway und Decoder sind erreichbar.'
            : 'Deine Sensoren senden. Die Messwerte laufen über den Datenweg bis in Home Assistant.'}</p>
          <div className="sp-incident-bottom">
            <button className="sp-button" onClick={() => { if (warning) { setChecked(false); setPanel('diagnose'); } else setPanel('network'); }}>{warning ? 'Signal untersuchen' : 'Datenweg ansehen'}<ArrowRight size={14} /></button>
            <span>{warning ? 'KELLER · MIOTY' : 'LETZTES SIGNAL GERADE EBEN'}</span>
          </div>
        </section>
        <section className="sp-feed">
          <div className="sp-section-title"><h3>Was gerade ankommt</h3><span className="sp-live"><i className="sp-dot" />LIVE</span></div>
          {(warning ? [
            { time: '14:08', title: 'Temperatur Büro aktualisiert', detail: '22.4 °C · an Home Assistant übertragen' },
            { time: '14:08', title: 'Luftfeuchte Lager aktualisiert', detail: '48.7 % · an Home Assistant übertragen' },
            { time: '11:12', title: 'Letztes Signal Füllstand Keller', detail: 'Batterie 18 % · Gateway erreichbar' },
          ] : [
            { time: '14:09', title: 'Füllstand Keller ist zurück', detail: '63.2 % · an Home Assistant übertragen' },
            { time: '14:08', title: 'Temperatur Büro aktualisiert', detail: '22.4 °C · an Home Assistant übertragen' },
            { time: '14:07', title: 'Gateway Dach verbunden', detail: 'mioty-Empfang stabil · 2 Decoder bereit' },
          ]).map(event => <div className="sp-event" key={event.title}><time>{event.time}</time><div><strong><CheckCircle2 size={13} />{event.title}</strong><p>{event.detail}</p></div></div>)}
        </section>
      </div>

      <section className="sp-fleet">
        <div className="sp-fleet-head">
          <h3>Deine Sensoren <span>{sensors.length.toString().padStart(2, '0')}</span></h3>
          <div className="sp-tabs">{['Alle', 'Aktiv', 'Prüfen'].map(item => <button key={item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>{item}{item === 'Prüfen' && warning ? ' · 1' : ''}</button>)}</div>
          <label className="sp-search"><Search size={14} /><input aria-label="Sensoren suchen" placeholder="Name oder EUI suchen" value={search} onChange={event => setSearch(event.target.value)} /></label>
        </div>
        <div className="sp-table-wrap"><table className="sp-table">
          <thead><tr><th>Sensor / EUI</th><th>Messwert</th><th>Batterie</th><th>Signal</th><th>Empfang</th><th /></tr></thead>
          <tbody>{visibleSensors.map(sensor => <tr key={sensor.id} tabIndex={0} role="button" aria-label={`${sensor.name} öffnen`} onClick={() => { setSelectedId(sensor.id); setPanel('sensor'); }} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelectedId(sensor.id); setPanel('sensor'); } }}>
            <td><div className="sp-device"><span className="sp-device-icon">{sensor.warning ? <BatteryLow size={17} /> : sensor.unit === '%' ? <Droplets size={17} /> : <Thermometer size={17} />}</span><span><strong>{sensor.name}</strong><small>{sensor.id}</small></span></div></td>
            <td className="sp-reading">{sensor.value} <small>{sensor.unit}</small></td><td className="sp-mono">{sensor.battery}</td><td className="sp-mono">{sensor.signal}</td>
            <td><span className={`sp-pill ${sensor.warning ? 'warning' : ''}`}><i className="sp-dot" />{sensor.warning ? 'Kein Signal' : sensor.ago}</span></td><td><ChevronRight size={14} /></td>
          </tr>)}</tbody>
        </table></div>
        {!visibleSensors.length && <div className="sp-empty"><Search size={22} /><p>Keine passenden Sensoren gefunden.</p><button className="sp-button secondary" onClick={() => { setSearch(''); setTab('Alle'); }}>Filter zurücksetzen</button></div>}
      </section>
      <footer className="sp-footer"><span>LIVE-ANSICHT · BEISPIELDATEN · LOKALER DEMO-WORKSPACE</span><span>mioty Application Center</span></footer>
    </main>

    {panel && <div className="sp-overlay" onClick={() => setPanel(null)}><aside className="sp-drawer" role="dialog" aria-modal="true" aria-label={panel === 'diagnose' ? 'Signaldetails' : panel === 'add' ? 'Sensor verbinden' : panel === 'sensor' ? 'Sensorwerte' : 'Datenweg'} onClick={event => event.stopPropagation()}>
      <div className="sp-drawer-top"><span className="sp-kicker">{panel === 'diagnose' ? 'SIGNAL PRÜFEN / 01' : panel === 'add' ? 'NEUER SENSOR' : 'DEIN DATENWEG'}</span><button className="sp-icon" aria-label="Schließen" onClick={() => setPanel(null)}><X size={16} /></button></div>
      {panel === 'diagnose' && <><h2>Das Signal zurückholen.</h2><p>Füllstand Keller · mioty-Sensor. Gateway und Decoder funktionieren; die Batterie ist die wahrscheinlichste Ursache.</p><div className="sp-check"><span><Check size={15} />Gateway Dach</span><span className="sp-pill">Erreichbar</span></div><div className="sp-check"><span><Check size={15} />Febris-Decoder</span><span className="sp-pill">Bereit</span></div><div className="sp-check"><span><BatteryLow size={15} />Sensorbatterie</span><span className="sp-pill warning">18 % · prüfen</span></div><label className="sp-check-toggle"><input type="checkbox" checked={checked} onChange={event => setChecked(event.target.checked)} /> Stromversorgung am Sensor geprüft</label><p className="sp-disclaimer">Demo: Ein Testsignal verändert keine echten Geräte.</p><button className="sp-button full" disabled={!checked} onClick={resolveWarning}>Testsignal simulieren<Radio size={15} /></button></>}
      {panel === 'add' && <form onSubmit={addSensor}><h2>Ein neues Signal.</h2><p>Verbinde einen mioty-Sensor mit dem Demo-Netzwerk und ordne ihn dem Datenweg zu.</p><label>Sensorname<input autoFocus value={name} onChange={event => setName(event.target.value)} placeholder="z. B. Temperatur Werkstatt" /></label><label>Geräte-EUI<input value={eui} onChange={event => setEui(event.target.value)} maxLength={16} placeholder="fca84a090000005f" /></label><label>Decoder<select defaultValue="Juno-TH"><option value="Juno-TH">Juno-TH · Temperatur & Luftfeuchte</option><option value="Febris">Febris · Füllstand</option></select></label><div className="sp-check"><span>Gateway Dach</span><ArrowRight size={14} /><span>Home Assistant</span></div>{error && <div className="sp-error" role="alert">{error}</div>}<button className="sp-button full" type="submit">Im Demo-Netzwerk verbinden<Plus size={15} /></button></form>}
      {panel === 'network' && <><h2>Der Weg nach Hause.</h2><p>Deine Messwerte passieren vier Stationen vom Funksignal bis zu Home Assistant.</p>{routeStages.map(({ label, detail, Icon }, index) => <div className="sp-check" key={label}><span><Icon size={19} /><span>{label}<small>{index === 0 ? 'mioty · Sensoren aktiv' : detail}</small></span></span><CheckCircle2 size={15} /></div>)}<button className="sp-button full" onClick={() => setTested(true)}><Activity size={15} />{tested ? 'Erneut prüfen' : 'Datenweg prüfen'}</button>{tested && <p className="sp-test-result" role="status">Alle Stationen erreichbar. Test erfolgreich.</p>}</>}
      {panel === 'sensor' && <><div className="sp-kicker">MIOTY-SENSOR · {selected.room.toUpperCase()}</div><h2>{selected.name}</h2><p className="sp-mono">{selected.id}</p><div className="sp-big-value">{selected.value}<small>{selected.unit}</small></div><div className="sp-check"><span>Letzter Empfang</span><strong>{selected.ago}</strong></div><div className="sp-check"><span>Batterie</span><strong>{selected.battery}</strong></div><div className="sp-check"><span>Signalstärke</span><strong>{selected.signal}</strong></div><div className="sp-check"><span>Datenweg</span><strong>Gateway → Decoder → Zuhause</strong></div><button className="sp-button full" onClick={() => { setPanel(selected.warning ? 'diagnose' : 'network'); }}>Datenweg ansehen<ArrowRight size={15} /></button></>}
      {panel === 'settings' && <><h2>Verbindungen.</h2><p>Demo-Einstellungen für diesen lokalen Workspace.</p><div className="sp-check"><span>Home Assistant MQTT</span><span className="sp-pill">Verbunden</span></div><div className="sp-check"><span>Auto Discovery</span><input aria-label="Auto Discovery umschalten" type="checkbox" checked={discovery} onChange={event => setDiscovery(event.target.checked)} /></div><div className="sp-check"><span>Service Center</span><span className="sp-pill">Verbunden</span></div><button className="sp-button full" onClick={() => setPanel(null)}>Fertig<Check size={15} /></button></>}
    </aside></div>}
  </div>;
}
