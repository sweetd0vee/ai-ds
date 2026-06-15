import { motion } from 'framer-motion'
import { BarChart3, Columns3, Rows3, Timer } from 'lucide-react'

export default function StatsCards({ shape, progress, graphCount, elapsed }) {
  const cards = [
    { icon: Rows3, label: 'Строк', value: shape?.[0] ?? '—' },
    { icon: Columns3, label: 'Столбцов', value: shape?.[1] ?? '—' },
    { icon: BarChart3, label: 'Графиков', value: graphCount ?? '—' },
    { icon: Timer, label: 'Прогресс', value: progress != null ? `${progress}%` : '—' },
  ]

  if (elapsed) {
    cards[3] = { icon: Timer, label: 'Время', value: elapsed }
  }

  return (
    <div className="stats-grid">
      {cards.map((card, i) => (
        <motion.div
          key={card.label}
          className="stat-card"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: i * 0.05 }}
        >
          <card.icon size={24} className="stat-icon" />
          <div>
            <span className="stat-value">{card.value}</span>
            <span className="stat-label">{card.label}</span>
          </div>
        </motion.div>
      ))}
    </div>
  )
}
