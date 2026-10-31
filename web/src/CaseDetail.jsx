import { useCallback, useEffect, useState } from 'react'
import * as api from './api'
import {
  approvalStatus, approvalTitle, CAUSES, EVENT_KINDS, guardrailLine, LANGUAGES, percent, stateOf,
} from './labels'
import PhoneMockup from './PhoneMockup'
import SignalCharts from './SignalCharts'
import { usePoll } from './usePoll'

const QUIET_RATIO = 0.6 // Same line as the detector: below this the shop has gone quiet.
const DETAIL_LIMIT = 160 // The real agent's tool results run to pages of JSON.
const DIALLING = 'Dialling merchant' // Written by wapsi/voice.py when a real call starts.
const SPEAKERS = ['Wapsi', 'Merchant']

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
  const text = Object.entries(detail)
    .map(([key, value]) => `${key}: ${typeof value === 'object' ? JSON.stringify(value) : value}`)
    .join(' · ')
  return text.length > DETAIL_LIMIT ? `${text.slice(0, DETAIL_LIMIT)}…` : text
}

const readable = (text) => text.replaceAll('_', ' ').replace('Case closed:', 'Outcome:')
const isRead = (event) => event.kind === 'tool_call' && event.title.startsWith('get_')
const checkName = (event) => readable(event.title.replace('get_', ''))

// Turns the raw events into what a person would say happened. Runs of read-only
// tools become one line, and the raw calls stay behind the All steps toggle.
function storyOf(events) {
  const story = []
  events.forEach((event) => {
    if (isRead(event)) {
      const last = story.at(-1)
      if (last?.type === 'checks') last.names.push(checkName(event))
      else story.push({ type: 'checks', id: event.id, names: [checkName(event)] })
    } else if (event.kind === 'call' && SPEAKERS.includes(event.title)) {
      story.push({ type: 'speech', id: event.id, event })
    } else if (['thought', 'guardrail', 'approval', 'call'].includes(event.kind)
      || (event.kind === 'status' && !event.title.startsWith('Diagnosis'))) {
      story.push({ type: 'step', id: event.id, event })
    }
  })
  return story
}

function StoryItem({ item }) {
  if (item.type === 'checks') {
    return <li className="step"><span className="muted">Checked {item.names.join(', ')}</span></li>
  }
  const { event } = item
  if (item.type === 'speech') {
    const mine = event.title === 'Wapsi'
    return (
      <li className={`speech ${mine ? 'speech-wapsi' : 'speech-merchant'}`}>
        <span className="muted">{mine ? 'Wapsi' : 'Merchant'}</span>
        <p lang="hi">{event.detail?.text}</p>
      </li>
    )
  }
  return (
    <li className={`step step-${event.kind}`}>
      <span>{readable(event.title)}</span>
      {event.kind === 'guardrail' && <span className="step-detail">{guardrailLine(event)}.</span>}
    </li>
  )
}

function AllSteps({ events }) {
  return (
    <ol className="raw">
      {events.map((event) => (
        <li key={event.id}>
          <span className="raw-kind">{EVENT_KINDS[event.kind] ?? event.kind}</span>
          <div>
            <div>{event.title}</div>
            {event.detail && <div className="muted raw-detail">{eventDetail(event.detail)}</div>}
          </div>
          <time className="muted" dateTime={event.ts}>{event.ts.slice(11)}</time>
        </li>
      ))}
    </ol>
  )
}

function Trace({ events, working }) {
  const [showAll, setShowAll] = useState(false)
  const story = storyOf(events)
  return (
    <section aria-labelledby="trace-title">
      <div className="section-head">
        <h2 id="trace-title">Agent trace {working && <span className="live-dot" aria-label="Live" />}</h2>
        {events.length > 0 && (
          <button type="button" className="link" aria-expanded={showAll} onClick={() => setShowAll(!showAll)}>
            {showAll ? 'Summary' : `All ${events.length} steps`}
          </button>
        )}
      </div>
      {events.length === 0 && <p className="muted">Steps appear here as the agent works.</p>}
      {showAll
        ? <AllSteps events={events} />
        : <ol className="story" aria-live="polite">{story.map((item) => <StoryItem key={item.id} item={item} />)}</ol>}
    </section>
  )
}

const clock = (seconds) => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`

// Bolna only gives the transcript after the call, so this is what the room watches.
function LiveCall({ owner, events }) {
  const callEvents = events.filter((event) => event.kind === 'call')
  const started = callEvents.findLast((event) => event.title === DIALLING)
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])
  const elapsed = started ? Math.max(0, Math.floor((now - Date.parse(started.ts)) / 1000)) : 0
  return (
    <section className="live-call" role="status">
      <span className="live-dot" aria-hidden="true" />
      <div>
        <strong>On the line with {owner}</strong>
        <span>{callEvents.at(-1)?.title ?? DIALLING}. The transcript appears when the call ends.</span>
      </div>
      <time>{clock(elapsed)}</time>
    </section>
  )
}

export default function CaseDetail({ caseId, runStarted, markCalled }) {
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
  const call = () => {
    markCalled(caseId)
    return act(() => api.startCall(caseId))
  }

  if (!data) {
    return error
      ? <p className="alert" role="alert">{error.message}</p>
      : <p className="muted">Loading the case…</p>
  }

  const { case: item, merchant, signals, events, approvals } = data
  const { label, tone } = stateOf(item)
  const onCall = item.status === 'on_call'

  return (
    <main>
      <header className="page-head">
        <div>
          <h1>{merchant.owner}</h1>
          <p className="muted">
            {merchant.shop_type} · {merchant.area}, {merchant.state} ·{' '}
            {LANGUAGES[merchant.language] ?? merchant.language} · {merchant.device_model}
          </p>
        </div>
        <div className="actions">
          <span className={`state state-${tone}`}>{label}</span>
          {item.status === 'new' && (
            <button type="button" className="primary" disabled={busy || runRequested || runStarted} onClick={run}>
              {runRequested || runStarted ? 'Working…' : 'Run this case'}
            </button>
          )}
          {item.status === 'awaiting_call' && (
            <button type="button" className="primary" disabled={busy} onClick={call}>
              {events.some((event) => event.title === DIALLING) ? 'Call again' : 'Call'}
            </button>
          )}
        </div>
      </header>

      {error && <p className="alert" role="alert">Cannot refresh this case. Showing the last data we received.</p>}
      {actionError && <p className="alert" role="alert">{actionError}</p>}

      <p className="lede">{signalSentence(item)}</p>

      {onCall && <LiveCall owner={merchant.owner} events={events} />}

      <div className="case-grid">
        <div className="case-column">
          <section aria-labelledby="diagnosis-title">
            <h2 id="diagnosis-title">Diagnosis</h2>
            <p className="diagnosis">{CAUSES[item.cause] ?? 'Not diagnosed yet'}</p>
            {item.summary && <p>{item.summary}</p>}
            {item.rep_brief && <p className="brief"><strong>Rep brief</strong> {item.rep_brief}</p>}
            {approvals.map((approval) => (
              <p className="brief" key={approval.id}>
                <strong>{approvalTitle(approval)}</strong> {approvalStatus(approval.status)}
                {approval.status === 'pending' && <> · <a href="#/manager">Review</a></>}
              </p>
            ))}
          </section>
          <SignalCharts signals={signals} />
        </div>
        <div className="case-column">
          <PhoneMockup events={events} owner={merchant.owner} />
          <Trace events={events} working={item.status === 'working' || onCall} />
        </div>
      </div>
    </main>
  )
}
