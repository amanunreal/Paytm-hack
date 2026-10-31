import { useCallback, useEffect, useState } from 'react'
import * as api from './api'
import Board from './Board'
import CaseDetail from './CaseDetail'
import DemoPath from './DemoPath'
import Manager from './Manager'
import Results from './Results'
import { usePoll } from './usePoll'

function useHash() {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onChange = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return hash
}

function Nav({ hash, board }) {
  const links = [
    { href: '#/', label: 'Board', current: !hash.startsWith('#/manager') && !hash.startsWith('#/results') },
    { href: '#/manager', label: 'Manager', count: board?.headline.needs_approval, current: hash === '#/manager' },
    { href: '#/results', label: 'Results', current: hash === '#/results' },
  ]
  return (
    <nav className="nav" aria-label="Main">
      <a className="wordmark" href="#/">Wapsi</a>
      {links.map((link) => (
        <a key={link.href} href={link.href} aria-current={link.current ? 'page' : undefined}>
          {link.label}
          {link.count > 0 && <span className="nav-count">{link.count}</span>}
        </a>
      ))}
      {board && (
        <span className="mode mode-live">{board.public ? 'Saved agent run' : 'Live agent'}</span>
      )}
    </nav>
  )
}

export default function App() {
  const hash = useHash()
  const { data: board, error, refresh } = usePoll(api.getBoard)
  // These live here so they survive moving between screens. Opening a case mid-run
  // must not unlock Run and Reset, and a finished call stays on the board's list.
  const [runStarted, setRunStarted] = useState(false)
  const [called, setCalled] = useState([])
  const [openGroups, setOpenGroups] = useState([])

  const markCalled = useCallback((id) => {
    setCalled((list) => (list.includes(id) ? list : [...list, id]))
  }, [])

  const caseId = hash.match(/^#\/cases\/([\w-]+)$/)?.[1]
  let screen = (
    <Board
      board={board}
      error={error}
      refresh={refresh}
      runStarted={runStarted}
      setRunStarted={setRunStarted}
      called={called}
      setCalled={setCalled}
      markCalled={markCalled}
      openGroups={openGroups}
      setOpenGroups={setOpenGroups}
    />
  )
  if (caseId) screen = <CaseDetail key={caseId} caseId={caseId} runStarted={runStarted} markCalled={markCalled} />
  if (hash === '#/manager') screen = <Manager />
  if (hash === '#/results') screen = <Results />

  return (
    <>
      <Nav hash={hash} board={board} />
      {board?.public && (
        <p className="public-note">
          Public demo: a saved real agent run on simulated merchants. The call here is scripted. See our video for the live Hindi call.
        </p>
      )}
      {new URLSearchParams(window.location.search).has('demo') && <DemoPath hash={hash} />}
      <div className="page">{screen}</div>
    </>
  )
}
