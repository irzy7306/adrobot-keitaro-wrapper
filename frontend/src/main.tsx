import React, {useCallback, useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {api, message, type Item, type Campaign, type Stream} from './api';
import './style.css';

type Options = {domains: Item[]; groups: Item[]; traffic_sources: Item[]; offers: Item[]};
const initial: Options = {domains: [], groups: [], traffic_sources: [], offers: []};
const iso = (d: Date) => d.toISOString().slice(0, 10);
const prior = new Date(); prior.setDate(prior.getDate() - 7);

function App() {
  const [tab, setTab] = useState<'create'|'edit'>('create');
  const [options, setOptions] = useState<Options>(initial);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<{campaign: Campaign; streams: Stream[]}|null>(null);
  const [name, setName] = useState('campaign1');
  const [geo, setGeo] = useState('DE');
  const [domain, setDomain] = useState('');
  const [group, setGroup] = useState('');
  const [source, setSource] = useState('');
  const [offer, setOffer] = useState('');
  const [streamId, setStreamId] = useState('');
  const [newOffer, setNewOffer] = useState('');
  const [stats, setStats] = useState<unknown>(null);
  const [from, setFrom] = useState(iso(prior));
  const [to, setTo] = useState(iso(new Date()));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const run = async (task: () => Promise<void>) => {
    setBusy(true); setError(''); setSuccess('');
    try { await task(); } catch (e) { setError(message(e)); } finally { setBusy(false); }
  };
  const loadCampaigns = useCallback(async () => {
    const {data} = await api.get('/campaigns');
    setCampaigns(Array.isArray(data) ? data : data.data ?? []);
  }, []);
  const loadDetail = useCallback(async (id: number) => {
    const {data} = await api.get(`/campaigns/${id}`);
    setDetail(data);
    setStreamId(old => data.streams.some((s: Stream) => String(s.id) === old) ? old : String(data.streams.find((s: Stream) => s.schema === 'offers' || s.schema === 'landings_offers')?.id ?? ''));
  }, []);
  useEffect(() => {
    void Promise.all([api.get('/options'), api.get('/campaigns')]).then(([o, c]) => {
      setOptions(o.data);
      const arr = Array.isArray(c.data) ? c.data : c.data.data ?? [];
      setCampaigns(arr);
      setDomain(String(o.data.domains?.[0]?.id ?? ''));
      setGroup(String(o.data.groups?.[0]?.id ?? ''));
      setSource(String(o.data.traffic_sources?.[0]?.id ?? ''));
      setOffer(String(o.data.offers?.[0]?.id ?? ''));
      setNewOffer(String(o.data.offers?.[0]?.id ?? ''));
    }).catch(e => setError(message(e)));
  }, []);
  useEffect(() => { if (selected !== null) void loadDetail(selected).catch(e => setError(message(e))); }, [selected, loadDetail]);

  const create = () => run(async () => {
    const {data} = await api.post('/campaigns', {name, geo, offer_id: Number(offer), domain_id: Number(domain), group_id: Number(group), traffic_source_id: Number(source)});
    setSuccess(`Создана кампания #${data.campaign.id}; потоки: ${data.stream_ids.join(', ')}`);
    await loadCampaigns();
  });
  const add = () => run(async () => {
    if (selected === null) return;
    await api.post(`/campaigns/${selected}/offers`, {stream_id: Number(streamId), offer_id: Number(newOffer), share: 100});
    await loadDetail(selected); setStats(null); setSuccess('Оффер добавлен');
  });
  const remove = (id: number) => run(async () => {
    if (selected === null || !window.confirm(`Удалить оффер #${id} из этого потока?`)) return;
    await api.delete(`/campaigns/${selected}/offers/${id}`, {data: {stream_id: Number(streamId)}});
    await loadDetail(selected); setStats(null); setSuccess('Оффер удалён');
  });
  const report = () => run(async () => {
    if (selected === null) return;
    const {data} = await api.post(`/campaigns/${selected}/stats`, {start: from, end: to});
    setStats(data);
  });
  const dropdown = (label: string, values: Item[], value: string, setter: (v: string) => void) =>
    <label>{label}<select value={value} onChange={e => setter(e.target.value)} required>{values.map(x => <option key={x.id} value={x.id}>{x.name || `#${x.id}`} (#{x.id})</option>)}</select></label>;
  const active = detail?.streams.find(s => String(s.id) === streamId);
  const list = active?.offers ?? [];
  const names = Object.fromEntries(options.offers.map(x => [x.id, x.name]));

  return <div className="app">
    <aside className="sidebar"><div className="brand"><span className="brand-icon">A</span><span>ADROBOT<small>Keitaro manager</small></span></div>
      <div className="side-label">УПРАВЛЕНИЕ</div>
      <button className={tab === 'create' ? 'nav active' : 'nav'} onClick={() => setTab('create')}>⊕ &nbsp; Новая кампания</button>
      <button className={tab === 'edit' ? 'nav active' : 'nav'} onClick={() => setTab('edit')}>☷ &nbsp; Редактор офферов</button>
      <div className="side-footer">FastAPI · React · CSS</div>
    </aside>
    <main className="content"><header className="topbar"><div className="muted">Рабочее пространство / <strong>{tab === 'create' ? 'Новая кампания' : 'Редактор офферов'}</strong></div><span className="status"><span className="dot"/> API Keitaro</span></header>
      <div className="page"><div className="eyebrow">KEITARO CAMPAIGNS</div><h1>{tab === 'create' ? 'Создание кампании' : 'Редактор кампании'}</h1>
        <p className="subtitle">{tab === 'create' ? 'Настройка двух потоков, геотаргетинга и направления трафика.' : 'Управляйте офферами в потоках без изменения остальных настроек.'}</p>
        {error && <div role="alert" className="alert error">{error}</div>}{success && <div role="status" className="alert success">{success}</div>}
        {tab === 'create' ? <div className="panel"><div className="panel-title">Параметры кампании <span className="chip">Новая</span></div>
          <form onSubmit={e => {e.preventDefault(); void create();}} className="form-grid">
            <label className="wide">Название кампании<input value={name} onChange={e => setName(e.target.value)} minLength={1} maxLength={120} placeholder="campaign1" required/><small>Префикс test_фамилия_ добавляет backend из .env</small></label>
            <label>Гео-код страны<input value={geo} onChange={e => setGeo(e.target.value.toUpperCase())} pattern="[A-Za-z]{2}" maxLength={2} required placeholder="DE"/></label>
            {dropdown('Оффер', options.offers, offer, setOffer)}
            {dropdown('Домен', options.domains, domain, setDomain)}
            {dropdown('Группа', options.groups, group, setGroup)}
            {dropdown('Источник трафика', options.traffic_sources, source, setSource)}
            <div className="wide flow-preview"><div><b>01</b><span><strong>Страна {geo || '—'}</strong><small>Google · приоритетный поток</small></span></div><div><b>02</b><span><strong>Все остальные страны</strong><small>Выбранный оффер · основной поток</small></span></div></div>
            <button disabled={busy || !offer || !domain || !group || !source} type="submit" className="primary">{busy ? 'Создаём…' : 'Создать кампанию →'}</button>
          </form></div> : <div className="stack"><div className="panel"><div className="panel-title">Выбор кампании <button className="ghost" disabled={busy} onClick={() => void run(loadCampaigns)}>Обновить список ↻</button></div>
          <label>Кампания<select value={selected ?? ''} onChange={e => {setSelected(e.target.value ? Number(e.target.value) : null); setDetail(null); setStats(null);}}><option value="">Выберите кампанию</option>{campaigns.map(x => <option key={x.id} value={x.id}>{x.name} (#{x.id})</option>)}</select></label>
          </div>{detail && <><div className="panel"><div className="panel-title">Офферы и потоки <span className="chip">#{selected}</span></div>
          <label>Поток<select value={streamId} onChange={e => setStreamId(e.target.value)}>{detail.streams.map(s => <option key={s.id} value={s.id}>{s.name} (#{s.id}, {s.schema})</option>)}</select></label>
          <div className="offer-header"><span>Подключённые офферы</span><span>{list.length} шт.</span></div>
          {list.length ? list.map(x => <div className="offer-row" key={x.offer_id}><span className="offer-icon">↗</span><div><strong>{names[x.offer_id] ?? `Оффер #${x.offer_id}`}</strong><small>ID {x.offer_id} · share {x.share} · {x.state ?? 'active'}</small></div><button disabled={busy} onClick={() => void remove(x.offer_id)} className="danger">Удалить</button></div>) : <p className="muted">Нет офферов в этом потоке.</p>}
          <div className="add-row">{dropdown('Добавить оффер', options.offers, newOffer, setNewOffer)}<button className="primary" disabled={busy || !newOffer || !['offers','landings_offers'].includes(active?.schema ?? '')} onClick={() => void add()}>+ Добавить</button></div>
          </div><div className="panel"><div className="panel-title">Статистика Keitaro</div><div className="report-controls"><label>С<input type="date" value={from} onChange={e => setFrom(e.target.value)}/></label><label>По<input type="date" value={to} onChange={e => setTo(e.target.value)}/></label><button className="primary" disabled={busy} onClick={() => void report()}>Загрузить</button></div>
          {stats !== null && <pre className="report-json">{JSON.stringify(stats, null, 2)}</pre>}<p className="helper">Отчёт поступает напрямую из Keitaro и не пересчитывается вручную.</p>
          </div></>}</div>}
      </div>
    </main>
  </div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
