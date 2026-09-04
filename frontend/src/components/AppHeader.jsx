import { History, Settings, Sparkles } from 'lucide-react'

export default function AppHeader({ onOpenSettings, onOpenHistory }) {
  return (
    <header className="app-header">
      <div className="app-header-inner">
        <div className="app-header-brand">
          <div className="app-header-logo">
            <Sparkles size={24} strokeWidth={2} />
          </div>
          <span className="app-header-title">AI Data Analysis</span>
        </div>

        <div className="app-header-actions">
          <button
            type="button"
            className="app-header-settings"
            onClick={onOpenHistory}
            aria-label="История"
            title="История анализов"
          >
            <History size={22} strokeWidth={2} />
          </button>
          <button
            type="button"
            className="app-header-settings"
            onClick={onOpenSettings}
            aria-label="Настройки"
            title="Настройки"
          >
            <Settings size={22} strokeWidth={2} />
          </button>
        </div>
      </div>
    </header>
  )
}
