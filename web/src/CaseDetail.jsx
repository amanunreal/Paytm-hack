import { useCallback, useEffect, useState } from 'react'
import * as api from './api'
import { CAUSES, EVENT_KINDS, LANGUAGES, percent, stateOf } from './labels'
import SignalCharts from './SignalCharts'
import { usePoll } from './usePoll'

const QUIET_RATIO = 0.6 // Same line as the detector: below this the shop has gone quiet.

const days = (count) => `${count} ${count === 1 ? 'day' : 'days'}`

// Facts only, from the detector's numbers. The diagnosis is the agent's to make.
function signalSentence({ volume_ratio: ratio, offline_days: offline }) {
  const volume = `${percent(ratio)} of normal`
  if (offline > 0 && ratio >= QUIET_RATIO) return `Box offline for ${days(offline)}, but QR payments are still at ${volume}.`
  if (offline > 0 && ratio === 0) return `Box offline for ${days(offline)}, and no QR payments.`
  if (offline > 0) return `Box offline for ${days(offline)}, and QR payments are down to ${volume}.`
  return `Box is online, but QR payments are down to ${volume}.`
}

function eventDetail(detail) {
  if (!detail) return null
  if (detail.text) return detail.text
  return Object.entries(detail)
    .map(([key, value]) => `${key}: ${typeof value === 'object' ? JSON.stringify(value) : value}`)
    .join(' · ')
}

function Trace({ events, working }) {
  return (
    <section className="panel" aria-labelledby="trace-title">
      <div className="panel-title">
        <h2 id="trace-title">Agent trace</h2>
        {working && <span className="pill pill-working">Live</span>}
      </div>
      {events.length === 0 && <p className="muted">Nothing yet. Steps appear here as the agent works.</p>}
      <ol className="trace" aria-live="polite">
        {events.map((event) => (
          <li key={event.id} className={`event event-${event.kind}`}>
            <span className="event-kind">{EVENT_KINDS[event.kind] ?? event.kind}</span>
            <div className="event-body">
              <div className="event-title">{event.title}</div>
              {event.detail && <div className="muted event-detail">{eventDetail(event.detail)}</div>}
            </div>
            <time className="muted" dateTime={event.ts}>{event.ts.slice(11)}</time>
          </li>
        ))}
      </ol>
    </section>
  )
}

export default function CaseDetail({ caseId, runStarted }) {
  const load = useCallback(() => api.getCase(caseId), [caseId])
  const { data, error, refresh } = usePoll(load)
  const [actionError, setActionError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [runRequested, setRunRequested] = useState(false)

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])

  const act = async (action) => {
    setBusy(true)
    setActionError(null)
    try {
      await action()
      await refresh()
    } catch (failure) {
      setActionError(failure.message)
      setRunRequested(false)
    } finally {
      setBusy(false)
    }
  }

  const run = () => {
    setRunRequested(true)
    return act(() => api.runCase(caseId))
  }

  const back = <a className="back" href="#/">← Board</a>

  if (!data) {
    return (
      <>
        {back}
        {error
          ? <p className="alert" role="alert">{error.message}</p>
          : <p className="muted">Loading the case…</p>}
      </>
    )
  }

  const { case: item, merchant, signals, events, approvals } = data
  const { label, tone } = stateOf(item)

  return (
    <>
      {back}
      <header className="topbar">
        <div className="brand">
          <h1>{merchant.owner}</h1>
          <p className="muted">
            {merchant.id} · {merchant.shop_type} · {merchant.area}, {merchant.state} ·{' '}
            {LANGUAGES[merchant.language] ?? merchant.language} · {merchant.device_model}
          </p>
        </div>
        <span className={`pill pill-${tone}`}>{label}</span>
        <div className="actions">
          {item.status === 'new' && (
            <button type="button" className="primary" disabled={busy || runRequested || runStarted} onClick={run}>
              {runRequested || runStarted ? 'Running…' : 'Run this case'}
            </button>
          )}
          {item.status === 'awaiting_call' && (
            <button type="button" className="primary" disabled={busy} onClick={() => act(() => api.startCall(caseId))}>
              {events.some((event) => event.kind === 'call') ? 'Call again' : 'Call'}
            </button>
          )}
        </div>
      </header>

      {error && <p className="alert" role="alert">Cannot refresh this case. Showing the last data we received.</p>}
      {actionError && <p className="alert" role="alert">{actionError}</p>}

      <p className="banner">{signalSentence(item)}</p>

      <main className="case-grid">
        <div className="case-column">
          <SignalCharts signals={signals} />
          <section className="panel" aria-labelledby="diagnosis-title">
            <h2 id="diagnosis-title">Diagnosis</h2>
            <dl className="facts">
              <dt>Cause</dt>
              <dd>{CAUSES[item.cause] ?? 'Not diagnosed yet'}</dd>
              {item.summary && <><dt>Summary</dt><dd>{item.summary}</dd></>}
              {item.rep_brief && <><dt>Rep brief</dt><dd>{item.rep_brief}</dd></>}
              {approvals.map((approval) => (
                <div className="fact-row" key={approval.id}>
                  <dt>Approval</dt>
                  <dd>{approval.kind.replace('_', ' ')} of {approval.amount}: {approval.status}</dd>
                </div>
              ))}
            </dl>
          </section>
        </div>
        <Trace events={events} working={item.status === 'working' || item.status === 'on_call'} />
      </main>
    </>
  )
}
