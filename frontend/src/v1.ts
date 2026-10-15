import { createApp } from 'vue'
import App from './App.vue'
import './style.css'
import { applyTheme, loadTheme } from './lib/theme'
import { dispatch, start } from './stores/tracker'

applyTheme(loadTheme())
if (import.meta.env.VITE_MOCK === '1') {
  void import('./mock/install').then((m) => {
    m.installMockMode(dispatch)
    createApp(App).mount('#app')
  })
} else {
  createApp(App).mount('#app')
  void start()
}
