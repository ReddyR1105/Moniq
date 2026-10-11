import { useEffect, useState } from 'react'
import { ArrowRight, Bell, BookOpen, Check, ChevronLeft, ChevronRight, CircleHelp, Coffee, LayoutDashboard, Menu, MessageCircle, Play, Repeat2, Settings, Sparkles, Tag, TrendingUp, Wallet, Users, X } from 'lucide-react'
import { api, errorText, prettyDate, useResource } from './api'
import { useRuntime } from './runtime'
import { ErrorNotice, Loading } from './components'
import { EditTransactionDialog, ImportDialog, PurchaseDialog } from './dialogs'
import { AssistantPage } from './pages/Assistant'
import { BudgetsPage } from './pages/Budgets'
import { DealsPage } from './pages/Deals'
import { InsightsPage } from './pages/Insights'
import { Overview } from './pages/Overview'
import { SettingsPage } from './pages/Settings'
import { SubscriptionsPage } from './pages/Subscriptions'
import { CirclesPage } from './pages/Circles'
import { PwaInstall } from './PwaInstall'
import { TransactionsPage } from './pages/Transactions'
import type { Dashboard, Page, Profile, Transaction } from './types'

const navigation = [
  {name:'Overview', icon:LayoutDashboard}, {name:'Transactions', icon:Wallet}, {name:'Budgets', icon:BookOpen},
  {name:'AI Insights', icon:Sparkles}, {name:'Student Deals', icon:Tag}, {name:'Subscriptions', icon:Repeat2},
  {name:'Circles', icon:Users}, {name:'AI Assistant', icon:MessageCircle}, {name:'Settings', icon:Settings},
] as const
const pageFromHash = (): Page => navigation.find(n => n.name.toLowerCase().replaceAll(' ', '-') === window.location.hash.slice(1))?.name || 'Overview'
const guideSteps = [
  {title:'Meet your student', text:'Overview shows Alex’s balance, income, spending, and budgets, calculated from synthetic GSU records.', page:'Overview'},
  {title:'Catch a purchase', text:'Open this step, then Simulate a purchase alert. Review the merchant, amount, category and ML confidence. Confirm & save the $15.75 expense.', action:'purchase'},
  {title:'Review your saved purchase', text:'Open Transactions to find your Chick-fil-A purchase. Use Edit to correct its category or details. Same-date, merchant and amount duplicates are blocked.', page:'Transactions'},
  {title:'See the plan adjust', text:'Visit Budgets. The saved food expense has increased spending and reduced the remaining limit.', page:'Budgets'},
  {title:'Try your next choice', text:'In AI Insights, run the $150 purchase scenario and compare the numerical balance with your baseline.', page:'AI Insights'},
  {title:'Find a relevant saving', text:'Student Deals ranks synthetic examples that match spending, eligibility, and remaining budget. Bookmark one you might use on a planned purchase.', page:'Student Deals'},
  {title:'Ask a real question', text:'Choose “How much did I spend this week?” The local assistant retrieves calculated values from your stored records.', page:'AI Assistant'},
  {title:'Ready for another walkthrough', text:'Review detected subscriptions, or open Settings to Reset Demo for the next judge. Export and deletion controls also work.', page:'Settings'},
] as const

export default function App() {
  const {public_demo,workspace,hosted_app,authenticated,email} = useRuntime()
  const [page, setPage] = useState<Page>(pageFromHash)
  const [revision, setRevision] = useState(0)
  const [mobile, setMobile] = useState(false)
  const [dialog, setDialog] = useState<'purchase' | 'import' | 'transaction' | null>(null)
  const [editing, setEditing] = useState<Transaction | undefined>()
  const [splitTransaction,setSplitTransaction] = useState<Transaction>()
  const [toast, setToast] = useState('')
  const [guide, setGuide] = useState<number | null>(null)
  const [alertsOpen, setAlertsOpen] = useState(false)
  const [resetting,setResetting] = useState(false)
  const [resetError,setResetError] = useState('')
  const dashboard = useResource<Dashboard>('/dashboard', revision)
  const profile = useResource<Profile | null>('/profile', revision)
  useEffect(() => {const handle = () => setPage(pageFromHash()); window.addEventListener('hashchange',handle); return () => window.removeEventListener('hashchange',handle)}, [])
  useEffect(() => {document.title = `${page} · Moniq | Spending, Made Smarter.`}, [page])
  useEffect(() => {if (!toast) return; const timeout = window.setTimeout(() => setToast(''), 6000); return () => window.clearTimeout(timeout)}, [toast])
  function navigate(next: Page) {setPage(next); window.location.hash = next.toLowerCase().replaceAll(' ', '-'); setMobile(false); window.scrollTo({top:0,behavior:'smooth'})}
  function changed(message: string) {setRevision(n => n+1); setToast(message)}
  function saved(message: string) {changed(message); setDialog(null); setEditing(undefined)}
  function add() {setEditing(undefined); setDialog('transaction')}
  function edit(t: Transaction) {setEditing(t); setDialog('transaction')}
  async function reset() {
    if (!window.confirm(public_demo ? 'Reset only your synthetic demo session?' : 'Replace your local records and corrections with the synthetic student demo?')) return
    setResetting(true);setResetError('')
    try {await api('/demo/reset',{method:'POST'});localStorage.removeItem('moniq-saved-deals');changed('Synthetic GSU demo restored.');navigate('Overview');setGuide(0)}
    catch(e) {setResetError(errorText(e))} finally {setResetting(false)}
  }
  function doGuideStep(index: number) {
    const step = guideSteps[index]
    if ('page' in step) navigate(step.page)
    if ('action' in step) setDialog('purchase')
  }
  const data = dashboard.data
  const firstName = profile.data?.name.split(' ')[0] || 'Student'
  const notifications = profile.data?.notifications !== false
  return <div className="app-shell">
    {mobile && <button className="sidebar-overlay" aria-label="Close navigation" onClick={() => setMobile(false)}/>}
    <aside className={`sidebar ${mobile ? 'open' : ''}`}><a className="brand" href="#overview" onClick={() => navigate('Overview')} aria-label="Moniq overview"><span className="brand-mark">m<span>•</span></span><span>moniq</span></a><p className="brand-tagline">Spending, Made Smarter.</p><div className="workspace-label">YOUR FINANCIAL SPACE</div><nav aria-label="Main navigation">{navigation.map(({name,icon:Icon}) => <button key={name} aria-label={name} className={`nav-item ${page === name ? 'active' : ''} ${name === 'Settings' ? 'settings-nav' : ''}`} aria-current={page === name ? 'page' : undefined} onClick={() => navigate(name)}><Icon size={19} strokeWidth={1.7}/><span>{name}</span>{name === 'AI Insights' && <span className="nav-new">NEW</span>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="demo-card"><span className="demo-card-icon"><Coffee size={20}/></span><h3>Your future starts small.</h3><p>Take a two-minute tour of a smarter student budget.</p><button onClick={() => {setGuide(0); navigate('Overview')}}>Start guided demo <ArrowRight size={15}/></button></div><div className="prototype-label"><span className="status-dot"/> {workspace === 'personal' ? 'PERSONAL WORKSPACE' : 'SYNTHETIC DEMO · PROTOTYPE'}</div><button className="profile-mini" onClick={() => navigate('Settings')}><span className="avatar">{firstName.charAt(0)}</span><span><strong>{profile.data?.name || 'Student profile'}</strong><small>{profile.data?.university === 'Georgia State University' ? 'Georgia State University' : profile.data?.university || 'Local demo'}</small></span><ChevronRight size={15}/></button></div>
    </aside>
    <div className="main-shell"><header className="topbar"><div className="topbar-location"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobile(true)}><Menu size={22}/></button><span>Your space</span><ChevronRight size={14}/><strong>{page}</strong></div><div className="topbar-right"><span className="today-date">{data ? prettyDate(data.as_of,{weekday:'short', month:'short', day:'numeric', year:'numeric'}) : 'Local student demo'}</span><button className="icon-button help-button" aria-label="Start guided demo" onClick={() => {setGuide(0); navigate('Overview')}}><CircleHelp size={20}/></button><div className="alerts-wrap"><button className="icon-button" aria-label="Financial notifications" aria-expanded={alertsOpen} onClick={() => setAlertsOpen(v => !v)}><Bell size={20}/>{notifications && data?.insights.warnings.length ? <span className="notification-dot"/> : null}</button>{alertsOpen && <div className="alerts-popover"><strong>Financial notifications</strong><button className="icon-button" aria-label="Close notifications" onClick={() => setAlertsOpen(false)}><X size={15}/></button>{!notifications ? <p>In-app alerts are disabled in Settings.</p> : data?.insights.warnings.length ? data.insights.warnings.map(w => <p key={w}>{w}</p>) : <p>No overspending alerts right now.</p>}</div>}</div><button className="avatar small-avatar" onClick={() => navigate('Settings')} aria-label="Open student settings">{firstName.charAt(0)}</button></div></header>
      <main id="main-content">{workspace === 'scenario' ? <div className="demo-ribbon"><span>ISOLATED SYNTHETIC SCENARIO</span><p>Real ledger calculations. No real Gmail access.</p><button className="text-button" onClick={async()=>{await api('/workspace',{method:'POST',body:JSON.stringify({workspace:'demo'})});window.location.reload()}}>Return to synthetic demo</button></div> : workspace === 'personal' ? <div className="demo-ribbon"><span><span className="status-dot"/> PERSONAL WORKSPACE</span><p>{hosted_app?"Private records in your authenticated workspace. Confirmed transactions update your plan.":"Local private records. Confirmed transactions update your plan."}</p><button className="text-button" onClick={() => navigate('Settings')}>Gmail &amp; accounts</button><button className="text-button" onClick={async () => {try {await api('/workspace',{method:'POST',body:JSON.stringify({workspace:'demo'})});window.location.reload()} catch(e) {setResetError(errorText(e))}}}>Open synthetic demo</button></div> : <div className="demo-ribbon"><span><span className="status-dot"/> DEMO MODE</span><p>{public_demo ? "Your isolated synthetic session. No personal statements or bank credentials. Resets on expiry or restart." : "Synthetic student data. Real calculations. No bank account needed."}</p><button className="text-button" onClick={() => {setGuide(0);navigate('Overview')}}>Start Demo</button>{page !== 'Settings' && <button className="text-button" disabled={resetting} onClick={() => void reset()}>Reset Demo</button>}<button className="text-button" onClick={() => setDialog('purchase')}><Play size={13}/> Try purchase alert</button></div>}
        {hosted_app && <div className="session-controls"><span>{authenticated?`Signed in as ${email}. ${workspace==='personal'?'Your private workspace.':'Synthetic demo; Gmail is unavailable here.'}`:'Anonymous synthetic demo session.'}</span>{authenticated&&workspace!=='personal'&&<button className="button secondary small" onClick={async()=>{try{await api('/workspace',{method:'POST',body:JSON.stringify({workspace:'personal'})});window.location.reload()}catch(e){setResetError(errorText(e))}}}>Open private workspace</button>}<button className="text-button" onClick={async()=>{try{await api(authenticated?'/auth/logout':'/welcome',{method:'POST',body:'{}'});window.location.hash='';window.location.reload()}catch(e){setResetError(errorText(e))}}}>{authenticated?'Log Out':'Return to welcome'}</button></div>}
        {guide !== null && <section className="guide-panel" aria-label="Guided demo"><span className="guide-number">{guide+1}/8</span><div><h3>{guideSteps[guide].title}</h3><p>{guideSteps[guide].text}</p></div><div className="guide-actions"><button className="button secondary small" onClick={() => doGuideStep(guide)}>Open step <ArrowRight size={14}/></button><button className="icon-button" aria-label="Previous demo step" disabled={guide === 0} onClick={() => setGuide(g => Math.max(0,(g || 0)-1))}><ChevronLeft size={18}/></button><button className="icon-button" aria-label={guide === 7 ? 'Finish guided demo' : 'Next demo step'} onClick={() => setGuide(g => g === 7 ? null : (g || 0)+1)}>{guide === 7 ? <Check size={18}/> : <ChevronRight size={18}/>}</button><button className="icon-button" aria-label="Close guided demo" onClick={() => setGuide(null)}><X size={17}/></button></div></section>}
        <ErrorNotice message={dashboard.error || profile.error || resetError}/>{dashboard.error && <button className="button secondary" onClick={() => public_demo ? window.location.reload() : setRevision(v => v+1)}>Retry connection</button>}
        {!data && dashboard.loading ? <Loading/> : data && <div className="page-content" key={page}>
          {page === 'Overview' && <Overview changed={changed} revision={revision} data={data} profile={profile.data} navigate={navigate} purchase={() => setDialog('purchase')} add={add}/>}
          {page === 'Transactions' && <TransactionsPage split={t=>{setSplitTransaction(t);navigate('Circles')}} revision={revision} edit={edit} add={add} importCsv={() => setDialog('import')} changed={changed}/>}
          {page === 'Budgets' && <BudgetsPage revision={revision} changed={changed} dashboard={data} settings={() => navigate('Settings')}/>}
          {page === 'AI Insights' && <InsightsPage revision={revision} changed={changed}/>}
          {page === 'Student Deals' && <DealsPage revision={revision}/>}
          {page === 'Subscriptions' && <SubscriptionsPage revision={revision} changed={changed}/>}
          {page === 'AI Assistant' && <AssistantPage/>}
          {page === 'Circles' && <CirclesPage revision={revision} changed={changed} splitTransaction={splitTransaction} onLinked={()=>setSplitTransaction(undefined)}/>}
          {page === 'Settings' && <><SettingsPage revision={revision} changed={changed}/><PwaInstall/></>}
        </div>}
        <footer className="page-footer"><span>Moniq <span>·</span> Spending, Made Smarter.</span><span>Built for college life <TrendingUp size={13}/></span></footer>
      </main>
    </div>
    {dialog === 'purchase' && <PurchaseDialog onClose={() => setDialog(null)} onSaved={saved}/>}
    {dialog === 'transaction' && <EditTransactionDialog item={editing} onClose={() => setDialog(null)} onSaved={saved}/>}
    {dialog === 'import' && <ImportDialog onClose={() => setDialog(null)} onSaved={saved}/>}
    {toast && <div className="toast" role="status"><Check size={18}/><span>{toast}</span><button aria-label="Dismiss notification" onClick={() => setToast('')}><X size={16}/></button></div>}
    <a className="skip-link" href="#main-content">Skip to main content</a>
  </div>
}
