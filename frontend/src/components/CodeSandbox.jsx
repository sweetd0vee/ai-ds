import { useCallback, useEffect, useRef, useState } from 'react'
import { Play, RotateCcw, Loader2 } from 'lucide-react'
import { runSandboxCode } from '../api'

export default function CodeSandbox({ jobId, defaultCode }) {
  const [code, setCode] = useState('')
  const [output, setOutput] = useState('')
  const [error, setError] = useState(null)
  const [warnings, setWarnings] = useState([])
  const [running, setRunning] = useState(false)
  const [ranOnce, setRanOnce] = useState(false)
  const initForJob = useRef(null)
  const userEdited = useRef(false)

  useEffect(() => {
    if (!jobId) return

    if (initForJob.current !== jobId) {
      initForJob.current = jobId
      userEdited.current = false
      setCode(defaultCode || '')
      setOutput('')
      setError(null)
      setWarnings([])
      setRanOnce(false)
      return
    }

    if (defaultCode && !userEdited.current && code !== defaultCode) {
      setCode(defaultCode)
    }
  }, [jobId, defaultCode, code])

  const handleCodeChange = (value) => {
    userEdited.current = true
    setCode(value)
  }

  const handleRun = useCallback(async () => {
    if (running) return

    if (!jobId) {
      setError('ID задачи не найден. Запустите анализ заново.')
      setRanOnce(true)
      return
    }

    if (!code.trim()) {
      setError('Введите код для выполнения')
      setRanOnce(true)
      return
    }

    setRunning(true)
    setError(null)
    setWarnings([])

    try {
      const result = await runSandboxCode(jobId, code)
      setOutput(result.output || '')
      setError(result.success ? null : (result.error || 'Ошибка выполнения'))
      setWarnings(result.warnings || [])
      setRanOnce(true)
    } catch (e) {
      setError(e.message)
      setOutput('')
      setRanOnce(true)
    } finally {
      setRunning(false)
    }
  }, [jobId, code, running])

  const handleReset = () => {
    userEdited.current = false
    setCode(defaultCode || '')
    setOutput('')
    setError(null)
    setWarnings([])
    setRanOnce(false)
  }

  const onKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      handleRun()
    }
  }

  const canRun = Boolean(jobId && code.trim() && !running)

  return (
    <div className="code-sandbox">
      <div className="sandbox-toolbar">
        <button
          type="button"
          className="sandbox-run-btn"
          onClick={handleRun}
          disabled={!canRun}
          title={!jobId ? 'Сначала запустите анализ' : !code.trim() ? 'Введите код' : 'Запустить код'}
        >
          {running ? <Loader2 size={16} className="spin" /> : <Play size={16} />}
          {running ? 'Выполняется…' : 'Запустить'}
        </button>
        <button
          type="button"
          className="sandbox-reset-btn"
          onClick={handleReset}
          disabled={running}
        >
          <RotateCcw size={14} />
          Сбросить
        </button>
        <span className="sandbox-hint">Ctrl+Enter — запуск</span>
      </div>

      {!jobId && (
        <div className="sandbox-status sandbox-status--warn">
          Задача не привязана — перезапустите анализ файла
        </div>
      )}

      <div className="sandbox-panels">
        <div className="sandbox-panel sandbox-panel--editor">
          <div className="sandbox-panel-label">Код</div>
          <textarea
            className="sandbox-editor"
            value={code}
            onChange={(e) => handleCodeChange(e.target.value)}
            onKeyDown={onKeyDown}
            spellCheck={false}
            placeholder="print(1)"
          />
        </div>

        <div className="sandbox-panel sandbox-panel--output">
          <div className="sandbox-panel-label">Результат</div>
          <div className={`sandbox-output ${error ? 'sandbox-output--error' : ''}`}>
            {!ranOnce && !running && (
              <span className="sandbox-placeholder">
                Нажмите «Запустить», чтобы выполнить код на сервере с вашим DataFrame
              </span>
            )}
            {running && (
              <span className="sandbox-placeholder">Выполнение…</span>
            )}
            {ranOnce && !running && error && (
              <>
                {output && <pre className="sandbox-output-text">{output}</pre>}
                <pre className="sandbox-output-text sandbox-output-text--error">{error}</pre>
              </>
            )}
            {ranOnce && !running && !error && output && (
              <pre className="sandbox-output-text">{output}</pre>
            )}
            {ranOnce && !running && !error && !output && (
              <span className="sandbox-placeholder">Код выполнен без вывода (добавьте print)</span>
            )}
          </div>
        </div>
      </div>

      {warnings.length > 0 && (
        <div className="sandbox-warnings">
          {warnings.map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}
    </div>
  )
}

