import { useState, type FormEvent } from 'react'
import { ArrowRight, CheckCircle2, LockKeyhole, Mail, Sparkles, Users, Wallet } from 'lucide-react'
import { api, errorText, setSessionCsrf } from './api'
import { ErrorNotice } from './components'
import { useRuntime } from './runtime'

type Screen = 'welcome'|'login'|'register'|'recover'|'reset'
function initial() {
  const fragment=new URLSearchParams(window.location.hash.slice(1))
  const invitation=fragment.get('invite')||''
  const reset=fragment.get('reset')||''
  if(invitation||reset) window.history.replaceState(null,'',window.location.pathname)
  return {screen:(reset?'reset':invitation?'register':window.location.hash==='#login'?'login':'welcome') as Screen,token:reset||invitation}
}
export function Welcome() {
  const {private_accounts_enabled} = useRuntime()
  const [link] = useState(initial)
  const [screen,setScreen] = useState<Screen>(link.screen)
  const [email,setEmail]=useState('')
  const [password,setPassword]=useState('')
  const [token,setToken]=useState(link.token)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  function open(next:Screen) {setScreen(next);setError('');setNotice('');setPassword('')}
  async function demo() {
    setBusy(true);setError('')
    try {await api('/demo/start',{method:'POST',body:'{}'});window.location.hash='overview';window.location.reload()}
    catch(e) {setError(errorText(e));setBusy(false)}
  }
  async function submit(e:FormEvent) {
    e.preventDefault();setBusy(true);setError('');setNotice('')
    try {
      if(screen==='login') {
        const result=await api<{csrf_token:string}>('/auth/login',{method:'POST',body:JSON.stringify({email,password})})
        setSessionCsrf(result.csrf_token);window.location.hash='overview';window.location.reload()
      } else if(screen==='register') {
        await api('/auth/register',{method:'POST',body:JSON.stringify({email,password,invitation:token})})
        setPassword('');setToken('');setScreen('login');setNotice('Your account is created and your email is verified. Log in to your private workspace.')
      } else if(screen==='recover') {
        const result=await api<{message:string}>('/auth/recover',{method:'POST',body:JSON.stringify({email})});setNotice(result.message)
      } else if(screen==='reset') {
        await api('/auth/reset-password',{method:'POST',body:JSON.stringify({token,password})});setPassword('');setToken('');setScreen('login');setNotice('Password updated. Your previous sessions have been signed out.')
      }
    } catch(e) {setError(errorText(e))} finally {setBusy(false)}
  }
  return <main className="welcome-page"><header className="welcome-nav"><a className="brand" href="#" onClick={()=>open('welcome')}><span className="brand-mark">m<span>•</span></span><span>moniq</span></a><div className="button-row"><button className="text-button" onClick={()=>open('login')}>Log In</button><button className="button primary small" onClick={()=>open('register')}>Create Account</button></div></header>
    <div className="welcome-layout"><section className="welcome-hero"><span className="eyebrow"><Sparkles size={16}/> MADE FOR STUDENT LIFE</span><h1>Your money.<br/>A little more clarity.</h1><p className="welcome-tagline">Spending, Made Smarter.</p><p>From a coffee run to splitting rent, see where your money goes and make room for what matters.</p><div className="button-row"><button className="button primary" onClick={()=>open('register')}>Create Account <ArrowRight size={17}/></button><button className="button secondary" disabled={busy} onClick={()=>void demo()}>Try Demo</button></div><p className="fine-print">Explore with synthetic student data. No Gmail connection or bank account required.</p><div className="welcome-features"><div><Wallet/><strong>A clearer budget</strong><span>Spending, balances and savings in one place.</span></div><div><Mail/><strong>Review before you save</strong><span>Try simulated email transaction approvals.</span></div><div><Users/><strong>Your share, sorted</strong><span>Split expenses with Circles.</span></div></div></section>
      <section className="welcome-card" aria-label="Account access">{screen==='welcome'?<><span className="welcome-card-icon"><LockKeyhole size={25}/></span><h2>A space that belongs to you.</h2><p>Private test accounts keep your records separate. Start with a demo, or log in with an invitation.</p><button className="button primary" onClick={()=>open('login')}>Log In <ArrowRight size={16}/></button><button className="button secondary" disabled={busy} onClick={()=>void demo()}>Try Demo</button><p className="fine-print">{private_accounts_enabled?'Private testing is invitation only. Verify your email with the invitation link before logging in.':'Private accounts are being prepared. The public demo is available now.'}</p></>:<><h2>{screen==='login'?'Welcome back.':screen==='register'?'Create your private space.':screen==='recover'?'Recover your account.':'Choose a new password.'}</h2><p>{screen==='register'?'Use the invitation sent to your authorized test email. Public signup is not open yet.':screen==='recover'?'We’ll email an expiring link if your address has an eligible account.':'Your personal records stay in your private workspace.'}</p>{!private_accounts_enabled?<div className="welcome-gated"><p>Private accounts are not enabled on this preview. Try the demo while secure storage and recovery are validated.</p><button className="button primary" disabled={busy} onClick={()=>void demo()}>Try Demo</button></div>:<form className="form-stack" onSubmit={submit}>{screen!=='reset'&&<label>Email address<input autoComplete="email" type="email" required maxLength={254} value={email} onChange={e=>setEmail(e.target.value)}/></label>}{screen!=='recover'&&<label>{screen==='reset'?'New password':'Password'}<input type="password" autoComplete={screen==='login'?'current-password':'new-password'} required minLength={screen==='login'?1:15} maxLength={128} value={password} onChange={e=>setPassword(e.target.value)}/></label>}{(screen==='register'||screen==='reset')&&<label>{screen==='register'?'Invitation code':'Reset code'}<input type="password" autoComplete="off" required minLength={20} maxLength={100} value={token} onChange={e=>setToken(e.target.value)}/></label>}<button className="button primary" disabled={busy}>{busy?'Please wait…':screen==='login'?'Log In':screen==='register'?'Create Account':screen==='recover'?'Send recovery link':'Update password'}</button>{screen==='login'&&<button type="button" className="text-button" onClick={()=>open('recover')}>Forgot password?</button>}</form>}<button className="text-button" onClick={()=>open('welcome')}>Back to Moniq</button></>}
        <ErrorNotice message={error}/>{notice&&<p role="status" className="welcome-notice"><CheckCircle2 size={18}/>{notice}</p>}
      </section></div><footer className="welcome-footer">Moniq · Spending, Made Smarter. <span>Estimated balances help you plan. Confirm transactions before relying on them.</span></footer></main>
}
