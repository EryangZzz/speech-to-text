import { spawnSync } from 'node:child_process'

const mode = process.argv[2]
const target = process.argv[3]

if (!mode || !target) {
  console.error('Usage: node scripts/build-tauri.mjs <mode> <target>')
  process.exit(1)
}

function runOrExit(command, args, options = {}) {
  const result = spawnSync(command, args, {
    stdio: 'inherit',
    shell: process.platform === 'win32',
    ...options,
  })

  if (result.error) {
    console.error(`Failed to start command: ${command}`)
    console.error(result.error.message)
    process.exit(1)
  }

  if (result.status !== 0) {
    process.exit(result.status ?? 1)
  }
}

runOrExit(process.execPath, ['scripts/configure-tauri.mjs', mode])

const generatedConfig = `src-tauri/gen/tauri.bundle.${mode}.json`
runOrExit(
  process.platform === 'win32' ? 'npm.cmd' : 'npm',
  ['run', 'tauri', '--', 'build', '--config', generatedConfig, '--target', target],
  { shell: process.platform === 'win32' },
)
