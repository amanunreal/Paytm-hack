// Every call to the API contract in PLAN.md goes through here.
const TIMEOUT_MS = 5000

async function request(path, options) {
  const response = await fetch(`/api${path}`, { ...options, signal: AbortSignal.timeout(TIMEOUT_MS) })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `${path} failed with ${response.status}`)
  }
  // The agent writes Rs in its text. The UI and the deck both show the rupee sign.
  return JSON.parse((await response.text()).replace(/\bRs\.? ?(?=\d)/g, '₹'))
}

export const getBoard = () => request('/board')
export const getCase = (caseId) => request(`/cases/${caseId}`)
export const runAll = () => request('/run', { method: 'POST' })
export const runCase = (caseId) => request(`/cases/${caseId}/run`, { method: 'POST' })
export const getApprovals = () => request('/approvals')
export const decide = (approvalId, decision) =>
  request(`/approvals/${approvalId}/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision }),
  })
export const getResults = () => request('/results')
export const reset = () => request('/reset', { method: 'POST' })
export const startCall = (caseId) => request(`/cases/${caseId}/call`, { method: 'POST' })
