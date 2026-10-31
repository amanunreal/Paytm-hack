// Display text for the fixed values in the PLAN.md contract.
export const CAUSES = {
  device_fault: 'Device fault',
  sim_network: 'SIM or network',
  money_problem: 'Money problem',
  billing_anger: 'Billing anger',
  competitor_switch: 'Competitor switch',
  closed_seasonal: 'Closed or seasonal',
}

export const LANGUAGES = {
  as: 'Assamese', bn: 'Bengali', gu: 'Gujarati', hi: 'Hindi', kn: 'Kannada', ml: 'Malayalam',
  mr: 'Marathi', or: 'Odia', pa: 'Punjabi', ta: 'Tamil', te: 'Telugu',
}

const STATUSES = {
  new: 'New',
  working: 'Working',
  awaiting_call: 'Awaiting call',
  on_call: 'On call',
  awaiting_approval: 'Needs approval',
  control: 'Control group',
}

export const BUCKETS = {
  handled_remote: 'Handled remotely',
  rep_visit: 'Rep visit',
  needs_approval: 'Needs approval',
  no_action: 'No action',
}

export const EVENT_KINDS = {
  thought: 'Thinking',
  tool_call: 'Tool call',
  tool_result: 'Tool result',
  guardrail: 'Guardrail',
  call: 'Call',
  whatsapp: 'WhatsApp',
  approval: 'Approval',
  status: 'Status',
}

// A finished case shows its outcome. Anything else shows where it is now.
export const stateOf = (item) => {
  const done = item.status === 'done'
  return {
    label: done ? BUCKETS[item.bucket] : STATUSES[item.status],
    tone: done ? item.bucket : item.status,
  }
}

// `amount` is a one-off refund for a waiver, but the new monthly rent for a counter-offer.
export const approvalTitle = ({ kind, amount }) =>
  kind === 'waiver' ? `Refund of Rs ${amount}` : `Counter-offer: Rs ${amount} monthly rent`

// The API stores a rejection as `rejectd`, so match it either way.
export const approvalStatus = (status) => (status.startsWith('reject') ? 'rejected' : status)

export const percent = (ratio) => `${Math.round(ratio * 100)}%`

export const shortDay = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })

export const longDate = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })
