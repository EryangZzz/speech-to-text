import fs from 'node:fs'
import path from 'node:path'

const mode = process.argv[2] || process.env.BUNDLE_MODE || 'macos-arm64'
const root = process.cwd()
const configPath = path.join(root, 'src-tauri', 'tauri.conf.json')
const raw = fs.readFileSync(configPath, 'utf8')
const config = JSON.parse(raw)

const bundleByMode = {
  'macos-arm64': {
    resources: {
      'resources/ffmpeg-macos-arm64': 'resources/ffmpeg-macos-arm64',
    },
    targets: ['dmg'],
  },
  'macos-x64': {
    resources: {
      'resources/ffmpeg-macos-x64': 'resources/ffmpeg-macos-x64',
    },
    targets: ['dmg'],
  },
  'macos-universal': {
    resources: {
      'resources/ffmpeg-macos-arm64': 'resources/ffmpeg-macos-arm64',
      'resources/ffmpeg-macos-x64': 'resources/ffmpeg-macos-x64',
    },
    targets: ['dmg'],
  },
  'windows-x64': {
    resources: {
      'resources/ffmpeg-windows-x64.exe': 'resources/ffmpeg-windows-x64.exe',
    },
    targets: ['nsis'],
  },
}

const selected = bundleByMode[mode]
if (!selected) {
  console.error(`Unknown bundle mode: ${mode}`)
  process.exit(1)
}

for (const rel of Object.keys(selected.resources)) {
  const abs = path.join(root, 'src-tauri', rel)
  if (!fs.existsSync(abs)) {
    console.error(`Missing resource for ${mode}: ${abs}`)
    process.exit(1)
  }
}

config.bundle = config.bundle || {}
config.bundle.resources = selected.resources
config.bundle.targets = selected.targets

fs.writeFileSync(configPath, JSON.stringify(config, null, 2) + '\n', 'utf8')
console.log(`Configured tauri.conf.json for ${mode}`)
