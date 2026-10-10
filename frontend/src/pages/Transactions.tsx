import { useState } from 'react'
import { Download, FileUp, Pencil, Plus, Search, Trash2 } from 'lucide-react'
import { api, dollars, errorText, prettyDate, title, useResource } from '../api'
import { CategoryIcon, Empty, ErrorNotice, Loading, Panel } from '../components'
import { categories, type Transaction } from '../types'

export function TransactionsPage({revision, edit, add, importCsv, changed, split}: {split:(t:Transaction)=>void;revision: number; edit: (t: Transaction) => void; add: () => void; importCsv: () => void; changed: (m: string) => void}) {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [kind, setKind] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [offset, setOffset] = useState(0)
  const [error, setError] = useState('')
  const [deleting, setDeleting] = useState<number | null>(null)
  const params = new URLSearchParams({q:query, limit:'50', offset:String(offset)})
  if (category) params.set('category', category)
  if (kind) params.set('kind', kind)
  if (start) params.set('start', start)
  if (end) params.set('end', end)
  const resource = useResource<Transaction[]>(`/transactions?${params}`, revision)
  async function remove(t: Transaction) {
    if (!window.confirm(`Delete ${t.merchant} (${dollars(Math.abs(t.amount))})? This updates your balance and budget.`)) return
    setError(''); setDeleting(t.id)
    try {await api(`/transactions/${t.id}`, {method:'DELETE'}); changed('Transaction deleted. Totals refreshed.')}
    catch (e) {setError(errorText(e))} finally {setDeleting(null)}
  }
  return <><div className="page-intro"><div><span className="eyebrow">LESS SPREADSHEET. MORE LIFE.</span><h1>Your money in motion.</h1><p>Search, organize, and make every transaction make sense.</p></div><div className="button-row"><button className="button secondary" onClick={importCsv}><FileUp size={17}/> Import CSV</button><button className="button primary" onClick={add}><Plus size={17}/> Add transaction</button></div></div>
    <Panel><div className="transaction-toolbar"><label className="search-field"><Search size={17}/><input aria-label="Search transactions" placeholder="Search a merchant or description…" value={query} onChange={e => {setQuery(e.target.value); setOffset(0)}}/></label><label className="sr-only" htmlFor="category-filter">Filter by category</label><select id="category-filter" value={category} onChange={e => {setCategory(e.target.value); setOffset(0)}}><option value="">All categories</option>{categories.map(c => <option key={c} value={c}>{title(c)}</option>)}</select><label className="sr-only" htmlFor="kind-filter">Filter by type</label><select id="kind-filter" value={kind} onChange={e => {setKind(e.target.value); setOffset(0)}}><option value="">All types</option><option value="expense">Expenses</option><option value="income">Income</option><option value="refund">Refunds</option><option value="reimbursement">Reimbursements</option><option value="settlement">Repayments</option></select><a className="icon-button" href="/api/export?format=csv" aria-label="Export transactions as CSV"><Download size={18}/></a></div>
      <div className="date-filters"><label>From<input type="date" value={start} onChange={e => {setStart(e.target.value); setOffset(0)}}/></label><label>To<input type="date" value={end} onChange={e => {setEnd(e.target.value); setOffset(0)}}/></label><span>Income and refunds are positive. Expenses are negative.</span></div>
      <ErrorNotice message={error || resource.error}/>{resource.loading ? <Loading/> : resource.data?.length ? <div className="table-scroll"><table className="transactions-table"><thead><tr><th>Merchant / description</th><th>Date</th><th>Category</th><th>Type / confidence</th><th className="right">Amount</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{resource.data.map(t => <tr key={t.id}><td><div className="merchant-cell"><CategoryIcon category={t.category}/><div><strong>{t.merchant}</strong><span>{t.description} · {t.source==='gmail-auto'?'Auto-approved':t.source}</span></div></div></td><td>{prettyDate(t.date)}</td><td><span className={`category-pill cat-${t.category}`}>{title(t.category)}</span></td><td><span>{title(t.kind)}</span><small className="confidence-text">{t.confidence === null ? 'Demo label' : `${Math.round(t.confidence * 100)}% ML confidence`}</small></td><td className={`right amount-cell ${t.amount > 0 ? 'positive' : ''}`}>{t.amount > 0 ? '+' : '−'}{dollars(Math.abs(t.amount))}</td><td><div className="row-actions">{t.kind==='expense'&&t.amount<0&&<button className="button secondary small" onClick={()=>split(t)}>Split this expense</button>}<button className="icon-button" aria-label={`Edit ${t.merchant}`} onClick={() => edit(t)}><Pencil size={15}/></button><button className="icon-button danger" aria-label={`Delete ${t.merchant}`} disabled={deleting === t.id} onClick={() => void remove(t)}><Trash2 size={15}/></button></div></td></tr>)}</tbody></table></div> : !resource.error && <Empty title="No matching transactions">Try a different filter, import a CSV, or add your first transaction.</Empty>}
      <div className="pagination"><span>{resource.data?.length || 0} records shown · page {Math.floor(offset / 50) + 1}</span><div className="button-row"><button className="button small secondary" disabled={offset === 0} onClick={() => setOffset(o => Math.max(0,o - 50))}>Previous</button><button className="button small secondary" disabled={(resource.data?.length || 0) < 50} onClick={() => setOffset(o => o + 50)}>Next</button></div></div>
    </Panel><p className="page-footnote">Same-day transactions with the same merchant and signed amount are treated as duplicates. Review the statement mapping for refunds.</p>
  </>
}
