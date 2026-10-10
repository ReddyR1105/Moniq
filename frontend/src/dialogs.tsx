import { useState, type FormEvent } from 'react'
import { Check, FileUp, LoaderCircle, Play, Sparkles } from 'lucide-react'
import { api, errorText, localDate, title } from './api'
import { ErrorNotice, Modal } from './components'
import { categories, type ParsedMessage, type Prediction, type Transaction, type TransactionDraft } from './types'
import { useRuntime } from './runtime'

type DialogProps = {onClose: () => void; onSaved: (message: string) => void}

function TransactionForm({initial, existingId, onSaved, notification}: {initial: TransactionDraft; existingId?: number; onSaved: DialogProps['onSaved']; notification?: ParsedMessage}) {
  const {public_demo} = useRuntime()
  const [draft, setDraft] = useState<TransactionDraft>(initial)
  const [prediction, setPrediction] = useState<Prediction | null>(notification || null)
  const [busy, setBusy] = useState(false)
  const [classifying, setClassifying] = useState(false)
  const [error, setError] = useState('')
  const update = (key: keyof TransactionDraft, value: string) => setDraft(d => ({...d, [key]: value}))
  async function classify() {
    setClassifying(true); setError('')
    try {
      const result = await api<Prediction>('/classify', {method: 'POST', body: JSON.stringify({description: draft.description})})
      setPrediction(result)
      setDraft(d => ({...d, category: d.kind === 'income' ? 'income' : result.category === 'income' ? 'miscellaneous' : result.category}))
    } catch (e) { setError(errorText(e)) } finally {setClassifying(false)}
  }
  async function save(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError('')
    try {
      await api(existingId ? `/transactions/${existingId}` : '/transactions', {method: existingId ? 'PUT' : 'POST', body: JSON.stringify({...draft, category: draft.kind === 'income' ? 'income' : draft.category, amount: String(draft.amount)})})
      onSaved(existingId ? 'Transaction updated. Your totals and budgets are refreshed.' : 'Transaction saved. Your totals and budgets are refreshed.')
    } catch (err) {setError(errorText(err))} finally {setBusy(false)}
  }
  return <form className="form-stack" onSubmit={save}>
    {notification && <div className="success-note"><Check size={18}/><div><strong>Alert understood. You’re in control.</strong><p>{notification.date_assumption} Review the fields before saving.</p></div></div>}
    <label>Description{public_demo ? <select value={draft.description} onChange={e => setDraft(d => ({...d,description:e.target.value,merchant:e.target.value}))}>{[...new Set([initial.description,'Sample campus coffee','Chick-fil-A restaurant','Kroger grocery','Campus job payroll','Unknown synthetic demo purchase'])].map(v => <option key={v}>{v}</option>)}</select> : <input required maxLength={300} value={draft.description} onChange={e => update('description', e.target.value)} placeholder="e.g. Chick-fil-A restaurant" />}</label>
    <label>Merchant<input readOnly={public_demo} maxLength={160} value={draft.merchant || ''} onChange={e => update('merchant', e.target.value)} placeholder="Automatically identified when left blank" /></label>
    <div className="form-grid"><label>Amount ($)<input type="number" required min="0.01" max="1000000" step="0.01" value={draft.amount} onChange={e => update('amount', e.target.value)} /></label><label>Date<input type="date" required value={draft.date} onChange={e => update('date', e.target.value)} /></label></div>
    <div className="form-grid"><label>Transaction type<select aria-label="Transaction type" value={draft.kind} onChange={e => {update('kind', e.target.value); if (e.target.value === 'income') update('category', 'income'); else if (draft.category === 'income') update('category', 'miscellaneous')}}><option value="expense">Expense</option><option value="income">Income</option><option value="refund">Refund</option></select></label>
      <label>Category<select aria-label="Category" value={draft.category || 'miscellaneous'} disabled={draft.kind === 'income'} onChange={e => update('category', e.target.value)}>{categories.filter(c => draft.kind === 'income' || c !== 'income').map(c => <option value={c} key={c}>{title(c)}</option>)}</select></label></div>
    <div className="classifier-note"><button type="button" className="text-button" onClick={classify} disabled={classifying || !draft.description.trim()}><Sparkles size={15}/>{classifying ? 'Classifying…' : 'Classify with ML'}</button>{prediction && <p><strong>{Math.round(prediction.confidence * 100)}% model confidence</strong> · {prediction.explanation}</p>}</div>
    <ErrorNotice message={error}/><button className="button primary full" disabled={busy} type="submit">{busy ? <LoaderCircle className="spin" size={17}/> : <Check size={17}/>} {existingId ? 'Save changes' : 'Confirm & save transaction'}</button>
    <p className="fine-print">Expenses reduce your balance. Income and refunds increase it. {public_demo ? 'Use fictional amounts only. Corrections stay in your session; model retraining is available locally.' : 'Category corrections are saved for retraining.'}</p>
  </form>
}

export function EditTransactionDialog({item, onClose, onSaved}: DialogProps & {item?: Transaction}) {
  const {public_demo} = useRuntime()
  const initial: TransactionDraft = item ? {...item, amount: Math.abs(item.amount)} : {date: localDate(), description: public_demo ? 'Sample campus coffee' : '', merchant: public_demo ? 'Sample campus coffee' : '', amount: public_demo ? 5.75 : '', kind: 'expense', category: 'miscellaneous'}
  return <Modal title={item ? 'Edit transaction' : 'Add a transaction'} subtitle="Small details. A clearer financial picture." onClose={onClose}><TransactionForm initial={initial} existingId={item?.id} onSaved={onSaved}/></Modal>
}

export function PurchaseDialog({onClose, onSaved}: DialogProps) {
  const {public_demo} = useRuntime()
  const examples = ['Your card ending in 1234 was charged $15.75 at Chick-fil-A.', `Purchase of $42.60 at Kroger grocery on ${localDate()}.`, 'Refund of $15.00 from Target clothing.', 'Payroll deposit of $620.00 from Campus job payroll.']
  const [text, setText] = useState(examples[0])
  const [parsed, setParsed] = useState<ParsedMessage | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function parse(message = text) {
    setBusy(true); setError('')
    try {setParsed(await api<ParsedMessage>('/notifications/parse', {method:'POST', body: JSON.stringify({text: message})}))}
    catch (e) {setError(errorText(e))} finally {setBusy(false)}
  }
  return <Modal title="From notification to transaction" subtitle="Paste an alert. Let ML organize it. Review, then save." onClose={onClose}>
    {parsed ? <><TransactionForm initial={parsed} notification={parsed} onSaved={onSaved}/><button className="text-button" onClick={() => setParsed(null)}>← Try another message</button></> : <div className="form-stack">
      <div className="message-preview"><span className="message-avatar"><WalletGlyph/></span><div><strong>Campus Bank <span>· simulated alert</span></strong><p>{text || 'Your purchase alert appears here.'}</p></div></div>
      <label>Purchase notification<textarea readOnly={public_demo} rows={4} maxLength={2000} value={text} onChange={e => setText(e.target.value)} aria-describedby="message-privacy" /></label>
      <p className="fine-print" id="message-privacy">{public_demo ? 'Public demo uses built-in alerts only. No personal messages or bank credentials.' : 'User-initiated paste only.'} Moniq does not access your texts or banking apps.</p>
      <div><span className="field-caption">TRY A SAMPLE</span><div className="sample-buttons">{examples.map((message, i) => <button key={message} className="chip" onClick={() => setText(message)}>{['Restaurant', 'Groceries', 'Refund', 'Paycheck'][i]}</button>)}</div></div>
      <ErrorNotice message={error}/><button className="button primary full" disabled={busy || !text.trim()} onClick={() => parse()}>{busy ? <LoaderCircle className="spin" size={18}/> : <Sparkles size={18}/>} Extract & classify</button>
      <button className="button secondary full" disabled={busy} onClick={() => {setText(examples[0]); void parse(examples[0])}}><Play size={16}/> Simulate a purchase alert</button>
    </div>}
  </Modal>
}
function WalletGlyph() {return <span aria-hidden="true">$</span>}

type Preview = {columns: string[]; sample: Record<string, string>[]; rows: number}
export function ImportDialog({onClose, onSaved}: DialogProps) {
  const {public_demo} = useRuntime()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<Preview | null>(null)
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [convention, setConvention] = useState('negative_expense')
  const [dayFirst, setDayFirst] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function importSample() {
    setBusy(true);setError('')
    try {const result = await api<{imported:number;duplicates:number}>('/demo/import-sample',{method:'POST'});onSaved(`${result.imported} transactions imported. ${result.duplicates} duplicates skipped.`)}
    catch(e) {setError(errorText(e))} finally {setBusy(false)}
  }
  async function inspect(chosen: File | undefined) {
    if (!chosen) return
    setFile(chosen); setPreview(null); setError(''); setBusy(true)
    try {
      if (chosen.size > 2 * 1024 * 1024) throw new Error('Choose a CSV smaller than 2 MB.')
      const form = new FormData(); form.append('file', chosen)
      const result = await api<Preview>('/imports/preview', {method:'POST', body: form})
      setPreview(result)
      const suggestions: Record<string, string> = {}
      for (const key of ['date', 'description', 'amount', 'debit', 'credit', 'kind', 'category']) {
        const aliases: Record<string, string[]> = {date:['date', 'transaction date', 'posted date', 'when'], description:['description', 'merchant', 'details', 'what'], amount:['amount', 'value'], debit:['debit', 'withdrawal', 'out'], credit:['credit', 'deposit', 'in'], kind:['kind', 'type'], category:['category']}
        suggestions[key] = result.columns.find(c => aliases[key].includes(c.toLowerCase())) || ''
      }
      setMapping(suggestions)
    } catch (e) {setError(errorText(e))} finally {setBusy(false)}
  }
  async function importFile() {
    if (!file) return
    setBusy(true); setError('')
    try {
      const form = new FormData(); form.append('file', file); form.append('mapping', JSON.stringify(mapping)); form.append('convention', convention); form.append('day_first', String(dayFirst))
      const result = await api<{imported: number; duplicates: number}>('/imports/csv', {method:'POST', body: form})
      onSaved(`${result.imported} transactions imported. ${result.duplicates} duplicates skipped.`)
    } catch (e) {setError(errorText(e))} finally {setBusy(false)}
  }
  if (public_demo) return <Modal title="Try a synthetic statement" subtitle="Four fictional transactions, processed by the same CSV import pipeline." onClose={onClose}><div className="form-stack"><p>No personal statements or banking credentials are accepted in this public demo. The sample includes coffee, tutoring pay, a clothing refund and groceries. Re-importing skips duplicates.</p><ErrorNotice message={error}/><button className="button primary" disabled={busy} onClick={() => void importSample()}>{busy ? 'Importing…' : 'Import synthetic statement'}</button></div></Modal>
  return <Modal title="Your statement, organized" subtitle="Map your bank’s columns. We’ll handle the categories." onClose={onClose} wide>
    <div className="form-stack"><label className="upload-zone"><FileUp size={30}/><strong>{file?.name || 'Choose a bank statement CSV'}</strong><span>UTF-8 · up to 2 MB · 10,000 rows</span><input type="file" accept=".csv,text/csv" onChange={e => void inspect(e.target.files?.[0])}/></label>
      {preview && <><div className="success-note"><Check size={17}/>{preview.rows} rows found. Confirm the column mapping below.</div>
        <div className="form-grid">{['date', 'description', 'amount', 'debit', 'credit', 'kind', 'category'].map(key => <label key={key}>{title(key)} column{['date', 'description'].includes(key) ? ' *' : ''}<select value={mapping[key]} onChange={e => setMapping(m => ({...m, [key]: e.target.value}))}><option value="">Not mapped</option>{preview.columns.map(c => <option key={c} value={c}>{c}</option>)}</select></label>)}</div>
        <p className="fine-print">Map one amount column, or both debit and credit. Positive credits default to income; map a type column to identify refunds. Type accepts expense, income, refund, debit, credit.</p>
        <div className="form-grid"><label>Amount convention<select value={convention} onChange={e => setConvention(e.target.value)}><option value="negative_expense">Negative amounts are expenses</option><option value="positive_expense">Positive amounts are expenses</option></select></label><label>Numeric date format<select value={String(dayFirst)} onChange={e => setDayFirst(e.target.value === 'true')}><option value="false">US: month/day/year</option><option value="true">UK: day/month/year</option></select></label></div>
        <div className="table-scroll"><table className="compact-table"><thead><tr>{preview.columns.map(c => <th key={c}>{c}</th>)}</tr></thead><tbody>{preview.sample.map((r,i) => <tr key={i}>{preview.columns.map(c => <td key={c}>{r[c]}</td>)}</tr>)}</tbody></table></div>
        <p className="fine-print">All rows are validated before saving. Same date, merchant and signed amount are treated as a duplicate. Identical same-day purchases may need distinct merchant labels.</p>
      </>}
      <ErrorNotice message={error}/><button className="button primary full" disabled={busy || !preview || !mapping.date || !mapping.description || !(mapping.amount || (mapping.debit && mapping.credit))} onClick={importFile}>{busy ? <LoaderCircle className="spin" size={17}/> : <FileUp size={17}/>} {busy ? 'Processing…' : 'Import transactions'}</button>
    </div>
  </Modal>
}
