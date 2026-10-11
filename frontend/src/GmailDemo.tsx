import { useState } from 'react'
import { Mail, Sparkles } from 'lucide-react'
import { api, errorText } from './api'
import { ErrorNotice, Panel, PanelHeading } from './components'
import { useRuntime } from './runtime'

export function GmailDemo({changed}:{changed:(message:string)=>void}) {
  const {public_demo,workspace}=useRuntime()
  const [started,setStarted]=useState(false)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  if(!public_demo||workspace==='personal') return null
  async function start() {
    if(!window.confirm('Start a simulated Gmail walkthrough with a $10 balance? This replaces only your temporary synthetic demo records.')) return
    setBusy(true);setError('')
    try {await api('/upgrade-demo/start',{method:'POST',body:JSON.stringify({starting_balance:'10.00'})});setStarted(true);changed('Simulated Gmail activity started. Estimated balance: $10.00.')}
    catch(e) {setError(errorText(e))} finally {setBusy(false)}
  }
  async function receive(event:'paycheck'|'purchase') {
    setBusy(true);setError('')
    try {await api('/upgrade-demo/financial-alert',{method:'POST',body:JSON.stringify({event})});changed('Simulated email received. Review the extracted details and confirm the posted transaction below.')}
    catch(e) {setError(errorText(e))} finally {setBusy(false)}
  }
  return <Panel className="gmail-demo"><PanelHeading title="Try Gmail Transaction Demo" subtitle="Simulated Gmail activity · no real inbox access"/><p>Start with $10. Receive a confirmed $400 paycheck, review the extracted details, and approve it to see $410. Approve a $15 purchase next to see $395.</p><div className="button-row">{!started?<button className="button primary" disabled={busy} onClick={()=>void start()}><Sparkles size={16}/> Start simulated Gmail demo</button>:<><button className="button secondary" disabled={busy} onClick={()=>void receive('paycheck')}><Mail size={16}/> Receive $400 paycheck alert</button><button className="button secondary" disabled={busy} onClick={()=>void receive('purchase')}><Mail size={16}/> Receive $15 purchase alert</button></>}</div><p className="fine-print">Approval is required. Repeated alerts cannot add the same transaction twice. These emails, accounts and amounts are synthetic.</p><ErrorNotice message={error}/></Panel>
}
