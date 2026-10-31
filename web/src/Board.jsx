import { useState } from 'react'
import * as api from './api'
import { CAUSES, LANGUAGES, longDate, percent, stateOf } from './labels'
import { usePoll } from './usePoll'

const HEADLINE = [
  ['flagged', 'Flagged'],
  ['handled_remote', 'Handled remotely'],
  ['rep_visit', 'Rep visit'],
  ['needs_approval', 'Needs approval'],
  ['no_action', 'No action'],
  ['awaiting_call', 'Awaiting call'],
]

// Undiagnosed first, so the work still to do stays at the top during a run.
function groupByCause(cases) {
  const causes = [null, ...Object.keys(CAUSES)]
  return causes
    .map((cause) => ({ cause, cases: cases.filter((item) => item.cause === cause) }))
    .filter((group) => group.cases.length > 0)
}

function CaseRow({ item, callDisabled, onCall }) {
  const { label, tone } = stateOf(item)
  return (
    <tr className={`row-${tone}`}>
      <td>
        <a className="owner" href={`#/cases/${item.id}`}>{item.owner}</a>
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
        {item.status === 'awaiting_approval' && <a className="row-link" href="#/manager">Review</a>}
      </td>
    </tr>
  )
}

export default function Board({ runStarted, setRunStarted }) {
  const { data: board, error, refresh } = usePoll(api.getBoard)
  const [actionError, setActionError] = useState(null)
  const [busy, setBusy] = useState(false)

  const act = async (action) => {
    setBusy(true)
    setActionError(null)
    try {
      await action()
      await refresh()
    } catch (failure) {
      setActionError(failure.message)
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
    <>
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
          {board && <a className="nav-link" href="#/manager">Manager view ({board.headline.needs_approval})</a>}
          {board && <a className="nav-link" href="#/results">Results</a>}
          <button type="button" className="primary" disabled={!board || busy || running || !statuses.has('new')} onClick={run}>
            {running ? 'Running…' : 'Run agent'}
          </button>
          <button type="button" disabled={!board || busy || running} onClick={reset}>Reset</button>
        </div>
      </header>

      {error && (
        <p className="alert" role="alert">
          Cannot reach the API on port 8000.{board ? ' Showing the last board we received.' : ''}
        </p>
      )}
      {actionError && <p className="alert" role="alert">{actionError}</p>}

      {!board && !error && <p className="muted">Loading the board…</p>}

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
    </>
  )
}
