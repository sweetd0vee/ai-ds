export function sectionHasData(sectionId, results) {
  if (!results) return false

  const checks = {
    preview: results.preview || results.tables?.length,
    structure: results.data_structure || results.parsed_data_structure || results.data_structure_raw
      || results.tables?.some((t) => t.structure) || results.tables?.length,
    relations: (results.tables?.length > 1) || results.relations,
    insights: results.quality_report || results.discovery
      || results.tables?.some((t) => t.quality_report || t.discovery),
    metrics_plan: results.metrics_plan_dict
      || results.tables?.some((t) => t.metrics_plan_dict && Object.keys(t.metrics_plan_dict).length),
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

  if (sectionId === 'relations') {
    return results.relations_raw || null
  }

  if (sectionId === 'insights') {
    const combined = results.insights_report_raw
    if (combined) return combined
    const discovery = results.discovery_raw || results.discovery_brief
    const { quality_report_raw: quality, correlations_raw: correlations } = results
    if (quality && correlations) {
      return discovery ? `${quality}\n\n${correlations}\n\n${discovery}` : `${quality}\n\n${correlations}`
    }
    return quality || correlations || discovery || null
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
          h.kind_label ? `Тип: ${h.kind_label}` : '',
        ].join('\n')).join('\n\n')
      : results.hypotheses_raw,
    report: results.final_report,
  }

  return fields[sectionId] ?? null
}
