import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { FileSpreadsheet, Loader2, Trash2, X } from 'lucide-react'
import { clearHistory, deleteHistoryJob, fetchJobHistory } from '../api'
import { formatDateTime } from '../utils/format'

const STATUS_LABELS = {
  completed: 'Завершено',
  running: 'Выполняется',
  failed: 'Ошибка',
  pending: 'Ожидание',
  unknown: 'Неизвестно',
}

export default function HistoryModal({ open, onClose, onSelect, onDeleted }) {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [clearing, setClearing] = useState(false)

  const loadHistory = useCallback(() => {
    setLoading(true)
    setError(null)
    return fetchJobHistory()
      .then(setJobs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!open) return
    loadHistory()
  }, [open, loadHistory])

  const handleDelete = async (e, jobId) => {
    e.stopPropagation()
    if (deletingId || clearing) return

    setDeletingId(jobId)
    setError(null)
    try {
      await deleteHistoryJob(jobId)
      setJobs((prev) => prev.filter((item) => item.job_id !== jobId))
      onDeleted?.(jobId)
    } catch (err) {
      setError(err.message)
    } finally {
      setDeletingId(null)
    }
  }

  const handleClearAll = async () => {
    if (clearing || deletingId || jobs.length === 0) return
    if (!window.confirm('Удалить все записи из истории?')) return

    setClearing(true)
    setError(null)
    try {
      await clearHistory()
      setJobs([])
      onDeleted?.(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setClearing(false)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="settings-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            className="settings-modal history-modal"
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ duration: 0.2 }}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-labelledby="history-title"
            aria-modal="true"
          >
            <div className="settings-modal-header">
              <h2 id="history-title">История анализов</h2>
              <div className="history-header-actions">
                {jobs.length > 0 && (
                  <button
                    type="button"
                    className="history-clear-all"
                    onClick={handleClearAll}
                    disabled={clearing || Boolean(deletingId)}
                    aria-label="Очистить всю историю"
                    title="Очистить всю историю"
                  >
                    {clearing ? <Loader2 size={18} className="spin" /> : <X size={18} />}
                  </button>
                )}
                <button type="button" className="settings-close" onClick={onClose} aria-label="Закрыть">
                  <X size={20} />
                </button>
              </div>
            </div>

            <div className="settings-modal-body history-modal-body">
              {loading && (
                <div className="history-state">
                  <Loader2 size={24} className="spin" />
                  <span>Загрузка…</span>
                </div>
              )}

              {!loading && error && (
                <div className="history-state history-state--error">{error}</div>
              )}

              {!loading && !error && jobs.length === 0 && (
                <div className="history-state">Пока нет завершённых анализов</div>
              )}

              {!loading && !error && jobs.length > 0 && (
                <ul className="history-list">
                  {jobs.map((item) => (
                    <li key={item.job_id} className="history-list-item">
                      <button
                        type="button"
                        className="history-item"
                        onClick={() => onSelect(item)}
                        disabled={Boolean(deletingId) || clearing}
                      >
                        <FileSpreadsheet size={20} className="history-item-icon" />
                        <div className="history-item-main">
                          <strong title={item.filename}>{item.filename}</strong>
                          <span className="history-item-meta">
                            {formatDateTime(item.created_at)}
                            {item.rows != null && item.cols != null && (
                              <> · {item.rows} × {item.cols}</>
                            )}
                            <> · {item.graph_count} граф.</>
                          </span>
                        </div>
                        <span className={`history-item-status history-item-status--${item.status}`}>
                          {STATUS_LABELS[item.status] || item.status}
                        </span>
                      </button>
                      <button
                        type="button"
                        className="history-item-delete"
                        onClick={(e) => handleDelete(e, item.job_id)}
                        disabled={deletingId === item.job_id || clearing}
                        aria-label="Удалить запись"
                        title="Удалить"
                      >
                        {deletingId === item.job_id
                          ? <Loader2 size={16} className="spin" />
                          : <Trash2 size={16} />}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
