# Whisper 跨平台桌面语音转文本工具 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个零依赖、开箱即用的跨平台桌面应用，让普通用户（无编程环境）可以直接通过 .dmg / .exe 安装使用，将音频/视频文件转换为文字或 SRT 字幕文件。支持本地文件拖拽、文件选择器、以及在线 URL 三种输入方式。

**Architecture:** 使用 Tauri 框架（Rust 壳 + WebView 前端），Rust 后端通过 `whisper-rs`（whisper.cpp 的 Rust 绑定）在本地执行语音识别，无需 Python 或任何运行时。前端为轻量 HTML/JS，提供文件拖拽上传、URL 输入、转换进度展示、结果编辑和导出功能。模型文件在首次启动时按需下载至用户本地目录。所有音频/视频解码统一通过内嵌 ffmpeg 静态二进制处理，确保跨平台一致性且无需用户额外安装任何工具。

**Tech Stack:**
- **框架**: Tauri 2.x
- **前端**: Vue 3 + Vite（`<script setup>` 组合式 API）
- **后端**: Rust + `whisper-rs` 0.11+
- **语音识别核心**: whisper.cpp（通过 whisper-rs 绑定）
- **音频/视频解码**: 内嵌 ffmpeg 静态编译二进制（支持所有主流音视频格式）
- **在线媒体下载**: `reqwest` 0.12（流式下载 + 进度回调）
- **并发控制**: `tokio::sync::Mutex`（防止重复转写）
- **打包**: Tauri Bundler → macOS `.dmg` / Windows `.msi` + `.exe`
- **CI/CD**: GitHub Actions 多平台构建

---

## 需求概述

### 用户场景
- 目标用户：非技术人员，电脑上没有 Python / Node.js 等开发环境
- 使用流程（三种输入方式）：
  1. **本地文件拖拽**：将音频/视频文件拖入窗口 → 点击转写 → 获得文本/字幕
  2. **文件选择器**：点击区域打开系统文件选择器 → 选择文件 → 点击转写
  3. **在线 URL**：粘贴音频/视频直链 URL → 点击下载+转写 → 获得结果

### 功能需求

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 本地文件拖拽导入 | P0 | 通过 Tauri drag-drop 事件获取文件路径 |
| 文件选择器导入 | P0 | 点击唤起系统文件对话框 |
| 在线 URL 导入 | P0 | 输入直链 URL，后端流式下载到临时目录 |
| 音视频格式支持 | P0 | 支持 mp3/mp4/wav/m4a/ogg/flac/mkv/avi/mov/webm 等，统一走内嵌 ffmpeg |
| 语音转文本 | P0 | 调用本地 Whisper 模型，输出纯文本 |
| 导出 TXT | P0 | 将识别结果保存为 .txt 文件 |
| 导出 SRT | P0 | 带时间戳字幕文件，标准 SRT 格式 |
| 模型选择 | P1 | 提供 tiny/base/small/medium/big 五档，按精度/速度权衡 |
| 首次自动下载模型 | P1 | 检测本地无模型时，从 Hugging Face 或国内镜像下载 |
| 语言选择 | P1 | 支持自动检测 或 手动指定语言（中文/英文/日文等） |
| 转写进度展示 | P1 | whisper-rs progress_callback 实时上报进度 |
| 下载进度展示 | P1 | 模型下载 / URL 媒体下载均显示进度条 |
| 并发保护 | P1 | 同一时刻只允许一个转写任务，后端 Mutex 保护 |
| 结果编辑 | P2 | 转换完成后可在界面内编辑文本再导出 |

### 非功能需求
- 安装包大小：不含模型 < 80MB（含内嵌 ffmpeg 约 50MB），含 tiny 模型 < 170MB
- 启动时间：< 3 秒
- 转换速度：tiny 模型处理 1 分钟音频 < 30 秒（现代 CPU）
- 平台：macOS 12+（Apple Silicon & Intel）、Windows 10/11 x64
- 无需网络（模型和 ffmpeg 准备完成后完全离线）
- 打包策略：按目标平台仅打包对应 ffmpeg 二进制（禁止跨平台资源全部入包）
- URL 下载支持断点提示（网络失败时给出明确错误，不留残缺文件）
- 模型下载支持真实断点续传（复用 `.tmp` 已下载字节 + HTTP `Range`），完成后做大小与哈希校验再 rename

---

## 文件结构

```
whisper-desktop/
├── package.json                        # 前端依赖、tauri dev/build 脚本
├── vite.config.ts                      # Vite 配置
├── src/                                # Vue 3 前端代码
│   ├── main.ts                         # Vue 应用入口
│   ├── App.vue                         # 根组件（空壳，引用主界面）
│   └── components/
│       └── MainView.vue                # 主界面：三种输入、进度、结果、导出
├── index.html                          # Vite HTML 入口（根目录）
├── src-tauri/                          # Rust 后端
│   ├── Cargo.toml                      # Rust 依赖声明
│   ├── tauri.conf.json                 # Tauri 配置：窗口、打包
│   ├── capabilities/
│   │   └── default.json                # Tauri 2 权限声明（drag-drop、dialog、fs 等）
│   ├── build.rs                        # 构建脚本（whisper-rs 需要）
│   └── src/
│       ├── main.rs                     # Tauri 入口，注册所有 command，持有全局状态
│       ├── transcribe.rs               # 核心转写逻辑，调用 whisper-rs（含进度回调）
│       ├── model.rs                    # 模型管理：路径解析、断点续传下载、大小校验
│       ├── audio.rs                    # 音视频预处理：调用内嵌 ffmpeg 解码为 f32 PCM
│       ├── media_fetch.rs              # 在线 URL 媒体下载（流式 + 进度 + 临时文件管理）
│       └── export.rs                   # 导出逻辑：TXT 格式、SRT 格式生成
├── resources/                          # 内嵌资源（打包进应用）
│   ├── ffmpeg-macos-arm64              # macOS Apple Silicon 静态 ffmpeg
│   ├── ffmpeg-macos-x64               # macOS Intel 静态 ffmpeg
│   └── ffmpeg-windows-x64.exe         # Windows 静态 ffmpeg
├── .github/
│   └── workflows/
│       └── build.yml                   # GitHub Actions 多平台构建
└── models/                             # （可选）打包内嵌模型目录
    └── .gitkeep
```

---

## Task 1: 初始化 Tauri 项目脚手架

**Files:**
- Create: `package.json`
- Create: `index.html`
- Create: `src-tauri/Cargo.toml`
- Create: `src-tauri/tauri.conf.json`
- Create: `src-tauri/src/main.rs`

- [ ] **Step 1: 安装 Rust 工具链和 Tauri CLI**

```bash
# 安装 Rust（如未安装）
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# macOS 还需要
xcode-select --install

# 安装 Tauri CLI
npm install -g @tauri-apps/cli@latest

# 验证
rustc --version   # 期望: rustc 1.75+
cargo --version
tauri --version
```

- [ ] **Step 2: 创建项目**

```bash
mkdir whisper-desktop && cd whisper-desktop
npm create tauri-app@latest .
# 选择: Vue, TypeScript
```

- [ ] **Step 3: 配置 `src-tauri/Cargo.toml`，添加所有依赖（一次性完整配置）**

```toml
[package]
name = "whisper-desktop"
version = "0.1.0"
edition = "2021"

[dependencies]
tauri = { version = "2", features = ["protocol-asset"] }
tauri-plugin-dialog = "2"               # 文件选择/保存对话框
# 注意：whisper-rs 不存在 "whisper-cpp" feature，直接使用默认即可
whisper-rs = { version = "0.11" }
hound = "3.5"          # WAV 读取（备用，主要走 ffmpeg）
serde = { version = "1", features = ["derive"] }
serde_json = "1"
anyhow = "1"
tokio = { version = "1", features = ["full"] }
# reqwest 0.12：与 tokio 1.x 完全兼容，stream + json features
reqwest = { version = "0.12", features = ["stream", "json"] }
futures-util = "0.3"   # 流式处理 bytes_stream()
tempfile = "3"         # 安全临时文件管理
sha2 = "0.10"          # 模型文件 SHA256 完整性校验

[profile.release]
strip = true           # 减小二进制体积
lto = true             # 链接时优化

[build-dependencies]
tauri-build = { version = "2", features = [] }
```

- [ ] **Step 4: 创建 `src-tauri/build.rs`**

```rust
fn main() {
    tauri_build::build()
}
```

- [ ] **Step 5: 验证项目可以启动**

```bash
npm run tauri dev
```

期望：窗口弹出，显示默认页面，无编译错误

- [ ] **Step 6: Commit**

```bash
git init
git add .
git commit -m "feat: init Tauri project scaffold"
```

---

## Task 2: 准备内嵌 ffmpeg 二进制

**Files:**
- Create: `resources/` 目录及各平台 ffmpeg 静态编译文件
- Modify: `src-tauri/tauri.conf.json`

**说明:** 不要求用户自行安装 ffmpeg，而是将静态编译的 ffmpeg 打包进应用。这样所有音视频格式（mp3/mp4/m4a/ogg/flac/mkv/avi/mov/webm 等）都能开箱即用。静态编译的 ffmpeg 体积约 40-60MB（每平台），是包体积增大的代价，但换来零依赖体验。

- [ ] **Step 1: 下载各平台静态编译 ffmpeg**

```bash
mkdir -p resources

# macOS Apple Silicon（arm64）
# 从 https://evermeet.cx/ffmpeg/ 下载静态版本
curl -L "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip" -o /tmp/ffmpeg-mac-arm64.zip
unzip /tmp/ffmpeg-mac-arm64.zip -d /tmp/ffmpeg-arm64/
cp /tmp/ffmpeg-arm64/ffmpeg resources/ffmpeg-macos-arm64
chmod +x resources/ffmpeg-macos-arm64

# macOS Intel（x64）
curl -L "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip?arch=x86_64" -o /tmp/ffmpeg-mac-x64.zip
unzip /tmp/ffmpeg-mac-x64.zip -d /tmp/ffmpeg-x64/
cp /tmp/ffmpeg-x64/ffmpeg resources/ffmpeg-macos-x64
chmod +x resources/ffmpeg-macos-x64

# Windows x64
# 从 https://www.gyan.dev/ffmpeg/builds/ 下载 essentials build
curl -L "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -o /tmp/ffmpeg-win.zip
unzip /tmp/ffmpeg-win.zip -d /tmp/ffmpeg-win/
cp "$(find /tmp/ffmpeg-win -type f -name ffmpeg.exe | head -1)" resources/ffmpeg-windows-x64.exe
```

- [ ] **Step 2: 在 `tauri.conf.json` 中声明资源文件**

在 `bundle` 节点下添加当前构建目标平台对应的一项（不要三平台同时添加）：
```json
"resources": {
  "resources/ffmpeg-macos-arm64": "resources/ffmpeg-macos-arm64"
}
```

- [ ] **Step 3: Commit**

```bash
git add resources/ src-tauri/tauri.conf.json
git commit -m "feat: bundle platform-specific static ffmpeg binaries"
```

---

## Task 3: 音视频预处理模块（audio.rs）

**Files:**
- Create: `src-tauri/src/audio.rs`
- Modify: `src-tauri/src/main.rs`

**说明:** 所有音频/视频文件统一通过内嵌 ffmpeg 解码为 16kHz、单声道、f32 PCM 数据。不再区分 WAV 和非 WAV，消除 8-bit WAV 等格式边界问题。通过 `tauri::AppHandle` 定位内嵌 ffmpeg 路径，在 release 包和 dev 模式下均可正确找到。

- [ ] **Step 1: 创建 `src-tauri/src/audio.rs`**

```rust
use anyhow::{Context, Result};
use std::path::{Path, PathBuf};
use std::process::Command;
use tempfile::NamedTempFile;
use tauri::AppHandle;
use tauri::Manager;

/// 获取内嵌 ffmpeg 可执行文件的路径
pub fn ffmpeg_path(app: &AppHandle) -> Result<PathBuf> {
    let resource_dir = app
        .path()
        .resource_dir()
        .with_context(|| "无法获取资源目录")?;

    // 根据当前平台选择对应的 ffmpeg 二进制
    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    let name = "ffmpeg-macos-arm64";
    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    let name = "ffmpeg-macos-x64";
    #[cfg(target_os = "windows")]
    let name = "ffmpeg-windows-x64.exe";
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    let name = "ffmpeg"; // Linux fallback（CI 用）

    let bundled = resource_dir.join("resources").join(name);
    if bundled.exists() {
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let mut perms = std::fs::metadata(&bundled)?.permissions();
            perms.set_mode(0o755);
            std::fs::set_permissions(&bundled, perms)?;
        }
        return Ok(bundled);
    }

    // dev 模式 fallback：优先尝试项目根目录 resources/
    let dev_candidates = [
        std::env::current_dir().ok().map(|p| p.join("resources").join(name)),
        std::env::current_dir().ok().map(|p| p.join("../resources").join(name)),
    ];
    for p in dev_candidates.into_iter().flatten() {
        if p.exists() {
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let mut perms = std::fs::metadata(&p)?.permissions();
                perms.set_mode(0o755);
                std::fs::set_permissions(&p, perms)?;
            }
            return Ok(p);
        }
    }

    anyhow::bail!(
        "内嵌 ffmpeg 未找到。已尝试: {:?} 和项目 resources 目录",
        bundled
    );
}

/// 将任意音视频文件解码为 whisper 所需的 16kHz mono f32 PCM 样本
/// 输入可以是本地文件路径或已下载到临时目录的文件路径
pub fn decode_audio(app: &AppHandle, file_path: &str) -> Result<Vec<f32>> {
    let ffmpeg = ffmpeg_path(app)?;

    // 使用唯一临时文件接收 ffmpeg 输出，避免时间戳重名冲突
    let tmp_pcm = NamedTempFile::new()
        .with_context(|| "创建 PCM 临时文件失败")?;
    let tmp_pcm_path = tmp_pcm.path().to_path_buf();
    let tmp_pcm_out = tmp_pcm_path.to_string_lossy().to_string();

    // ffmpeg 输出原始 f32le PCM，16kHz，单声道
    let output = Command::new(&ffmpeg)
        .args([
            "-y",
            "-i", file_path,
            "-ar", "16000",
            "-ac", "1",
            "-f", "f32le",     // 直接输出 f32 little-endian，无需二次转换
            tmp_pcm_out.as_str(),
        ])
        .output()
        .with_context(|| format!("执行 ffmpeg 失败，路径: {:?}", ffmpeg))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("ffmpeg 解码失败: {}", stderr);
    }

    // 读取原始 PCM bytes，转换为 f32 Vec
    let raw = std::fs::read(&tmp_pcm_path)
        .with_context(|| "读取 PCM 临时文件失败")?;

    if raw.len() % 4 != 0 {
        anyhow::bail!("PCM 数据长度异常: {} bytes（不是 4 的倍数）", raw.len());
    }

    let samples: Vec<f32> = raw
        .chunks_exact(4)
        .map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]]))
        .collect();

    Ok(samples)
}
```

- [ ] **Step 2: 在 `main.rs` 中声明模块**

```rust
mod audio;
mod export;
mod media_fetch;
mod model;
mod transcribe;
```

- [ ] **Step 3: 编译验证**

```bash
cd src-tauri && cargo build 2>&1 | head -50
```

期望：编译成功，无 error

- [ ] **Step 4: Commit**

```bash
git add src-tauri/src/audio.rs src-tauri/src/main.rs
git commit -m "feat: add audio/video decode module via embedded ffmpeg"
```

---

## Task 4: 模型管理模块（model.rs）

**Files:**
- Create: `src-tauri/src/model.rs`

**说明:** 负责确定模型文件存储路径、检测模型是否已下载、执行带断点续传的下载并上报进度。下载采用"复用 `.tmp` + HTTP Range + 完成后校验大小/哈希 + rename"策略，防止网络中断或损坏文件。

- [ ] **Step 1: 创建 `src-tauri/src/model.rs`**

```rust
use anyhow::{Context, Result};
use sha2::{Digest, Sha256};
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use tauri::{AppHandle, Emitter, Manager};

/// 支持的模型规格
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub enum ModelSize {
    Tiny,   // ~75MB，速度最快，精度一般
    Base,   // ~142MB，速度较快，精度较好
    Small,  // ~466MB，速度较慢，精度最好
    Medium, // ~1.5GB，精度高，速度更慢
    Big,    // ~3.1GB（large-v3），精度最高，速度最慢
}

impl ModelSize {
    pub fn filename(&self) -> &str {
        match self {
            ModelSize::Tiny  => "ggml-tiny.bin",
            ModelSize::Base  => "ggml-base.bin",
            ModelSize::Small => "ggml-small.bin",
            ModelSize::Medium => "ggml-medium.bin",
            ModelSize::Big => "ggml-large-v3.bin",
        }
    }

    /// 优先使用国内镜像，海外可换回 huggingface.co
    pub fn download_url(&self) -> &str {
        match self {
            ModelSize::Tiny =>
                "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
            ModelSize::Base =>
                "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
            ModelSize::Small =>
                "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
            ModelSize::Medium =>
                "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin",
            ModelSize::Big =>
                "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin",
        }
    }

    /// 预期文件大小（字节），用于校验下载完整性
    pub fn expected_size_bytes(&self) -> u64 {
        match self {
            ModelSize::Tiny  => 75_000_000,
            ModelSize::Base  => 142_000_000,
            ModelSize::Small => 466_000_000,
            ModelSize::Medium => 1_530_000_000,
            ModelSize::Big => 3_090_000_000,
        }
    }

    /// 可选：强校验哈希（示例值请在发布时替换为官方最新 SHA256）
    pub fn expected_sha256(&self) -> &'static str {
        match self {
            ModelSize::Tiny => "REPLACE_WITH_REAL_SHA256_TINY",
            ModelSize::Base => "REPLACE_WITH_REAL_SHA256_BASE",
            ModelSize::Small => "REPLACE_WITH_REAL_SHA256_SMALL",
            ModelSize::Medium => "REPLACE_WITH_REAL_SHA256_MEDIUM",
            ModelSize::Big => "REPLACE_WITH_REAL_SHA256_LARGE_V3",
        }
    }
}

/// 返回模型存储目录（系统 AppData）
pub fn models_dir(app: &AppHandle) -> Result<PathBuf> {
    let data_dir = app
        .path()
        .app_data_dir()
        .with_context(|| "无法获取 AppData 目录")?;
    let dir = data_dir.join("models");
    std::fs::create_dir_all(&dir)?;
    Ok(dir)
}

/// 返回指定模型的完整路径
pub fn model_path(app: &AppHandle, size: &ModelSize) -> Result<PathBuf> {
    Ok(models_dir(app)?.join(size.filename()))
}

/// 检测模型是否已存在且大小合理
/// 说明：不同来源模型可能存在少量大小差异，因此不使用“完全相等”硬编码
pub fn model_exists(app: &AppHandle, size: &ModelSize) -> Result<bool> {
    let path = model_path(app, size)?;
    if !path.exists() {
        return Ok(false);
    }
    let actual_size = std::fs::metadata(&path)?.len();
    let threshold = size.expected_size_bytes() * 9 / 10;
    Ok(actual_size >= threshold)
}

/// 下载模型（带 HTTP Range 断点续传）
/// 策略：复用 <filename>.tmp 已下载字节，完成后校验大小与 SHA256，再 rename 为正式文件
/// 事件: "model-download-progress" { downloaded: u64, total: u64, percent: f32 }
pub async fn download_model(app: AppHandle, size: ModelSize) -> Result<PathBuf> {
    use futures_util::StreamExt;
    use reqwest::Client;
    use reqwest::StatusCode;

    let dest = model_path(&app, &size)?;
    let tmp_path = dest.with_extension("bin.tmp");
    let url = size.download_url();
    let expected = size.expected_size_bytes();

    let resumed = if tmp_path.exists() {
        std::fs::metadata(&tmp_path)?.len()
    } else {
        0
    };

    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(3600)) // 大文件下载超时 1 小时
        .build()?;

    let mut request = client.get(url);
    if resumed > 0 {
        request = request.header("Range", format!("bytes={}-", resumed));
    }
    let response = request
        .send()
        .await
        .with_context(|| format!("连接模型下载地址失败: {}", url))?;

    if !(response.status().is_success()
        || response.status() == StatusCode::PARTIAL_CONTENT)
    {
        anyhow::bail!("下载请求失败，HTTP {}", response.status());
    }

    // 若服务端不支持 Range，且本地有残留 tmp，则清空后从头下载
    let fresh_start = resumed > 0 && response.status() == StatusCode::OK;
    if fresh_start {
        let _ = std::fs::remove_file(&tmp_path);
    }

    let start = if fresh_start { 0 } else { resumed };
    let total = response.content_length().unwrap_or(expected.saturating_sub(start)) + start;

    let mut downloaded: u64 = start;
    let mut file: File = OpenOptions::new()
        .create(true)
        .append(start > 0)
        .write(true)
        .truncate(start == 0)
        .open(&tmp_path)
        .with_context(|| format!("创建/打开临时文件失败: {:?}", tmp_path))?;

    let mut stream = response.bytes_stream();
    while let Some(chunk) = stream.next().await {
        let chunk = chunk.with_context(|| "下载过程中网络中断")?;
        file.write_all(&chunk)?;
        downloaded += chunk.len() as u64;
        let percent = if total > 0 {
            downloaded as f32 / total as f32 * 100.0
        } else {
            0.0
        };
        let _ = app.emit("model-download-progress", serde_json::json!({
            "downloaded": downloaded,
            "total": total,
            "percent": percent,
        }));
    }
    file.flush()?;
    drop(file);

    // 校验下载完整性（大小）
    // 优先使用响应头 content-length 推导 total；若不可用则回退到经验阈值
    let actual_size = std::fs::metadata(&tmp_path)?.len();
    let min_acceptable = expected * 9 / 10;
    if actual_size < min_acceptable {
        let _ = std::fs::remove_file(&tmp_path);
        anyhow::bail!(
            "下载的模型文件大小异常（{}MB），预期约 {}MB，文件已删除，请重试",
            actual_size / 1_000_000,
            expected / 1_000_000
        );
    }

    // 校验 SHA256（示例；实际请替换 expected_sha256 为真实值）
    let mut hasher = Sha256::new();
    let bytes = std::fs::read(&tmp_path)?;
    hasher.update(bytes);
    let actual_hash = format!("{:x}", hasher.finalize());
    let expected_hash = size.expected_sha256();
    if !expected_hash.starts_with("REPLACE_WITH_REAL_SHA256")
        && actual_hash != expected_hash
    {
        let _ = std::fs::remove_file(&tmp_path);
        anyhow::bail!("模型哈希校验失败，文件已删除，请重试下载");
    }

    // 原子性重命名为正式文件
    std::fs::rename(&tmp_path, &dest)
        .with_context(|| "模型文件重命名失败")?;

    Ok(dest)
}
```

- [ ] **Step 2: 编译验证**

```bash
cd src-tauri && cargo build 2>&1 | head -50
```

期望：编译成功

- [ ] **Step 3: Commit**

```bash
git add src-tauri/src/model.rs
git commit -m "feat: add model management with safe download (tmp + rename + size check)"
```

---

## Task 5: 在线 URL 媒体下载模块（media_fetch.rs）

**Files:**
- Create: `src-tauri/src/media_fetch.rs`

**说明:** 支持用户粘贴在线音频/视频直链 URL，后端流式下载到系统临时目录，下载过程中通过 Tauri 事件上报进度。下载完成后返回临时文件路径，后续走同一套 `audio::decode_audio` 流程。临时文件在转写完成后由调用方清理。

- [ ] **Step 1: 创建 `src-tauri/src/media_fetch.rs`**

```rust
use anyhow::{Context, Result};
use futures_util::StreamExt;
use reqwest::Client;
use std::io::Write;
use std::path::PathBuf;
use tempfile::Builder;
use tauri::{AppHandle, Emitter};

/// 从 URL 下载媒体文件到临时目录，流式上报进度
/// 事件: "media-download-progress" { downloaded: u64, total: u64, percent: f32, indeterminate: bool }
/// 返回：下载后的临时文件路径（调用方负责清理）
pub async fn download_media_from_url(
    app: AppHandle,
    url: String,
) -> Result<PathBuf> {
    // 基本 URL 格式校验
    if !url.starts_with("http://") && !url.starts_with("https://") {
        anyhow::bail!("URL 必须以 http:// 或 https:// 开头");
    }

    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(3600))
        .user_agent("Mozilla/5.0 WhisperDesktop/0.1")
        .build()?;

    let response = client
        .get(&url)
        .send()
        .await
        .with_context(|| format!("连接 URL 失败: {}", url))?;

    if !response.status().is_success() {
        anyhow::bail!("URL 请求失败，HTTP {}: {}", response.status(), url);
    }

    // 从 Content-Type 或 URL 猜测文件扩展名
    let ext = guess_extension(&url, &response);

    // 生成唯一临时文件路径（避免并发命名冲突）
    let tmp_file = Builder::new()
        .prefix("whisper_media_")
        .suffix(&format!(".{}", ext))
        .tempfile()
        .with_context(|| "创建媒体临时文件失败")?;
    // 关键：keep() 防止 NamedTempFile 在函数返回时自动删除
    let (mut file, tmp_path) = tmp_file
        .keep()
        .with_context(|| "持久化媒体临时文件失败")?;

    let total = response.content_length(); // 可能为 None（服务器未返回 Content-Length）
    let mut downloaded: u64 = 0;

    let mut stream = response.bytes_stream();
    while let Some(chunk) = stream.next().await {
        let chunk = match chunk {
            Ok(c) => c,
            Err(e) => {
                let _ = std::fs::remove_file(&tmp_path);
                anyhow::bail!("媒体文件下载过程中网络中断: {}", e);
            }
        };
        file.write_all(&chunk)?;
        downloaded += chunk.len() as u64;

        let (percent, indeterminate) = match total {
            Some(t) if t > 0 => (downloaded as f32 / t as f32 * 100.0, false),
            _ => (0.0, true), // 未知总大小，显示不确定进度
        };

        let _ = app.emit("media-download-progress", serde_json::json!({
            "downloaded": downloaded,
            "total": total.unwrap_or(0),
            "percent": percent,
            "indeterminate": indeterminate,
        }));
    }
    file.flush()?;
    drop(file);

    if downloaded == 0 {
        let _ = std::fs::remove_file(&tmp_path);
        anyhow::bail!("下载的媒体文件为空: {}", url);
    }

    Ok(tmp_path)
}

/// 根据 URL 路径和 Content-Type 猜测文件扩展名
fn guess_extension(url: &str, response: &reqwest::Response) -> String {
    // 先从 Content-Type 判断
    if let Some(ct) = response.headers().get("content-type") {
        if let Ok(ct_str) = ct.to_str() {
            let ext = match ct_str.split(';').next().unwrap_or("").trim() {
                "audio/mpeg"  | "audio/mp3"  => "mp3",
                "audio/mp4"   | "video/mp4"  => "mp4",
                "audio/x-m4a" | "audio/m4a"  => "m4a",
                "audio/ogg"   | "video/ogg"  => "ogg",
                "audio/flac"                  => "flac",
                "audio/wav"   | "audio/x-wav"=> "wav",
                "video/webm"                  => "webm",
                "video/x-matroska"            => "mkv",
                _ => "",
            };
            if !ext.is_empty() {
                return ext.to_string();
            }
        }
    }

    // 从 URL 路径取扩展名
    if let Some(last_segment) = url.split('?').next().and_then(|u| u.split('/').last()) {
        if let Some(dot_pos) = last_segment.rfind('.') {
            let ext = &last_segment[dot_pos + 1..];
            if matches!(ext, "mp3" | "mp4" | "m4a" | "ogg" | "flac" | "wav" | "webm" | "mkv" | "avi" | "mov") {
                return ext.to_string();
            }
        }
    }

    // 默认使用 mp4（ffmpeg 可识别大多数容器）
    "mp4".to_string()
}
```

- [ ] **Step 2: 编译验证**

```bash
cd src-tauri && cargo build 2>&1 | head -50
```

期望：编译成功

- [ ] **Step 3: Commit**

```bash
git add src-tauri/src/media_fetch.rs
git commit -m "feat: add online URL media download module with progress events"
```

---

## Task 6: 转写核心模块（transcribe.rs）

**Files:**
- Create: `src-tauri/src/transcribe.rs`

**说明:** 调用 whisper-rs 执行语音识别，通过 `set_progress_callback` 实时上报进度事件，返回带时间戳的片段列表。转写为 CPU 密集型操作，调用方需在 `spawn_blocking` 中执行。

- [ ] **Step 1: 创建 `src-tauri/src/transcribe.rs`**

```rust
use anyhow::{Context, Result};
use tauri::{AppHandle, Emitter};
use whisper_rs::{FullParams, SamplingStrategy, WhisperContext, WhisperContextParameters};

/// 单个转写片段（对应 SRT 的一条字幕）
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Segment {
    pub start_ms: i64,
    pub end_ms: i64,
    pub text: String,
}

/// 转写参数
#[derive(Debug, serde::Deserialize)]
pub struct TranscribeOptions {
    pub model_path: String,
    pub audio_path: String,
    pub language: Option<String>,
    pub translate: bool,
}

/// 执行转写，返回片段列表，通过 Tauri 事件上报进度
/// 事件: "transcribe-progress" { percent: f32 }
pub fn transcribe(app: AppHandle, opts: TranscribeOptions) -> Result<Vec<Segment>> {
    // 1. 加载模型
    let ctx = WhisperContext::new_with_params(
        &opts.model_path,
        WhisperContextParameters::default(),
    )
    .with_context(|| format!("无法加载模型: {}", opts.model_path))?;

    // 2. 解码音频（通过内嵌 ffmpeg）
    let samples = crate::audio::decode_audio(&app, &opts.audio_path)
        .with_context(|| format!("音视频解码失败: {}", opts.audio_path))?;

    // 3. 配置参数
    let mut params = FullParams::new(SamplingStrategy::Greedy { best_of: 1 });

    match opts.language.as_deref() {
        Some(lang) => params.set_language(Some(lang)),
        None => params.set_language(None), // None 才是 whisper 自动检测语言
    }

    params.set_translate(opts.translate);
    params.set_print_realtime(false);
    params.set_print_progress(false);
    params.set_print_timestamps(true);

    // 4. 注册进度回调（通过 Tauri 事件通知前端）
    let app_clone = app.clone();
    params.set_progress_callback(move |progress: i32| {
        let _ = app_clone.emit("transcribe-progress", serde_json::json!({
            "percent": progress,
        }));
    });

    // 5. 执行推理
    let mut state = ctx.create_state().with_context(|| "创建 whisper state 失败")?;
    state
        .full(params, &samples)
        .with_context(|| "whisper 推理失败")?;

    // 6. 提取片段
    let num_segments = state.full_n_segments().with_context(|| "获取片段数失败")?;
    let mut segments = Vec::with_capacity(num_segments as usize);

    for i in 0..num_segments {
        let text = state
            .full_get_segment_text(i)
            .with_context(|| format!("获取第 {} 段文本失败", i))?;
        // whisper 时间单位是 1/100 秒（centiseconds），乘以 10 转为毫秒
        let start_ms = state
            .full_get_segment_t0(i)
            .with_context(|| format!("获取第 {} 段开始时间失败", i))?
            * 10;
        let end_ms = state
            .full_get_segment_t1(i)
            .with_context(|| format!("获取第 {} 段结束时间失败", i))?
            * 10;

        segments.push(Segment {
            start_ms,
            end_ms,
            text: text.trim().to_string(),
        });
    }

    Ok(segments)
}
```

- [ ] **Step 2: 编译验证**

```bash
cd src-tauri && cargo build 2>&1 | head -80
```

期望：编译成功（whisper-rs 首次编译会下载并编译 whisper.cpp，约需 2-5 分钟）

- [ ] **Step 3: Commit**

```bash
git add src-tauri/src/transcribe.rs
git commit -m "feat: add transcribe module with progress callback"
```

---

## Task 7: 导出模块（export.rs）

**Files:**
- Create: `src-tauri/src/export.rs`

- [ ] **Step 1: 创建 `src-tauri/src/export.rs`**

```rust
use crate::transcribe::Segment;
use anyhow::Result;

/// 将片段列表导出为纯文本（每段一行）
pub fn to_txt(segments: &[Segment]) -> String {
    segments
        .iter()
        .map(|s| s.text.as_str())
        .collect::<Vec<_>>()
        .join("\n")
}

/// 将片段列表导出为标准 SRT 字幕格式
pub fn to_srt(segments: &[Segment]) -> String {
    segments
        .iter()
        .enumerate()
        .map(|(i, seg)| {
            format!(
                "{}\n{} --> {}\n{}\n",
                i + 1,
                format_srt_time(seg.start_ms),
                format_srt_time(seg.end_ms),
                seg.text
            )
        })
        .collect::<Vec<_>>()
        .join("\n")
}

/// 毫秒 → SRT 时间格式 HH:MM:SS,mmm
fn format_srt_time(ms: i64) -> String {
    let ms = ms.max(0);
    let hours   = ms / 3_600_000;
    let minutes = (ms % 3_600_000) / 60_000;
    let seconds = (ms % 60_000) / 1_000;
    let millis  = ms % 1_000;
    format!("{:02}:{:02}:{:02},{:03}", hours, minutes, seconds, millis)
}

/// 将内容写入文件
pub fn write_file(path: &str, content: &str) -> Result<()> {
    std::fs::write(path, content.as_bytes())?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::transcribe::Segment;

    fn seg(start_ms: i64, end_ms: i64, text: &str) -> Segment {
        Segment { start_ms, end_ms, text: text.to_string() }
    }

    #[test]
    fn test_format_srt_time_zero() {
        assert_eq!(format_srt_time(0), "00:00:00,000");
    }

    #[test]
    fn test_format_srt_time_complex() {
        let ms = 1 * 3_600_000 + 2 * 60_000 + 3 * 1_000 + 456;
        assert_eq!(format_srt_time(ms), "01:02:03,456");
    }

    #[test]
    fn test_format_srt_time_negative_clamped() {
        // 负值应被 clamp 为 0
        assert_eq!(format_srt_time(-100), "00:00:00,000");
    }

    #[test]
    fn test_to_txt() {
        let segments = vec![seg(0, 1000, "Hello"), seg(1000, 2000, "World")];
        assert_eq!(to_txt(&segments), "Hello\nWorld");
    }

    #[test]
    fn test_to_srt() {
        let segments = vec![seg(0, 1500, "你好"), seg(2000, 4000, "世界")];
        let srt = to_srt(&segments);
        assert!(srt.contains("1\n00:00:00,000 --> 00:00:01,500\n你好"));
        assert!(srt.contains("2\n00:00:02,000 --> 00:00:04,000\n世界"));
    }
}
```

- [ ] **Step 2: 运行单元测试**

```bash
cd src-tauri && cargo test export
```

期望：5 个测试全部通过

- [ ] **Step 3: Commit**

```bash
git add src-tauri/src/export.rs
git commit -m "feat: add TXT/SRT export module with unit tests"
```

---

## Task 8: Tauri Command 层（main.rs）

**Files:**
- Modify: `src-tauri/src/main.rs`

**说明:** 将所有功能封装为 Tauri Command。使用全局 `Mutex<bool>` 防止并发转写。`transcribe_audio` 支持传入本地路径或 URL（通过 `input_type` 区分），URL 类型会先触发下载再转写，转写完成后自动清理临时文件。

- [ ] **Step 1: 替换 `src-tauri/src/main.rs` 全部内容**

```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod audio;
mod export;
mod media_fetch;
mod model;
mod transcribe;

use model::{ModelSize, download_model, model_exists, model_path};
use std::sync::Arc;
use tauri::{AppHandle, Manager, State};
use tokio::sync::Mutex;

/// 全局状态：防止并发转写
struct AppState {
    transcribing: Arc<Mutex<bool>>,
}

/// 检查指定模型是否已下载且完整
#[tauri::command]
async fn check_model(app: AppHandle, size: String) -> Result<bool, String> {
    let size = parse_model_size(&size)?;
    model_exists(&app, &size).map_err(|e| e.to_string())
}

/// 下载模型（异步，通过事件上报进度）
#[tauri::command]
async fn download_model_cmd(app: AppHandle, size: String) -> Result<(), String> {
    let size = parse_model_size(&size)?;
    download_model(app, size)
        .await
        .map(|_| ())
        .map_err(|e| e.to_string())
}

/// 执行转写
/// input_type: "local"（本地文件路径）或 "url"（在线直链）
/// audio_input: 对应的文件路径或 URL
#[tauri::command]
async fn transcribe_audio(
    app: AppHandle,
    state: State<'_, AppState>,
    audio_input: String,
    input_type: String,   // "local" | "url"
    model_size: String,
    language: Option<String>,
) -> Result<Vec<transcribe::Segment>, String> {
    // 并发保护：同一时刻只允许一个转写任务
    {
        let mut is_transcribing = state.transcribing.lock().await;
        if *is_transcribing {
            return Err("已有转写任务进行中，请等待完成后再试".to_string());
        }
        *is_transcribing = true;
    } // 锁在此处释放

    // 克隆 Arc 用于后续重置（do_transcribe 是普通函数，直接传 Arc 而非 State）
    let transcribing_flag = state.transcribing.clone();

    let result = do_transcribe(app, transcribing_flag.clone(), audio_input, input_type, model_size, language).await;

    // 无论成功失败，都重置转写状态
    *transcribing_flag.lock().await = false;

    result
}

/// 实际执行转写逻辑（接收 Arc 而非 State，避免 State lifetime 问题）
async fn do_transcribe(
    app: AppHandle,
    _transcribing_flag: Arc<Mutex<bool>>, // 由调用方负责重置
    audio_input: String,
    input_type: String,
    model_size: String,
    language: Option<String>,
) -> Result<Vec<transcribe::Segment>, String> {
    // 1. 先检查模型（本地/URL 统一逻辑）
    let size = parse_model_size(&model_size)?;
    let exists = model_exists(&app, &size).map_err(|e| e.to_string())?;
    if !exists {
        return Err(format!("模型未下载: {}", model_size));
    }
    let mp = model_path(&app, &size).map_err(|e| e.to_string())?;

    // 2. 确定实际音频文件路径
    let (audio_path, is_temp) = match input_type.as_str() {
        "local" => (audio_input, false),
        "url" => {
            let tmp_path = media_fetch::download_media_from_url(app.clone(), audio_input)
                .await
                .map_err(|e| format!("媒体文件下载失败: {}", e))?;
            (tmp_path.to_string_lossy().to_string(), true)
        }
        other => return Err(format!("非法 input_type: {}（仅支持 local/url）", other)),
    };

    let opts = transcribe::TranscribeOptions {
        model_path: mp.to_string_lossy().to_string(),
        audio_path: audio_path.clone(),
        language,
        translate: false,
    };

    // 3. 在阻塞线程中执行 CPU 密集型转写
    let app_clone = app.clone();
    let result = tokio::task::spawn_blocking(move || transcribe::transcribe(app_clone, opts))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string());

    // 4. 清理临时媒体文件（无论成功失败都清理）
    if is_temp {
        let _ = std::fs::remove_file(&audio_path);
    }

    result
}

/// 导出结果到文件
#[tauri::command]
async fn export_result(
    segments: Vec<transcribe::Segment>,   // 用于 SRT（以及 TXT 回退）
    result_text: Option<String>,          // 前端编辑后的文本
    output_path: String,
    format: String,  // "txt" 或 "srt"
) -> Result<(), String> {
    let content = match format.as_str() {
        "txt" => {
            let text = result_text.unwrap_or_else(|| export::to_txt(&segments));
            if text.trim().is_empty() {
                return Err("没有可导出的文本内容".to_string());
            }
            text
        }
        "srt" => {
            if segments.is_empty() {
                return Err("SRT 导出需要分段时间戳数据".to_string());
            }
            export::to_srt(&segments)
        }
        other => return Err(format!("不支持的导出格式: {}", other)),
    };
    export::write_file(&output_path, &content).map_err(|e| e.to_string())
}

fn parse_model_size(s: &str) -> Result<ModelSize, String> {
    match s {
        "tiny"  => Ok(ModelSize::Tiny),
        "base"  => Ok(ModelSize::Base),
        "small" => Ok(ModelSize::Small),
        "medium" => Ok(ModelSize::Medium),
        "big" | "large" | "large-v3" => Ok(ModelSize::Big),
        other   => Err(format!("未知模型规格: {}", other)),
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())   // 注册 dialog 插件
        .manage(AppState {
            transcribing: Arc::new(Mutex::new(false)),
        })
        .invoke_handler(tauri::generate_handler![
            check_model,
            download_model_cmd,
            transcribe_audio,
            export_result,
        ])
        .run(tauri::generate_context!())
        .expect("Tauri 启动失败");
}
```

- [ ] **Step 2: 编译验证**

```bash
cd src-tauri && cargo build 2>&1 | grep -E "^error"
```

期望：无输出（无 error）

- [ ] **Step 3: Commit**

```bash
git add src-tauri/src/main.rs
git commit -m "feat: expose Tauri commands with concurrency guard and URL input support"
```

---

## Task 9: 前端界面（Vue 3 + Vite）

**Files:**
- Create: `src/main.ts`
- Create: `src/App.vue`
- Create: `src/components/MainView.vue`
- Create: `vite.config.ts`

**说明:** 使用 Vue 3 `<script setup>` 组合式 API，将所有逻辑集中在 `MainView.vue` 中。支持三种输入方式：拖拽（通过 Tauri `tauri://drag-drop` 事件，而非 Web File API）、文件选择器（`dialog:open`）、在线 URL 输入框。用 `onUnmounted` 统一清理 Tauri 事件监听器防止泄漏。

- [ ] **Step 1: 安装前端 Tauri 插件依赖**

```bash
npm install @tauri-apps/api @tauri-apps/plugin-dialog
```

- [ ] **Step 2: 创建 `vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
  },
  envPrefix: ['VITE_', 'TAURI_'],
  build: {
    target: ['es2021', 'chrome100', 'safari13'],
    minify: !process.env.TAURI_DEBUG ? 'esbuild' : false,
    sourcemap: !!process.env.TAURI_DEBUG,
  },
})
```

- [ ] **Step 3: 创建 `src/main.ts`**

```typescript
import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')
```

- [ ] **Step 4: 创建 `src/App.vue`**

```vue
<script setup lang="ts">
import MainView from './components/MainView.vue'
</script>

<template>
  <MainView />
</template>
```

- [ ] **Step 5: 创建 `src/components/MainView.vue`**

```vue
<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { invoke } from '@tauri-apps/api/core'
import { open, save } from '@tauri-apps/plugin-dialog'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'

// ── 类型定义 ──────────────────────────────────────────
interface Segment {
  start_ms: number
  end_ms: number
  text: string
}

// ── 响应式状态 ─────────────────────────────────────────
const currentInputType = ref<'local' | 'url'>('local')
const selectedFilePath = ref<string | null>(null)
const urlValue = ref('')
const modelSize = ref<'tiny' | 'base' | 'small' | 'medium' | 'big'>('base')
const language = ref('')
const modelReady = ref<boolean | null>(null)  // null=检查中
const isDownloading = ref(false)
const isTranscribing = ref(false)
const progressPercent = ref(0)
const progressIndeterminate = ref(false)
const statusMsg = ref('请选择音视频文件或输入 URL')
const resultText = ref('')
const segments = ref<Segment[]>([])

// ── 事件监听器清理 ─────────────────────────────────────
const unlisteners: UnlistenFn[] = []

onUnmounted(() => {
  unlisteners.forEach(fn => fn())
})

// ── 初始化拖拽与模型检查 ───────────────────────────────
onMounted(async () => {
  // 注册 Tauri drag-drop 事件（必须用 Tauri 事件，不能用 Web File API）
  const ulDrop = await listen<{ paths: string[] }>('tauri://drag-drop', (event) => {
    if (currentInputType.value !== 'local') return
    const paths = event.payload?.paths
    if (paths && paths.length > 0) setFile(paths[0])
  })
  const ulOver = await listen('tauri://drag-over', () => {
    if (currentInputType.value === 'local') isDragOver.value = true
  })
  const ulLeave = await listen('tauri://drag-leave', () => {
    isDragOver.value = false
  })
  unlisteners.push(ulDrop, ulOver, ulLeave)

  await checkModel()
})

const isDragOver = ref(false)

// ── 输入方式切换 ───────────────────────────────────────
function switchInput(type: 'local' | 'url') {
  currentInputType.value = type
  selectedFilePath.value = null
  urlValue.value = ''
  statusMsg.value = '请选择音视频文件或输入 URL'
}

// ── 文件处理 ───────────────────────────────────────────
function setFile(path: string) {
  selectedFilePath.value = path
  const name = path.replace(/\\/g, '/').split('/').pop() ?? path
  statusMsg.value = `已选择：${name}`
}

async function openFilePicker() {
  const path = await open({
    multiple: false,
    filters: [{
      name: '音视频文件',
      extensions: ['mp3', 'mp4', 'wav', 'm4a', 'ogg', 'flac', 'mkv', 'avi', 'mov', 'webm']
    }]
  })
  if (typeof path === 'string') setFile(path)
}

// ── 模型管理 ───────────────────────────────────────────
async function checkModel() {
  modelReady.value = null
  try {
    modelReady.value = await invoke<boolean>('check_model', { size: modelSize.value })
  } catch {
    modelReady.value = false
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
  unlisteners.push(ul)

  try {
    await invoke('download_model_cmd', { size: modelSize.value })
    statusMsg.value = '模型下载完成！'
    await checkModel()
  } catch (e) {
    statusMsg.value = `下载失败: ${e}`
  } finally {
    ul()  // 立即取消此次下载的监听（已在 unlisteners 中，但提前清理更安全）
    isDownloading.value = false
    progressPercent.value = 0
  }
}

// ── 转写 ───────────────────────────────────────────────
const originalResultText = computed(() => segments.value.map(s => s.text).join('\n'))
const hasEditedResult = computed(() => resultText.value !== originalResultText.value)

const canTranscribe = computed(() => {
  if (currentInputType.value === 'url') {
    return urlValue.value.startsWith('http://') || urlValue.value.startsWith('https://')
  }
  return selectedFilePath.value !== null
})

async function startTranscribe() {
  const audioInput = currentInputType.value === 'url'
    ? urlValue.value.trim()
    : selectedFilePath.value!
  const inputType = currentInputType.value

  // 本地/URL 都先检查模型
  const exists = await invoke<boolean>('check_model', { size: modelSize.value })
  if (!exists) { statusMsg.value = '请先下载模型'; return }

  isTranscribing.value = true
  resultText.value = ''
  segments.value = []
  progressPercent.value = 0

  // URL 模式监听媒体下载进度
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
    statusMsg.value = '转写中，请稍候...'
  }

  // 监听转写进度
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
    resultText.value = result.map(s => s.text).join('\n')
    statusMsg.value = `转写完成，共 ${result.length} 段`
  } catch (e) {
    statusMsg.value = `失败: ${e}`
  } finally {
    ulMedia?.()
    ulTranscribe()
    isTranscribing.value = false
    progressPercent.value = 0
    progressIndeterminate.value = false
  }
}

// ── 导出 ───────────────────────────────────────────────
async function exportAs(format: 'txt' | 'srt') {
  if (!segments.value.length) return
  if (format === 'srt' && hasEditedResult.value) {
    statusMsg.value = '已编辑文本时，SRT 仍按原始时间轴导出'
  }
  const ext = format === 'srt' ? 'srt' : 'txt'
  const name = format === 'srt' ? '字幕文件' : '文本文件'
  const path = await save({ filters: [{ name, extensions: [ext] }] })
  if (!path) return
  await invoke('export_result', {
    segments: segments.value,
    resultText: resultText.value,
    outputPath: path,
    format,
  })
  statusMsg.value = `已导出 ${ext.toUpperCase()}: ${path}`
}
</script>

<template>
  <div class="app">
    <!-- 顶栏 -->
    <header class="header">
      <h1>Whisper 语音/视频转文本</h1>
    </header>

    <div class="main">
      <!-- 左侧控制面板 -->
      <aside class="sidebar">

        <!-- 输入方式标签 -->
        <div class="input-tabs">
          <button
            :class="['input-tab', { active: currentInputType === 'local' }]"
            @click="switchInput('local')"
          >本地文件</button>
          <button
            :class="['input-tab', { active: currentInputType === 'url' }]"
            @click="switchInput('url')"
          >在线 URL</button>
        </div>

        <!-- 本地文件：拖拽 / 点击选择 -->
        <div
          v-if="currentInputType === 'local'"
          :class="['drop-zone', { dragover: isDragOver, 'has-file': selectedFilePath }]"
          @click="openFilePicker"
        >
          <div class="icon">🎵</div>
          <p>拖拽音视频文件到这里<br>或点击选择文件</p>
          <p v-if="selectedFilePath" class="file-hint">{{ selectedFilePath.split('/').pop() }}</p>
          <p v-else style="margin-top:6px;font-size:11px;color:#666;">
            MP3 / MP4 / WAV / M4A / OGG / FLAC / MKV / AVI / MOV / WEBM
          </p>
        </div>

        <!-- 在线 URL 输入 -->
        <div v-if="currentInputType === 'url'" class="url-input-area">
          <label class="field-label">音视频直链 URL</label>
          <input
            v-model="urlValue"
            class="url-input"
            type="url"
            placeholder="https://example.com/audio.mp3"
          />
          <p style="font-size:11px;color:#666;">支持 http/https 直链</p>
        </div>

        <!-- 模型选择 -->
        <div>
          <label class="field-label">模型</label>
          <select v-model="modelSize" @change="checkModel">
            <option value="tiny">Tiny（~75MB，速度最快）</option>
            <option value="base">Base（~142MB，推荐）</option>
            <option value="small">Small（~466MB，速度/精度均衡）</option>
            <option value="medium">Medium（~1.5GB，高精度）</option>
            <option value="big">Big / Large-v3（~3.1GB，最高精度）</option>
          </select>
          <span :class="['model-status', modelReady ? 'ready' : 'missing']" style="margin-top:6px;display:inline-block;">
            <template v-if="modelReady === null">检查中...</template>
            <template v-else-if="modelReady">✓ 模型已就绪</template>
            <template v-else>✗ 模型未下载</template>
          </span>
        </div>

        <!-- 语言选择 -->
        <div>
          <label class="field-label">语言</label>
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

        <!-- 下载模型按钮 -->
        <button
          v-if="modelReady === false"
          class="btn-download"
          :disabled="isDownloading"
          @click="downloadModel"
        >
          {{ isDownloading ? '下载中...' : '⬇ 下载模型' }}
        </button>

        <!-- 进度条 -->
        <div v-if="isDownloading || isTranscribing" class="progress-wrap">
          <div class="progress-bar">
            <div
              :class="['fill', { indeterminate: progressIndeterminate }]"
              :style="progressIndeterminate ? {} : { width: Math.min(100, progressPercent).toFixed(1) + '%' }"
            ></div>
          </div>
        </div>

        <!-- 开始转写 -->
        <button
          :disabled="!canTranscribe || isTranscribing || isDownloading"
          @click="startTranscribe"
        >
          {{ isTranscribing ? '转写中...' : '▶ 开始转写' }}
        </button>

        <div class="status">{{ statusMsg }}</div>
      </aside>

      <!-- 右侧结果区域 -->
      <section class="result-area">
        <div class="result-toolbar">
          <button class="btn-secondary" :disabled="!segments.length" @click="exportAs('txt')">导出 TXT</button>
          <button class="btn-secondary" :disabled="!segments.length" @click="exportAs('srt')">导出 SRT</button>
        </div>
        <textarea
          v-model="resultText"
          placeholder="转写结果将在这里显示，可以直接编辑..."
        ></textarea>
      </section>
    </div>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; margin: 0; padding: 0; }

.app {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #1a1a2e;
  color: #e0e0e0;
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  padding: 16px 24px;
  border-bottom: 1px solid #2a2a4a;
}
.header h1 { font-size: 18px; font-weight: 600; color: #a78bfa; }

.main { flex: 1; display: flex; overflow: hidden; }

.sidebar {
  width: 300px;
  padding: 20px;
  border-right: 1px solid #2a2a4a;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
}

.input-tabs { display: flex; border-radius: 8px; overflow: hidden; border: 1px solid #3a3a5a; }
.input-tab {
  flex: 1; padding: 7px 0; text-align: center; font-size: 12px;
  cursor: pointer; background: #2a2a4a; color: #888;
  transition: background 0.2s, color 0.2s; border: none;
}
.input-tab.active { background: #7c3aed; color: #fff; }

.drop-zone {
  border: 2px dashed #4a4a6a; border-radius: 12px; padding: 28px 16px;
  text-align: center; cursor: pointer; transition: border-color 0.2s, background 0.2s;
}
.drop-zone.dragover { border-color: #a78bfa; background: #2a2a4a; }
.drop-zone.has-file { border-color: #7c3aed; }
.drop-zone .icon { font-size: 32px; margin-bottom: 8px; }
.drop-zone p { font-size: 12px; color: #888; }
.file-hint { color: #a78bfa !important; margin-top: 6px; word-break: break-all; }

.url-input-area { display: flex; flex-direction: column; gap: 8px; }
.url-input {
  width: 100%; padding: 10px 12px; border-radius: 8px;
  border: 1px solid #3a3a5a; background: #0f0f23; color: #e0e0e0; font-size: 13px;
}
.url-input::placeholder { color: #555; }
.url-input:focus { outline: none; border-color: #7c3aed; }

.field-label { font-size: 12px; color: #888; display: block; margin-bottom: 4px; }

select, button {
  width: 100%; padding: 8px 12px; border-radius: 8px;
  border: 1px solid #3a3a5a; background: #2a2a4a; color: #e0e0e0; font-size: 14px;
}
button {
  cursor: pointer; background: #7c3aed; border-color: #7c3aed;
  font-weight: 600; transition: background 0.2s;
}
button:hover:not(:disabled) { background: #6d28d9; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-download { background: #059669; border-color: #059669; }
.btn-download:hover:not(:disabled) { background: #047857; }

.model-status { font-size: 11px; padding: 3px 8px; border-radius: 4px; background: #2a2a4a; }
.model-status.ready { color: #34d399; }
.model-status.missing { color: #f87171; }

.progress-wrap { display: flex; flex-direction: column; gap: 4px; }
.progress-bar { height: 4px; background: #2a2a4a; border-radius: 4px; overflow: hidden; }
.fill { height: 100%; background: #a78bfa; transition: width 0.3s; width: 0%; }
.fill.indeterminate {
  width: 40% !important;
  animation: slide 1.2s infinite ease-in-out;
}
@keyframes slide {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(300%); }
}

.status { font-size: 12px; color: #888; min-height: 18px; }

.result-area { flex: 1; display: flex; flex-direction: column; padding: 20px; gap: 12px; }
.result-toolbar { display: flex; gap: 8px; justify-content: flex-end; }
.result-toolbar button { width: auto; padding: 6px 16px; font-size: 13px; }
.btn-secondary { background: #2a2a4a !important; border-color: #4a4a6a !important; }

textarea {
  flex: 1; background: #0f0f23; border: 1px solid #2a2a4a; border-radius: 8px;
  padding: 16px; color: #e0e0e0; font-size: 14px; line-height: 1.7;
  resize: none; font-family: inherit;
}
</style>
```

- [ ] **Step 6: 更新 `index.html` 指向 Vue 入口**

```html
<!DOCTYPE html>
<html lang="zh">
  <head>
    <meta charset="UTF-8" />
    <title>Whisper 语音转文本</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 7: 启动开发模式验证 UI**

```bash
npm run tauri dev
```

期望：三种输入方式切换正常，拖拽文件有高亮反馈，URL 输入验证正常，进度条在下载和转写时均有显示

- [ ] **Step 8: Commit**

```bash
git add src/ index.html vite.config.ts
git commit -m "feat: add Vue 3 frontend with local/url input, drag-drop, progress"
```


## Task 10: 配置 Tauri 打包

**Files:**
- Modify: `src-tauri/tauri.conf.json`
- Create: `src-tauri/capabilities/default.json`

- [ ] **Step 1: 完整 `src-tauri/tauri.conf.json`**

```json
{
  "productName": "WhisperDesktop",
  "version": "0.1.0",
  "identifier": "com.yourcompany.whisper-desktop",
  "build": {
    "frontendDist": "../dist",
    "devUrl": "http://localhost:1420",
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build"
  },
  "app": {
    "windows": [
      {
        "title": "Whisper 语音转文本",
        "width": 960,
        "height": 640,
        "minWidth": 720,
        "minHeight": 520,
        "resizable": true,
        "fullscreen": false
      }
    ],
    "security": {
      "csp": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "resources": {
      "resources/ffmpeg-macos-arm64": "resources/ffmpeg-macos-arm64"
    },
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ],
    "macOS": {
      "minimumSystemVersion": "12.0"
    },
    "windows": {
      "wix": {},
      "nsis": {}
    }
  }
}
```

**注意：** Tauri 2 中 `build.frontendDist` 指向 Vite 构建输出目录 `../dist`，不再是 `../src`。`beforeDevCommand` 和 `beforeBuildCommand` 确保 Vite 与 Tauri 联动。
生产构建必须按平台裁剪 `bundle.resources`，不要把 3 个平台 ffmpeg 同时打进单个平台安装包。建议在 CI 中生成平台专用配置：

```json
// macOS arm64
"resources": {
  "resources/ffmpeg-macos-arm64": "resources/ffmpeg-macos-arm64"
}
```

```json
// macOS x64
"resources": {
  "resources/ffmpeg-macos-x64": "resources/ffmpeg-macos-x64"
}
```

```json
// Windows x64
"resources": {
  "resources/ffmpeg-windows-x64.exe": "resources/ffmpeg-windows-x64.exe"
}
```

- [ ] **Step 2: 创建 `src-tauri/capabilities/default.json`（Tauri 2 权限声明）**

Tauri 2 将权限从 `tauri.conf.json` 拆分到独立的 capabilities 文件，必须显式声明所需权限：

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Capability for the main window",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "dialog:default",
    "dialog:allow-open",
    "dialog:allow-save"
  ]
}
```

**说明：**
- `core:default`：包含 drag-drop、event、window、app 等核心权限（含文件拖拽）
- `dialog:default` + `dialog:allow-open` + `dialog:allow-save`：文件选择/保存对话框

- [ ] **Step 3: 本地构建测试**

```bash
# macOS
npm run tauri build
# 产物路径: src-tauri/target/release/bundle/dmg/*.dmg

# Windows（在 Windows 机器上执行）
npm run tauri build
# 产物路径: src-tauri/target/release/bundle/nsis/*.exe
```

期望：构建成功，安装包体积（含 ffmpeg，不含模型）< 80MB

建议额外增加包体积门禁（CI）：
```bash
# macOS DMG 大小检查（示例阈值 80MB）
MAX_MB=80
ACTUAL_MB=$(du -m src-tauri/target/release/bundle/dmg/*.dmg | awk '{print $1}')
test "$ACTUAL_MB" -le "$MAX_MB"
```

- [ ] **Step 4: Commit**

```bash
git add src-tauri/tauri.conf.json src-tauri/capabilities/
git commit -m "chore: configure Tauri bundler, CSP, and capabilities for dialog/drag-drop"
```

---

## Task 11: GitHub Actions 多平台 CI/CD

**Files:**
- Create: `.github/workflows/build.yml`

**调整：** macOS 两个架构合并为 Universal Binary，减少 CI 时间和复杂度。需要额外配置 `--target universal-apple-darwin`。如果 Metal 加速有问题，可退回两个独立 job。

- [ ] **Step 1: 创建 `.github/workflows/build.yml`**

```yaml
name: Build

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust stable with both macOS targets
        uses: dtolnay/rust-toolchain@stable
        with:
          targets: aarch64-apple-darwin,x86_64-apple-darwin

      - name: Rust cache
        uses: Swatinem/rust-cache@v2
        with:
          workspaces: './src-tauri -> target'

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install frontend dependencies
        run: npm install

      - name: Build Tauri app (Universal Binary)
        uses: tauri-apps/tauri-action@v0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tagName: ${{ github.ref_name }}
          releaseName: 'WhisperDesktop ${{ github.ref_name }}'
          releaseBody: '语音/视频转文本桌面工具'
          releaseDraft: true
          prerelease: false
          args: --target universal-apple-darwin

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust stable
        uses: dtolnay/rust-toolchain@stable

      - name: Rust cache
        uses: Swatinem/rust-cache@v2
        with:
          workspaces: './src-tauri -> target'

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install frontend dependencies
        run: npm install

      - name: Build Tauri app
        uses: tauri-apps/tauri-action@v0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tagName: ${{ github.ref_name }}
          releaseName: 'WhisperDesktop ${{ github.ref_name }}'
          releaseBody: '语音/视频转文本桌面工具'
          releaseDraft: true
          prerelease: false
```

- [ ] **Step 2: 推送 tag 触发构建**

```bash
git tag v0.1.0
git push origin v0.1.0
```

期望：macOS Universal DMG + Windows NSIS 安装包自动构建并上传到 GitHub Release Draft

- [ ] **Step 3: Commit**

```bash
git add .github/
git commit -m "ci: add multi-platform GitHub Actions build workflow"
```

---

## 注意事项 & 已知问题

### ffmpeg 静态二进制来源
- macOS: https://evermeet.cx/ffmpeg/ （静态编译，无依赖）
- Windows: https://www.gyan.dev/ffmpeg/builds/ （essentials build，约 40MB）
- 每次应用发布时，建议更新到最新的 ffmpeg 稳定版

### Apple Silicon / Intel 通用包
使用 `--target universal-apple-darwin` 编译通用包，同时兼容两种架构。whisper.cpp 的 Metal GPU 加速在通用包中需要在运行时动态选择，建议首版先以 CPU 模式发布，Metal 支持作为后续优化。

### 在线 URL 限制
- 仅支持直链（直接返回媒体文件的 URL），不支持 YouTube / B站 等需要解析的页面链接
- 服务器需允许无需认证的 GET 请求
- 如需支持带认证的 URL，可在后续版本中添加自定义 Headers 输入

### 模型下载镜像
默认使用国内镜像 `hf-mirror.com`，海外用户可在 `model.rs` 中替换为：
```
https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin
```

### Windows 代码签名
发布正式版本前需要 EV 代码签名证书，否则 Windows SmartScreen 会拦截安装。可在 CI 中配置 `TAURI_SIGNING_PRIVATE_KEY` 等环境变量实现自动签名。

### 转写进度回调 API 版本
`whisper-rs` 的 `set_progress_callback` 接口在不同 minor 版本可能有变化，如编译报错，查阅对应版本文档调整回调签名。

---

## 验收标准

- [ ] macOS 用户双击 .dmg 安装后可直接打开，无需安装 Python/Node/Rust/ffmpeg
- [ ] Windows 用户双击 .exe 安装后可直接打开
- [ ] **本地文件**：拖拽音频/视频文件 → 文件名显示 → 点击转写 → 显示文本结果
- [ ] **文件选择器**：点击拖拽区域 → 系统文件对话框 → 选择文件 → 正常转写
- [ ] **在线 URL**：切换到 URL 标签 → 输入直链 → 显示下载进度 → 转写 → 显示结果
- [ ] 导出 TXT 文件内容正确
- [ ] 导出 SRT 文件时间戳格式正确（HH:MM:SS,mmm）
- [ ] 模型未下载时提示下载，下载进度条正常显示
- [ ] 转写过程中进度条有更新，完成后隐藏
- [ ] 快速连点「开始转写」不会启动多个并发任务（第二次点击应提示任务进行中）
- [ ] 网络下载失败时给出明确错误提示，不留残缺临时文件
- [ ] 安装包体积：含 ffmpeg 不含模型 < 80MB
