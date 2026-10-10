import { useEffect, useState, type FormEvent } from 'react'
import { ArrowRight, Check, Plus, Wallet } from 'lucide-react'
import { api, dollars, errorText, title, useResource } from '../api'
import { CategoryIcon, Empty, ErrorNotice, Loading, Panel, PanelHeading, Progress } from '../components'
import { categories, type Budget, type Dashboard } from '../types'

function BudgetCard({budget, changed}: {budget: Budget; changed: (m: string) => void}) {
  const [limit, setLimit] = useState(String(budget.limit))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {setLimit(String(budget.limit))}, [budget.limit])
  async function save(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError('')
    try {await api('/budgets', {method:'PUT', body: JSON.stringify({category: budget.category, period: budget.period, limit})}); changed(`${title(budget.category)} budget saved.`)}
    catch (err) {setError(errorText(err))} finally {setBusy(false)}
  }
  return <Panel className="budget-card"><div className="budget-card-top"><CategoryIcon category={budget.category}/><span className={`subtle-chip ${budget.overspent ? 'warn-chip' : ''}`}>{budget.overspent ? 'Over budget' : 'Within budget'}</span></div><h2>{title(budget.category)}</h2><div className="budget-figures"><strong>{dollars(budget.spent)}</strong><span>of {dollars(budget.limit)}</span></div><Progress value={budget.progress} warn={budget.overspent} label={`${budget.category} ${budget.period} budget`}/><p className={budget.overspent ? 'warning-text' : ''}>{budget.overspent ? `${dollars(-budget.remaining)} over your limit` : `${dollars(budget.remaining)} left to spend`}</p><form onSubmit={save} className="inline-form"><label>{title(budget.category)} {budget.period} limit<input aria-label={`${title(budget.category)} ${budget.period} limit`} type="number" min="0" max="1000000" step="0.01" required value={limit} onChange={e => setLimit(e.target.value)}/></label><button className="button secondary small" type="submit" disabled={busy}><Check size={15}/> Save</button></form><ErrorNotice message={error}/></Panel>
}

export function BudgetsPage({revision, changed, dashboard, settings}: {revision: number; changed: (m: string) => void; dashboard: Dashboard; settings: () => void}) {
  const {data, loading, error} = useResource<Budget[]>('/budgets', revision)
  const [period, setPeriod] = useState<'monthly' | 'weekly'>('monthly')
  const [category, setCategory] = useState('food')
  const [limit, setLimit] = useState('100')
  const [saveError, setSaveError] = useState('')
  const [busy, setBusy] = useState(false)
  async function save(e: FormEvent) {
    e.preventDefault(); setBusy(true); setSaveError('')
    try {await api('/budgets', {method:'PUT', body: JSON.stringify({category, period, limit})}); changed('Category budget added or updated.')}
    catch (err) {setSaveError(errorText(err))} finally {setBusy(false)}
  }
  const chosen = data?.filter(b => b.period === period) || []
  return <><div className="page-intro"><div><span className="eyebrow">A PLAN, WITH ROOM TO BREATHE</span><h1>Spend with a little intention.</h1><p>Set your limits. Make space for both essentials and the good stuff.</p></div><div className="segmented" aria-label="Budget period"><button className={period === 'monthly' ? 'active' : ''} onClick={() => setPeriod('monthly')}>Monthly</button><button className={period === 'weekly' ? 'active' : ''} onClick={() => setPeriod('weekly')}>Weekly</button></div></div>
    <div className="budget-overview"><Wallet size={27}/><div><span>Monthly spending plan</span><strong>{dollars(dashboard.budget_total)}</strong></div><div><span>Spent so far</span><strong>{dollars(dashboard.expenses)}</strong></div><div><span>Room remaining</span><strong>{dollars(dashboard.remaining_budget)}</strong></div><button className="text-button" onClick={settings}>Income & savings goals <ArrowRight size={16}/></button></div>
    <ErrorNotice message={error}/>{loading ? <Loading/> : chosen.length ? <div className="budget-grid">{chosen.map(b => <BudgetCard key={b.id} budget={b} changed={changed}/>)}</div> : <Panel><Empty title={`Make a ${period} plan`}>Add a category limit below to begin.</Empty></Panel>}
    <Panel className="mt"><PanelHeading title="Give another category a plan" subtitle="Choose a category to add or update its spending limit."/><form onSubmit={save} className="budget-add-form"><label>Budget category<select value={category} onChange={e => setCategory(e.target.value)}>{categories.filter(c => c !== 'income').map(c => <option value={c} key={c}>{title(c)}</option>)}</select></label><label>{title(period)} limit ($)<input type="number" required min="0" max="1000000" step="0.01" value={limit} onChange={e => setLimit(e.target.value)}/></label><button className="button primary" disabled={busy}><Plus size={16}/> Save category limit</button></form><ErrorNotice message={saveError}/></Panel>
    <p className="page-footnote">Weeks start Monday. Monthly and weekly limits are separate views and aren’t added together. Refunds reduce category spending.</p>
  </>
}
