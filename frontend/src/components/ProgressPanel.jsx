import { motion } from 'framer-motion'
import ErrorAlert from './ErrorAlert'
import PipelineStepper from './PipelineStepper'
import StatsCards from './StatsCards'

const STATUS_LABEL = {
  running: 'Выполняется',
  completed: 'Завершено',
  failed: 'Ошибка',
}

export default function ProgressPanel({ job, results, elapsed }) {
  if (!job) return null

  return (
    <motion.section
      className="panel progress-panel"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="panel-header">
        <div>
          <h2>Прогресс анализа</h2>
          <p className="progress-msg">{job.message}</p>
        </div>
        <span className={`status-pill ${job.status}`}>
          {STATUS_LABEL[job.status] || 'Ошибка'}
        </span>
      </div>

      <StatsCards
        shape={results?.shape}
        tableCount={results?.table_count || results?.tables?.length}
        progress={job.progress}
        graphCount={job.graph_count}
        elapsed={elapsed}
      />

      <PipelineStepper
        currentStep={job.step}
        progress={job.progress}
        status={job.status}
      />

      {job.error && <ErrorAlert message={job.error} />}
    </motion.section>
  )
}
