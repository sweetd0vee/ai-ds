export function sectionHasData(sectionId, results) {
  if (!results) return false

  const checks = {
    preview: results.preview,
    structure: results.data_structure || results.data_structure_raw,
    insights: results.quality_report,
    metrics_plan: results.metrics_plan_dict,
    calculation_code: results.calculation_code,
    metrics: results.metrics_results_raw,
    analysis: results.analysis_summary,
    hypotheses: results.hypotheses?.length || results.hypotheses_raw,
    viz_code: results.viz_code,
    report: results.final_report,
    plots: results.plot_files?.length,
  }

  return Boolean(checks[sectionId])
}

export function sectionTextContent(sectionId, results) {
  if (!results) return null

  if (sectionId === 'insights') {
    const combined = results.insights_report_raw
    if (combined) return combined
    const { quality_report_raw: quality, correlations_raw: correlations } = results
    if (quality && correlations) return `${quality}\n\n${correlations}`
    return quality || correlations || null
  }

  const fields = {
    calculation_code: results.calculation_code,
    metrics: results.metrics_results_raw,
    viz_code: results.viz_code,
    analysis: results.analysis_summary,
    hypotheses: results.hypotheses?.length
      ? results.hypotheses.map((h) => [
          `${h.id}. ${h.title}`,
          `Формулировка: ${h.statement}`,
          `Основание: ${h.rationale}`,
          `Столбцы: ${(h.columns || []).join(', ')}`,
          `Как проверить: ${h.verification}`,
          `Приоритет: ${h.priority_label || h.priority}`,
        ].join('\n')).join('\n\n')
      : results.hypotheses_raw,
    report: results.final_report,
  }

  return fields[sectionId] ?? null
}
