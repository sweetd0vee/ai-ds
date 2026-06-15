import React from 'react'
import ReactDOM from 'react-dom/client'
import sberbankFavicon from '../img/sberbank-favicon.png'
import './settings'
import App from './App'
import './index.css'
import './styles/theme-overrides.css'

const favicon = document.createElement('link')
favicon.rel = 'icon'
favicon.type = 'image/png'
favicon.href = sberbankFavicon
document.head.appendChild(favicon)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
