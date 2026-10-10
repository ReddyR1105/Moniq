import { createContext, useContext } from 'react'

export type RuntimeConfig = {public_demo:boolean; session_ttl_minutes:number; upload_enabled:boolean; retrain_enabled:boolean;workspace:'demo'|'personal'|'scenario'}
export const RuntimeContext = createContext<RuntimeConfig>({public_demo:false,session_ttl_minutes:120,upload_enabled:true,retrain_enabled:true,workspace:'demo'})
export const useRuntime = () => useContext(RuntimeContext)
