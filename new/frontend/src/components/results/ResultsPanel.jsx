import { AnimatePresence, motion } from 'framer-motion'
import { Download, Table2 } from 'lucide-react'
import { useState } from 'react'
import {
  downloadAllPlots,
  downloadJobFile,
  downloadPlot,
  downloadUrl,
  plotUrl,
} from '../../api'
import { PREVIEW_ROWS, RESULT_SECTIONS } from '../../constants'
import { RESULT_ICONS } from '../../utils/icons'
import CodeSandbox from '../CodeSandbox'
import AnalysisView from './AnalysisView'
import HypothesesView from './HypothesesView'
import CopyButton from './CopyButton'
import InsightsView from './InsightsView'
import MetricsPlanView from './MetricsPlanView'
import PlotsGallery from './PlotsGallery'
import PreviewTable from './PreviewTable'
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

function ResultsContent({ activeSection, results, jobId, effectiveJobId, onOpenPlot }) {
  switch (activeSection) {
    case 'preview':
      return (
        <div className="content-body-fill">
          {results?.shape && (
            <p className="preview-meta">
              {results.shape[0]} строк × {results.shape[1]} столбцов · первые {PREVIEW_ROWS} записей
            </p>
          )}
          <PreviewTable preview={results?.preview} columns={results?.columns} />
        </div>
      )
    case 'structure':
      return (
        <div className="content-body-fill">
          <StructureView results={results} />
        </div>
      )
    case 'insights':
      return (
        <div className="content-body-fill">
          <InsightsView results={results} />
        </div>
      )
    case 'metrics_plan':
      return (
        <div className="content-body-fill">
          <MetricsPlanView results={results} />
        </div>
      )
    case 'calculation_code':
      return (
        <div className="content-body-fill">
          <CodeSandbox jobId={jobId} defaultCode={results?.calculation_code} />
        </div>
      )
    case 'metrics':
      return <pre className="code-view">{results?.metrics_results_raw || 'Ожидание…'}</pre>
    case 'analysis':
      return (
        <div className="content-body-fill">
          <AnalysisView text={results?.analysis_summary} />
        </div>
      )
    case 'hypotheses':
      return (
        <div className="content-body-fill">
          <HypothesesView results={results} />
        </div>
      )
    case 'viz_code':
      return <pre className="code-view">{results?.viz_code || 'Ожидание…'}</pre>
    case 'report':
      return (
        <div className="content-body-fill">
          <ReportView text={results?.final_report} />
        </div>
      )
    case 'plots':
      return (
        <div className="content-body-fill">
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

export default function ResultsPanel({ jobId, job, activeSection, onSection }) {
  const results = job?.results
  const [lightbox, setLightbox] = useState(null)
  const effectiveJobId = jobId || job?.job_id || job?.id
  const plotFiles = results?.plot_files || []
  const textContent = sectionTextContent(activeSection, results)

  const handleDownloadAllPlots = async () => {
    if (!effectiveJobId || !plotFiles.length) return
    try {
      await downloadAllPlots(effectiveJobId, plotFiles)
    } catch {
      /* ignore */
    }
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
          {RESULT_SECTIONS.map((section) => {
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

            {activeSection === 'insights' && job?.status === 'completed' && (
              <>
                <a className="download-btn" href={downloadUrl(effectiveJobId, 'quality_report.txt')} download>
                  <Download size={14} />
                  Качество TXT
                </a>
                <a className="download-btn" href={downloadUrl(effectiveJobId, 'correlations.txt')} download>
                  <Download size={14} />
                  Связи TXT
                </a>
              </>
            )}

            {activeSection === 'analysis' && results?.analysis_summary && (
              <button
                type="button"
                className="download-btn"
                onClick={() => downloadArtifact(effectiveJobId, 'analysis_summary_report.docx', 'Не удалось скачать анализ')}
                disabled={!effectiveJobId}
              >
                <Download size={14} />
                Анализ DOCX
              </button>
            )}

            {activeSection === 'hypotheses' && (results?.hypotheses?.length || results?.hypotheses_raw) && (
              <>
                <a
                  className="download-btn"
                  href={downloadUrl(effectiveJobId, 'hypotheses_report.txt')}
                  download
                >
                  <Download size={14} />
                  Гипотезы TXT
                </a>
                <button
                  type="button"
                  className="download-btn"
                  onClick={() => downloadArtifact(effectiveJobId, 'hypotheses_report.docx', 'Не удалось скачать гипотезы')}
                  disabled={!effectiveJobId}
                >
                  <Download size={14} />
                  Гипотезы DOCX
                </button>
              </>
            )}

            {activeSection === 'structure' && results?.data_structure?.columns?.length > 0 && (
              <button
                type="button"
                className="download-btn"
                onClick={() => downloadArtifact(effectiveJobId, 'data_structure.xlsx', 'Не удалось скачать структуру')}
                disabled={!effectiveJobId}
              >
                <Download size={14} />
                Структура XLSX
              </button>
            )}

            {activeSection === 'plots' && plotFiles.length > 0 && (
              <button type="button" className="download-btn" onClick={handleDownloadAllPlots}>
                <Download size={14} />
                Скачать все графики
              </button>
            )}

            {activeSection === 'report' && job?.status === 'completed' && (
              <button
                type="button"
                className="download-btn"
                onClick={() => downloadArtifact(effectiveJobId, 'final_report.docx', 'Не удалось скачать отчёт')}
                disabled={!effectiveJobId}
              >
                <Download size={14} />
                Отчёт DOCX
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
                jobId={jobId}
                effectiveJobId={effectiveJobId}
                onOpenPlot={setLightbox}
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
