import { AnimatePresence, motion } from 'framer-motion'
import { FileSpreadsheet, Upload, X } from 'lucide-react'
import { GRAPH_OPTIONS } from '../constants'
import { formatFileSize } from '../utils/format'

export default function UploadSection({
  file, dragOver, graphCount, loading, compact,
  onFile, onDrop, onDragOver, onDragLeave,
  onAnalyze, onClear, onGraphCount, inputRef,
}) {
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
            CSV или Excel — перетащите файл или выберите вручную
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
        className={`dropzone ${compact ? 'dropzone--compact' : 'dropzone--hero'} ${dragOver ? 'dragover' : ''} ${file ? 'has-file' : ''}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => !file && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx"
          onChange={(e) => onFile(e.target.files[0])}
        />
        <AnimatePresence mode="wait">
          {file ? (
            <motion.div
              key="file"
              className="file-info"
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
            >
              <FileSpreadsheet size={compact ? 28 : 40} className="file-icon" />
              <div className="file-meta">
                <strong title={file.name}>{file.name}</strong>
                <span>{file.fromHistory ? 'из истории' : formatFileSize(file.size)}</span>
              </div>
              {!loading && (
                <button className="icon-btn" onClick={onClear} title="Убрать файл" type="button">
                  <X size={18} />
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
              {!compact && <p className="dropzone-title">Перетащите файл сюда</p>}
              <p className="dropzone-hint">
                {compact ? 'Файл · .csv, .xlsx' : 'или нажмите для выбора · .csv, .xlsx'}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

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
        disabled={!file || loading || file.fromHistory}
        onClick={onAnalyze}
        whileHover={{ scale: file && !loading ? 1.02 : 1 }}
        whileTap={{ scale: file && !loading ? 0.98 : 1 }}
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
          <li>Структура и качество данных</li>
          <li>Метрики и корреляции</li>
          <li>Графики и итоговый отчёт</li>
        </motion.ul>
      )}
    </motion.section>
  )
}
