import { AnimatePresence, motion } from 'framer-motion'
import { Download, Loader2, Table2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import {
  downloadAllPlots,
  downloadJobFile,
  downloadPlot,
  exportHypotheses,
  plotUrl,
} from '../../api'
import { RESULT_SECTIONS } from '../../constants'
import { RESULT_ICONS } from '../../utils/icons'
import CodeSandbox from '../CodeSandbox'
import AnalysisView from './AnalysisView'
import HypothesesView from './HypothesesView'
import CopyButton from './CopyButton'
import InsightsView from './InsightsView'
import MetricsPlanView from './MetricsPlanView'
import PlotsGallery from './PlotsGallery'
import PreviewView from './PreviewView'
import RelationsView from './RelationsView'
import ReportView from './ReportView'
import StructureView from './StructureView'
import { sectionHasData, sectionTextContent } from './sectionMeta'

async function downloadArtifact(jobId, filename, errorLabel) {
  if (!jobId) return
  try {
    await downloadJobFile(jobId, filename)
  } catch (e) {
    window.alert(e.message || errorLabel)
  }
}

const SECTION_DOWNLOADS = [
  {
    section: 'insights',
    filename: 'quality_insights.xlsx',
    label: 'Качество XLSX',
    when: (job) => job?.status === 'completed',
  },
  {
    section: 'analysis',
    filename: 'analysis_summary_report.docx',
    label: 'Анализ DOCX',
    when: (_, results) => Boolean(results?.analysis_summary),
  },
  {
    section: 'relations',
    filename: 'relations.txt',
    label: 'Связи TXT',
    when: (_, results) => Boolean(results?.relations_raw && results?.table_count > 1),
  },
  {
    section: 'structure',
    filename: 'data_structure.xlsx',
    label: 'Структура XLSX',
    when: (_, results) => Boolean(
      results?.data_structure?.columns?.length || results?.parsed_data_structure?.columns?.length,
    ),
  },
  {
    section: 'report',
    filename: 'final_report.docx',
    label: 'Отчёт DOCX',
    when: (job) => job?.status === 'completed',
  },
]

function BodyFill({ children }) {
  return <div className="content-body-fill">{children}</div>
}

function ResultsContent({
  activeSection,
  results,
  effectiveJobId,
  onOpenPlot,
  pending,
  selectedHypothesisIds,
  onToggleHypothesis,
  onSelectAllHypotheses,
  onSelectNoneHypotheses,
  canAddHypothesis,
  onHypothesisAdded,
}) {
  switch (activeSection) {
    case 'preview':
      return (
        <BodyFill>
          <PreviewView results={results} pending={pending} />
        </BodyFill>
      )
    case 'structure':
      return (
        <BodyFill>
          <StructureView results={results} />
        </BodyFill>
      )
    case 'relations':
      return (
        <BodyFill>
          <RelationsView results={results} />
        </BodyFill>
      )
    case 'insights':
      return (
        <BodyFill>
          <InsightsView results={results} />
        </BodyFill>
      )
    case 'metrics_plan':
      return (
        <BodyFill>
          <MetricsPlanView results={results} />
        </BodyFill>
      )
    case 'calculation_code':
      return (
        <BodyFill>
          <CodeSandbox jobId={effectiveJobId} defaultCode={results?.calculation_code} />
        </BodyFill>
      )
    case 'metrics':
      return <pre className="code-view">{results?.metrics_results_raw || 'Ожидание…'}</pre>
    case 'analysis':
      return (
        <BodyFill>
          <AnalysisView text={results?.analysis_summary} />
        </BodyFill>
      )
    case 'hypotheses':
      return (
        <BodyFill>
          <HypothesesView
            results={results}
            selectedIds={selectedHypothesisIds}
            onToggle={onToggleHypothesis}
            onSelectAll={onSelectAllHypotheses}
            onSelectNone={onSelectNoneHypotheses}
            jobId={effectiveJobId}
            canAdd={canAddHypothesis}
            onAdded={onHypothesisAdded}
          />
        </BodyFill>
      )
    case 'viz_code':
      return <pre className="code-view">{results?.viz_code || 'Ожидание…'}</pre>
    case 'report':
      return (
        <BodyFill>
          <ReportView text={results?.final_report} />
        </BodyFill>
      )
    case 'plots':
      return (
        <div className="content-body-fill content-body-fill--scroll">
          <PlotsGallery
            jobId={effectiveJobId}
            plotFiles={results?.plot_files}
            onOpen={onOpenPlot}
          />
        </div>
      )
    default:
      return null
  }
}

export default function ResultsPanel({ jobId, job, activeSection, onSection, loading = false, onJobUpdate }) {
  const results = job?.results
  const pending = Boolean(
    loading
    || job?.status === 'running'
    || (job && job.status !== 'completed' && job.status !== 'failed' && !results?.preview?.length),
  )
  const [lightbox, setLightbox] = useState(null)
  const [plotsDownloading, setPlotsDownloading] = useState(false)
  const [hypothesesExporting, setHypothesesExporting] = useState(null)
  const [selectedHypothesisIds, setSelectedHypothesisIds] = useState(() => new Set())
  const effectiveJobId = jobId || job?.job_id || job?.id
  const plotFiles = results?.plot_files || []
  const textContent = sectionTextContent(activeSection, results)
  const hypothesisItems = results?.hypotheses || []
  const hypothesisIdsKey = hypothesisItems.map((item) => item.id).join(',')
  const canExportHypotheses = Boolean(hypothesisItems.length || results?.hypotheses_raw)
  const canAddHypothesis = Boolean(effectiveJobId && job && job.status !== 'running' && job.status !== 'pending')
  const selectionJobRef = useRef(null)
  const prevHypothesisIdsRef = useRef('')

  useEffect(() => {
    const parseIds = (key) => key.split(',').filter(Boolean).map((id) => {
      const numeric = Number(id)
      return Number.isNaN(numeric) ? id : numeric
    })
    const allIds = parseIds(hypothesisIdsKey)
    const jobChanged = selectionJobRef.current !== effectiveJobId
    const previousIds = new Set(parseIds(prevHypothesisIdsRef.current))
    selectionJobRef.current = effectiveJobId
    prevHypothesisIdsRef.current = hypothesisIdsKey

    if (!effectiveJobId || !allIds.length) {
      setSelectedHypothesisIds(new Set())
      return
    }
    if (jobChanged) {
      setSelectedHypothesisIds(new Set(allIds))
      return
    }
    setSelectedHypothesisIds((prev) => {
      const valid = new Set(allIds)
      const next = new Set([...prev].filter((id) => valid.has(id)))
      allIds.forEach((id) => {
        if (!previousIds.has(id)) next.add(id)
      })
      return next
    })
  }, [effectiveJobId, hypothesisIdsKey])

  const handleDownloadAllPlots = async () => {
    if (!effectiveJobId || !plotFiles.length || plotsDownloading) return
    setPlotsDownloading(true)
    try {
      await downloadAllPlots(effectiveJobId)
    } catch (e) {
      window.alert(e.message || 'Не удалось скачать отчёт по графикам')
    } finally {
      setPlotsDownloading(false)
    }
  }

  const handleHypothesesExport = async (format) => {
    if (!effectiveJobId || hypothesesExporting) return
    if (hypothesisItems.length) {
      if (!selectedHypothesisIds.size) {
        window.alert('Выберите хотя бы одну гипотезу для экспорта')
        return
      }
      setHypothesesExporting(format)
      try {
        await exportHypotheses(effectiveJobId, [...selectedHypothesisIds], format)
      } catch (e) {
        window.alert(e.message || 'Не удалось экспортировать гипотезы')
      } finally {
        setHypothesesExporting(null)
      }
      return
    }

    const filename = format === 'xlsx' ? 'hypotheses_report.xlsx' : 'hypotheses_report.docx'
    await downloadArtifact(effectiveJobId, filename, 'Не удалось экспортировать гипотезы')
  }

  const toggleHypothesis = (id) => {
    setSelectedHypothesisIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <motion.section
      className="panel results-panel"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
    >
      <div className="results-layout">
        <nav className="results-nav">
          {RESULT_SECTIONS.filter((section) => (
            section.id !== 'relations' || (results?.table_count > 1) || (results?.tables?.length > 1)
          )).map((section) => {
            const Icon = RESULT_ICONS[section.icon] || Table2
            const hasData = sectionHasData(section.id, results)

            return (
              <button
                key={section.id}
                type="button"
                className={`nav-item ${activeSection === section.id ? 'active' : ''} ${hasData ? 'has-data' : ''}`}
                onClick={() => onSection(section.id)}
              >
                <Icon size={20} />
                <span>{section.label}</span>
                {hasData && <span className="nav-dot" />}
              </button>
            )
          })}
        </nav>

        <div className="results-content">
          <div className="content-toolbar">
            {textContent && <CopyButton text={textContent} />}

            {SECTION_DOWNLOADS.filter(
              (item) => item.section === activeSection && item.when(job, results),
            ).map((item) => (
              <button
                key={item.filename}
                type="button"
                className="download-btn"
                onClick={() => downloadArtifact(effectiveJobId, item.filename, `Не удалось скачать: ${item.label}`)}
                disabled={!effectiveJobId}
              >
                <Download size={14} />
                {item.label}
              </button>
            ))}

            {activeSection === 'hypotheses' && canExportHypotheses && (
              <>
                <button
                  type="button"
                  className="download-btn"
                  onClick={() => handleHypothesesExport('docx')}
                  disabled={!effectiveJobId || Boolean(hypothesesExporting) || (hypothesisItems.length > 0 && selectedHypothesisIds.size === 0)}
                >
                  {hypothesesExporting === 'docx' ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
                  {hypothesesExporting === 'docx' ? 'Формирование…' : 'Гипотезы DOCX'}
                </button>
                {hypothesisItems.length > 0 && (
                  <button
                    type="button"
                    className="download-btn"
                    onClick={() => handleHypothesesExport('xlsx')}
                    disabled={!effectiveJobId || Boolean(hypothesesExporting) || selectedHypothesisIds.size === 0}
                  >
                    {hypothesesExporting === 'xlsx' ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
                    {hypothesesExporting === 'xlsx' ? 'Формирование…' : 'Гипотезы XLSX'}
                  </button>
                )}
              </>
            )}

            {activeSection === 'plots' && plotFiles.length > 0 && (
              <button
                type="button"
                className="download-btn"
                onClick={handleDownloadAllPlots}
                disabled={plotsDownloading || !effectiveJobId}
              >
                {plotsDownloading ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
                {plotsDownloading ? 'Формирование…' : 'Отчёт по графикам DOCX'}
              </button>
            )}
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={activeSection}
              className="content-body"
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12 }}
              transition={{ duration: 0.2 }}
            >
              <ResultsContent
                activeSection={activeSection}
                results={results}
                effectiveJobId={effectiveJobId}
                onOpenPlot={setLightbox}
                pending={pending}
                selectedHypothesisIds={selectedHypothesisIds}
                onToggleHypothesis={toggleHypothesis}
                onSelectAllHypotheses={() => setSelectedHypothesisIds(new Set(hypothesisItems.map((item) => item.id)))}
                onSelectNoneHypotheses={() => setSelectedHypothesisIds(new Set())}
                canAddHypothesis={canAddHypothesis}
                onHypothesisAdded={(data) => onJobUpdate?.(data)}
              />
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      <AnimatePresence>
        {lightbox && (
          <motion.div
            className="lightbox"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setLightbox(null)}
          >
            <motion.img
              src={plotUrl(effectiveJobId, lightbox)}
              alt={lightbox}
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              onClick={(e) => e.stopPropagation()}
            />
            <div className="lightbox-actions" onClick={(e) => e.stopPropagation()}>
              <p>{lightbox}</p>
              <button
                type="button"
                className="download-btn lightbox-download"
                onClick={() => downloadPlot(effectiveJobId, lightbox)}
              >
                <Download size={14} />
                Скачать PNG
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.section>
  )
}
