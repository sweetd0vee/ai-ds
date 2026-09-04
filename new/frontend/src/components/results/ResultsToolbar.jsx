import { Download, Loader2 } from 'lucide-react'
import CopyButton from './CopyButton'

export const SECTION_DOWNLOADS = [
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

export default function ResultsToolbar({
  job,
  results,
  activeSection,
  textContent,
  effectiveJobId,
  onDownloadArtifact,
  canExportHypotheses,
  hypothesisItems,
  selectedHypothesisIds,
  hypothesesExporting,
  onExportHypotheses,
  plotFiles,
  plotsDownloading,
  onDownloadAllPlots,
}) {
  return (
    <div className="content-toolbar">
      {textContent && <CopyButton text={textContent} />}

      {SECTION_DOWNLOADS.filter(
        (item) => item.section === activeSection && item.when(job, results),
      ).map((item) => (
        <button
          key={item.filename}
          type="button"
          className="download-btn"
          onClick={() => onDownloadArtifact(item.filename, `Не удалось скачать: ${item.label}`)}
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
            onClick={() => onExportHypotheses('docx')}
            disabled={!effectiveJobId || Boolean(hypothesesExporting) || (hypothesisItems.length > 0 && selectedHypothesisIds.size === 0)}
          >
            {hypothesesExporting === 'docx' ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
            {hypothesesExporting === 'docx' ? 'Формирование…' : 'Гипотезы DOCX'}
          </button>
          {hypothesisItems.length > 0 && (
            <button
              type="button"
              className="download-btn"
              onClick={() => onExportHypotheses('xlsx')}
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
          onClick={onDownloadAllPlots}
          disabled={plotsDownloading || !effectiveJobId}
        >
          {plotsDownloading ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
          {plotsDownloading ? 'Формирование…' : 'Отчёт по графикам DOCX'}
        </button>
      )}
    </div>
  )
}
