import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@picovoice/web-voice-processor': path.resolve(__dirname, 'node_modules/@picovoice/web-voice-processor/dist/esm/index.js'),
      '@picovoice/porcupine-web': path.resolve(__dirname, 'node_modules/@picovoice/porcupine-web/dist/esm/index.js'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
  },
});
