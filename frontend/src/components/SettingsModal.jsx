import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { THEMES } from '../settings'

export default function SettingsModal({
  open,
  draft,
  models,
  modelsLoading,
  onChange,
  onSave,
  onCancel,
}) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="settings-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onCancel}
        >
          <motion.div
            className="settings-modal"
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ duration: 0.2 }}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-labelledby="settings-title"
            aria-modal="true"
          >
            <div className="settings-modal-header">
              <h2 id="settings-title">Настройки</h2>
              <button type="button" className="settings-close" onClick={onCancel} aria-label="Закрыть">
                <X size={20} />
              </button>
            </div>

            <div className="settings-modal-body">
              <fieldset className="settings-field">
                <legend>Тема оформления</legend>
                <div className="settings-theme-grid">
                  {THEMES.map((theme) => (
                    <label
                      key={theme.id}
                      className={`settings-theme-option ${draft.theme === theme.id ? 'active' : ''}`}
                    >
                      <input
                        type="radio"
                        name="theme"
                        value={theme.id}
                        checked={draft.theme === theme.id}
                        onChange={() => onChange({ theme: theme.id })}
                      />
                      <span className={`settings-theme-preview settings-theme-preview--${theme.id}`} />
                      <span>{theme.label}</span>
                    </label>
                  ))}
                </div>
              </fieldset>

              <fieldset className="settings-field">
                <legend>LLM-модель для анализа данных</legend>
                <p className="settings-hint">
                  Используется для интерпретации метрик (Ollama). Применяется к следующему запуску анализа.
                </p>
                <select
                  className="settings-select"
                  value={draft.analystModel}
                  onChange={(e) => onChange({ analystModel: e.target.value })}
                  disabled={modelsLoading}
                >
                  {(models.length ? models : [draft.analystModel]).map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </fieldset>
            </div>

            <div className="settings-modal-footer">
              <button type="button" className="settings-btn settings-btn--ghost" onClick={onCancel}>
                Отмена
              </button>
              <button type="button" className="settings-btn settings-btn--primary" onClick={onSave}>
                Сохранить
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
