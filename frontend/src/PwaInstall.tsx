import { useEffect, useState } from 'react'
import { Download } from 'lucide-react'

type InstallPrompt = Event & {
  prompt: () => Promise<{ outcome: 'accepted' | 'dismissed' }>
}

export function PwaInstall() {
  const [prompt, setPrompt] = useState<InstallPrompt | null>(null)
  const [installed, setInstalled] = useState(() => window.matchMedia('(display-mode: standalone)').matches
    || Boolean((navigator as Navigator & { standalone?: boolean }).standalone))
  const [error, setError] = useState('')
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent)
    || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  useEffect(() => {
    const ready = (event: Event) => { event.preventDefault(); setPrompt(event as InstallPrompt) }
    const done = () => { setInstalled(true); setPrompt(null) }
    window.addEventListener('beforeinstallprompt', ready)
    window.addEventListener('appinstalled', done)
    return () => {
      window.removeEventListener('beforeinstallprompt', ready)
      window.removeEventListener('appinstalled', done)
    }
  }, [])
  if (installed) return null
  return <section className="panel pwa-install" aria-label="Install Moniq">
    <h2>Moniq on your home screen</h2>
    <p>{ios ? 'In Safari, open Share, then Add to Home Screen. Choose Open as Web App when offered.'
      : 'In Chrome, open the browser menu and choose Install app or Add to Home screen when available.'}</p>
    {prompt && <button className="button primary" onClick={async () => {
      setError('')
      try { const result = await prompt.prompt(); if (result.outcome === 'accepted') setInstalled(true) }
      catch { setError('Use your browser menu to install Moniq.') }
      finally { setPrompt(null) }
    }}><Download size={18}/> Install Moniq</button>}
    {error && <p role="status">{error}</p>}
    <p className="fine-print">Open online to load your current workspace. Financial data is unavailable offline.</p>
  </section>
}
