const API_BASE = '/api'

function parseApiDetail(detail, fallback) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg || String(d)).join(', ')
  return fallback
}

function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export async function fetchConfig() {
  const res = await fetch(`${API_BASE}/config`)
  if (!res.ok) throw new Error('Не удалось загрузить настройки сервера')
  return res.json()
}

export async function startAnalysis(file, graphCount = 20, analystModel) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('graph_count', String(graphCount))
  if (analystModel) formData.append('analyst_model', analystModel)

  let res
  try {
    res = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      body: formData,
    })
  } catch {
    throw new Error('Сервер недоступен. Запустите backend: cd new/backend && python run_dev.py')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(parseApiDetail(err.detail, `Ошибка сервера (${res.status})`) || 'Ошибка запуска анализа')
  }

  return res.json()
}

export async function getJobStatus(jobId) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`)
  if (!res.ok) throw new Error('Не удалось получить статус задачи')
  return res.json()
}

export async function fetchJobHistory() {
  const res = await fetch(`${API_BASE}/jobs`)
  if (!res.ok) throw new Error('Не удалось загрузить историю анализов')
  const data = await res.json()
  return data.jobs || []
}

export async function deleteHistoryJob(jobId) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(parseApiDetail(err.detail, 'Не удалось удалить запись'))
  }
  return res.json()
}

export async function clearHistory() {
  const res = await fetch(`${API_BASE}/jobs`, { method: 'DELETE' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(parseApiDetail(err.detail, 'Не удалось очистить историю'))
  }
  return res.json()
}

export function streamJobStatus(jobId, onUpdate, onError) {
  const source = new EventSource(`${API_BASE}/jobs/${jobId}/stream`)

  source.onmessage = (event) => {
    try {
      onUpdate(JSON.parse(event.data))
    } catch (e) {
      onError?.(e)
    }
  }

  source.onerror = () => {
    onError?.(new Error('Соединение с сервером прервано'))
  }

  return () => source.close()
}

export function plotUrl(jobId, filename) {
  return `${API_BASE}/jobs/${jobId}/plots/${filename}`
}

export async function downloadPlot(jobId, filename) {
  const res = await fetch(plotUrl(jobId, filename))
  if (!res.ok) throw new Error('Не удалось скачать график')
  triggerBlobDownload(await res.blob(), filename)
}

function downloadUrl(jobId, filename) {
  return `${API_BASE}/jobs/${jobId}/download/${filename}`
}

export async function downloadAllPlots(jobId) {
  await downloadJobFile(jobId, 'plots_report.docx')
}

export async function downloadJobFile(jobId, filename) {
  if (!jobId) throw new Error('Задача не найдена')
  const res = await fetch(downloadUrl(jobId, filename))
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(parseApiDetail(err.detail, `Не удалось скачать файл (${res.status})`))
  }
  triggerBlobDownload(await res.blob(), filename)
}

export async function exportHypotheses(jobId, ids, format = 'xlsx') {
  if (!jobId) throw new Error('Задача не найдена')
  const filename = format === 'docx' ? 'hypotheses_report.docx' : 'hypotheses_report.xlsx'
  const res = await fetch(`${API_BASE}/jobs/${jobId}/hypotheses/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids, format }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(parseApiDetail(err.detail, `Не удалось скачать файл (${res.status})`))
  }
  triggerBlobDownload(await res.blob(), filename)
}

export async function runSandboxCode(jobId, code) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/run-code`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  })

  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    throw new Error(parseApiDetail(data.detail, 'Ошибка выполнения кода'))
  }

  return data
}
