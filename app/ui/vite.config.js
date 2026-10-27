import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Day-7 API runs on :8000; /v1 is proxied in dev so the UI stays same-origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/v1': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.js'],
  },
});
