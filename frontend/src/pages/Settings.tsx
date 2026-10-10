import { useEffect, useState, type FormEvent } from 'react'
import { Check, Download, GraduationCap, RotateCcw, Target, Trash2 } from 'lucide-react'
import { api, dollars, errorText, localDate, useResource } from '../api'
import { Empty, ErrorNotice, Loading, Panel, PanelHeading, Progress } from '../components'
import type { Goal, Profile } from '../types'
import { useRuntime } from '../runtime'
import { SmartApproveSettings } from '../SmartApprove'
import { GmailSettings } from '../GmailSettings'
import { AccountTools } from '../AccountTools'

function GoalEditor({goal, changed}: {goal: Goal; changed: (m: string) => void}) {
  const {public_demo} = useRuntime()
  const [form, setForm] = useState(goal)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [monthly,setMonthly] = useState(String(goal.monthly_contribution))
  const [contribution,setContribution] = useState('25.00')
  useEffect(() => setForm(goal), [goal])
  async function save(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError('')
    try {await api(`/goals/${goal.id}`, {method:'PUT', body: JSON.stringify(form)}); changed('Savings goal updated.')}
    catch (err) {setError(errorText(err))} finally {setBusy(false)}
  }
  return <><form onSubmit={save} className="form-stack"><div className="goal-heading"><Target size={20}/><strong>{goal.name}</strong><span>{dollars(goal.saved)} / {dollars(goal.target)}</span></div><Progress value={goal.saved / goal.target} label={goal.name}/><label>Goal name<input readOnly={public_demo} required maxLength={80} value={form.name} onChange={e => setForm(f => ({...f,name:e.target.value}))}/></label><div className="form-grid"><label>Target ($)<input type="number" required min="0.01" max="1000000" step="0.01" value={form.target} onChange={e => setForm(f => ({...f,target:Number(e.target.value)}))}/></label><label>Saved ($)<input type="number" required min="0" max="1000000" step="0.01" value={form.saved} onChange={e => setForm(f => ({...f,saved:Number(e.target.value)}))}/></label></div><button className="button secondary" disabled={busy}><Check size={16}/> Save goal</button><ErrorNotice message={error}/></form>
    <p className="fine-print">{goal.recommendation} {goal.projected_completion ? `Estimated completion: ${goal.projected_completion}.` : ''} {goal.assumption}</p>
    <form className="form-stack" onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');try{await api(`/goals/${goal.id}/plan`,{method:'PUT',body:JSON.stringify({monthly_contribution:monthly})});changed('Savings plan updated. Estimated money is not deposited.')}catch(e){setError(errorText(e))}finally{setBusy(false)}}}><label>Planned monthly contribution ($)<input type="number" required min="0" max="1000000" step="0.01" value={monthly} onChange={e=>setMonthly(e.target.value)}/></label><button className="button secondary" disabled={busy}>Save contribution plan</button></form>
    <form className="form-stack mt" onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');try{await api(`/goals/${goal.id}/contributions`,{method:'POST',body:JSON.stringify({amount:contribution,date:localDate(),request_key:crypto.randomUUID()})});changed('Savings contribution recorded. Account cash remains unchanged.')}catch(e){setError(errorText(e))}finally{setBusy(false)}}}><label>Recorded contribution ($)<input type="number" required min="0.01" max="1000000" step="0.01" value={contribution} onChange={e=>setContribution(e.target.value)}/></label><button className="button secondary" disabled={busy}>Record goal contribution</button></form>
    {goal.contributions.map(c=><p className="fine-print" key={c.id}>{c.date}: {dollars(c.amount)} recorded contribution</p>)}
  </>
}

export function SettingsPage({revision, changed}: {revision: number; changed: (m: string) => void}) {
  const {public_demo,workspace} = useRuntime()
  const profile = useResource<Profile | null>('/profile', revision)
  const goals = useResource<Goal[]>('/goals', revision)
  const [form, setForm] = useState<Profile | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => setForm(profile.data), [profile.data])
  async function save(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError('')
    try {await api('/profile', {method:'PUT', body: JSON.stringify(form)}); changed('Profile saved. Allowance schedule and recommendations refreshed.')}
    catch (err) {setError(errorText(err))} finally {setBusy(false)}
  }
  function update<K extends keyof Profile>(key: K, value: Profile[K]) {setForm(f => f ? {...f,[key]:value} : f)}
  async function reset() {
    if (!window.confirm(public_demo ? 'Reset only your synthetic session?' : 'Replace all local data and corrections with the synthetic GSU demo?')) return
    setBusy(true); setError('')
    try {await api('/demo/reset', {method:'POST'}); localStorage.removeItem('moniq-saved-deals'); changed('Synthetic GSU demo restored.')}
    catch (err) {setError(errorText(err))} finally {setBusy(false)}
  }
  async function erase() {
    if (!window.confirm(public_demo ? 'Delete only your synthetic session records?' : 'Delete all local financial records, profile, goals, notifications, and classifier corrections? Export first if you need a copy.')) return
    setBusy(true); setError('')
    try {await api('/data', {method:'DELETE'}); localStorage.removeItem('moniq-saved-deals'); changed(public_demo ? 'Your session records deleted. Reset Demo can restore synthetic examples.' : workspace === 'personal' ? 'Personal records deleted and Gmail disconnected.' : 'Local records deleted. Reset Demo can restore synthetic examples.')}
    catch (err) {setError(errorText(err))} finally {setBusy(false)}
  }
  return <><div className="page-intro"><div><span className="eyebrow">MAKE IT FEEL LIKE YOU</span><h1>Your life. Your settings.</h1><p>{public_demo ? "Explore a fictional plan in your isolated temporary session." : "Shape your financial plan and stay in control of your local data."}</p></div></div><ErrorNotice message={error || profile.error || goals.error}/>
    {workspace !== 'scenario' && !public_demo && <GmailSettings revision={revision} changed={changed}/>}
    <AccountTools revision={revision} changed={changed}/>
    <SmartApproveSettings revision={revision} changed={changed}/>
    {profile.loading ? <Loading/> : <div className="settings-grid"><Panel><PanelHeading title="Student profile" subtitle={workspace === 'personal' ? "Your personal planning preferences" : "A synthetic Georgia State student in demo mode"} action={<GraduationCap size={22}/>}/>{form ? <form className="form-stack" onSubmit={save}><div className="form-grid"><label>Name<input readOnly={public_demo} required maxLength={80} value={form.name} onChange={e => update('name',e.target.value)}/></label><label>Academic year<select value={form.academic_year} onChange={e => update('academic_year',e.target.value)}>{['Freshman','Sophomore','Junior','Senior','Graduate'].map(y => <option key={y}>{y}</option>)}</select></label></div><label>University{public_demo ? <select value={form.university} onChange={e => update('university',e.target.value)}>{["Georgia State University","Georgia Tech","Emory University","Other synthetic university"].map(v => <option key={v}>{v}</option>)}</select> : <input required maxLength={120} value={form.university} onChange={e => update('university',e.target.value)}/>}</label><div className="form-grid"><label>Monthly allowance ($)<input type="number" required min="0" max="1000000" step="0.01" value={form.allowance} onChange={e => update('allowance',Number(e.target.value))}/></label><label>Income preference<select value={form.income_preference} onChange={e => update('income_preference',e.target.value)}>{['Part-time employment','Family allowance','Scholarships / financial aid','Mixed income'].map(v => <option key={v}>{v}</option>)}</select></label></div><label>Interests (comma-separated){public_demo ? <select value={form.interests} onChange={e => update('interests',e.target.value)}>{["food,technology,education,transportation","groceries,food","technology,education","transportation,entertainment"].map(v => <option key={v}>{v}</option>)}</select> : <input maxLength={300} value={form.interests} placeholder="food,technology,education" onChange={e => update('interests',e.target.value)}/>}</label><label className="checkbox-label"><input type="checkbox" checked={form.student_verified} onChange={e => update('student_verified',e.target.checked)}/><span>Simulated student eligibility for sample offers</span></label><label className="checkbox-label"><input type="checkbox" checked={form.notifications} onChange={e => update('notifications',e.target.checked)}/><span>Show in-app spending alerts</span></label><p className="fine-print">Allowance changes update the existing income schedule. Income preference describes your profile; salary and scholarship income are recorded as transactions. No real enrollment verification or push notifications are connected.</p><button className="button primary" disabled={busy}><Check size={16}/> Save profile</button></form> : <Empty title="Profile deleted">{workspace === 'personal' ? 'Personal records remain separate from the synthetic demo.' : 'Reset Demo to restore the sample profile.'}</Empty>}</Panel>
      <div className="settings-side"><Panel><PanelHeading title="Something to work toward" subtitle="Goal tracking, without moving money"/>{goals.data?.length ? goals.data.map(g => <GoalEditor key={g.id} goal={g} changed={changed}/>) : <><Empty title="Start a savings goal">Track a target here. It does not reserve or transfer account funds.</Empty><button className="button secondary" disabled={busy} onClick={async () => {setBusy(true); try {await api('/goals/1', {method:'PUT', body:JSON.stringify({name:'Emergency fund', target:1500, saved:0})}); changed('New savings goal created.')} catch(e) {setError(errorText(e))} finally {setBusy(false)}}}><Target size={16}/> Create emergency fund goal</button></>}<button className="button secondary mt" disabled={busy} onClick={async()=>{setBusy(true);try{const id=Math.max(0,...(goals.data||[]).map(g=>g.id))+1;await api(`/goals/${id}`,{method:'PUT',body:JSON.stringify({name:'Laptop fund',target:1000,saved:0})});changed('Additional savings goal created.')}catch(e){setError(errorText(e))}finally{setBusy(false)}}}>Add another savings goal</button><p className="fine-print">Saved amounts are a progress record. They are not deducted from your available balance.</p></Panel>
      <Panel><PanelHeading title="Your data belongs to you" subtitle="Export everything or only transactions"/><div className="button-row"><a className="button secondary" href="/api/export"><Download size={16}/> Export JSON</a><a className="button secondary" href="/api/export?format=csv"><Download size={16}/> Export CSV</a></div><p className="fine-print">JSON includes profile, account, budgets, schedules, goals, transactions, imported notifications, and corrections.</p></Panel></div></div>}
    <Panel className="mt"><PanelHeading title="Demo & data controls" subtitle={public_demo ? "Temporary isolated session, synthetic financial data" : workspace === 'personal' ? "Private local records, separate from the demo" : "Local, single-user prototype, synthetic financial data"}/>{workspace !== 'personal' && <div className="data-controls"><div><h3>Reset the demo</h3><p>Restore the GSU student profile, spending history, budgets, goals, and sample offers.</p></div><button className="button secondary" disabled={busy} onClick={() => void reset()}><RotateCcw size={16}/> Reset Demo</button></div>}<div className="data-controls"><div><h3>{public_demo ? "Delete session data" : "Delete local data"}</h3><p>{public_demo ? "Remove records in only your session. The server can restart or expire sessions at any time." : "Remove financial records and correction-trained model effects. Data stays deleted after a restart."}</p></div><button className="button danger-button" disabled={busy} onClick={() => void erase()}><Trash2 size={16}/> Delete all data</button></div></Panel>
    <div className="sample-disclosure"><strong>Prototype, with clear boundaries.</strong><p>{public_demo ? "Temporary isolated synthetic session, not persistent cloud storage. Personal uploads, free-form personal fields and shared model retraining are disabled. " : "SQLite persistence on this computer. Keep the backend bound to localhost. "}{!public_demo && "Gmail is an optional, explicitly authorized read-only connection with encrypted backend tokens. "}No bank connection, SMS access, real student verification, subscription cancellation, or production account authentication. Keep this personal workspace local.</p></div>
  </>
}
