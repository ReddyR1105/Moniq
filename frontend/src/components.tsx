import { useEffect, useRef, type ReactNode } from 'react'
import { ArrowUpRight, BookOpen, Car, Clapperboard, Coffee, HeartPulse, Home, LoaderCircle, MoreHorizontal, Repeat2, ShoppingBag, ShoppingBasket, Sparkles, Wallet, X } from 'lucide-react'
import { dollars, prettyDate, title } from './api'
import type { Category, Transaction } from './types'

const categoryIcons = {food: Coffee, groceries: ShoppingBasket, shopping: ShoppingBag, transportation: Car, rent: Home, education: BookOpen, subscriptions: Repeat2, entertainment: Clapperboard, healthcare: HeartPulse, income: Wallet, miscellaneous: MoreHorizontal}
export const chartColors = ['#176c54', '#aed488', '#e8b56b', '#88b6c7', '#8989b3', '#b2b69c', '#dd967e', '#75998a', '#af95b4', '#82a564', '#adb9b2']

export function CategoryIcon({category, small = false}: {category: Category; small?: boolean}) {
  const Icon = categoryIcons[category] || MoreHorizontal
  return <span className={`category-icon cat-${category} ${small ? 'small' : ''}`}><Icon size={small ? 16 : 19} strokeWidth={1.8} /></span>
}

export function Panel({children, className = ''}: {children: ReactNode; className?: string}) {
  return <section className={`panel ${className}`}>{children}</section>
}

export function PanelHeading({title: heading, subtitle, action}: {title: string; subtitle?: string; action?: ReactNode}) {
  return <div className="panel-heading"><div><h2>{heading}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>
}

export function ErrorNotice({message}: {message: string}) {
  if (!message) return null
  return <div className="error-notice" role="alert">{message}</div>
}

export function Loading({label = 'Reading your financial picture…'}: {label?: string}) {
  return <div className="loading" role="status"><LoaderCircle className="spin" size={22} /><span>{label}</span></div>
}

export function Empty({title: heading, children}: {title: string; children?: ReactNode}) {
  return <div className="empty-state"><Wallet size={28} /><h3>{heading}</h3><p>{children || 'Add a transaction or reset the synthetic demo in Settings.'}</p></div>
}

export function Progress({value, label, warn = false}: {value: number; label: string; warn?: boolean}) {
  return <div className={`progress-track ${warn ? 'warning' : ''}`} role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(Math.min(100, Math.max(0, value * 100)))}><span style={{width: `${Math.min(100, Math.max(0, value * 100))}%`}} /></div>
}

export function TransactionRows({items, edit}: {items: Transaction[]; edit?: (item: Transaction) => void}) {
  return <div className="transaction-rows">{items.map(t => <div className="transaction-row" key={t.id}>
    <CategoryIcon category={t.category} /><div className="transaction-name"><strong>{t.merchant}</strong><span>{title(t.category)} · {prettyDate(t.date)}</span></div>
    <strong className={`transaction-amount ${t.amount > 0 ? 'positive' : ''}`}>{t.amount > 0 ? '+' : '−'}{dollars(Math.abs(t.amount))}</strong>
    {edit && <button className="icon-button" aria-label={`Edit ${t.merchant}`} onClick={() => edit(t)}><ArrowUpRight size={17} /></button>}
  </div>)}</div>
}

export function Modal({title: heading, subtitle, children, onClose, wide = false}: {title: string; subtitle?: string; children: ReactNode; onClose: () => void; wide?: boolean}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const element = ref.current
    if (element && !element.open) element.showModal()
    return () => { if (element?.open) element.close() }
  }, [])
  return <dialog ref={ref} className={`modal ${wide ? 'wide' : ''}`} aria-labelledby="modal-title" onCancel={onClose} onClick={e => {if (e.target === e.currentTarget) onClose()}}>
    <div className="modal-heading"><div><span className="eyebrow"><Sparkles size={13} /> A LITTLE LESS ADMIN</span><h2 id="modal-title">{heading}</h2>{subtitle && <p>{subtitle}</p>}</div><button className="icon-button" aria-label="Close dialog" onClick={onClose}><X size={21}/></button></div>
    {children}
  </dialog>
}
