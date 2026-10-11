import { useEffect, useState, type FormEvent } from 'react'
import { Mail, RefreshCw, Unplug } from 'lucide-react'
import { api, dollars, errorText, localDate, title, useResource } from './api'
import { ErrorNotice, Panel, PanelHeading } from './components'
import { categories, type Category } from './types'
import { useRuntime } from './runtime'

type Account = {id:number;name:string;account_type:string;last_four:string|null;opening_balance:number;balance:number;balance_date:string;estimated?:boolean}
type GmailStatus = {configured:boolean;connected:boolean;tokens_present:boolean;connection_error:string|null;email:string|null;redirect_uri:string;scope:string}
type EmailItem = {id:number;subject:string;sender:string;event_type:string;merchant:string;amount:number|null;date:string;last_four:string|null;category:Category;confidence:number;reasons:string[];account_id:number|null;status:string}
type Props = {revision:number;changed:(message:string)=>void}

export function EmailReview({item,accounts,changed,active=false}: {item:EmailItem;accounts:Account[];changed:Props['changed'];active?:boolean}) {
  const {workspace} = useRuntime()
  const [merchant,setMerchant] = useState(item.merchant)
  const [amount,setAmount] = useState(item.amount === null ? '' : String(item.amount))
  const [day,setDay] = useState(item.date)
  const [account,setAccount] = useState(item.account_id === null ? '' : String(item.account_id))
  const [kind,setKind] = useState(item.event_type === 'income' ? 'income' : item.event_type === 'refund' ? 'refund' : 'expense')
  const [category,setCategory] = useState<Category>(item.category)
  const [posted,setPosted] = useState(false)
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState('')
  async function confirm(e:FormEvent) {
    e.preventDefault();setBusy(true);setError('')
    try {
      const result = await api<{status:string}>(`${active?'/approvals':'/gmail/items'}/${item.id}/confirm`,{method:'POST',body:JSON.stringify({description:merchant,merchant,amount,date:day,account_id:Number(account),kind,category:kind==='income'?'income':category,posted_confirmed:posted})})
      changed(result.status === 'duplicate' ? 'Duplicate email transaction skipped.' : 'Gmail transaction confirmed. Balance, budgets and forecast refreshed.')
    } catch(e) {setError(errorText(e))} finally {setBusy(false)}
  }
  async function dismiss() {
    setBusy(true);setError('')
    try {await api(`${active?'/approvals':'/gmail/items'}/${item.id}/dismiss`,{method:'POST'});changed('Email dismissed. No balance change.')} catch(e) {setError(errorText(e))} finally {setBusy(false)}
  }
  return <article className="gmail-review"><h3>{item.subject || 'Financial email'}</h3><p className="fine-print">{item.sender} · {title(item.event_type)}{item.last_four ? ` · ending ${item.last_four}` : ''} · {Math.round(item.confidence*100)}% ML confidence</p>
    {item.reasons.length > 0 && <ul className="gmail-reasons">{item.reasons.map(r=><li key={r}>{r}</li>)}</ul>}
    <form className="form-stack" onSubmit={confirm}><fieldset disabled={busy || (!active && workspace !== 'personal')}>
      <div className="form-grid"><label>Detected merchant<input required maxLength={160} value={merchant} onChange={e=>setMerchant(e.target.value)}/></label><label>Registered account<select required value={account} onChange={e=>setAccount(e.target.value)}><option value="">Choose account</option>{accounts.map(a=><option key={a.id} value={a.id}>{a.name}{a.last_four?` · ${a.last_four}`:''}</option>)}</select></label></div>
      <div className="form-grid"><label>Detected amount ($)<input type="number" required min="0.01" max="1000000" step="0.01" value={amount} onChange={e=>setAmount(e.target.value)}/></label><label>Posted transaction date<input type="date" required value={day} onChange={e=>setDay(e.target.value)}/></label></div>
      <div className="form-grid"><label>Cash-flow type<select value={kind} onChange={e=>setKind(e.target.value)}><option value="expense">Expense</option><option value="income">Confirmed income</option><option value="refund">Refund</option></select></label><label>Email category<select value={kind==='income'?'income':category} disabled={kind==='income'} onChange={e=>setCategory(e.target.value as Category)}>{categories.filter(c=>kind==='income'||c!=='income').map(c=><option key={c} value={c}>{title(c)}</option>)}</select></label></div>
      <label className="checkbox-label"><input type="checkbox" required checked={posted} onChange={e=>setPosted(e.target.checked)}/><span>I verified this is posted, not pending, a future bill, or a duplicate.</span></label>
      <div className="button-row"><button className="button primary" disabled={!posted || !account || busy}>Confirm email transaction</button><button type="button" className="button secondary" onClick={()=>void dismiss()}>Dismiss email</button></div>
    </fieldset><ErrorNotice message={error}/></form>
    {!active && workspace !== 'personal' && <p className="fine-print">Open the personal workspace to confirm. The synthetic demo remains separate.</p>}
  </article>
}

export function GmailSettings({revision,changed}:Props) {
  const {workspace} = useRuntime()
  const status = useResource<GmailStatus>('/gmail/status',revision)
  const accounts = useResource<Account[]>('/gmail/accounts',revision)
  const items = useResource<EmailItem[]>('/gmail/items',revision)
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState('')
  const [notice,setNotice] = useState('')
  const [editing,setEditing] = useState<number|null>(null)
  const [form,setForm] = useState({name:'Checking',account_type:'checking',last_four:'',opening_balance:'10.00',balance_date:localDate()})
  useEffect(()=>{
    const result = new URLSearchParams(window.location.search).get('gmail')
    if (result) {
      setNotice(result === 'connected' ? 'Gmail connected. Sync Now loads emails into the review queue.' : 'Google authorization was cancelled. No new connection was made.')
      window.history.replaceState(null,'',window.location.pathname+'#settings')
    }
  },[])
  async function connect() {
    setBusy(true);setError('')
    try {const result=await api<{authorization_url:string}>('/gmail/connect',{method:'POST'});window.location.assign(result.authorization_url)} catch(e) {setError(errorText(e));setBusy(false)}
  }
  async function sync() {
    setBusy(true);setError('')
    try {const result=await api<{queued:number;auto_approved?:number;more_available:boolean}>('/gmail/sync',{method:'POST'});changed(`${result.auto_approved||0} auto-approved; ${result.queued} financial emails queued for review.${result.more_available ? ' More available; Sync Now continues the next batch.' : ''}`)} catch(e) {setError(errorText(e))} finally {setBusy(false)}
  }
  async function disconnect() {
    setBusy(true);setError('')
    try {const result=await api<{message:string}>('/gmail/disconnect',{method:'POST'});setNotice(result.message);changed('Gmail disconnected. Confirmed transactions are retained.')} catch(e) {setError(errorText(e))} finally {setBusy(false)}
  }
  async function switchWorkspace(next:'demo'|'personal') {
    setBusy(true);setError('')
    try {await api('/workspace',{method:'POST',body:JSON.stringify({workspace:next})});window.location.reload()} catch(e) {setError(errorText(e));setBusy(false)}
  }
  async function saveAccount(e:FormEvent) {
    e.preventDefault();setBusy(true);setError('')
    try {await api(editing===null?'/gmail/accounts':`/gmail/accounts/${editing}`,{method:editing===null?'POST':'PUT',body:JSON.stringify({...form,last_four:form.last_four||null})});setEditing(null);changed('Personal account saved. Starting balance and posted records determine its balance.')} catch(e) {setError(errorText(e))} finally {setBusy(false)}
  }
  function edit(a:Account) {setEditing(a.id);setForm({name:a.name,account_type:a.account_type,last_four:a.last_four||'',opening_balance:String(a.opening_balance),balance_date:a.balance_date})}
  const pending = items.data?.filter(i=>i.status==='review') || []
  return <>
    <Panel className="mt"><PanelHeading title="Gmail financial alerts" subtitle="Private local connection, separate from the synthetic demo" action={<Mail size={22}/>}/>
      <ErrorNotice message={error || status.error || status.data?.connection_error || accounts.error || items.error}/>{notice && <p className="success-note" role="status">{notice}</p>}
      <p>{status.data?.connected ? `Connected to ${status.data.email}.` : 'Connect your Google test account to review purchase, paycheck, refund, subscription and bill emails.'}</p>
      <div className="button-row mt"><button className="button primary" disabled={busy || !status.data?.configured} onClick={()=>void connect()}><Mail size={16}/> {status.data?.connected?'Reconnect Gmail':'Connect Gmail'}</button><button className="button secondary" disabled={busy || !status.data?.connected} onClick={()=>void sync()}><RefreshCw size={16}/> Sync Now</button><button className="button secondary" disabled={busy || !status.data?.tokens_present} onClick={()=>void disconnect()}><Unplug size={16}/> Disconnect Gmail</button></div>
      {!status.data?.configured && <p className="fine-print">Setup needed: put GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET and GMAIL_TOKEN_ENCRYPTION_KEY in the backend .env, then restart. See docs/GMAIL_SETUP.md. Do not paste secrets into Moniq.</p>}
      <p className="fine-print">Gmail read-only access. Tokens stay encrypted on this backend. No emails are sent, modified or deleted. SmartApprove may confirm eligible posted events only when you enable a trusted sender. All other items require manual confirmation. Gmail balances are estimates. Raw email bodies and attachments are not saved.</p>
      <div className="data-controls"><div><h3>{workspace==='personal'?'Personal workspace is active':'Synthetic workspace is active'}</h3><p>Your personal account balances and email review queue are in a separate local database.</p></div><button className="button secondary" disabled={busy} onClick={()=>void switchWorkspace(workspace==='personal'?'demo':'personal')}>{workspace==='personal'?'Use synthetic demo':'Open personal workspace'}</button></div>
    </Panel>
    <Panel className="mt"><PanelHeading title="Registered personal accounts" subtitle="Register only the name, type, starting balance/date and optional last four digits"/>
      {accounts.data?.map(a=><div className="data-controls" key={a.id}><div><h3>{a.name} {a.last_four?`· ${a.last_four}`:''}</h3><p>{title(a.account_type)} · {dollars(a.balance)} estimated balance · starting {dollars(a.opening_balance)} on {a.balance_date}</p></div><button className="button secondary" onClick={()=>edit(a)}>Edit {a.name} account</button></div>)}
      <form className="form-stack mt" onSubmit={saveAccount}><div className="form-grid"><label>Personal account name<input required maxLength={80} value={form.name} onChange={e=>setForm(f=>({...f,name:e.target.value}))}/></label><label>Personal account type<select value={form.account_type} onChange={e=>setForm(f=>({...f,account_type:e.target.value}))}><option value="checking">Checking</option><option value="savings">Savings</option><option value="credit">Credit</option></select></label></div>
        <div className="form-grid"><label>Account or card last four<input inputMode="numeric" pattern="[0-9]{4}" maxLength={4} value={form.last_four} onChange={e=>setForm(f=>({...f,last_four:e.target.value}))}/></label><label>Starting balance ($)<input type="number" required min="-1000000" max="1000000" step="0.01" value={form.opening_balance} onChange={e=>setForm(f=>({...f,opening_balance:e.target.value}))}/></label></div>
        <label>Starting balance date<input type="date" required value={form.balance_date} onChange={e=>setForm(f=>({...f,balance_date:e.target.value}))}/></label><button className="button secondary" disabled={busy}>{editing===null?'Register account':'Save account'}</button>
        <p className="fine-print">Starting balance is the amount before this date's transactions. Earlier emails are excluded from confirmation. Use negative balances for debt; no bank password or full card number is accepted.</p>
      </form>
    </Panel>
    <Panel className="mt"><PanelHeading title="Email review queue" subtitle={`${pending.length} pending · manual review for events outside your enabled sender policy`}/>
      {pending.length ? pending.map(item=><EmailReview key={item.id} item={item} accounts={accounts.data||[]} changed={changed}/>) : <p className="fine-print">No pending emails. Connect Gmail and Sync Now to load supported financial alerts.</p>}
    </Panel>
  </>
}

export function DashboardApprovals({revision,changed}:Props) {
  const {workspace,public_demo} = useRuntime()
  const queue = useResource<{items:EmailItem[];accounts:Account[];synthetic_scenario:boolean}>('/approvals',revision)
  const [busy,setBusy] = useState(false), [error,setError] = useState('')
  async function simulate(event:'paycheck'|'purchase') {setBusy(true);setError('');try{await api('/upgrade-demo/financial-alert',{method:'POST',body:JSON.stringify({event})});changed('Synthetic email parsed. Review the extracted fields before confirming.')}catch(e){setError(errorText(e))}finally{setBusy(false)}}
  const synthetic = workspace==='scenario'||queue.data?.synthetic_scenario
  if(workspace!=='personal'&&!synthetic&&!queue.data?.items.length) return null
  return <Panel><PanelHeading title="Pending transaction approvals" subtitle={workspace==='scenario'||public_demo?'Simulated emails - actual parser, classifier and ledger':'Your financial emails - confirm posted transactions before they change your balance'}/><ErrorNotice message={queue.error||error}/>
    {synthetic&&<div className="button-row"><button className="button secondary" disabled={busy} onClick={()=>void simulate('paycheck')}>Simulate $400 paycheck email</button><button className="button secondary" disabled={busy} onClick={()=>void simulate('purchase')}>Simulate $15 purchase email</button></div>}
    {queue.data?.items.length?queue.data.items.map(item=><EmailReview active key={item.id} item={item} accounts={queue.data?.accounts||[]} changed={changed}/>):<p className="fine-print">No transactions awaiting confirmation. Connection and sync controls are in Settings.</p>}
  </Panel>
}
