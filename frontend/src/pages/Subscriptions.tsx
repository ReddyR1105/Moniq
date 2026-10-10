import { useState } from 'react'
import { Check, Repeat2, X } from 'lucide-react'
import { api, dollars, errorText, prettyDate, useResource } from '../api'
import { CategoryIcon, Empty, ErrorNotice, Loading, Panel, PanelHeading } from '../components'
import type { Subscriptions } from '../types'

export function SubscriptionsPage({revision, changed}: {revision: number; changed: (m: string) => void}) {
  const {data, loading, error} = useResource<Subscriptions>('/subscriptions', revision)
  const [busy, setBusy] = useState<number | null>(null)
  const [saveError, setSaveError] = useState('')
  async function mark(id: number, status: string) {
    setBusy(id); setSaveError('')
    try {await api(`/subscriptions/${id}`, {method:'PUT', body: JSON.stringify({status})}); changed(status === 'confirmed' ? 'Recurring service confirmed.' : 'Detection marked incorrect and excluded from the forecast.')}
    catch (e) {setSaveError(errorText(e))} finally {setBusy(null)}
  }
  return <><div className="page-intro"><div><span className="eyebrow">THE LITTLE MONTHLY CHARGES</span><h1>Know what’s on repeat.</h1><p>Find recurring services, review the patterns, and keep what’s useful.</p></div><span className="subtle-chip"><Repeat2 size={15}/> Pattern detection</span></div>
    <ErrorNotice message={error || saveError}/>{loading ? <Loading/> : data && <><div className="stat-grid"><Panel><span className="field-caption">ESTIMATED MONTHLY TOTAL</span><strong className="stat-number">{dollars(data.monthly_total)}</strong><p>Confirmed + candidate services</p></Panel><Panel><span className="field-caption">ANNUALIZED COST</span><strong className="stat-number">{dollars(data.annual_total)}</strong><p>At today’s typical billing amounts</p></Panel><Panel><span className="field-caption">SERVICES TO REVIEW</span><strong className="stat-number">{data.items.filter(s => s.status === 'candidate').length}</strong><p>Confirm or mark an incorrect detection</p></Panel></div>
      {data.possible_duplicates.map(n => <div className="warning-note" key={n}><Repeat2 size={18}/>{n}</div>)}<Panel><PanelHeading title="Your recurring services" subtitle="Three or more similar charges, approximately one calendar month apart"/>{data.items.length ? <div className="subscription-list">{data.items.map(s => <div key={s.id} className={`subscription-row ${s.status === 'incorrect' ? 'excluded' : ''}`}><CategoryIcon category={s.category}/><div className="subscription-details"><strong>{s.merchant}</strong><span>Estimated renewal {prettyDate(s.renewal)} · {dollars(s.annual_cost)} / year</span><small>{s.explanation}</small></div><div className="subscription-price"><strong>{dollars(s.amount)}</strong><span>/ month</span></div><span className={`subtle-chip ${s.status === 'confirmed' ? 'confirmed-chip' : ''}`}>{s.status === 'candidate' ? 'Needs review' : s.status === 'confirmed' ? 'Confirmed' : 'Excluded'}</span><div className="subscription-actions"><button className="button small secondary" disabled={busy === s.id || s.status === 'confirmed'} onClick={() => void mark(s.id, 'confirmed')} aria-label={`Confirm ${s.merchant}`}><Check size={14}/> Confirm</button><button className="icon-button" disabled={busy === s.id || s.status === 'incorrect'} onClick={() => void mark(s.id, 'incorrect')} aria-label={`Mark ${s.merchant} incorrect`}><X size={17}/></button></div></div>)}</div> : <Empty title="No recurring services detected">Import at least three months of history to see monthly patterns.</Empty>}</Panel><div className="sample-disclosure"><strong>Review, then decide.</strong><p>{data.note} Variable billing amounts, annual subscriptions, and services with fewer than three charges may be missed. Regular shopping trips are excluded from subscription detection.</p></div></>}
  </>
}
