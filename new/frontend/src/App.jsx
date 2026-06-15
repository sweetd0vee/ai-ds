import { useCallback, useEffect, useRef, useState } from 'react'
import { LayoutGroup, motion } from 'framer-motion'
import { fetchConfig, startAnalysis } from './api'
import { useJobStream } from './hooks/useJobStream'
import { useSettings } from './hooks/useSettings'
import { formatElapsed } from './utils/format'
import AppHeader from './components/AppHeader'
import ErrorAlert from './components/ErrorAlert'
import SettingsModal from './components/SettingsModal'
import UploadSection from './components/UploadSection'
import PipelineStepper from './components/PipelineStepper'
import StatsCards from './components/StatsCards'
import ResultsPanel from './components/results/ResultsPanel'
import './App.css'

const shellTransition = { type: 'spring', stiffness: 280, damping: 32, mass: 0.9 }

export default function App() {
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [graphCount, setGraphCount] = useState(20)
  const [jobId, setJobId] = useState(null)
  const [activeSection, setActiveSection] = useState('preview')
  const [elapsed, setElapsed] = useState(0)
  const inputRef = useRef(null)
  const timerRef = useRef(null)

  const { job, loading, error, setError, startStream, setLoading } = useJobStream()
  const {
    settings,
    draft,
    modalOpen,
    openSettings,
    closeSettings,
    saveDraft,
    updateDraft,
  } = useSettings()
  const [analystModels, setAnalystModels] = useState([])
  const [modelsLoading, setModelsLoading] = useState(true)

  const isAnalysisMode = Boolean(job || loading)

  useEffect(() => {
    fetchConfig()
      .then((cfg) => setAnalystModels(cfg.analyst_models || []))
      .catch(() => setAnalystModels([]))
      .finally(() => setModelsLoading(false))
  }, [])

  useEffect(() => {
    if (loading) {
      const start = Date.now()
      timerRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - start) / 1000))
      }, 1000)
    } else {
      clearInterval(timerRef.current)
    }
    return () => clearInterval(timerRef.current)
  }, [loading])

  const handleFile = useCallback((f) => {
    if (!f) return
    const ext = f.name.split('.').pop()?.toLowerCase()
    if (!['csv', 'xlsx'].includes(ext)) {
      setError('Поддерживаются только .csv и .xlsx')
      return
    }
    setFile(f)
    setError(null)
    setJobId(null)
    setElapsed(0)
  }, [setError])

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files[0])
  }, [handleFile])

  const onAnalyze = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    setElapsed(0)
    setActiveSection('preview')
    try {
      const res = await startAnalysis(file, graphCount, settings.analystModel)
      setJobId(res.job_id)
      startStream(res.job_id)
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  const results = job?.results

  const uploadProps = {
    compact: isAnalysisMode,
    file,
    dragOver,
    graphCount,
    loading,
    onFile: handleFile,
    onDrop,
    onDragOver: (e) => { e.preventDefault(); setDragOver(true) },
    onDragLeave: () => setDragOver(false),
    onAnalyze,
    onClear: () => setFile(null),
    onGraphCount: setGraphCount,
    inputRef,
  }

  return (
    <div className="app-shell">
      <AppHeader onOpenSettings={openSettings} />

      <SettingsModal
        open={modalOpen}
        draft={draft}
        models={analystModels}
        modelsLoading={modelsLoading}
        onChange={updateDraft}
        onSave={saveDraft}
        onCancel={closeSettings}
      />

      <div className={`app ${isAnalysisMode ? 'app--analysis' : 'app--hero'}`}>
        <div className="app-bg" />
        {!isAnalysisMode && <div className="app-bg-glow" aria-hidden />}

        <LayoutGroup>
          {!isAnalysisMode ? (
            <motion.div
              className="upload-shell upload-shell--hero"
              layoutId="upload-shell"
              transition={shellTransition}
            >
              <UploadSection {...uploadProps} />
              <ErrorAlert message={error} variant="hero" />
            </motion.div>
          ) : (
            <main className="main-grid">
              <div className="left-col">
                <motion.div
                  className="upload-shell upload-shell--dock"
                  layoutId="upload-shell"
                  transition={shellTransition}
                >
                  <UploadSection {...uploadProps} />
                </motion.div>

                <ErrorAlert message={error} />

                {job && (
                  <motion.section
                    className="panel progress-panel"
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <div className="panel-header">
                      <div>
                        <h2>Прогресс анализа</h2>
                        <p className="progress-msg">{job.message}</p>
                      </div>
                      <span className={`status-pill ${job.status}`}>
                        {job.status === 'running' ? 'Выполняется' :
                         job.status === 'completed' ? 'Завершено' : 'Ошибка'}
                      </span>
                    </div>

                    <StatsCards
                      shape={results?.shape}
                      progress={job.progress}
                      graphCount={job.graph_count}
                      elapsed={loading || job.status === 'completed' ? formatElapsed(elapsed) : null}
                    />

                    <PipelineStepper
                      currentStep={job.step}
                      progress={job.progress}
                      status={job.status}
                    />

                    {job.error && <ErrorAlert message={job.error} />}
                  </motion.section>
                )}
              </div>

              <div className="right-col">
                <ResultsPanel
                  jobId={jobId}
                  job={job}
                  activeSection={activeSection}
                  onSection={setActiveSection}
                />
              </div>
            </main>
          )}
        </LayoutGroup>
      </div>
    </div>
  )
}
