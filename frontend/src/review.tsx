import { useEffect, useState } from 'react'
import type { Chain, Decision, Location, Result } from './types'
import { api, label, post } from './types'
import { Chip } from './desk'

export function Matrix({result, select}: {result: Result; select: (field: Location) => void}) {
  return <section className="panel wide"><div className="section-head"><small className="eyebrow">CORRELATION / 01</small><h2>Cross-document matrix</h2>
    <p>Compare normalized fields and open each value on its original page.</p></div>
    <div className="table-scroll"><table><thead><tr><th>Field</th>{result.documents.map(d => <th key={d.id}>{d.type}</th>)}<th>Relationship</th></tr></thead>
      <tbody>{result.matrix.map(row => <tr className={row.status==='Mismatch'?'mismatch':''} key={row.key}><th scope="row">{label(row.key)}</th>
        {row.cells.map((field,i) => <td key={i}>{field ? <button className="text-link" onClick={() => select(field)}>{field.value}</button> : '—'}</td>)}
        <td><span className={row.status==='Benign variant'?'good':''}>{row.status}</span></td></tr>)}</tbody></table></div>
  </section>
}

export function Review({result, setDecision}: {result: Result; setDecision: (decision: Decision) => void}) {
  const [reason, setReason] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  async function act(action: string) {
    setPending(true); setError('')
    try { setDecision(await api<Decision>(`/api/cases/${result.id}/decision`,post({action,reason}))); setReason('') }
    catch (err) { setError((err as Error).message) }
    finally { setPending(false) }
  }
  return <div className="review-grid">
    <section className="panel wide"><div className="section-head"><small className="eyebrow">REVIEW / 01</small><h2>Concern breakdown</h2>
      <Chip value={result.summary.concern}/><p>{result.summary.formula}</p></div>
      <ul className="score-list">{result.findings.map(e => <li key={e.id}><code>{e.id}</code><span>{e.summary}</span><b>+{e.points}</b></li>)}</ul>
      <p className="score-total">Total concern points <strong>{result.summary.score}</strong></p>
      <label className="reason">Reviewer note <textarea value={reason} onChange={e => setReason(e.target.value)} maxLength={1000} placeholder="Required for escalation"/></label>
      <div className="decision-actions">{['Clear','Request more documents','Escalate'].map(a =>
        <button key={a} disabled={pending || (a==='Escalate' && !reason.trim())} className={a==='Request more documents'?'primary':''} onClick={() => void act(a)}>{a}</button>)}</div>
      {error && <p role="alert" className="error">{error}</p>}
      {result.decision && <p role="status" className="notice">✓ Audit entry recorded · <b>{result.decision.action}</b> · {new Date(result.decision.timestamp).toLocaleString()}</p>}
    </section>
    <section className="panel wide"><div className="section-head"><small className="eyebrow">REVIEW / 02</small><h2>Applicant letter</h2><p>Draft for the reviewer to copy after checking the evidence.</p></div>
      <pre className="letter">{result.summary.letter}</pre>
    </section>
  </div>
}

export function Dossier({result}: {result: Result}) {
  const [head, setHead] = useState('')
  const [chainError, setChainError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    api<Chain>(`/api/audit/verify?case_id=${result.id}`, {signal:controller.signal})
      .then(chain => {setHead(chain.head);setChainError(chain.valid?'':'Chain verification failed.')})
      .catch(() => {if (!controller.signal.aborted) setChainError('Could not read the audit-chain head.')})
    return () => controller.abort()
  },[result.id,result.decision?.timestamp])
  return <section className="panel wide dossier"><div className="section-head"><small className="eyebrow">CASE FILE</small><h2>Investigation dossier</h2>
    <a className="button primary" href={`/api/cases/${result.id}/dossier.pdf`} download>↓ Download PDF</a></div>
    <h3>Document Overview</h3>{result.documents.map(d => <p key={d.id}>{d.name} · {d.type} · {d.status}<br/><code>{d.sha256}</code></p>)}
    <h3>Extracted Information</h3>{result.documents.map(d => <div key={d.id}><strong>{d.name}</strong>
      {d.fields.length ? <ul>{d.fields.map((f,i) => <li key={i}>{label(f.key)} · {f.value} · p. {f.page} · {f.method}, unverified</li>)}</ul> : <p>No readable fields.</p>}</div>)}
    <h3>Contextual Analysis</h3><ul>{result.findings.filter(f => f.layer==='fields').map(f => <li key={f.id}>{f.id} · {f.summary}</li>)}</ul>
    <h3>Visual Forensic Findings</h3><ul>{result.findings.filter(f => f.layer!=='fields').map(f => <li key={f.id}>{f.id} · {f.summary}</li>)}</ul>
    <h3>Evidence and Traceability</h3><p>Case <code>{result.id}</code></p>
    {head && <p>Audit-chain head <code>{head}</code></p>}
    {chainError && <p role="alert" className="error">{chainError}</p>}
    {result.findings.map(f => <details key={f.id}><summary>{f.id} · {f.summary}</summary><p>Page {f.page} · {f.method}</p><p>{f.limits}</p><p>{f.explanation.settle}</p></details>)}
    <h3>Investigation Summary</h3><p><Chip value={result.summary.concern}/> {result.summary.score} concern points</p>
    <p>{result.summary.formula}</p><p>{result.decision ? `${result.decision.action} · ${result.decision.timestamp} · ${result.decision.reason}` : 'Human decision pending.'}</p>
  </section>
}

export function Audit({id}: {id: string}) {
  const [chain, setChain] = useState<Chain | null>(null)
  const [error, setError] = useState('')
  const [working, setWorking] = useState(false)
  async function verify() {
    setWorking(true); setError('')
    try { setChain(await api<Chain>(`/api/audit/verify?case_id=${id}`)) }
    catch (err) { setError((err as Error).message) }
    finally { setWorking(false) }
  }
  return <section className="panel wide"><div className="section-head"><small className="eyebrow">CHAIN OF CUSTODY</small><h2>Audit trail</h2>
    <p>Each event commits to its predecessor and the canonical event payload.</p>
    <button className="primary" disabled={working} onClick={() => void verify()}>{working?'Verifying…':'Verify chain'}</button></div>
    {error && <p role="alert" className="error">{error}</p>}
    {chain ? <><p role="status" className="notice">{chain.valid ? `✓ Verified · ${chain.count} entries` : `Integrity check failed at event ${chain.failed_at}`}</p>
      <p>Head <code>{chain.head}</code></p><ol className="chain">{chain.entries.map(row => <li key={row.seq}>
        <strong>{label(row.event.action)}</strong> <small>{row.event.timestamp}</small><br/>
        <code>{row.previous.slice(0,12)} → {row.hash.slice(0,12)}</code>
        <details><summary>Event payload</summary><pre>{JSON.stringify(row.event.details,null,2)}</pre></details></li>)}</ol></>
      : <p className="empty">Verify the chain to inspect its entries.</p>}
  </section>
}
