import { useEffect, useState } from 'react'
import Board from './Board'
import CaseDetail from './CaseDetail'

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

  return (
    <div className="page">
      {caseId
        ? <CaseDetail key={caseId} caseId={caseId} runStarted={runStarted} />
        : <Board runStarted={runStarted} setRunStarted={setRunStarted} />}
    </div>
  )
}
