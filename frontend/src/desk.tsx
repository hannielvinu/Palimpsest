import { useState } from 'react'
import type { Box, Doc, Finding, Location, Result } from './types'
import { label } from './types'

export function Chip({value}: {value: string}) {
  const style = value.toLowerCase().replaceAll(' ', '-').replaceAll('_', '-')
  const icon = ({low:'✓', high:'◆', moderate:'▲', 'cannot-determine':'?', observed:'○', inconsistency:'▲', 'possible-manipulation':'◆'} as Record<string,string>)[style] || '○'
  return <span className={`chip ${style}`}>{icon} {value.replaceAll('_',' ')}</span>
}

function Render({doc, page, revision, overlays, zoom, heatmap=false}: {doc: Doc; page: number; revision: number; overlays: {box: Box; focus?: boolean; layer: string}[]; zoom: number; heatmap?: boolean}) {
  const url = `/api/documents/${doc.id}/render?page=${page}&revision=${revision}&layer=${heatmap?'ela':'source'}`
  const [failed, setFailed] = useState('')
  const [loaded, setLoaded] = useState('')
  if (failed === url) return <p className="paper-error">Cannot determine. This page could not be rendered.</p>
  return <div className="paper" aria-busy={loaded !== url} style={{width:`${zoom}%`}}>
    {loaded !== url && <p className="paper-error" role="status">Rendering page…</p>}
    <img src={url} alt={`${doc.type}, page ${page}, ${heatmap ? 'recompression heatmap' : revision ? 'prior revision' : 'current file'}`} onLoad={() => setLoaded(url)} onError={() => setFailed(url)} />
    {overlays.map(({box:[x,y,x1,y1],focus,layer}, i) => <span aria-hidden="true" key={i} className={`box ${layer} ${focus ? 'focus' : ''}`}
      style={{left:`${x*100}%`,top:`${y*100}%`,width:Math.max(0,x1-x)*100+'%',height:Math.max(0,y1-y)*100+'%'}} />)}
  </div>
}

const layers = [['fields','Extracted fields'],['visual','Visual anomalies'],['signature','Signatures'],['hidden','Hidden text']]

export function Viewer({doc, result, target, setTarget}: {doc: Doc; result: Result; target: Location | null; setTarget: (target: Location) => void}) {
  const page = target?.document_id === doc.id ? target.page : 1
  const [zoom, setZoom] = useState(100)
  const [enabled, setEnabled] = useState(new Set(['visual','signature','hidden']))
  const [peel, setPeel] = useState(0)
  const [heatmap, setHeatmap] = useState(false)
  const revision = doc.revisions.find(r => r.revision === peel)
  const changes = revision?.changes.filter(c => c.page === page) || []
  const overlays: {box: Box; focus?: boolean; layer: string}[] = []
  if (enabled.has('fields')) for (const f of doc.fields) if (f.page === page && f.bbox) overlays.push({box:f.bbox,layer:'fields'})
  for (const f of result.findings) if (f.document_id === doc.id && f.page === page && f.bbox && enabled.has(f.layer)) overlays.push({box:f.bbox,layer:f.layer})
  if (target?.bbox) overlays.push({box:target.bbox,focus:true,layer:'visual'})
  return <section className="viewer panel" aria-label="Document viewer">
    <header className="pane-head"><div><small className="eyebrow">02 / SOURCE</small><h2>{doc.type}</h2></div><span className="mono viewer-page">PAGE {page}/{doc.pages}</span></header>
    <div className="viewer-tools">
      <button aria-label="Zoom out" onClick={() => setZoom(Math.max(75,zoom-15))}>−</button>
      <span className="mono">{zoom}%</span><button aria-label="Zoom in" onClick={() => setZoom(Math.min(190,zoom+15))}>+</button>
      {doc.pages > 1 && <select aria-label="Page" value={page} onChange={e => setTarget({document_id:doc.id,page:Number(e.target.value)})}>
        {Array.from({length:doc.pages},(_,i) => <option key={i} value={i+1}>Page {i+1}</option>)}</select>}
      {!!doc.revisions.length && <button className={peel ? 'peel active' : 'peel'} aria-pressed={!!peel} onClick={() => setPeel(peel ? 0 : doc.revisions.at(-1)!.revision)}>◫ Peel layer</button>}
      {doc.mime === 'image/jpeg' && <button className="peel" aria-pressed={heatmap} onClick={() => setHeatmap(!heatmap)}>ELA heatmap</button>}
    </div>
    {peel > 0 && <div className="peel-controls"><label>Revision <select value={peel} onChange={e => setPeel(Number(e.target.value))}>
      {doc.revisions.map(r => <option key={r.revision} value={r.revision}>Prior revision {r.revision}</option>)}</select></label>
      {changes.map((change, i) => <div className="revision-values" key={i}><span><small>PRIOR TEXT</small>{change.before || '—'}</span><span><small>CURRENT TEXT</small>{change.current || '—'}</span></div>)}
    </div>}
    {heatmap && <p className="heatmap-note">Brighter areas show larger recompression residuals. This is a weak signal.</p>}
    <div className={`raster ${peel ? 'split' : ''}`}>
      {peel > 0 && <div><span className="raster-tag">Prior revision</span><Render doc={doc} page={page} revision={peel} overlays={[]} zoom={zoom}/></div>}
      <div>{peel > 0 && <span className="raster-tag">Current file</span>}<Render doc={doc} page={page} revision={0} overlays={overlays} zoom={zoom} heatmap={heatmap}/></div>
    </div>
    <fieldset className="layers"><legend>Overlay layers</legend>{layers.map(([key,title]) =>
      <label key={key}><input type="checkbox" checked={enabled.has(key)} onChange={() => setEnabled(prev => {
        const next = new Set(prev); next.has(key) ? next.delete(key) : next.add(key); return next
      })}/>{title}</label>)}</fieldset>
    {!!Object.keys(doc.metadata).length && <details className="meta"><summary>PDF metadata</summary>
      {Object.entries(doc.metadata).map(([k,v]) => <p key={k}><b>{label(k)}</b> {v || '—'}</p>)}</details>}
  </section>
}

function Card({item, select, active}: {item: Finding; select: (location: Location, id: string) => void; active: boolean}) {
  const [view, setView] = useState<'why'|'harmless'>('why')
  const [related, showRelated] = useState(false)
  return <article className={`finding ${active ? 'selected' : ''}`}>
    <div className="finding-top"><Chip value={item.status}/><code>{item.id}</code></div>
    <h3>{item.summary}</h3><p className="finding-meta">Method confidence {Math.round(item.confidence*100)}% · +{item.points} concern</p>
    <div className="segment" aria-label="Explanation options">
      <button aria-pressed={view==='why'} onClick={() => setView('why')}>Why flagged</button>
      <button aria-pressed={view==='harmless'} onClick={() => setView('harmless')}>Harmless explanations</button>
    </div>
    <p>{view === 'why' ? item.explanation.why : item.explanation.harmless}</p>
    <p className="settle"><strong>What would settle it</strong> {item.explanation.settle}</p>
    <div className="card-actions">
      <button onClick={() => select(item,item.id)}>◎ Show on document</button>
      {!!item.related.length && <button aria-expanded={related} onClick={() => showRelated(!related)}>Related fields</button>}
    </div>
    {related && <ul className="related">{item.related.map((field,i) => <li key={i}><button onClick={() => select(field,item.id)}>
      {field.key ? `${label(field.key)} · ${field.value}` : `Related region · page ${field.page}`}</button></li>)}</ul>}
    <details><summary>Method, values and limits</summary><p>{item.method}</p><p>{item.limits}</p>
      {Object.entries(item.values).map(([key,value]) => <p key={key}><strong>{label(key)}</strong> {typeof value === 'string' ? value : JSON.stringify(value)}</p>)}
    </details>
  </article>
}

export function Desk({result, target, selected, select}: {result: Result; target: Location | null; selected: string; select: (target: Location, id?: string) => void}) {
  const doc = result.documents.find(d => d.id === target?.document_id) || result.documents[0]
  return <div className="desk-grid">
    <aside className="panel doc-list"><header className="pane-head"><div><small className="eyebrow">01 / FILES</small><h2>Documents</h2></div></header>
      {result.documents.map(item => <button key={item.id} className={item.id===doc.id ? 'doc active' : 'doc'} aria-pressed={item.id===doc.id}
        onClick={() => select({document_id:item.id,page:1})}><span className="file-icon">▤</span><span><strong>{item.type}</strong>
          <small>{item.name}</small><code>{item.sha256.slice(0,12)}…</code><small>{item.status}</small></span></button>)}
      <p className="doc-note">Original SHA-256 hashes are recorded at ingestion.</p>
    </aside>
    <Viewer key={doc.id} doc={doc} result={result} target={target} setTarget={select}/>
    <section className="panel evidence"><header className="pane-head"><div><small className="eyebrow">03 / EVIDENCE</small><h2>Findings</h2></div>
      <span className="count">{result.findings.length}</span></header>
      {!result.findings.length && <p className="empty">No evidence was emitted. Review the extracted fields before deciding.</p>}
      <div className="feed">{result.findings.map(item => <Card key={item.id} item={item} select={select} active={selected===item.id}/>)}</div>
    </section>
  </div>
}
