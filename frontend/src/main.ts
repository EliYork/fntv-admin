import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { applyStoredTheme } from './stores/theme'
import './styles/main.css'

applyStoredTheme()

createApp(App).use(createPinia()).use(router).use(ElementPlus).mount('#app')
