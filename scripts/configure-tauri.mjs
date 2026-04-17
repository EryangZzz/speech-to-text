import fs from 'node:fs'
import path from 'node:path'

const mode = process.argv[2] || process.env.BUNDLE_MODE || 'macos-arm64'
const root = process.cwd()
const srcTauriDir = path.join(root, 'src-tauri')
const configPath = path.join(srcTauriDir, 'tauri.conf.json')
const genDir = path.join(srcTauriDir, 'gen')

if (!fs.existsSync(configPath)) {
  console.error(`Missing base Tauri config: ${configPath}`)
  process.exit(1)
}

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
  const abs = path.join(srcTauriDir, rel)
  if (!fs.existsSync(abs)) {
    console.error(`Missing resource for ${mode}: ${abs}`)
    process.exit(1)
  }

  const stat = fs.statSync(abs)
  if (stat.size < 1_000_000) {
    console.error(`Resource too small for ${mode}: ${abs} (${stat.size} bytes)`)
    process.exit(1)
  }
}

const raw = fs.readFileSync(configPath, 'utf8')
JSON.parse(raw)

const generatedConfig = {
  bundle: {
    resources: selected.resources,
    targets: selected.targets,
  },
}

fs.mkdirSync(genDir, { recursive: true })
const generatedPath = path.join(genDir, `tauri.bundle.${mode}.json`)
fs.writeFileSync(generatedPath, JSON.stringify(generatedConfig, null, 2) + '\n', 'utf8')
console.log(`Generated Tauri bundle config for ${mode}: ${generatedPath}`)
