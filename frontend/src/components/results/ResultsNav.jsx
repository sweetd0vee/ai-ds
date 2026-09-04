import { Table2 } from 'lucide-react'
import { RESULT_SECTIONS } from '../../constants'
import { RESULT_ICONS } from '../../utils/icons'
import { sectionHasData } from './sectionMeta'

export default function ResultsNav({ results, activeSection, onSection }) {
  const visible = RESULT_SECTIONS.filter((section) => (
    section.id !== 'relations' || (results?.table_count > 1) || (results?.tables?.length > 1)
  ))

  return (
    <nav className="results-nav">
      {visible.map((section) => {
        const Icon = RESULT_ICONS[section.icon] || Table2
        const hasData = sectionHasData(section.id, results)

        return (
          <button
            key={section.id}
            type="button"
            className={`nav-item ${activeSection === section.id ? 'active' : ''} ${hasData ? 'has-data' : ''}`}
            onClick={() => onSection(section.id)}
          >
            <Icon size={20} />
            <span>{section.label}</span>
            {hasData && <span className="nav-dot" />}
          </button>
        )
      })}
    </nav>
  )
}
