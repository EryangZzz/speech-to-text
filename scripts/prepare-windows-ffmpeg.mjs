import { spawnSync } from 'node:child_process'

if (process.platform !== 'win32') {
  console.error('Windows packaging must run on Windows or in the Windows GitHub Actions job.')
  process.exit(1)
}

const result = spawnSync(
  'powershell.exe',
  [
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    'scripts/prepare-windows-ffmpeg.ps1',
  ],
  { stdio: 'inherit' },
)

process.exit(result.status ?? 1)
