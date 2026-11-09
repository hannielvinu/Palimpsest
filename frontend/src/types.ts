export type Box = [number, number, number, number]
export type Location = {document_id: string; page: number; bbox?: Box | null}
export type Field = Location & {key: string; value: string; normalized: string | null; method: string; confidence: number}
export type Change = {before: string; current: string; page: number; bbox?: Box | null; revision: number}
export type Doc = {id: string; name: string; mime: string; sha256: string; type: string; status: string; reason?: string; pages: number;
  fields: Field[]; revisions: {revision: number; pages: number; changes: Change[]}[]; metadata: Record<string,string>}
export type Finding = Location & {
  id: string; detector: string; status: string; summary: string; method: string; limits: string; confidence: number;
  values: Record<string, unknown>; related: (Location & {key?: string; value?: string})[]; layer: string; points: number;
  explanation: {why: string; harmless: string; settle: string}
}
export type Step = {step: string; detail: string; ms: number}
export type Decision = {action: string; timestamp: string; reason: string; audit_head?: string}
export type Status = {id: string; title: string; state: string; progress: Step[]; decision: Decision | null}
export type Result = Status & {documents: Doc[]; findings: Finding[];
  matrix: {key: string; cells: (Field | null)[]; status: string}[];
  summary: {concern: string; score: number; formula: string; letter: string; narrative: string[]}}
export type Chain = {valid: boolean; count?: number; head: string; failed_at?: number;
  entries: {seq: number; hash: string; previous: string; event: {action: string; timestamp: string; details: unknown}}[]}

export const label = (key: string) => key.replaceAll('_', ' ').replace(/^./, v => v.toUpperCase())
export const STEPS = ['Ingest','Classify','Extract','Visual forensics','Context','Cross-document','Evidence','Dossier']

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(typeof data.detail === 'string' ? data.detail : `Request failed (${response.status}).`)
  }
  return response.status === 204 ? undefined as T : response.json()
}
export const post = (data?: unknown): RequestInit => data instanceof FormData ? {method:'POST',body:data}
  : {method:'POST',headers:{'Content-Type':'application/json'},body:data === undefined ? undefined : JSON.stringify(data)}
