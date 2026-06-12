'use client';

import { useMemo, useState } from 'react';
import { Download, FileText, MapPin, Route, Search, Sparkles } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const FLOORPLAN = '/floorplan_hardware_pioneers_max26.png';
const IMG_W = 1344;
const IMG_H = 2048;
const DEFAULT_QUERY = 'machine learning, AI, edge AI, embedded systems, FPGA, firmware, robotics, computer vision, IoT, sensors, Python, Linux, graduate, internship';
const ENTRANCE = { x: 687, y: 1695 };

const PRESETS = {
  ai: 'AI, machine learning, edge AI, tinyML, computer vision, neural networks, inference, data',
  embedded: 'embedded systems, firmware, FPGA, microcontroller, PCB, semiconductor, sensors, C++, Linux',
  robotics: 'robotics, autonomous systems, automation, control systems, sensor fusion, computer vision',
  jobs: 'graduate, internship, junior, early career, hiring, careers, placement, software engineer',
  suppliers: 'components, distributor, electronics, PCB, sensors, connectors, manufacturing, supply chain'
};

function priorityClass(item) {
  return item?.priority?.key || 'backup';
}

function downloadCsv(plan) {
  const rows = [
    ['Rank', 'Company', 'Stand', 'Priority', 'Match %', 'Reason', 'Website', 'Event profile']
  ];
  plan.results.forEach((item) => {
    rows.push([
      item.rank,
      item.company,
      item.stand,
      item.priority?.label || '',
      item.matchPercent,
      item.reason,
      item.website || '',
      item.profileUrl || ''
    ]);
  });
  const csv = rows
    .map((row) => row.map((cell) => `"${String(cell ?? '').replaceAll('"', '""')}"`).join(','))
    .join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'standscout_visit_plan.csv';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function RouteLine({ route, show }) {
  if (!show || !route?.length) return null;
  const points = [ENTRANCE, ...route].map((p) => `${p.x},${p.y}`).join(' ');
  return (
    <svg className="routeSvg" viewBox={`0 0 ${IMG_W} ${IMG_H}`} aria-hidden="true">
      <polyline points={points} fill="none" stroke="var(--blue)" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" opacity="0.86" />
      <circle cx={ENTRANCE.x} cy={ENTRANCE.y} r="15" fill="var(--green)" stroke="white" strokeWidth="5" />
    </svg>
  );
}

function Floorplan({ results, route, showRoute, setActiveTab, setFocusRank }) {
  return (
    <section className="mapShell">
      <div className="mapHint">
        <span><i className="legendDot visit" /> Visit first</span>
        <span><i className="legendDot worth" /> Worth visiting</span>
        <span><i className="legendDot backup" /> Backup</span>
      </div>
      <div className="mapScroll">
        <div className="mapStage">
          <img src={FLOORPLAN} alt="Hardware Pioneers MAX 26 floorplan" />
          <RouteLine route={route} show={showRoute} />
          {results.map((item) => {
            if (typeof item.x !== 'number' || typeof item.y !== 'number') return null;
            return (
              <button
                key={`${item.rank}-${item.company}`}
                className={`marker ${priorityClass(item)}`}
                style={{ left: `${(item.x / IMG_W) * 100}%`, top: `${(item.y / IMG_H) * 100}%` }}
                title={`${item.rank}. ${item.company} — ${item.stand}`}
                onClick={() => {
                  setFocusRank(item.rank);
                  setActiveTab('plan');
                  setTimeout(() => document.getElementById(`result-${item.rank}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 50);
                }}
              >
                {item.rank}
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function ResultCard({ item, focused }) {
  return (
    <article id={`result-${item.rank}`} className={`resultCard ${priorityClass(item)} ${focused ? 'focused' : ''}`}>
      <div className="rankBubble">{item.rank}</div>
      <div className="resultMain">
        <div className="resultTopLine">
          <div>
            <h3>{item.company}</h3>
            <p>{item.reason}</p>
          </div>
          <span className="standBadge">{item.stand || item.standCode}</span>
        </div>
        <div className="chips">
          <span className={`priorityChip ${priorityClass(item)}`}>{item.priority?.label}</span>
          <span>{item.matchPercent}% match</span>
          <span>{item.mapped ? 'Shown on floorplan' : 'No map location'}</span>
          {item.categoryHints?.slice(0, 3).map((hint) => <span key={hint}>{hint}</span>)}
        </div>
        <div className="links">
          {item.website ? <a href={item.website} target="_blank" rel="noreferrer">Website</a> : null}
          {item.profileUrl ? <a href={item.profileUrl} target="_blank" rel="noreferrer">Event profile</a> : null}
        </div>
      </div>
    </article>
  );
}

export default function Home() {
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [topN, setTopN] = useState(20);
  const [mode, setMode] = useState('balanced');
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('plan');
  const [showRoute, setShowRoute] = useState(true);
  const [focusRank, setFocusRank] = useState(null);

  async function runPlanner(nextQuery = query) {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_URL}/api/rank`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: nextQuery, top_n: Number(topN), mode })
      });
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data = await res.json();
      setPlan(data);
      setActiveTab('plan');
    } catch (err) {
      setError('Could not reach the Python API. Start the FastAPI backend first, then refresh this page.');
    } finally {
      setLoading(false);
    }
  }

  function applyPreset(key) {
    const value = PRESETS[key];
    setQuery(value);
    setTimeout(() => runPlanner(value), 0);
  }

  const results = plan?.results || [];
  const summary = plan?.summary || {};
  const route = plan?.route || [];

  const routeText = useMemo(() => {
    if (!route.length) return 'Route will appear after ranking.';
    return route.slice(0, 4).map((r) => r.stand.replace('Stand ', '')).join(' → ') + (route.length > 4 ? ' → …' : '');
  }, [route]);

  return (
    <main>
      <header className="hero">
        <div className="heroText">
          <p className="eyebrow"><Sparkles size={16} /> StandScout</p>
          <h1>Find the right stands before walking the expo floor.</h1>
          <p>
            A client-facing Next.js UI connected to a Python ranking API. Type what matters, get a clear visit plan, and see the stands on the Hardware Pioneers MAX 26 floorplan.
          </p>
        </div>
        <div className="heroStats">
          <div><b>{summary.exhibitorsAnalysed || 50}</b><span>exhibitors</span></div>
          <div><b>{summary.mappedResults || 0}</b><span>mapped results</span></div>
          <div><b>{summary.visitFirst || 0}</b><span>visit first</span></div>
        </div>
      </header>

      <div className="workspace">
        <aside className="controlPanel">
          <div className="panelTitle"><Search size={18} /><h2>Choose interests</h2></div>
          <label htmlFor="query">What are you looking for?</label>
          <textarea id="query" value={query} onChange={(e) => setQuery(e.target.value)} />

          <div className="presetGrid">
            <button onClick={() => applyPreset('ai')}>AI / ML</button>
            <button onClick={() => applyPreset('embedded')}>Embedded / FPGA</button>
            <button onClick={() => applyPreset('robotics')}>Robotics</button>
            <button onClick={() => applyPreset('jobs')}>Jobs / hiring</button>
            <button onClick={() => applyPreset('suppliers')}>Suppliers</button>
          </div>

          <div className="formGrid">
            <div>
              <label htmlFor="topN">Show</label>
              <select id="topN" value={topN} onChange={(e) => setTopN(e.target.value)}>
                <option value={10}>Top 10</option>
                <option value={20}>Top 20</option>
                <option value={30}>Top 30</option>
                <option value={50}>Top 50</option>
              </select>
            </div>
            <div>
              <label htmlFor="mode">Match style</label>
              <select id="mode" value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="balanced">Balanced</option>
                <option value="strict">Strict keywords</option>
                <option value="prepared">Prepared ranking</option>
              </select>
            </div>
          </div>

          <button className="primaryBtn" onClick={() => runPlanner()} disabled={loading}>
            {loading ? 'Generating...' : 'Generate visit plan'}
          </button>

          <div className="secondaryActions">
            <button onClick={() => plan && downloadCsv(plan)} disabled={!plan}><Download size={16} /> CSV</button>
            <button onClick={() => window.print()}><FileText size={16} /> Print/PDF</button>
          </div>

          {error ? <div className="errorBox">{error}</div> : null}

          <div className="miniSummary">
            <b>Suggested route</b>
            <span>{routeText}</span>
          </div>
        </aside>

        <section className="resultsPanel">
          <div className="tabs">
            <button className={activeTab === 'plan' ? 'active' : ''} onClick={() => setActiveTab('plan')}>Visit plan</button>
            <button className={activeTab === 'map' ? 'active' : ''} onClick={() => setActiveTab('map')}>Floorplan map</button>
            <button className={activeTab === 'about' ? 'active' : ''} onClick={() => setActiveTab('about')}>How it works</button>
            <label className="routeToggle"><input type="checkbox" checked={showRoute} onChange={(e) => setShowRoute(e.target.checked)} /> Route line</label>
          </div>

          {activeTab === 'plan' && (
            <div className="tabBody">
              <div className="summaryStrip">
                <div><small>Top stand</small><b>{summary.topStand || 'Run planner'}</b></div>
                <div><small>Top company</small><b>{summary.topCompany || '—'}</b></div>
                <div><small>Shown</small><b>{summary.resultsShown || 0} stands</b></div>
              </div>
              {!results.length ? (
                <div className="emptyState">Click <b>Generate visit plan</b> to rank the event stands.</div>
              ) : (
                <div className="resultList">
                  {results.map((item) => <ResultCard key={`${item.rank}-${item.company}`} item={item} focused={focusRank === item.rank} />)}
                </div>
              )}
            </div>
          )}

          {activeTab === 'map' && (
            <div className="tabBody">
              <Floorplan results={results} route={route} showRoute={showRoute} setActiveTab={setActiveTab} setFocusRank={setFocusRank} />
            </div>
          )}

          {activeTab === 'about' && (
            <div className="tabBody aboutGrid">
              <div><MapPin size={22} /><h3>1. It reads exhibitor data</h3><p>The API uses the scraped event profiles, company names, stand numbers, and mapped floorplan coordinates.</p></div>
              <div><Search size={22} /><h3>2. It scores relevance</h3><p>Your search terms are compared with each exhibitor profile, then combined with prepared event ranking signals.</p></div>
              <div><Route size={22} /><h3>3. It plans the visit</h3><p>The UI shows who to visit first, why they match, where they are, and a simple walking order.</p></div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
