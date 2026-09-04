import { AnimatePresence, motion } from 'framer-motion'
import { Download } from 'lucide-react'
import { downloadPlot, plotUrl } from '../../api'

export default function PlotLightbox({ jobId, filename, onClose }) {
  return (
    <AnimatePresence>
      {filename && (
        <motion.div
          className="lightbox"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.img
            src={plotUrl(jobId, filename)}
            alt={filename}
            initial={{ scale: 0.8 }}
            animate={{ scale: 1 }}
            onClick={(e) => e.stopPropagation()}
          />
          <div className="lightbox-actions" onClick={(e) => e.stopPropagation()}>
            <p>{filename}</p>
            <button
              type="button"
              className="download-btn lightbox-download"
              onClick={() => downloadPlot(jobId, filename)}
            >
              <Download size={14} />
              Скачать PNG
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
