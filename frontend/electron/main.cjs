/**
 * CommonJS entry kept for tooling that still points at electron/main.cjs
 * (older electron-builder invocations, external scripts). The real
 * implementation lives in electron/main.js as an ES module - the frontend
 * package is "type": "module", so a CommonJS main file cannot use `import`.
 * This shim just hands control to the ES module.
 */
import('./main.js').catch((err) => {
  console.error('[job-hunter-os] failed to start the main process:', err)
  process.exit(1)
})