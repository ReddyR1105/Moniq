import { useState, type FormEvent } from 'react'
import { ArrowUp, Check, LoaderCircle, Sparkles } from 'lucide-react'
import { api, errorText } from '../api'
import { ErrorNotice, Panel } from '../components'
import type { AssistantReply } from '../types'
import { useRuntime } from '../runtime'

type Chat = {role: 'user' | 'assistant'; text: string; evidence?: AssistantReply['evidence']}
const questions = ['When was my last confirmed paycheck?', 'How much money do I have left?', 'Am I on track with my savings goal?', 'Can I afford a $100 purchase?', 'How much did I spend this week?', 'Can I afford a $150 purchase?', 'How much will I have left after rent?', 'Where can I save money?', 'Which expenses increased recently?', 'Which student deals are relevant to me?', 'Which subscriptions am I paying for?', 'How much should I save this month?', 'How much do my roommates owe me?', 'How much have I spent on shared meals?', 'What shared subscriptions are recurring?', 'How much should I reserve for shared rent?', 'Which shared expenses affect my budget?']

export function AssistantPage() {
  const {public_demo} = useRuntime()
  const [messages, setMessages] = useState<Chat[]>([])
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function ask(text: string) {
    if (!text.trim() || busy) return
    setBusy(true); setError(''); setQuestion('')
    setMessages(m => [...m, {role:'user', text}])
    try {const result = await api<AssistantReply>('/assistant', {method:'POST', body: JSON.stringify({question:text})}); setMessages(m => [...m, {role:'assistant', text:result.answer, evidence:result.evidence}])}
    catch (e) {setError(errorText(e)); setQuestion(text)} finally {setBusy(false)}
  }
  function submit(e: FormEvent) {e.preventDefault(); void ask(question)}
  return <><div className="page-intro"><div><span className="eyebrow">A LITTLE HELP, WHEN YOU NEED IT</span><h1>Let’s talk about your money.</h1><p>Clear answers grounded in your actual stored financial picture.</p></div><span className="subtle-chip"><span className="status-dot"/> Local assistant</span></div>
    <Panel className="assistant-panel"><div className="assistant-welcome"><span className="assistant-avatar"><Sparkles size={28}/></span><h2>Hey, I’m your Moniq assistant.</h2><p>Ask about your spending, your budget, or that purchase you’re thinking about. I’ll do the math from your records.</p><div className="assistant-badges"><span><Check size={13}/> Data-backed values</span><span><Check size={13}/> No API key needed</span></div></div>
      <div className="quick-questions">{questions.map(q => <button key={q} disabled={busy} onClick={() => void ask(q)}>{q}<ArrowUp size={14}/></button>)}</div>
      <div className="chat-messages" aria-live="polite">{messages.map((m,i) => <div className={`chat-message ${m.role}`} key={i}>{m.role === 'assistant' && <span className="chat-avatar"><Sparkles size={17}/></span>}<div><span className="chat-role">{m.role === 'user' ? 'You' : 'Moniq · local'}</span><p>{m.text}</p>{m.evidence && Object.keys(m.evidence).length > 0 && <details className="evidence"><summary>See the calculated values</summary><pre>{JSON.stringify(m.evidence, null, 2)}</pre></details>}</div></div>)}{busy && <div className="chat-pending"><LoaderCircle className="spin" size={16}/> Checking your stored records…</div>}</div>
      <ErrorNotice message={error}/><form className="chat-composer" onSubmit={submit}><label className="sr-only" htmlFor="assistant-question">Ask a financial question</label><input readOnly={public_demo} id="assistant-question" maxLength={1000} placeholder="What’s on your mind?" value={question} onChange={e => setQuestion(e.target.value)}/><button className="icon-button send-button" type="submit" aria-label="Send question" disabled={busy || !question.trim()}><ArrowUp size={21}/></button></form><p className="assistant-footnote">{public_demo && "Public demo accepts sample questions only; do not enter personal information. "}A local intent-based assistant, powered by backend calculations. Forecasts are estimates. This prototype provides no investment, tax, or credit advice.</p>
    </Panel>
  </>
}
