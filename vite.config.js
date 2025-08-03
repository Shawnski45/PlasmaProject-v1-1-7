import { defineConfig } from 'vite';
import { resolve } from 'path';
import { fileURLToPath } from 'url';

// Path to your static files
const staticPath = resolve(fileURLToPath(import.meta.url), '../app/static');

// https://vitejs.dev/config/
export default defineConfig({
  // Root directory for the project
  root: __dirname,
  
  // Base public path when served in development or production
  base: '/static/',
  
  // Development server configuration
  server: {
    port: 3001,
    strictPort: true,
    cors: true,
    host: '0.0.0.0',
    
    // Configure HMR for Flask templates
    hmr: {
      protocol: 'ws',
      host: 'localhost',
      port: 3001, // Match the server port
      path: '/vite-hmr',
    },
    
    // Proxy configuration for API requests
    proxy: {
      // Proxy API requests to Flask backend
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      
      // Handle Vite's HMR
      '/vite-hmr': {
        target: 'ws://localhost:3001',
        ws: true,
      },
      
      // Proxy all other requests to Flask
      '^/(?!static/).*': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
  
  // Build configuration
  build: {
    outDir: resolve(staticPath, 'dist'),
    assetsDir: '',
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: {
        main: resolve(staticPath, 'js/main.js'),
        styles: resolve(staticPath, 'css/input.css'),
      },
      output: {
        entryFileNames: 'js/[name].[hash].js',
        chunkFileNames: 'js/[name].[hash].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name.endsWith('.css')) {
            return 'css/[name].[hash][extname]';
          }
          return 'assets/[name].[hash][extname]';
        },
      },
    },
  },
  
  // CSS configuration
  css: {
    devSourcemap: true,
    postcss: {
      plugins: [
        require('tailwindcss'),
        require('autoprefixer'),
      ],
    },
  },
  
  // Resolve configuration
  resolve: {
    alias: {
      '@': resolve(staticPath, 'js'),
    },
  },
});