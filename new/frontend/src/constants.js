export const PIPELINE_STEPS = [
  { id: 'preparing', label: 'Подготовка', icon: 'database' },
  { id: 'structure_analysis', label: 'Структура', icon: 'scan' },
  { id: 'data_insights', label: 'Качество', icon: 'shield' },
  { id: 'scientific_discovery', label: 'Инсайты', icon: 'sparkles' },
  { id: 'metrics_plan', label: 'План метрик', icon: 'list' },
  { id: 'metrics_calculation', label: 'Расчёт', icon: 'calculator' },
  { id: 'metrics_analysis', label: 'Анализ', icon: 'brain' },
  { id: 'hypotheses_generation', label: 'Гипотезы', icon: 'lightbulb' },
  { id: 'viz_generation', label: 'Графики', icon: 'palette' },
  { id: 'visualization', label: 'Отчёт', icon: 'chart' },
  { id: 'final_report', label: 'Сохранение', icon: 'file' },
  { id: 'completed', label: 'Готово', icon: 'check' },
]

export const RESULT_SECTIONS = [
  { id: 'preview', label: 'Данные', icon: 'table' },
  { id: 'structure', label: 'Структура', icon: 'layers' },
  { id: 'relations', label: 'Связи таблиц', icon: 'git-merge' },
  { id: 'insights', label: 'Инсайты', icon: 'shield' },
  { id: 'metrics_plan', label: 'Метрики', icon: 'list' },
  { id: 'calculation_code', label: 'Код', icon: 'terminal' },
  { id: 'metrics', label: 'Результаты', icon: 'hash' },
  { id: 'analysis', label: 'Анализ', icon: 'text' },
  { id: 'hypotheses', label: 'Гипотезы', icon: 'lightbulb' },
  { id: 'viz_code', label: 'Визуализация', icon: 'image' },
  { id: 'report', label: 'Отчёт', icon: 'file-text' },
  { id: 'plots', label: 'Графики', icon: 'bar-chart' },
]

export const PREVIEW_ROWS = 20

export const GRAPH_OPTIONS = [
  { value: 10, label: '10 — быстро' },
  { value: 15, label: '15 — сбалансировано' },
  { value: 20, label: '20 — рекомендуется' },
  { value: 30, label: '30 — подробно' },
]
