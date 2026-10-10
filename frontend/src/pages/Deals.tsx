import { useState } from 'react'
import { ArrowUpRight, Bookmark, Check, GraduationCap, Tag } from 'lucide-react'
import { dollars, prettyDate, title, useResource } from '../api'
import { CategoryIcon, Empty, ErrorNotice, Loading, Panel } from '../components'
import type { Deals } from '../types'

export function DealsPage({revision}: {revision: number}) {
  const {data, loading, error} = useResource<Deals>('/deals', revision)
  const [filter, setFilter] = useState('all')
  const [saved, setSaved] = useState<number[]>(() => {
    try {const value: unknown = JSON.parse(localStorage.getItem('moniq-saved-deals') || '[]'); return Array.isArray(value) ? value.filter((v): v is number => typeof v === 'number') : []} catch {return []}
  })
  function toggle(id: number) {
    const next = saved.includes(id) ? saved.filter(v => v !== id) : [...saved,id]
    setSaved(next)
    try {localStorage.setItem('moniq-saved-deals', JSON.stringify(next))} catch { /* Bookmark remains available in this session. */ }
  }
  const items = data?.items.filter(d => filter === 'all' || filter === 'saved' && saved.includes(d.id) || d.category === filter) || []
  const filters = [...new Set(data?.items.map(d => d.category) || [])]
  return <><div className="page-intro"><div><span className="eyebrow">YOUR STUDENT STATUS HAS PERKS</span><h1>Save on what you already need.</h1><p>Recommendations that fit your life, your spending, and your budget.</p></div><span className="subtle-chip"><GraduationCap size={15}/> Synthetic sample offers</span></div>
    <div className="deal-banner"><span className="deal-banner-icon"><Tag size={30}/></span><div><h2>A discount is only a saving if you needed it.</h2><p>We prioritize planned purchases and filter out offers that exceed your remaining category budget.</p></div></div>
    <div className="filter-chips"><button className={`chip ${filter === 'all' ? 'selected' : ''}`} onClick={() => setFilter('all')}>For you</button>{filters.map(c => <button key={c} className={`chip ${filter === c ? 'selected' : ''}`} onClick={() => setFilter(c)}>{title(c)}</button>)}<button className={`chip ${filter === 'saved' ? 'selected' : ''}`} onClick={() => setFilter('saved')}><Bookmark size={14}/> Saved ({saved.length})</button></div>
    <ErrorNotice message={error}/>{loading ? <Loading label="Matching offers to your spending…"/> : items.length ? <div className="deals-grid">{items.map((d,i) => <Panel className="deal-card" key={d.id}><div className="deal-top"><CategoryIcon category={d.category}/><button className={`icon-button ${saved.includes(d.id) ? 'positive' : ''}`} aria-label={`${saved.includes(d.id) ? 'Unsave' : 'Save'} ${d.merchant} offer`} onClick={() => toggle(d.id)}><Bookmark size={19} fill={saved.includes(d.id) ? 'currentColor' : 'none'}/></button></div><div className="deal-merchant"><h2>{d.merchant}</h2>{i === 0 && filter === 'all' && <span className="subtle-chip">Top match</span>}</div><p>{d.description}</p><div className="deal-price"><strong>{d.discounted_price === null ? 'Price unknown' : dollars(d.discounted_price)}</strong>{d.original_price !== null && <del>{dollars(d.original_price)}</del>}<span>Save {dollars(d.savings)}</span></div><div className="deal-reason"><Check size={16}/><span>{d.reason}</span></div><div className="deal-details"><span><GraduationCap size={14}/>{d.eligibility}</span><span>Expiration: {d.expiration ? prettyDate(d.expiration) : 'Not provided'}</span><span>Verification: {d.verification}</span></div>{d.source_url ? <a className="text-button" href={d.source_url} target="_blank" rel="noreferrer">View source <ArrowUpRight size={15}/></a> : <span className="sample-label">Illustrative only · no redemption or live source</span>}</Panel>)}</div> : !error && <Panel><Empty title={filter === 'saved' ? 'Keep a possibility for later' : 'No matching sample offers'}>{filter === 'saved' ? 'Bookmark an offer to keep it in this browser.' : 'Check your remaining budgets and simulated student eligibility in Settings.'}</Empty></Panel>}
    {data && <div className="sample-disclosure"><strong>Clear about what’s real.</strong><p>{data.notice} {data.omitted} sample offers were filtered out by relevance, eligibility, affordability, or expiry.</p></div>}
  </>
}
