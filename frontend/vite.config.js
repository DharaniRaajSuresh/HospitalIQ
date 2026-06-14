import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  optimizeDeps: { 
    include: ['jspdf', 'recharts', 'leaflet', 'react-leaflet'],
  },
  build: {
    // Optimize chunk splitting
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/') || id.includes('node_modules/react-router-dom')) return 'react-vendor';
          if (id.includes('node_modules/framer-motion') || id.includes('node_modules/lucide-react')) return 'ui-vendor';
          if (id.includes('node_modules/recharts')) return 'charts-vendor';
          if (id.includes('node_modules/leaflet') || id.includes('node_modules/react-leaflet')) return 'maps-vendor';
          if (id.includes('node_modules/clsx') || id.includes('node_modules/tailwind-merge')) return 'utils-vendor';
        },
      },
    },
    // Enable source maps for debugging
    sourcemap: true,
    // Minify CSS
    cssMinify: true,
    // Chunk size warning limit
    chunkSizeWarningLimit: 1000,
  },
  server: {
    port: 8510,
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
