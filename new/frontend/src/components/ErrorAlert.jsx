import { motion } from 'framer-motion'
import { AlertCircle } from 'lucide-react'

export default function ErrorAlert({ message, variant = 'inline' }) {
  if (!message) return null

  const isHero = variant === 'hero'

  return (
    <motion.div
      className={`alert error${isHero ? ' hero-alert' : ''}`}
      initial={isHero ? { opacity: 0, y: 8 } : { opacity: 0, height: 0 }}
      animate={isHero ? { opacity: 1, y: 0 } : { opacity: 1, height: 'auto' }}
    >
      <AlertCircle size={18} />
      {message}
    </motion.div>
  )
}
