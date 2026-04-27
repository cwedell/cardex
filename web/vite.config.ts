import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/cardex/',
  optimizeDeps: {
    // onnxruntime-web manages its own WASM loading; exclude from Vite pre-bundling
    exclude: ['onnxruntime-web'],
  },
})
