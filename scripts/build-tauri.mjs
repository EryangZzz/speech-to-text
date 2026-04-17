import { spawnSync } from 'node:child_process'

const mode = process.argv[2]
const target = process.argv[3]

if (!mode || !target) {
  console.error('Usage: node scripts/build-tauri.mjs <mode> <target>')
  process.exit(1)
}

const nodeRunner = process.platform === 'win32' ? 'node.exe' : 'node'
const prepare = spawnSync(nodeRunner, ['scripts/configure-tauri.mjs', mode], {
  stdio: 'inherit',
})

if (prepare.status !== 0) {
  process.exit(prepare.status ?? 1)
}

const generatedConfig = `src-tauri/gen/tauri.bundle.${mode}.json`
const npmRunner = process.platform === 'win32' ? 'npm.cmd' : 'npm'
const build = spawnSync(
  npmRunner,
  ['run', 'tauri', '--', 'build', '--config', generatedConfig, '--target', target],
  { stdio: 'inherit' },
)

process.exit(build.status ?? 1)
