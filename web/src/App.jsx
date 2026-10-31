import { useCallback, useEffect, useState } from 'react'
import * as api from './api'

const POLL_MS = 1000

const CAUSES = {
  device_fault: 'Device fault',
  sim_network: 'SIM or network',
  money_problem: 'Money problem',
  billing_anger: 'Billing anger',
  competitor_switch: 'Competitor switch',
  closed_seasonal: 'Closed or seasonal',
}

const LANGUAGES = {
  as: 'Assamese', bn: 'Bengali', gu: 'Gujarati', hi: 'Hindi', kn: 'Kannada', ml: 'Malayalam',
  mr: 'Marathi', or: 'Odia', pa: 'Punjabi', ta: 'Tamil', te: 'Telugu',
}

const STATUSES = {
  new: 'New',
  working: 'Working',
  awaiting_call: 'Awaiting call',
  on_call: 'On call',
  awaiting_approval: 'Needs approval',
}

const BUCKETS = {
  handled_remote: 'Handled remotely',
  rep_visit: 'Rep visit',
  needs_approval: 'Needs approval',
  no_action: 'No action',
}

const HEADLINE = [
  ['flagged', 'Flagged'],
  ['handled_remote', 'Handled remotely'],
  ['rep_visit', 'Rep visit'],
  ['needs_approval', 'Needs approval'],
  ['no_action', 'No action'],
  ['awaiting_call', 'Awaiting call'],
]

const percent = (ratio) => `${Math.round(ratio * 100)}%`

const longDate = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })

// Undiagnosed first, so the work still to do stays at the top during a run.
function groupByCause(cases) {
  const causes = [null, ...Object.keys(CAUSES)]
  return causes
    .map((cause) => ({ cause, cases: cases.filter((item) => item.cause === cause) }))
    .filter((group) => group.cases.length > 0)
}

function CaseRow({ item, callDisabled, onCall }) {
  const label = item.status === 'done' ? BUCKETS[item.bucket] : STATUSES[item.status]
  const tone = item.status === 'done' ? item.bucket : item.status
  return (
    <tr className={`row-${tone}`}>
      <td>
        <div className="owner">{item.owner}</div>
        <div className="muted">{item.merchant_id} · {item.shop_type}</div>
      </td>
      <td>
        <div>{item.area}</div>
        <div className="muted">{item.state}</div>
      </td>
      <td>{LANGUAGES[item.language] ?? item.language}</td>
      <td className="number">{percent(item.volume_ratio)}</td>
      <td className="number">{item.offline_days > 0 ? `${item.offline_days}d` : '–'}</td>
      <td><span className={`pill pill-${tone}`}>{label}</span></td>
      <td className="summary">{item.summary ?? ''}</td>
      <td>
        {item.status === 'awaiting_call' && (
          <button type="button" className="primary" disabled={callDisabled} onClick={() => onCall(item.id)}>
            Call
          </button>
        )}
      </td>
    </tr>
  )
}

export default function App() {
  const [board, setBoard] = useState(null)
  const [offline, setOffline] = useState(false)
  const [actionError, setActionError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [runStarted, setRunStarted] = useState(false)

  const refresh = useCallback(async () => {
    try {
      setBoard(await api.getBoard())
      setOffline(false)
    } catch {
      setOffline(true)
    }
  }, [])

  useEffect(() => {
    let stopped = false
    let timer
    const poll = async () => {
      await refresh()
      if (!stopped) timer = setTimeout(poll, POLL_MS)
    }
    poll()
    return () => {
      stopped = true
      clearTimeout(timer)
    }
  }, [refresh])

  const act = async (action) => {
    setBusy(true)
    setActionError(null)
    try {
      await action()
      await refresh()
    } catch (error) {
      setActionError(error.message)
    } finally {
      setBusy(false)
    }
  }

  const statuses = new Set(board?.cases.map((item) => item.status))
  // The run snapshots new cases and keeps writing in the background, so a second
  // run or a reset mid-run would leave a dirty demo. Reloading the page clears this.
  const running = statuses.has('working') || statuses.has('on_call') || (runStarted && statuses.has('new'))

  const run = () => {
    setRunStarted(true)
    return act(api.runAll)
  }
  const reset = () => {
    setRunStarted(false)
    return act(api.reset)
  }

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <h1>Wapsi</h1>
          <p className="muted">
            {board ? `All-India board · 8:00 AM, ${longDate(board.date)}` : 'All-India board'}
          </p>
        </div>
        {board && (
          <span className={`badge ${board.agent_mode === 'live' ? 'badge-live' : 'badge-stub'}`}>
            {board.agent_mode === 'live' ? 'Live agent' : 'Stub agent: canned reasoning'}
          </span>
        )}
        <div className="actions">
          <button type="button" className="primary" disabled={!board || busy || running || !statuses.has('new')} onClick={run}>
            {running ? 'Running…' : 'Run agent'}
          </button>
          <button type="button" disabled={!board || busy || running} onClick={reset}>Reset</button>
        </div>
      </header>

      {offline && (
        <p className="alert" role="alert">
          Cannot reach the API on port 8000.{board ? ' Showing the last board we received.' : ''}
        </p>
      )}
      {actionError && <p className="alert" role="alert">{actionError}</p>}

      {!board && !offline && <p className="muted">Loading the board…</p>}

      {board && (
        <main>
          <section className="tiles" aria-label="Headline counts">
            {HEADLINE.map(([key, label]) => (
              <div className="tile" key={key}>
                <div className="tile-value">{board.headline[key]}</div>
                <div className="muted">{label}</div>
              </div>
            ))}
          </section>

          {board.area_dips.map((dip) => (
            <p className="banner" key={dip.area}>
              <strong>{dip.merchants} {dip.area} merchants dipped with their area</strong>
              {' '}(area at {percent(dip.ratio)} of normal), so Wapsi did nothing.
            </p>
          ))}

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Merchant</th>
                  <th scope="col">Place</th>
                  <th scope="col">Language</th>
                  <th scope="col" className="number">Volume vs normal</th>
                  <th scope="col" className="number">Box offline</th>
                  <th scope="col">State</th>
                  <th scope="col">Summary</th>
                  <th scope="col"><span className="sr-only">Action</span></th>
                </tr>
              </thead>
              {groupByCause(board.cases).map((group) => (
                <tbody key={group.cause ?? 'undiagnosed'}>
                  <tr className="group">
                    <th scope="colgroup" colSpan={8}>
                      {CAUSES[group.cause] ?? 'Not diagnosed yet'}
                      <span className="group-count">{group.cases.length}</span>
                    </th>
                  </tr>
                  {group.cases.map((item) => (
                    <CaseRow
                      key={item.id}
                      item={item}
                      callDisabled={busy}
                      onCall={(id) => act(() => api.startCall(id))}
                    />
                  ))}
                </tbody>
              ))}
            </table>
          </div>
        </main>
      )}
    </div>
  )
}
