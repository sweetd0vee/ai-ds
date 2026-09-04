import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import {
  downloadAllPlots,
  downloadJobFile,
  exportHypotheses,
} from '../../api'
import { useActiveTable } from '../../hooks/useActiveTable'
import CodeSandbox from '../CodeSandbox'
import AnalysisView from './AnalysisView'
import DatasetSwitcher from './DatasetSwitcher'
import HypothesesView from './HypothesesView'
import InsightsView from './InsightsView'
import MetricsPlanView from './MetricsPlanView'
import MetricsResultsView from './MetricsResultsView'
import PlotLightbox from './PlotLightbox'
import PlotsGallery from './PlotsGallery'
import PreviewView from './PreviewView'
import RelationsView from './RelationsView'
import ReportView from './ReportView'
import ResultsNav from './ResultsNav'
import ResultsToolbar from './ResultsToolbar'
import StructureView from './StructureView'
import { sectionTextContent } from './sectionMeta'

async function downloadArtifact(jobId, filename, errorLabel) {
  if (!jobId) return
  try {
    await downloadJobFile(jobId, filename)
  } catch (e) {
    window.alert(e.message || errorLabel)
  }
}

function BodyFill({ children }) {
  return <div className="content-body-fill">{children}</div>
}

function PlotsSection({ results, effectiveJobId, onOpenPlot }) {
  const tables = results?.tables || []
  const { items, active, activeId, setActiveId } = useActiveTable(tables)
  const plotFiles = (active?.plot_files?.length
    ? active.plot_files
    : (tables.length <= 1 ? results?.plot_files : active?.plot_files)) || []
  return (
    <div className="content-body-fill content-body-fill--scroll">
      <DatasetSwitcher items={items} value={activeId} onChange={setActiveId} />
      <PlotsGallery
        jobId={effectiveJobId}
        plotFiles={plotFiles.length ? plotFiles : results?.plot_files}
        onOpen={onOpenPlot}
      />
    </div>
  )
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
      return (
        <BodyFill>
          <MetricsResultsView results={results} />
        </BodyFill>
      )
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
        <PlotsSection
          results={results}
          effectiveJobId={effectiveJobId}
          onOpenPlot={onOpenPlot}
        />
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
        <ResultsNav
          results={results}
          activeSection={activeSection}
          onSection={onSection}
        />

        <div className="results-content">
          <ResultsToolbar
            job={job}
            results={results}
            activeSection={activeSection}
            textContent={textContent}
            effectiveJobId={effectiveJobId}
            onDownloadArtifact={(filename, errorLabel) => downloadArtifact(effectiveJobId, filename, errorLabel)}
            canExportHypotheses={canExportHypotheses}
            hypothesisItems={hypothesisItems}
            selectedHypothesisIds={selectedHypothesisIds}
            hypothesesExporting={hypothesesExporting}
            onExportHypotheses={handleHypothesesExport}
            plotFiles={plotFiles}
            plotsDownloading={plotsDownloading}
            onDownloadAllPlots={handleDownloadAllPlots}
          />

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

      <PlotLightbox
        jobId={effectiveJobId}
        filename={lightbox}
        onClose={() => setLightbox(null)}
      />
    </motion.section>
  )
}
