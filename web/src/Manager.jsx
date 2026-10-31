import { useCallback, useState } from 'react'
import * as api from './api'
import { approvalTitle, BUCKETS, LANGUAGES } from './labels'
import { usePoll } from './usePoll'

async function loadPending() {
  const approvals = await api.getApprovals()
  return Promise.all(approvals.map(async (approval) => ({ approval, ...(await api.getCase(approval.case_id)) })))
}

const NEXT_STEPS = {
  waiver: { approve: 'Refund paid, case closed', reject: 'Rep visits instead' },
  counter_offer: { approve: 'Rep visits with the offer', reject: 'Rep visits without an offer' },
}

// Guardrail text is written for the agent, so reword its first sentence for a person.
function guardrailLine(event) {
  const firstSentence = event.detail?.text?.split('. ')[0] ?? event.title
  return firstSentence.replace('your', "the agent's")
}

function ApprovalCard({ item, disabled, onDecide }) {
  const { approval, merchant, events } = item
  const blocked = events.filter((event) => event.kind === 'guardrail')
  const next = NEXT_STEPS[approval.kind]
  return (
    <article className="panel approval">
      <div className="panel-title">
        <h2><a href={`#/cases/${approval.case_id}`}>{merchant.owner}</a></h2>
        <span className="muted">
          {merchant.id} · {merchant.shop_type} · {merchant.area}, {merchant.state} ·{' '}
          {LANGUAGES[merchant.language] ?? merchant.language}
        </span>
      </div>
      <p className="approval-ask">{approvalTitle(approval)}</p>
      <p>{approval.reason}</p>
      {blocked.map((event) => (
        <p className="guardrail-note" key={event.id}>
          <strong>Guardrail:</strong> {guardrailLine(event)}.
        </p>
      ))}
      <div className="decision">
        <button type="button" className="primary" disabled={disabled} onClick={() => onDecide(item, 'approve')}>
          Approve
        </button>
        <span className="muted">{next?.approve ?? BUCKETS[approval.next_bucket]}</span>
        <button type="button" disabled={disabled} onClick={() => onDecide(item, 'reject')}>Reject</button>
        <span className="muted">{next?.reject ?? BUCKETS.rep_visit}</span>
      </div>
    </article>
  )
}

export default function Manager() {
  const { data: pending, error, refresh } = usePoll(loadPending)
  const [decided, setDecided] = useState([])
  const [actionError, setActionError] = useState(null)
  const [busy, setBusy] = useState(false)

  const decide = useCallback(async ({ approval, merchant }, decision) => {
    setBusy(true)
    setActionError(null)
    try {
      const { bucket } = await api.decide(approval.id, decision)
      setDecided((list) => [{ id: approval.id, owner: merchant.owner, title: approvalTitle(approval), decision, bucket }, ...list])
    } catch (failure) {
      setActionError(failure.message)
    } finally {
      await refresh()
      setBusy(false)
    }
  }, [refresh])

  return (
    <>
      <a className="back" href="#/">← Board</a>
      <header className="topbar">
        <div className="brand">
          <h1>Manager view</h1>
          <p className="muted">Decisions the agent is not allowed to make alone</p>
        </div>
      </header>

      {error && <p className="alert" role="alert">Cannot reach the API. Showing the last list we received.</p>}
      {actionError && <p className="alert" role="alert">{actionError}</p>}
      {!pending && !error && <p className="muted">Loading approvals…</p>}

      <main className="approvals">
        {pending?.length === 0 && <p className="panel muted">Nothing is waiting for you.</p>}
        {pending?.map((item) => (
          <ApprovalCard key={item.approval.id} item={item} disabled={busy} onDecide={decide} />
        ))}

        {decided.length > 0 && (
          <section className="panel" aria-labelledby="decided-title">
            <h2 id="decided-title">Decided</h2>
            <ul className="decided">
              {decided.map((item) => (
                <li key={item.id}>
                  <strong>{item.owner}:</strong> {item.title} {item.decision === 'approve' ? 'approved' : 'rejected'}.{' '}
                  Case is now {BUCKETS[item.bucket]}.
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </>
  )
}
