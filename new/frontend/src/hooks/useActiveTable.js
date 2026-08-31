import { useEffect, useMemo, useState } from 'react'

export function tableLabel(table) {
  if (!table) return ''
  if (table.sheet && table.filename) return `${table.filename} / ${table.sheet}`
  return table.label || table.name || table.filename || table.id || ''
}

export function useActiveTable(tables) {
  const items = useMemo(
    () => (tables || []).map((table) => ({
      ...table,
      label: tableLabel(table),
    })),
    [tables],
  )

  const [activeId, setActiveId] = useState(items[0]?.id)

  useEffect(() => {
    if (!items.some((item) => item.id === activeId)) {
      setActiveId(items[0]?.id)
    }
  }, [items, activeId])

  const active = items.find((item) => item.id === activeId) || items[0] || null
  return { items, active, activeId, setActiveId }
}
