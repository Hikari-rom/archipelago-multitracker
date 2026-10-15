import { createApp } from 'vue'
import './theme.css'
import AppV2 from './AppV2.vue'
import { dispatch, start } from '../stores/tracker'
import { applyV2Theme, resolveTheme } from './lib/tokens'
import { loadThemeChoice } from './lib/prefs'

function loadMonoFont(): void {
  const l = document.createElement('link')
  l.rel = 'stylesheet'
  l.href = 'https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap'
  document.head.appendChild(l)
}

applyV2Theme(resolveTheme(loadThemeChoice(), matchMedia('(prefers-color-scheme: dark)').matches))
loadMonoFont()
if (import.meta.env.VITE_MOCK === '1') {
  void import('../mock/install').then((m) => {
    m.installMockMode(dispatch)
    createApp(AppV2).mount('#app')
  })
} else {
  createApp(AppV2).mount('#app')
  void start()
}
