<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { invoke } from '@tauri-apps/api/core'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'
import { open, save } from '@tauri-apps/plugin-dialog'

interface Segment {
  start_ms: number
  end_ms: number
  text: string
}

type InputType = 'local' | 'url'
type ModelSize = 'tiny' | 'base' | 'small' | 'medium' | 'big'

const currentInputType = ref<InputType>('local')
const selectedFilePath = ref<string | null>(null)
const urlValue = ref('')
const modelSize = ref<ModelSize>('base')
const language = ref('')

const modelReady = ref<boolean | null>(null)
const modelsDir = ref('')
const isDownloading = ref(false)
const isTranscribing = ref(false)
const isDragOver = ref(false)
const cleanNoise = ref(true)

const progressPercent = ref(0)
const progressIndeterminate = ref(false)
const statusMsg = ref('准备就绪：选择文件或输入 URL 后即可开始转写')

const segments = ref<Segment[]>([])
const resultText = ref('')

const persistentUnlisteners: UnlistenFn[] = []

const originalResultText = computed(() => segments.value.map((s) => s.text).join('\n'))
const hasEditedResult = computed(() => resultText.value !== originalResultText.value)

const fileName = computed(() => {
  if (!selectedFilePath.value) return ''
  return selectedFilePath.value.replace(/\\/g, '/').split('/').pop() ?? selectedFilePath.value
})

const canTranscribe = computed(() => {
  if (currentInputType.value === 'url') {
    const v = urlValue.value.trim()
    return v.startsWith('http://') || v.startsWith('https://')
  }
  return selectedFilePath.value !== null
})

const segmentCount = computed(() => segments.value.length)
const charCount = computed(() => resultText.value.trim().length)
const minuteEstimate = computed(() => {
  if (!segments.value.length) return 0
  const end = Math.max(...segments.value.map((s) => s.end_ms))
  return Math.max(1, Math.round(end / 60000))
})
const timelineSegments = computed(() => segments.value)

onMounted(async () => {
  const ulDrop = await listen<{ paths: string[] }>('tauri://drag-drop', (event) => {
    if (currentInputType.value !== 'local') return
    const path = event.payload?.paths?.[0]
    if (path) setFile(path)
  })

  const ulOver = await listen('tauri://drag-over', () => {
    if (currentInputType.value === 'local') {
      isDragOver.value = true
    }
  })

  const ulLeave = await listen('tauri://drag-leave', () => {
    isDragOver.value = false
  })

  persistentUnlisteners.push(ulDrop, ulOver, ulLeave)
  await loadModelsDir()
  await checkModel()
})

onUnmounted(() => {
  persistentUnlisteners.forEach((fn) => fn())
})

function switchInput(type: InputType) {
  currentInputType.value = type
  selectedFilePath.value = null
  urlValue.value = ''
  isDragOver.value = false
  statusMsg.value = type === 'local' ? '请拖拽文件或点击卡片选择文件' : '请输入可直连下载的 URL'
}

function setFile(path: string) {
  selectedFilePath.value = path
  const name = path.replace(/\\/g, '/').split('/').pop() ?? path
  statusMsg.value = `已选择文件：${name}`
}

async function openFilePicker() {
  const path = await open({
    multiple: false,
    filters: [
      {
        name: '音视频文件',
        extensions: ['mp3', 'mp4', 'wav', 'm4a', 'ogg', 'flac', 'mkv', 'avi', 'mov', 'webm'],
      },
    ],
  })
  if (typeof path === 'string') {
    setFile(path)
  }
}

async function checkModel() {
  modelReady.value = null
  try {
    modelReady.value = await invoke<boolean>('check_model', { size: modelSize.value })
  } catch {
    modelReady.value = false
  }
}

async function loadModelsDir() {
  try {
    modelsDir.value = await invoke<string>('get_models_dir')
  } catch {
    modelsDir.value = ''
  }
}

async function openModelsDir() {
  try {
    await invoke('open_models_dir')
  } catch (e) {
    statusMsg.value = `打开模型目录失败: ${String(e)}`
  }
}

async function clearModels() {
  try {
    await invoke('clear_models')
    await checkModel()
    statusMsg.value = '模型文件已清理'
  } catch (e) {
    statusMsg.value = `清理模型失败: ${String(e)}`
  }
}

async function downloadModel() {
  isDownloading.value = true
  progressPercent.value = 0
  progressIndeterminate.value = false
  statusMsg.value = '正在下载模型...'

  const ul = await listen<{ percent: number }>('model-download-progress', (event) => {
    progressPercent.value = event.payload.percent
    statusMsg.value = `模型下载中... ${event.payload.percent.toFixed(1)}%`
  })

  try {
    await invoke('download_model_cmd', { size: modelSize.value })
    statusMsg.value = '模型下载完成'
    await checkModel()
  } catch (e) {
    statusMsg.value = `模型下载失败: ${String(e)}`
  } finally {
    ul()
    isDownloading.value = false
    progressPercent.value = 0
    progressIndeterminate.value = false
  }
}

async function startTranscribe() {
  const exists = await invoke<boolean>('check_model', { size: modelSize.value })
  if (!exists) {
    statusMsg.value = '请先下载模型'
    return
  }

  const audioInput = currentInputType.value === 'url' ? urlValue.value.trim() : selectedFilePath.value!
  const inputType = currentInputType.value

  isTranscribing.value = true
  resultText.value = ''
  segments.value = []
  progressPercent.value = 0
  progressIndeterminate.value = false

  let ulMedia: UnlistenFn | null = null
  if (inputType === 'url') {
    statusMsg.value = '正在下载媒体文件...'
    ulMedia = await listen<{ percent: number; indeterminate: boolean }>('media-download-progress', (event) => {
      progressIndeterminate.value = event.payload.indeterminate
      progressPercent.value = event.payload.percent
      statusMsg.value = event.payload.indeterminate
        ? '下载中...'
        : `下载中... ${event.payload.percent.toFixed(1)}%`
    })
  } else {
    statusMsg.value = '转写中...'
  }

  const ulTranscribe = await listen<{ percent: number }>('transcribe-progress', (event) => {
    progressIndeterminate.value = false
    progressPercent.value = event.payload.percent
    statusMsg.value = `转写中... ${event.payload.percent}%`
  })

  try {
    const result = await invoke<Segment[]>('transcribe_audio', {
      audioInput,
      inputType,
      modelSize: modelSize.value,
      language: language.value || null,
      cleanNoise: cleanNoise.value,
    })
    segments.value = result
    resultText.value = result.map((s) => s.text).join('\n')
    statusMsg.value = `转写完成：${result.length} 段`
  } catch (e) {
    statusMsg.value = `转写失败: ${String(e)}`
  } finally {
    if (ulMedia) ulMedia()
    ulTranscribe()
    isTranscribing.value = false
    progressPercent.value = 0
    progressIndeterminate.value = false
  }
}

async function exportAs(format: 'txt' | 'srt') {
  if (!segments.value.length) return
  if (format === 'srt' && hasEditedResult.value) {
    statusMsg.value = '已编辑文本时，SRT 仍按原始时间轴导出'
  }

  const ext = format === 'srt' ? 'srt' : 'txt'
  const name = format === 'srt' ? '字幕文件' : '文本文件'
  const outputPath = await save({ filters: [{ name, extensions: [ext] }] })
  if (!outputPath) return

  await invoke('export_result', {
    segments: segments.value,
    resultText: resultText.value,
    outputPath,
    format,
  })

  statusMsg.value = `已导出 ${ext.toUpperCase()}`
}

function formatSrtTime(ms: number): string {
  const total = Math.max(0, Math.floor(ms))
  const h = Math.floor(total / 3600000)
  const m = Math.floor((total % 3600000) / 60000)
  const s = Math.floor((total % 60000) / 1000)
  const msPart = total % 1000
  return [h, m, s].map((n) => String(n).padStart(2, '0')).join(':') + ',' + String(msPart).padStart(3, '0')
}

async function copyResultText() {
  if (!resultText.value.trim()) return
  try {
    await navigator.clipboard.writeText(resultText.value)
    statusMsg.value = '已复制转写文本到剪贴板'
  } catch (e) {
    statusMsg.value = `复制失败: ${String(e)}`
  }
}

function clearResultText() {
  resultText.value = ''
  segments.value = []
  statusMsg.value = '已清空结果区'
}
</script>

<template>
  <div class="shell">
    <div class="grain" aria-hidden="true" />

    <header class="hero">
      <p class="eyebrow">Whisper Desktop</p>
      <h1>音频 / 视频转写工作台</h1>
      <p class="subtitle">本地转写、URL 拉取、模型管理和字幕导出集中在同一界面。</p>
    </header>

    <main class="layout">
      <section class="panel control-panel">
        <div class="card">
          <div class="section-title">输入源</div>
          <div class="switcher">
            <button :class="['chip', { active: currentInputType === 'local' }]" @click="switchInput('local')">本地文件</button>
            <button :class="['chip', { active: currentInputType === 'url' }]" @click="switchInput('url')">在线 URL</button>
          </div>

          <div
            v-if="currentInputType === 'local'"
            :class="['drop', { dragover: isDragOver, hasfile: selectedFilePath }]"
            @click="openFilePicker"
          >
            <p class="drop-title">拖拽文件到这里，或点击选择</p>
            <p class="drop-meta">支持 mp3/mp4/wav/m4a/ogg/flac/mkv/avi/mov/webm</p>
            <p v-if="selectedFilePath" class="picked">{{ fileName }}</p>
          </div>

          <div v-if="currentInputType === 'url'" class="url-box">
            <label>可直链下载的 URL</label>
            <input v-model="urlValue" type="url" placeholder="https://example.com/media.mp4" />
          </div>
        </div>

        <div class="card">
          <div class="section-title">模型与语言</div>

          <label>模型规格</label>
          <select v-model="modelSize" @change="checkModel">
            <option value="tiny">tiny (~75MB)</option>
            <option value="base">base (~142MB)</option>
            <option value="small">small (~466MB)</option>
            <option value="medium">medium (~1.5GB)</option>
            <option value="big">big / large-v3 (~3.1GB)</option>
          </select>

          <p class="inline-note ok" v-if="modelReady === true">模型已就绪</p>
          <p class="inline-note warn" v-else-if="modelReady === false">模型未下载</p>
          <p class="inline-note" v-else>检查中...</p>

          <label>语言</label>
          <select v-model="language">
            <option value="">自动检测</option>
            <option value="zh">中文</option>
            <option value="en">English</option>
            <option value="ja">日本語</option>
            <option value="ko">한국어</option>
            <option value="fr">Français</option>
            <option value="de">Deutsch</option>
          </select>

          <label class="toggle-line">
            <input v-model="cleanNoise" type="checkbox" />
            <span>过滤非语音标签（如 [music] / [applause]）</span>
          </label>

          <div class="row-actions">
            <button type="button" class="ghost" @click="openModelsDir">打开模型目录</button>
            <button type="button" class="ghost" @click="clearModels">清理模型</button>
          </div>
          <p v-if="modelsDir" class="path">{{ modelsDir }}</p>

          <button v-if="modelReady === false" class="accent" :disabled="isDownloading" @click="downloadModel">
            {{ isDownloading ? '模型下载中...' : '下载模型' }}
          </button>
        </div>

        <div class="card action-card">
          <button class="primary" :disabled="!canTranscribe || isDownloading || isTranscribing" @click="startTranscribe">
            {{ isTranscribing ? '正在转写...' : '开始转写' }}
          </button>
          <div v-if="isDownloading || isTranscribing" class="progress">
            <div class="bar">
              <div
                :class="['fill', { indeterminate: progressIndeterminate }]"
                :style="progressIndeterminate ? {} : { width: `${Math.min(progressPercent, 100)}%` }"
              />
            </div>
          </div>
          <p class="status">{{ statusMsg }}</p>
          <p class="noise-note">遇到误过滤时，可关闭“过滤非语音标签”后重试。</p>
        </div>
      </section>

      <section class="panel result-panel">
        <div class="stats">
          <article>
            <p>片段数</p>
            <strong>{{ segmentCount }}</strong>
          </article>
          <article>
            <p>字符数</p>
            <strong>{{ charCount }}</strong>
          </article>
          <article>
            <p>音频时长(约)</p>
            <strong>{{ minuteEstimate }} min</strong>
          </article>
        </div>

        <div class="toolbar">
          <button :disabled="!resultText.trim()" @click="copyResultText">复制全文</button>
          <button :disabled="!resultText.trim()" @click="clearResultText">清空</button>
          <button :disabled="!segments.length" @click="exportAs('txt')">导出 TXT</button>
          <button :disabled="!segments.length" @click="exportAs('srt')">导出 SRT</button>
        </div>

        <div class="preview-grid">
          <textarea v-model="resultText" placeholder="转写结果会显示在这里，可编辑后导出。" />

          <div class="timeline-card">
            <div class="timeline-title">时间轴预览（全部分段）</div>
            <div class="timeline-list">
              <article class="timeline-item" v-for="(seg, idx) in timelineSegments" :key="`${seg.start_ms}-${idx}`">
                <p class="time">{{ formatSrtTime(seg.start_ms) }} -> {{ formatSrtTime(seg.end_ms) }}</p>
                <p class="line">{{ seg.text }}</p>
              </article>
              <div v-if="!timelineSegments.length" class="timeline-empty">
                暂无分段结果。开始转写后，这里会按时间轴显示全部片段。
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }

.shell {
  --bg: #f4f0ea;
  --paper: #fffdf9;
  --ink: #1e1a16;
  --muted: #6f645b;
  --line: #d7cdc1;
  --accent: #0f6d66;
  --accent-strong: #0b5954;
  --focus: #ff8a3d;
  --soft: #efe5d8;
  height: 100vh;
  color: var(--ink);
  background:
    radial-gradient(1600px 500px at 5% -20%, #fff8d9 0%, rgba(255, 248, 217, 0) 55%),
    radial-gradient(1200px 500px at 95% -10%, #d8efe9 0%, rgba(216, 239, 233, 0) 58%),
    var(--bg);
  padding: 26px;
  font-family: 'Avenir Next', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.grain {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.18;
  background-image: radial-gradient(rgba(0, 0, 0, 0.14) 0.5px, transparent 0.5px);
  background-size: 3px 3px;
}

.hero {
  position: relative;
  z-index: 1;
  margin: 4px 0 18px;
  animation: rise .55s ease-out;
  flex: 0 0 auto;
}

.eyebrow {
  margin: 0;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: var(--accent-strong);
}

.hero h1 {
  margin: 8px 0 4px;
  font-size: 34px;
  line-height: 1.08;
  letter-spacing: 0.01em;
  font-family: 'Baskerville', 'Times New Roman', serif;
}

.subtitle {
  margin: 0;
  color: var(--muted);
}

.layout {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 18px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.panel {
  border: 1px solid var(--line);
  border-radius: 20px;
  background: linear-gradient(180deg, #fffefb 0%, #fffaf2 100%);
  box-shadow: 0 14px 42px rgba(38, 31, 25, 0.08);
  min-height: 0;
}

.control-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  overflow: hidden;
  min-height: 0;
}

.card {
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 14px;
  background: var(--paper);
  animation: rise .48s ease-out;
}

.section-title {
  font-size: 12px;
  letter-spacing: 0.1em;
  color: var(--muted);
  text-transform: uppercase;
  margin-bottom: 10px;
}

.switcher {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.chip {
  border: 1px solid var(--line);
  background: #f5efe6;
  color: var(--ink);
  border-radius: 999px;
  padding: 9px 10px;
  cursor: pointer;
  transition: all .2s ease;
}

.chip.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.drop {
  margin-top: 10px;
  border: 1px dashed #b8a999;
  border-radius: 14px;
  padding: 18px;
  text-align: center;
  cursor: pointer;
  background: #fff8ee;
  transition: .2s ease;
}

.drop:hover { transform: translateY(-1px); }
.drop.dragover { border-color: var(--focus); background: #fff2e6; }
.drop.hasfile { border-color: var(--accent); }

.drop-title {
  margin: 0;
  font-weight: 600;
}

.drop-meta {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--muted);
}

.picked {
  margin: 10px 0 0;
  color: var(--accent-strong);
  font-weight: 600;
  word-break: break-all;
}

.url-box {
  display: grid;
  gap: 7px;
}

label {
  margin-top: 8px;
  font-size: 12px;
  color: var(--muted);
}

input,
select,
button,
textarea {
  border: 1px solid var(--line);
  border-radius: 11px;
  color: var(--ink);
  background: #fff;
}

input,
select,
button {
  padding: 10px 11px;
}

select,
input,
textarea {
  outline: none;
}

select:focus,
input:focus,
textarea:focus {
  border-color: var(--focus);
  box-shadow: 0 0 0 3px rgba(255, 138, 61, 0.2);
}

.inline-note {
  margin: 7px 0 0;
  font-size: 12px;
  color: var(--muted);
}

.inline-note.ok { color: #0b6e58; }
.inline-note.warn { color: #b5512a; }

.row-actions {
  margin-top: 10px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.path {
  margin: 8px 0 0;
  font-size: 11px;
  color: var(--muted);
  word-break: break-all;
}

.toggle-line {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--ink);
}

.toggle-line input {
  width: 15px;
  height: 15px;
  accent-color: var(--accent);
}

button {
  cursor: pointer;
  transition: transform .15s ease, background-color .2s ease, border-color .2s ease;
}

button:hover:not(:disabled) { transform: translateY(-1px); }
button:disabled { opacity: 0.55; cursor: not-allowed; }

.ghost {
  background: #f6f1e8;
}

.accent {
  margin-top: 10px;
  width: 100%;
  background: #ecf7f5;
  border-color: #8dc6bf;
  color: #0b5954;
}

.action-card { background: linear-gradient(180deg, #fffdf9 0%, #f9f1e6 100%); }

.primary {
  width: 100%;
  border: 1px solid var(--accent);
  background: var(--accent);
  color: #fff;
  font-weight: 600;
}

.progress {
  margin-top: 10px;
}

.bar {
  height: 6px;
  border-radius: 999px;
  overflow: hidden;
  background: #eadfce;
}

.fill {
  height: 100%;
  width: 0;
  background: linear-gradient(90deg, #0f6d66 0%, #ff8a3d 100%);
  transition: width .2s linear;
}

.fill.indeterminate {
  width: 38%;
  animation: run 1.1s linear infinite;
}

.status {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--muted);
  min-height: 18px;
}

.noise-note {
  margin: 8px 0 0;
  font-size: 11px;
  color: #5e7f7a;
}

.result-panel {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 12px;
  padding: 14px;
  min-height: 0;
  overflow: hidden;
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.stats article {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px;
  background: #fffdf9;
}

.stats p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
}

.stats strong {
  display: block;
  margin-top: 4px;
  font-size: 22px;
  font-weight: 700;
}

.toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.toolbar button {
  background: #f7efe4;
}

.timeline-card {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 10px;
  background: #fffdf9;
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.timeline-title {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
}

.timeline-item {
  border: 1px solid #e9dece;
  border-radius: 10px;
  padding: 8px;
  background: #fffaf1;
}

.timeline-item .time {
  margin: 0;
  font-size: 11px;
  color: #6a847f;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
}

.timeline-item .line {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--ink);
  line-height: 1.45;
}

.timeline-empty {
  border: 1px dashed #dbcdbb;
  border-radius: 10px;
  padding: 14px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
  background: #fffaf1;
}

textarea {
  width: 100%;
  height: 100%;
  resize: none;
  padding: 14px;
  line-height: 1.66;
  font-size: 14px;
  background: #fffdf9;
  overflow: auto;
}

.preview-grid {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(0, 1fr);
  gap: 12px;
  height: 100%;
  overflow: hidden;
}

@keyframes run {
  from { transform: translateX(-120%); }
  to { transform: translateX(320%); }
}

@keyframes rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 980px) {
  .shell { padding: 14px; }
  .layout {
    grid-template-columns: 1fr;
    min-height: 0;
  }
  .control-panel { max-height: none; }
  .stats { grid-template-columns: 1fr; }
  .preview-grid {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(220px, 1fr) minmax(180px, 1fr);
  }
  textarea {
    min-height: 0;
  }
}
</style>
