#!/usr/bin/env node
/**
 * Pre-packaging guard.
 *
 * electron-builder silently skips a missing extraResources source, which
 * produces an app whose backend is missing and that fails only at runtime.
 * This check runs automatically via the "predist" npm script.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(here, '..')
const backendDist = path.resolve(root, '../backend/dist/Job Hunter OS')

const exe = process.platform === 'win32' ? 'job-hunter-os.exe' : 'job-hunter-os'
const exePath = path.join(backendDist, exe)
const indexPath = path.resolve(root, 'dist/index.html')

const problems = []

if (!fs.existsSync(indexPath)) {
  problems.push(`Frontend bundle missing: ${indexPath}\n  Fix: npm run build`)
}

if (!fs.existsSync(exePath)) {
  problems.push(
    `Frozen backend missing: ${exePath}\n` +
      '  Fix: run the PyInstaller step for this platform first, e.g.\n' +
      '    macOS   : backend/packaging/build-macos.sh\n' +
      '    Windows : backend\\packaging\\build-windows.bat'
  )
}

if (problems.length > 0) {
  console.error('\nCannot package Job Hunter OS:\n')
  for (const p of problems) console.error(`  - ${p}`)
  console.error('')
  process.exit(1)
}

console.log('Pre-packaging checks passed.')
console.log(`  frontend : ${indexPath}`)
console.log(`  backend  : ${exePath}`)