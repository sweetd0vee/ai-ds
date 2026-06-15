import { motion } from 'framer-motion'
import { Download } from 'lucide-react'
import { downloadPlot, plotUrl } from '../../api'

export default function PlotsGallery({ jobId, plotFiles, onOpen }) {
  const handleDownload = async (e, name) => {
    e.stopPropagation()
    try {
      await downloadPlot(jobId, name)
    } catch {
      window.open(plotUrl(jobId, name), '_blank')
    }
  }

  if (!plotFiles?.length) {
    return (
      <div className="table-scroll table-scroll--empty">
        <div className="empty">Графики появятся после визуализации</div>
      </div>
    )
  }

  return (
    <div className="plots-masonry">
      {plotFiles.map((name, i) => (
        <motion.div
          key={name}
          className="plot-item"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: i * 0.03 }}
          onClick={() => onOpen(name)}
        >
          <div className="plot-item-media">
            <img src={plotUrl(jobId, name)} alt={name} loading="lazy" />
            <button
              type="button"
              className="plot-download-btn"
              title="Скачать PNG"
              aria-label={`Скачать ${name}`}
              onClick={(e) => handleDownload(e, name)}
            >
              <Download size={16} />
            </button>
          </div>
          <span>{name}</span>
        </motion.div>
      ))}
    </div>
  )
}
