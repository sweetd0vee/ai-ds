import { motion } from 'framer-motion'
import { Database, Loader2 } from 'lucide-react'
import { PIPELINE_STEPS } from '../constants'
import { PIPELINE_ICONS } from '../utils/icons'

function stepIndex(stepId) {
  const idx = PIPELINE_STEPS.findIndex((s) => s.id === stepId)
  return idx === -1 ? 0 : idx
}

export default function PipelineStepper({ currentStep, progress, status }) {
  const currentIdx = stepIndex(currentStep)
  const isFailed = status === 'failed'

  return (
    <div className="pipeline-stepper">
      <div className="pipeline-track">
        <motion.div
          className="pipeline-track-fill"
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>
      <div className="pipeline-steps">
        {PIPELINE_STEPS.map((step, idx) => {
          const Icon = PIPELINE_ICONS[step.icon] || Database
          const isDone = idx < currentIdx || currentStep === 'completed'
          const isActive = idx === currentIdx && status === 'running'
          const isError = isFailed && idx === currentIdx

          return (
            <motion.div
              key={step.id}
              className={`pipeline-step ${isDone ? 'done' : ''} ${isActive ? 'active' : ''} ${isError ? 'error' : ''}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.03 }}
            >
              <div className="step-icon-wrap">
                {isActive ? <Loader2 size={18} className="spin" /> : <Icon size={18} />}
              </div>
              <span className="step-label">{step.label}</span>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
