import { useCallback, useEffect, useRef, useState } from 'react'
import { getJobStatus, streamJobStatus } from '../api'

export function useJobStream() {
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const cleanupRef = useRef(null)

  const stopStream = useCallback(() => {
    cleanupRef.current?.()
    cleanupRef.current = null
  }, [])

  const startStream = useCallback((jobId) => {
    stopStream()
    setLoading(true)
    setError(null)

    const apply = (data) => {
      if (!data) return
      setJob(data)
      if (data.status === 'completed' || data.status === 'failed') {
        setLoading(false)
        stopStream()
      }
    }

    const poll = () => {
      getJobStatus(jobId).then(apply).catch(() => {})
    }

    const intervalId = setInterval(poll, 2000)
    const closeSse = streamJobStatus(jobId, apply, poll)

    cleanupRef.current = () => {
      clearInterval(intervalId)
      closeSse()
    }
  }, [stopStream])

  const resetJob = useCallback(() => {
    stopStream()
    setJob(null)
    setLoading(false)
    setError(null)
  }, [stopStream])

  useEffect(() => () => stopStream(), [stopStream])

  return {
    job,
    loading,
    error,
    setError,
    setJob,
    setLoading,
    startStream,
    stopStream,
    resetJob,
  }
}
