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

const progressPercent = ref(0)
const progressIndeterminate = ref(false)
const statusMsg = ref('请选择音视频文件或输入 URL')

const segments = ref<Segment[]>([])
const resultText = ref('')

const persistentUnlisteners: UnlistenFn[] = []

const originalResultText = computed(() => segments.value.map((s) => s.text).join('\n'))
const hasEditedResult = computed(() => resultText.value !== originalResultText.value)
const canTranscribe = computed(() => {
  if (currentInputType.value === 'url') {
    const v = urlValue.value.trim()
    return v.startsWith('http://') || v.startsWith('https://')
  }
  return selectedFilePath.value !== null
})

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
  statusMsg.value = '请选择音视频文件或输入 URL'
}

function setFile(path: string) {
  selectedFilePath.value = path
  const name = path.replace(/\\/g, '/').split('/').pop() ?? path
  statusMsg.value = `已选择：${name}`
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
    statusMsg.value = `下载中... ${event.payload.percent.toFixed(1)}%`
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
    })
    segments.value = result
    resultText.value = result.map((s) => s.text).join('\n')
    statusMsg.value = `转写完成，共 ${result.length} 段`
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
</script>

<template>
  <div class="app">
    <header class="header">
      <h1>Whisper 语音/视频转文本</h1>
    </header>

    <main class="main">
      <aside class="sidebar">
        <div class="input-tabs">
          <button :class="['input-tab', { active: currentInputType === 'local' }]" @click="switchInput('local')">本地文件</button>
          <button :class="['input-tab', { active: currentInputType === 'url' }]" @click="switchInput('url')">在线 URL</button>
        </div>

        <div
          v-if="currentInputType === 'local'"
          :class="['drop-zone', { dragover: isDragOver, hasfile: selectedFilePath }]"
          @click="openFilePicker"
        >
          <p>拖拽音视频文件到这里，或点击选择文件</p>
          <p v-if="selectedFilePath" class="hint">{{ selectedFilePath.split('/').pop() }}</p>
        </div>

        <div v-if="currentInputType === 'url'" class="url-area">
          <label>音视频直链 URL</label>
          <input v-model="urlValue" type="url" placeholder="https://example.com/audio.mp3" />
        </div>

        <div>
          <label>模型</label>
          <select v-model="modelSize" @change="checkModel">
            <option value="tiny">tiny (~75MB)</option>
            <option value="base">base (~142MB)</option>
            <option value="small">small (~466MB)</option>
            <option value="medium">medium (~1.5GB)</option>
            <option value="big">big/large-v3 (~3.1GB)</option>
          </select>
          <p class="hint">
            <template v-if="modelReady === null">检查中...</template>
            <template v-else-if="modelReady">模型已就绪</template>
            <template v-else>模型未下载</template>
          </p>
          <p v-if="modelsDir" class="hint path">模型目录：{{ modelsDir }}</p>
          <div class="model-actions">
            <button type="button" @click="openModelsDir">打开模型目录</button>
            <button type="button" @click="clearModels">清理模型</button>
          </div>
        </div>

        <div>
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
        </div>

        <button v-if="modelReady === false" :disabled="isDownloading" @click="downloadModel">
          {{ isDownloading ? '下载中...' : '下载模型' }}
        </button>

        <div v-if="isDownloading || isTranscribing" class="progress">
          <div class="bar">
            <div :class="['fill', { indeterminate: progressIndeterminate }]" :style="progressIndeterminate ? {} : { width: `${Math.min(progressPercent, 100)}%` }" />
          </div>
        </div>

        <button :disabled="!canTranscribe || isDownloading || isTranscribing" @click="startTranscribe">
          {{ isTranscribing ? '转写中...' : '开始转写' }}
        </button>

        <p class="status">{{ statusMsg }}</p>
      </aside>

      <section class="result">
        <div class="toolbar">
          <button :disabled="!segments.length" @click="exportAs('txt')">导出 TXT</button>
          <button :disabled="!segments.length" @click="exportAs('srt')">导出 SRT</button>
        </div>
        <textarea v-model="resultText" placeholder="转写结果将在这里显示，可编辑后导出" />
      </section>
    </main>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.app { height: 100vh; display: flex; flex-direction: column; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #10131c; color: #eef1f8; }
.header { padding: 14px 20px; border-bottom: 1px solid #232a3d; }
.header h1 { margin: 0; font-size: 18px; }
.main { flex: 1; display: flex; min-height: 0; }
.sidebar { width: 320px; border-right: 1px solid #232a3d; padding: 16px; display: flex; flex-direction: column; gap: 12px; overflow-y: auto; }
.input-tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.input-tab { border: 1px solid #33405c; background: #1a2233; color: #ccd4e6; border-radius: 8px; padding: 8px; cursor: pointer; }
.input-tab.active { background: #2a3f75; }
.drop-zone { border: 1px dashed #425376; border-radius: 10px; padding: 18px; text-align: center; cursor: pointer; }
.drop-zone.dragover { border-color: #7ea2ff; }
.drop-zone.hasfile { border-color: #82d4a8; }
.url-area { display: flex; flex-direction: column; gap: 6px; }
input, select, button, textarea { border-radius: 8px; border: 1px solid #33405c; background: #151d2d; color: #eef1f8; }
input, select, button { padding: 9px 10px; }
button { cursor: pointer; }
button:disabled { opacity: 0.55; cursor: not-allowed; }
.progress .bar { height: 6px; background: #273044; border-radius: 999px; overflow: hidden; }
.fill { height: 100%; background: #6d92ff; transition: width .2s; width: 0; }
.fill.indeterminate { width: 35%; animation: run 1.1s linear infinite; }
@keyframes run { from { transform: translateX(-120%); } to { transform: translateX(320%); } }
.hint, .status { margin: 0; color: #a6b3ce; font-size: 12px; }
.path { word-break: break-all; }
.model-actions { display: flex; gap: 8px; }
.model-actions button { flex: 1; font-size: 12px; padding: 7px 8px; }
.result { flex: 1; min-width: 0; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
.toolbar { display: flex; justify-content: flex-end; gap: 8px; }
textarea { flex: 1; width: 100%; resize: none; padding: 12px; line-height: 1.6; }
@media (max-width: 900px) {
  .main { flex-direction: column; }
  .sidebar { width: 100%; border-right: 0; border-bottom: 1px solid #232a3d; }
}
</style>
