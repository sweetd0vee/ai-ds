import { useCallback, useEffect, useState } from 'react'
import { loadSettings, saveSettings, applyTheme } from '../settings'

export function useSettings() {
  const [settings, setSettings] = useState(() => loadSettings())
  const [modalOpen, setModalOpen] = useState(false)
  const [draft, setDraft] = useState(settings)

  useEffect(() => {
    applyTheme(settings.theme)
  }, [settings.theme])

  const openSettings = useCallback(() => {
    setDraft(settings)
    setModalOpen(true)
  }, [settings])

  const closeSettings = useCallback(() => {
    setModalOpen(false)
    setDraft(settings)
    applyTheme(settings.theme)
  }, [settings])

  const saveDraft = useCallback(() => {
    saveSettings(draft)
    setSettings(draft)
    applyTheme(draft.theme)
    setModalOpen(false)
  }, [draft])

  const updateDraft = useCallback((patch) => {
    setDraft((prev) => {
      const next = { ...prev, ...patch }
      if (patch.theme) applyTheme(patch.theme)
      return next
    })
  }, [])

  return {
    settings,
    draft,
    modalOpen,
    openSettings,
    closeSettings,
    saveDraft,
    updateDraft,
  }
}
