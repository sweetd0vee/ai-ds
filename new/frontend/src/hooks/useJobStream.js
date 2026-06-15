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

    cleanupRef.current = streamJobStatus(
      jobId,
      (data) => {
        setJob(data)
        if (data.status === 'completed' || data.status === 'failed') {
          setLoading(false)
          stopStream()
        }
      },
      (err) => {
        getJobStatus(jobId).then(setJob).catch(() => {})
        setError(err?.message || 'Ошибка соединения')
        setLoading(false)
      },
    )
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
