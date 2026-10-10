import { createApp } from 'vue'
import App from './App.vue'
import './style.css'
import { dispatch, start } from './stores/tracker'

createApp(App).mount('#app')

if (import.meta.env.VITE_MOCK === '1') {
  void import('./mock/install').then((m) => {
    m.installMockMode(dispatch)
  })
} else {
  void start()
}
