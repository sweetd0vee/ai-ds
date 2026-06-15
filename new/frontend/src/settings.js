const STORAGE_KEY = 'ds-app-settings'

const LIGHT_THEMES = new Set(['light', 'ocean'])

export const THEMES = [
  { id: 'light', label: 'Светлая' },
  { id: 'dark', label: 'Тёмная' },
  { id: 'ocean', label: 'Океан' },
  { id: 'dracula', label: 'Dracula' },
  { id: 'nord', label: 'Nord' },
  { id: 'solarized', label: 'Solarized' },
  { id: 'catppuccin', label: 'Catppuccin' },
  { id: 'monokai', label: 'Monokai' },
]

const DEFAULT_ANALYST_MODEL = 'qwen3:8b'

const DEFAULT_SETTINGS = {
  theme: 'light',
  analystModel: DEFAULT_ANALYST_MODEL,
}

export function loadSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...DEFAULT_SETTINGS }
    const parsed = JSON.parse(raw)
    return {
      theme: THEMES.some((t) => t.id === parsed.theme) ? parsed.theme : DEFAULT_SETTINGS.theme,
      analystModel: parsed.analystModel || DEFAULT_SETTINGS.analystModel,
    }
  } catch {
    return { ...DEFAULT_SETTINGS }
  }
}

export function saveSettings(settings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
}

export function applyTheme(theme) {
  const id = theme || 'light'
  document.documentElement.setAttribute('data-theme', id)
  document.documentElement.setAttribute('data-theme-mode', LIGHT_THEMES.has(id) ? 'light' : 'dark')
}

applyTheme(loadSettings().theme)
