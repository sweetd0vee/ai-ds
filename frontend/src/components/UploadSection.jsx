import { AnimatePresence, motion } from 'framer-motion'
import { FileSpreadsheet, Plus, Upload, X } from 'lucide-react'
import { GRAPH_OPTIONS } from '../constants'
import { formatFileSize } from '../utils/format'

function fileKey(file) {
  return `${file.name}:${file.size}:${file.lastModified || 0}`
}

export default function UploadSection({
  files = [], dragOver, graphCount, loading, compact,
  onFiles, onDrop, onDragOver, onDragLeave,
  onAnalyze, onClear, onRemoveFile, onGraphCount, inputRef,
}) {
  const fromHistory = files.some((f) => f.fromHistory)
  const hasFiles = files.length > 0
  const totalSize = files.reduce((sum, f) => sum + (f.size || 0), 0)

  const openPicker = () => {
    if (fromHistory || loading) return
    inputRef.current?.click()
  }

  return (
    <motion.section className="upload-panel" layout>
      {!compact && (
        <motion.div
          className="upload-hero-header"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
        >
          <h1 className="upload-hero-title">Электронный Датасаентист</h1>
          <p className="upload-hero-subtitle">
            CSV или Excel — можно сразу несколько таблиц, связи между ними найдутся автоматически
          </p>
        </motion.div>
      )}

      {compact && (
        <div className="upload-compact-header">
          <Upload size={18} />
          <span>Данные</span>
        </div>
      )}

      <div
        className={`dropzone ${compact ? 'dropzone--compact' : 'dropzone--hero'} ${dragOver ? 'dragover' : ''} ${hasFiles ? 'has-file' : ''}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => !hasFiles && openPicker()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx"
          multiple
          onChange={(e) => {
            onFiles(e.target.files)
            e.target.value = ''
          }}
        />
        <AnimatePresence mode="wait">
          {hasFiles ? (
            <motion.div
              key="files"
              className="file-list"
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
            >
              {files.map((file, index) => (
                <div key={fileKey(file)} className="file-info">
                  <FileSpreadsheet size={compact ? 22 : 32} className="file-icon" />
                  <div className="file-meta">
                    <strong title={file.name}>{file.name}</strong>
                    <span>{file.fromHistory ? 'из истории' : formatFileSize(file.size)}</span>
                  </div>
                  {!loading && !fromHistory && (
                    <button
                      className="icon-btn"
                      onClick={() => onRemoveFile(index)}
                      title="Убрать файл"
                      type="button"
                    >
                      <X size={16} />
                    </button>
                  )}
                </div>
              ))}
              {!fromHistory && !loading && (
                <button type="button" className="file-add-btn" onClick={openPicker}>
                  <Plus size={16} />
                  Добавить таблицы
                </button>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              className="dropzone-empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Upload size={compact ? 32 : 56} className="dropzone-icon" />
              {!compact && <p className="dropzone-title">Перетащите файлы сюда</p>}
              <p className="dropzone-hint">
                {compact ? 'Файлы · .csv, .xlsx' : 'один или несколько · .csv, .xlsx'}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {hasFiles && !fromHistory && !compact && (
        <p className="upload-file-count">
          {files.length} {files.length === 1 ? 'файл' : files.length < 5 ? 'файла' : 'файлов'}
          {totalSize ? ` · ${formatFileSize(totalSize)}` : ''}
        </p>
      )}

      <div className={`options-row ${compact ? 'options-row--compact' : ''}`}>
        <label className="option-label">
          {compact ? 'Графики' : 'Количество графиков'}
          <select
            value={graphCount}
            onChange={(e) => onGraphCount(Number(e.target.value))}
            disabled={loading}
          >
            {GRAPH_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>
      </div>

      <motion.button
        className={`btn-primary ${compact ? 'btn-primary--compact' : 'btn-primary--hero'}`}
        disabled={!hasFiles || loading || fromHistory}
        onClick={onAnalyze}
        whileHover={{ scale: hasFiles && !loading ? 1.02 : 1 }}
        whileTap={{ scale: hasFiles && !loading ? 0.98 : 1 }}
        layout
      >
        {loading ? 'Анализ…' : compact ? 'Запустить' : 'Запустить анализ'}
      </motion.button>

      {!compact && (
        <motion.ul
          className="upload-hero-features"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <li>Несколько таблиц и связи между ними</li>
          <li>Структура, качество и корреляции</li>
          <li>Графики и итоговый отчёт</li>
        </motion.ul>
      )}
    </motion.section>
  )
}
