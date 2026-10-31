import { useCallback, useEffect, useState } from 'react'

const POLL_MS = 1000

// Polls `load`, which must be stable. Keeps the last good data through a failure.
export function usePoll(load) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    try {
      setData(await load())
      setError(null)
    } catch (failure) {
      setError(failure)
    }
  }, [load])

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

  return { data, error, refresh }
}
