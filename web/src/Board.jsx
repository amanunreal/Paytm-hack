import { useState } from 'react'
import * as api from './api'
import { CAUSES, LANGUAGES, longDate, percent, stateOf } from './labels'

const STATS = [
  ['handled_remote', 'Handled remotely', 'good'],
  ['rep_visit', 'Rep visit', 'rep'],
  ['needs_approval', 'Needs approval', 'wait'],
  ['awaiting_call', 'Awaiting call', 'wait'],
  ['no_action', 'No action', 'quiet'],
]

const NEEDS_YOU = ['awaiting_call', 'on_call', 'awaiting_approval']

const place = (item) => `${item.area}, ${item.state} · ${LANGUAGES[item.language] ?? item.language}`

// Undiagnosed first, so the work still to do stays at the top during a run.
function groupByCause(cases) {
  const causes = [null, ...Object.keys(CAUSES)]
  return causes
    .map((cause) => ({ cause, cases: cases.filter((item) => item.cause === cause) }))
    .filter((group) => group.cases.length > 0)
}

function tally(cases) {
  const counts = new Map()
  cases.forEach((item) => {
    const { label } = stateOf(item)
    counts.set(label, (counts.get(label) ?? 0) + 1)
  })
  return [...counts].map(([label, count]) => `${count} ${label.toLowerCase()}`).join(' · ')
}

function Progress({ headline }) {
  return (
    <section className="progress" aria-label="Where the flagged merchants stand">
      <div className="meter" aria-hidden="true">
        {STATS.map(([key, , tone]) => headline[key] > 0 && (
          <div key={key} className={`meter-part meter-${tone}`} style={{ flexGrow: headline[key] }} />
        ))}
      </div>
      <dl className="stats">
        {STATS.map(([key, label]) => (
          <div key={key}>
            <dd>{headline[key]}</dd>
            <dt>{label}</dt>
          </div>
        ))}
      </dl>
    </section>
  )
}

function NeedsYouRow({ item, busy, onCall }) {
  const { label, tone } = stateOf(item)
  return (
    <li className={`todo todo-${tone}`}>
      <a href={`#/cases/${item.id}`}>
        <strong>{item.owner}</strong>
        <span className="muted">{place(item)}</span>
      </a>
      <span className="muted todo-cause">{CAUSES[item.cause]}</span>
      {item.status === 'awaiting_call' && (
        <button type="button" className="primary" disabled={busy} onClick={() => onCall(item.id)}>Call</button>
      )}
      {item.status === 'awaiting_approval' && <a className="button" href="#/manager">Review</a>}
      {item.status === 'on_call' && <span className="state state-live">On the line</span>}
      {item.status === 'done' && <span className={`state state-${tone}`}>{label}</span>}
    </li>
  )
}

function CaseRow({ item }) {
  const { label, tone } = stateOf(item)
  return (
    <li>
      <a className="case-row" href={`#/cases/${item.id}`}>
        <span>
          <strong>{item.owner}</strong>
          <span className="muted">{item.shop_type}</span>
        </span>
        <span className="muted">{place(item)}</span>
        <span className="muted case-signal">
          {percent(item.volume_ratio)} volume{item.offline_days > 0 && ` · box offline ${item.offline_days}d`}
        </span>
        <span className={`state state-${tone}`}>{label}</span>
      </a>
    </li>
  )
}

function CauseGroup({ group, open, onToggle }) {
  const id = `group-${group.cause ?? 'new'}`
  return (
    <section className="group">
      <h3>
        <button type="button" className="group-head" aria-expanded={open} aria-controls={id} onClick={onToggle}>
          <span className="chevron" aria-hidden="true">›</span>
          <span className="group-name">{CAUSES[group.cause] ?? 'Not diagnosed yet'}</span>
          <span className="group-count">{group.cases.length}</span>
          <span className="muted group-tally">{tally(group.cases)}</span>
        </button>
      </h3>
      {open && (
        <ul id={id} className="case-list">
          {group.cases.map((item) => <CaseRow key={item.id} item={item} />)}
        </ul>
      )}
    </section>
  )
}

export default function Board({
  board, error, refresh, runStarted, setRunStarted, called, setCalled, markCalled, openGroups, setOpenGroups,
}) {
  const [actionError, setActionError] = useState(null)
  const [busy, setBusy] = useState(false)

  if (!board) {
    return error
      ? <p className="alert" role="alert">Cannot reach the API on port 8000.</p>
      : <p className="muted">Loading the board…</p>
  }

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

  const statuses = new Set(board.cases.map((item) => item.status))
  // The run snapshots new cases and keeps writing in the background, so a second
  // run or a reset mid-run would leave a dirty demo. Reloading the page clears this.
  const running = statuses.has('working') || statuses.has('on_call') || (runStarted && statuses.has('new'))
  const hasNew = statuses.has('new')

  const run = () => {
    setRunStarted(true)
    return act(api.runAll)
  }
  const reset = () => {
    setRunStarted(false)
    setCalled([])
    return act(api.reset)
  }
  const call = (id) => {
    markCalled(id)
    return act(() => api.startCall(id))
  }
  const toggle = (key) => {
    setOpenGroups((open) => (open.includes(key) ? open.filter((item) => item !== key) : [...open, key]))
  }

  const needsYou = board.cases
    .filter((item) => NEEDS_YOU.includes(item.status) || called.includes(item.id))
    .sort((a, b) => a.status.localeCompare(b.status) * -1)
  const groups = groupByCause(board.cases)

  return (
    <main>
      <header className="page-head">
        <div>
          <h1>{board.headline.flagged} merchants flagged</h1>
          <p className="muted">All India · 8:00 AM, {longDate(board.date)}</p>
        </div>
        <div className="actions">
          {(hasNew || running) && (
            <button type="button" className="primary" disabled={busy || running} onClick={run}>
              {running ? 'Working…' : 'Run agent'}
            </button>
          )}
          <button type="button" className="quiet" disabled={busy || running} onClick={reset}>Reset</button>
        </div>
      </header>

      {error && <p className="alert" role="alert">Cannot reach the API. Showing the last board we received.</p>}
      {actionError && <p className="alert" role="alert">{actionError}</p>}

      <Progress headline={board.headline} />

      {board.area_dips.map((dip) => (
        <p className="note" key={dip.area}>
          <strong>{dip.merchants} {dip.area} merchants dipped with their area</strong>
          {' '}({percent(dip.ratio)} of normal), so Wapsi did nothing.
        </p>
      ))}

      {needsYou.length > 0 && (
        <section aria-labelledby="needs-you">
          <h2 id="needs-you">Needs you</h2>
          <ul className="todos">
            {needsYou.map((item) => <NeedsYouRow key={item.id} item={item} busy={busy} onCall={call} />)}
          </ul>
        </section>
      )}

      <section aria-labelledby="by-cause">
        <h2 id="by-cause">By cause</h2>
        {groups.map((group) => {
          const key = group.cause ?? 'new'
          return (
            <CauseGroup
              key={key}
              group={group}
              open={openGroups.includes(key) || group.cause === null}
              onToggle={() => toggle(key)}
            />
          )
        })}
      </section>
    </main>
  )
}
