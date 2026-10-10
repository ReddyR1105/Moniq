import { StrictMode, Component, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { useResource } from './api'
import { Loading, ErrorNotice } from './components'
import { RuntimeContext, type RuntimeConfig } from './runtime'
import './styles.css'

class ErrorBoundary extends Component<{children: ReactNode}, {failed: boolean}> {
  state = {failed:false}
  static getDerivedStateFromError() {return {failed:true}}
  render() {return this.state.failed ? <main className="fatal-error"><h1>Moniq needs a fresh start.</h1><p>Your stored records are preserved. Reload the page to try again.</p><button className="button primary" onClick={() => window.location.reload()}>Reload app</button></main> : this.props.children}
}
function Bootstrap() {
  // Establish the isolated cookie before parallel dashboard/profile requests.
  const {data,error} = useResource<RuntimeConfig>('/config',0)
  if (error) return <main className="fatal-error"><h1>Connect to Moniq.</h1><ErrorNotice message={error}/><button className="button primary" onClick={() => window.location.reload()}>Retry connection</button></main>
  return data ? <RuntimeContext.Provider value={data}><App/></RuntimeContext.Provider> : <main className="fatal-error"><Loading label="Opening your financial space…"/></main>
}
createRoot(document.getElementById('root')!).render(<StrictMode><ErrorBoundary><Bootstrap/></ErrorBoundary></StrictMode>)
