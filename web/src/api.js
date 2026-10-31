// Every call to the API contract in PLAN.md goes through here.
const TIMEOUT_MS = 5000

async function request(path, options) {
  const response = await fetch(`/api${path}`, { ...options, signal: AbortSignal.timeout(TIMEOUT_MS) })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `${path} failed with ${response.status}`)
  }
  return response.json()
}

export const getBoard = () => request('/board')
export const runAll = () => request('/run', { method: 'POST' })
export const reset = () => request('/reset', { method: 'POST' })
export const startCall = (caseId) => request(`/cases/${caseId}/call`, { method: 'POST' })
