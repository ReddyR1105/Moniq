import { useState, type FormEvent } from 'react'
import { CalendarPlus, Pencil, Trash2, X } from 'lucide-react'
import { api, dollars, errorText, localDate, prettyDate, title, useResource } from './api'
import { CategoryIcon, ErrorNotice, Panel, PanelHeading } from './components'
import { categories, type Schedule } from './types'
import { useRuntime } from './runtime'

type Draft = Omit<Schedule, 'id' | 'status'>
const tomorrow = () => {const day = new Date(`${localDate()}T12:00:00`); day.setDate(day.getDate()+1); return `${day.getFullYear()}-${String(day.getMonth()+1).padStart(2,'0')}-${String(day.getDate()).padStart(2,'0')}`}
const blank = (): Draft => ({merchant:'',amount:100, category:'rent',kind:'expense',next_due:tomorrow(),interval_days:30})

export function ScheduleManager({revision, changed}: {revision: number; changed: (m: string) => void}) {
  const {public_demo} = useRuntime()
  const {data, error} = useResource<Schedule[]>('/schedules', revision)
  const [draft, setDraft] = useState<Draft>(blank)
  const [editing, setEditing] = useState<number | null>(null)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [saveError, setSaveError] = useState('')
  async function save(e: FormEvent) {
    e.preventDefault(); setBusy(true); setSaveError('')
    try {await api(editing ? `/schedules/${editing}` : '/schedules', {method: editing ? 'PUT' : 'POST', body:JSON.stringify(draft)}); changed('Schedule saved. Cash-flow estimates refreshed.'); setOpen(false); setEditing(null); setDraft(blank())}
    catch (err) {setSaveError(errorText(err))} finally {setBusy(false)}
  }
  async function remove(s: Schedule) {
    if (!window.confirm(`Remove the ${s.merchant} schedule? Historical transactions will be preserved.`)) return
    setBusy(true); setSaveError('')
    try {await api(`/schedules/${s.id}`,{method:'DELETE'}); changed('Schedule removed from forecast.')}
    catch (err) {setSaveError(errorText(err))} finally {setBusy(false)}
  }
  return <Panel className="mt"><PanelHeading title="Plan a bill or payday" subtitle="Rent, tuition, meal plans, allowance, salary, or scholarship payments" action={<button className="button secondary small" onClick={() => {setOpen(true); setEditing(null); setDraft(public_demo ? {...blank(),merchant:'One-time tuition payment'} : blank()); setSaveError('')}}><CalendarPlus size={15}/> Add schedule</button>}/>
    <ErrorNotice message={error || saveError}/>{open && <form className="form-stack schedule-form" onSubmit={save}><label>Schedule merchant or source{public_demo ? <select value={draft.merchant} onChange={e => setDraft(d => ({...d,merchant:e.target.value}))}>{[...new Set([draft.merchant,"Campus apartment rent","Family allowance","Campus job payroll","One-time tuition payment","Meal plan","Scholarship deposit","Tutoring wages"])].map(v => <option key={v}>{v}</option>)}</select> : <input required maxLength={160} value={draft.merchant} onChange={e => setDraft(d => ({...d,merchant:e.target.value}))}/>}</label><div className="form-grid"><label>Schedule amount ($)<input type="number" required min="0.01" max="1000000" step="0.01" value={draft.amount} onChange={e => setDraft(d => ({...d,amount:Number(e.target.value)}))}/></label><label>Next due date<input type="date" required value={draft.next_due} onChange={e => setDraft(d => ({...d,next_due:e.target.value}))}/></label><label>Schedule type<select value={draft.kind} onChange={e => setDraft(d => ({...d,kind:e.target.value as Draft['kind'],category:e.target.value === 'income' ? 'income' : 'rent'}))}><option value="expense">Expense</option><option value="income">Income</option></select></label><label>Schedule category<select value={draft.category} disabled={draft.kind === 'income'} onChange={e => setDraft(d => ({...d,category:e.target.value as Draft['category']}))}>{categories.filter(c => draft.kind === 'income' || c !== 'income').map(c => <option key={c} value={c}>{title(c)}</option>)}</select></label><label>Repeat interval<select value={draft.interval_days} onChange={e => setDraft(d => ({...d,interval_days:Number(e.target.value)}))}><option value={0}>One-time payment</option><option value={7}>Every week</option><option value={14}>Every two weeks</option><option value={30}>Each calendar month</option><option value={365}>Every 365 days</option>{![0,7,14,30,365].includes(draft.interval_days) && <option value={draft.interval_days}>Every {draft.interval_days} days</option>}</select></label></div><div className="button-row"><button className="button primary" disabled={busy}>Save schedule</button><button className="button secondary" type="button" onClick={() => setOpen(false)}><X size={15}/> Cancel</button></div></form>}
    <div className="schedule-list">{data?.filter(s => s.status !== 'incorrect').map(s => <div className="transaction-row" key={s.id}><CategoryIcon category={s.category}/><div className="transaction-name"><strong>{s.merchant}</strong><span>{prettyDate(s.next_due)} · {s.interval_days === 0 ? 'One-time' : s.interval_days === 30 ? 'Monthly' : `Every ${s.interval_days} days`} · {s.status}</span></div><strong className={s.kind === 'income' ? 'positive' : ''} style={{fontSize:11}}>{dollars(s.amount)}</strong><button className="icon-button" aria-label={`Edit ${s.merchant} schedule`} onClick={() => {setEditing(s.id); setDraft(s); setOpen(true); setSaveError('')}}><Pencil size={14}/></button><button className="icon-button danger" aria-label={`Delete ${s.merchant} schedule`} disabled={busy} onClick={() => void remove(s)}><Trash2 size={14}/></button></div>)}</div><p className="fine-print mt">Schedules affect estimates; they do not create paid transactions or move money. Record actual payments as transactions. For a single tuition or aid payment, choose one-time. Calendar months use their actual number of days.</p>
  </Panel>
}
