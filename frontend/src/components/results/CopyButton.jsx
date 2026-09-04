import { Check, Copy } from 'lucide-react'
import { useState } from 'react'

export default function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button type="button" className="copy-btn" onClick={copy} title="Копировать">
      {copied ? <Check size={14} /> : <Copy size={14} />}
      {copied ? 'Скопировано' : 'Копировать'}
    </button>
  )
}
