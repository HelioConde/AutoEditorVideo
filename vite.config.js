import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // FFmpeg creates a Worker via import.meta.url; Vite's dependency optimizer
  // otherwise rewrites it to /node_modules/.vite/deps/worker.js (404).
  optimizeDeps: { exclude: ['@ffmpeg/ffmpeg', '@ffmpeg/util'] },
  // GitHub Pages publishes a project under /AutoEditorVideo/ (not the domain root).
  // Keep the local desktop build at / so its /api calls are unchanged.
  base: mode === 'web' ? '/AutoEditorVideo/' : '/',
  server: {
    host: '127.0.0.1',
    port: mode === 'web' ? 5174 : 5173,
    strictPort: true,
    ...(mode === 'web' ? {} : { proxy: { '/api': 'http://127.0.0.1:3011' } }),
  },
}));
