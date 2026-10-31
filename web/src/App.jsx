import { useEffect, useState } from 'react'
import Board from './Board'
import CaseDetail from './CaseDetail'
import Manager from './Manager'

function useHash() {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onChange = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return hash
}

export default function App() {
  const hash = useHash()
  // Lives here so opening a case mid-run does not unlock Run and Reset on the board.
  const [runStarted, setRunStarted] = useState(false)
  const caseId = hash.match(/^#\/cases\/([\w-]+)$/)?.[1]

  let screen = <Board runStarted={runStarted} setRunStarted={setRunStarted} />
  if (caseId) screen = <CaseDetail key={caseId} caseId={caseId} runStarted={runStarted} />
  if (hash === '#/manager') screen = <Manager />

  return <div className="page">{screen}</div>
}
