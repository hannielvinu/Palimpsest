import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Audit, Dossier, Matrix, Review } from './review'
import { Chip, Desk } from './desk'
import { api, label, post, STEPS } from './types'
import type { Location, Result, Status } from './types'
import './style.css'

const samples = [
  {id:'meena', n:'01', name:'Meena', title:'The everyday exception', copy:'An abbreviated name, a blurry scan and a normal payroll delay.', badge:'Routine review'},
  {id:'ravi', n:'02', name:'Ravi', title:'The changed amount', copy:'A payslip, a bank credit and an earlier value still inside the PDF.', badge:'Payroll review'},
  {id:'injection', n:'03', name:'injection', title:'The hidden instruction', copy:'Invisible text addresses the automated reviewer directly.', badge:'Safety check'},
  {id:'degraded', n:'04', name:'degraded', title:'The unreadable scan', copy:'When the source is too poor, the desk asks for a better copy.', badge:'Quality gate'},
]
const views = ['Investigation','Cross-document','Decision','Dossier','Audit trail'] as const
type View = typeof views[number]
type Info = {matrix: [string,string][]; demo_only: boolean; standards: string}
type Metrics = {benchmark: {label:string; total:number; caught:number; missed:number; false_alarms:number; genuine:number; per_detector:Record<string,{hits:number; expected:number}>} | null;
  robustness: {conditions:{condition:string; flagged:number; total:number; cannot_determine:number}[]} | null}

function Mark() {
  return <svg width="31" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
    <path d="M8 11h17v16H8z" stroke="#d3b984" strokeWidth="1.5" transform="rotate(-12 8 11)"/>
    <path d="M5 4h18l4 4v15H5z" fill="#202936" stroke="#f6f1e7" strokeWidth="1.5"/>
    <path d="M9 11h12M9 15h9M9 19h7" stroke="#d3b984" strokeWidth="1.2"/></svg>
}

function App() {
  const [info,setInfo] = useState<Info | null>(null)
  const [metrics,setMetrics] = useState<Metrics | null>(null)
  const [screen,setScreen] = useState<'start'|'about'|'benchmark'|'case'>('start')
  const [caseId,setCaseId] = useState('')
  const [status,setStatus] = useState<Status | null>(null)
  const [result,setResult] = useState<Result | null>(null)
  const [error,setError] = useState('')
  const [loading,setLoading] = useState('')
  const [view,setView] = useState<View>('Investigation')
  const [target,setTarget] = useState<Location | null>(null)
  const [selected,setSelected] = useState('')
  const [dark,setDark] = useState(false)
  const [purging,setPurging] = useState(false)
  const [warming,setWarming] = useState(false)
  useEffect(() => {
    let live = true
    const timer = setTimeout(() => { if (live) setWarming(true) }, 1500)
    async function check() {
      for (let attempt=0; attempt<8 && live; attempt++) {
        try { const value = await api<Info>('/api/capabilities'); if (live) {setInfo(value);setWarming(false);clearTimeout(timer)}; return }
        catch { await new Promise(resolve => setTimeout(resolve,1000+attempt*500)) }
      }
    }
    void check()
    return () => {live=false;clearTimeout(timer)}
  }, [])
  useEffect(() => {
    if (screen !== 'benchmark' || metrics) return
    api<Metrics>('/api/benchmark').then(setMetrics).catch(err => setError(err.message))
  },[screen,metrics])
  useEffect(() => {
    if (!caseId) return
    let live = true
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try {
        const next = await api<Status>(`/api/cases/${caseId}/status`)
        if (!live) return
        setStatus(next)
        if (next.state === 'ready') {
          const data = await api<Result>(`/api/cases/${caseId}/findings`)
          if (live) setResult(data)
          return
        }
        if (next.state === 'failed') {setError('Cannot determine. Analysis failed or reached its time limit.'); return}
        timer = setTimeout(poll,350)
      } catch(err) {if (live) setError((err as Error).message)}
    }
    void poll()
    return () => {live=false;clearTimeout(timer)}
  },[caseId])

  function go(next: typeof screen) { setError(''); setScreen(next); window.scrollTo(0,0) }
  function open(id: string) {
    setStatus(null);setResult(null);setTarget(null);setSelected('');setView('Investigation');setPurging(false);setCaseId(id);go('case')
  }
  async function load(id: string) {
    setLoading(id);setError('')
    try { open((await api<{id:string}>(`/api/samples/${id}/load`,post())).id) }
    catch(err) {setError((err as Error).message)}
    finally {setLoading('')}
  }
  async function upload(files: File[]) {
    if (!files.length) return
    setLoading('upload');setError('')
    let id: string | undefined
    try {
      id = (await api<{id:string}>('/api/cases',post({title:'Uploaded synthetic records'}))).id
      const data = new FormData()
      for (const file of files) data.append('files',file)
      await api(`/api/cases/${id}/documents`,post(data))
      await api(`/api/cases/${id}/analyze`,post())
      open(id)
    } catch(err) {
      if (id) await api(`/api/cases/${id}`,{method:'DELETE'}).catch(() => {})
      setError((err as Error).message)
    } finally {setLoading('')}
  }
  async function purge() {
    try { await api(`/api/cases/${caseId}`,{method:'DELETE'});setCaseId('');setStatus(null);setResult(null);go('start') }
    catch(err) {setError((err as Error).message)}
  }
  function choose(location: Location,id='') {setTarget(location);setSelected(id);setView('Investigation')}
  return <div className={dark?'app dark':'app'}>
    <header className="mast"><div className="mast-inner">
      <button className="brand" onClick={() => go('start')} aria-label="Palimpsest home"><Mark/><span>Palimpsest</span></button>
      <nav aria-label="Main navigation"><button aria-current={screen==='start'?'page':undefined} onClick={() => go('start')}>Case desk</button>
      {caseId && <button aria-current={screen==='case'?'page':undefined} onClick={() => go('case')}>Current case</button>}
      <button aria-current={screen==='benchmark'?'page':undefined} onClick={() => go('benchmark')}>Benchmark</button>
      <button aria-current={screen==='about'?'page':undefined} onClick={() => go('about')}>About</button>
      <button aria-label="Toggle dark mode" aria-pressed={dark} onClick={() => setDark(!dark)}>{dark?'☀':'◐'}</button></nav>
    </div></header>
    <div className="data-strip"><div><span>◆</span> All sample data is synthetic. No real personal data.</div><small>HACK THE CORE / 2026</small></div>
    <main>
      {error && <p className="error" role="alert">{error}</p>}
      {screen==='start' && <>
        <section className="hero"><div><p className="eyebrow">DOCUMENT FORENSICS / INVESTIGATION DESK</p><h1>Every document has<br/> a <em>second layer.</em></h1>
          <p className="hero-copy">Trace inconsistencies to the original page, consider harmless explanations, and leave the decision with the reviewer.</p></div>
          <div className="folio" aria-hidden="true"><div className="folio-back"/><div className="folio-page">
            <span>FIELD NOTE / 001</span><div className="folio-title">Case<br/>evidence</div><div className="folio-lines"/><div className="folio-mark">REVIEW<br/>REQUIRED</div>
          </div><div className="folio-caption">FIG. 01 / THE LAYERS OF A RECORD</div></div>
        </section>
        {warming && <p role="status" className="notice">Warming up. The investigation service is starting.</p>}
        <section aria-labelledby="samples"><div className="section-rule"><h2 id="samples">Open a sample case</h2><span className="eyebrow">04 / FICTIONAL INVESTIGATIONS</span></div>
          <div className="sample-grid">{samples.map(s => <article className={`sample ${s.id}`} key={s.id}>
            <div className="sample-top"><span className="mono">{s.n}</span><span>{s.badge}</span></div><h3>{s.title}</h3><p>{s.copy}</p>
            <button disabled={!!loading} onClick={() => void load(s.id)}>{loading===s.id?'Opening…':`Load ${s.name} case`} <span aria-hidden="true">↗</span></button>
          </article>)}</div>
        </section>
        <section className="upload panel"><div><h2>Start with your own synthetic files</h2><p>PDF, PNG or JPG · Up to eight documents · 8 MiB each</p></div>
          {info?.demo_only ? <p>Uploads are available in the local edition.</p> : <label className="button primary file-button">{loading==='upload'?'Uploading…':'↑ Upload documents'}
            <input type="file" multiple accept=".pdf,.png,.jpeg,.jpg" disabled={!!loading} onChange={e => {void upload(Array.from(e.target.files || []));e.target.value=''}}/></label>}
        </section>
      </>}
      {screen==='case' && <><div className="case-header"><div><small className="eyebrow">CASE FILE / {caseId.slice(0,8).toUpperCase()}</small>
        <h1>{status?.title || 'Opening case'}</h1></div>{result && <Chip value={result.summary.concern}/>}</div>
        {!result && <section className="panel wide" aria-live="polite"><h2>{status?.state==='failed'?'Cannot determine':'Processing documents'}</h2>
          <ol className="steps">{STEPS.map((step,i) => {const entry=status?.progress.find(s => s.step===step);return <li key={step}>
            <b className={entry?'good':''}>{entry?'✓':String(i+1).padStart(2,'0')}</b><span>{step}</span><small>{entry?.detail || (i===status?.progress.length?'In progress…':'Queued')}</small>
            <code>{entry ? `${entry.ms} ms` : '—'}</code></li>})}</ol></section>}
        {result && <><nav className="case-nav" aria-label="Case navigation">{views.map(v => <button key={v} aria-current={v===view?'page':undefined} onClick={() => setView(v)}>{v}</button>)}</nav>
          {view==='Investigation' && <Desk result={result} target={target} selected={selected} select={choose}/>}
          {view==='Cross-document' && <Matrix result={result} select={choose}/>}
          {view==='Decision' && <Review result={result} setDecision={decision => setResult({...result,decision})}/>}
          {view==='Dossier' && <Dossier result={result}/>}
          {view==='Audit trail' && <Audit id={caseId}/>}
          <div className="case-footer">{purging ? <><span>Delete the originals, findings and audit trail for this case?</span>
            <button onClick={() => void purge()}>Confirm purge</button><button onClick={() => setPurging(false)}>Cancel</button></> :
            <button onClick={() => setPurging(true)}>Purge local case</button>}</div>
        </>}
      </>}
      {screen==='about' && <section className="panel wide"><div className="section-head"><small className="eyebrow">METHODS & LIMITS</small><h2>About Palimpsest</h2>
        <p>A palimpsest is a manuscript scraped clean and rewritten, where traces of the earlier writing remain.</p></div>
        <h3>Capability matrix</h3>{info ? <table><tbody>{info.matrix.map(([status,copy],i) => <tr key={i}><th scope="row">{status}</th><td>{copy}</td></tr>)}</tbody></table> : <p role="status">Loading capabilities…</p>}
        <h3>Security model</h3><p>Bundled cases use fictional data. Uploads are bounded and checked. Native document parsing runs in timed processes. The explanation engine uses fixed evidence templates and treats every embedded instruction as data.</p>
        <h3>Limitations</h3><p>Layout rules target labeled English records. Recompression and shared templates can produce weak visual signals. Flattened PDFs lose recoverable history. The chain can be recomputed by an actor who controls the whole database.</p>
        <h3>Standards referenced</h3><p>{info?.standards || 'Loading…'}</p>
      </section>}
      {screen==='benchmark' && <section className="panel wide"><div className="section-head"><small className="eyebrow">REPRODUCIBLE EVALUATION</small><h2>Benchmark</h2>
        <p>{metrics?.benchmark?.label || 'Measured detector and robustness runs.'}</p></div>
        {!metrics && !error && <p role="status">Loading benchmark…</p>}
        {metrics && !metrics.benchmark && <p>No recorded benchmark. Run scripts/run_benchmark.py.</p>}
        {metrics?.benchmark && <><table><thead><tr><th scope="col">Cases</th><th scope="col">Caught</th><th scope="col">Missed</th><th scope="col">False alarms</th></tr></thead>
          <tbody><tr><td>{metrics.benchmark.total}</td><td>{metrics.benchmark.caught}</td><td>{metrics.benchmark.missed}</td><td>{metrics.benchmark.false_alarms} / {metrics.benchmark.genuine}</td></tr></tbody></table>
          <h3>Expected detector hits</h3><table><tbody>{Object.entries(metrics.benchmark.per_detector).map(([key,row]) =>
            <tr key={key}><th scope="row">{label(key)}</th><td>{row.hits} / {row.expected}</td></tr>)}</tbody></table></>}
        <h3>Robustness sweep</h3>{metrics?.robustness ? <table><thead><tr><th>Condition</th><th>False alarms</th><th>Cannot determine</th></tr></thead>
          <tbody>{metrics.robustness.conditions.map(row => <tr key={row.condition}><th scope="row">{row.condition}</th><td>{row.flagged} / {row.total}</td><td>{row.cannot_determine}</td></tr>)}</tbody></table>
          : <p>{metrics?'No recorded sweep. Run scripts/robustness_sweep.py.':'Loading…'}</p>}
      </section>}
    </main>
    <footer className="footer"><span>PALIMPSEST / HUMAN-LED DOCUMENT REVIEW</span><span>Built by hannielvinu</span></footer>
  </div>
}

createRoot(document.getElementById('root')!).render(<App />)
