# WhisperDesktop

基于 Tauri + Rust + Vue 3 的本地语音 / 视频转文本桌面应用。

项目目标是提供一个可直接交付的桌面转写工具，支持本地文件、URL 拉取、Whisper 模型管理，以及 TXT / SRT 导出。

## 功能概览

- 本地音视频文件拖拽或文件选择
- 远程 URL 下载后转写
- Whisper 模型下载、打开目录、清理模型
- `memory` / `balanced` / `fast` 三种性能模式
- 全量时间轴预览与可编辑文本结果区
- 导出 TXT / SRT
- macOS Apple Silicon、macOS Intel、Windows x64 三端打包

## 技术栈

- 前端：Vue 3 + TypeScript + Vite
- 桌面容器：Tauri 2
- 后端：Rust
- 推理：`whisper-rs`
- 音频解码：内置打包的 `ffmpeg`

## 目录说明

- `src/`：Vue 前端界面
- `src-tauri/src/`：Rust 命令、转写、模型、导出逻辑
- `src-tauri/resources/`：平台相关 ffmpeg 二进制
- `scripts/`：构建、资源准备、打包辅助脚本
- `.github/workflows/build.yml`：GitHub Actions 多平台打包工作流

## 开发环境要求

### 通用

- Node.js 20+
- Rust stable
- `npm`

### macOS 开发 / 打包

- Xcode Command Line Tools
- `cmake`

安装示例：

```bash
xcode-select --install
brew install cmake
```

### Windows 本地打包

- Windows 10/11 x64
- PowerShell 5+ 或 PowerShell 7+
- Visual Studio C++ Build Tools / Rust Windows toolchain

说明：
- `npm run build:win` 会在 Windows 上自动下载并准备 `ffmpeg-windows-x64.exe`
- 在 macOS 上不能原生生成 Windows NSIS 安装包

## 安装依赖

```bash
npm install
```

## 本地开发启动

```bash
npm run tauri dev
```

说明：
- 开发模式下前端由 Vite 提供，Tauri 会自动连接到本地 dev server
- 首次编译 Rust 依赖耗时会比较长

## 应用使用说明

### 输入源

- 本地文件：拖拽文件到界面，或点击选择
- 在线 URL：输入可直接下载的音视频链接

### 模型与语言

- 模型规格：`tiny` / `base` / `small` / `medium` / `big`
- 语言：支持自动检测，也可手动指定
- 性能模式：
  - `memory`：更省内存，速度更慢
  - `balanced`：默认推荐
  - `fast`：更快，失败时会自动回退一次 `balanced`

### 结果区

- 左侧文本区可直接编辑
- 右侧时间轴显示全部分段
- 导出 TXT 时优先使用当前编辑后的文本
- 导出 SRT 时始终使用原始分段时间轴

## 模型存储位置与清理

模型下载到应用数据目录中的 `models` 子目录。

当前应用标识符：

```text
com.example.whisper-desktop
```

默认路径：

- macOS：`~/Library/Application Support/com.example.whisper-desktop/models`
- Windows：`%APPDATA%\com.example.whisper-desktop\models`

应用内提供：

- 打开模型目录
- 清理模型

卸载行为：

- macOS：删除应用本体不会自动清理模型目录
- Windows：NSIS 卸载钩子会尝试删除 `%APPDATA%\com.example.whisper-desktop\models`

## 打包资源说明

打包前需要准备与目标平台匹配的 ffmpeg：

- `src-tauri/resources/ffmpeg-macos-arm64`
- `src-tauri/resources/ffmpeg-macos-x64`
- `src-tauri/resources/ffmpeg-windows-x64.exe`

当前策略：

- macOS arm64：默认从 `ffmpeg-static` 复制
- macOS x64：通过脚本或 CI 准备 x64 ffmpeg
- Windows x64：本地 Windows 构建和 GitHub Actions 都会自动下载并准备 ffmpeg

## 手动打包

### macOS Apple Silicon

```bash
npm run build:mac:arm
```

主要产物：

- `src-tauri/target/aarch64-apple-darwin/release/bundle/dmg/WhisperDesktop_0.1.0_aarch64.dmg`

### macOS Intel

```bash
npm run build:mac:intel
```

主要产物：

- `src-tauri/target/x86_64-apple-darwin/release/bundle/dmg/WhisperDesktop_0.1.0_x64.dmg`

### macOS Universal

```bash
npm run build:mac:universal
```

说明：
- 需要先安装 `aarch64-apple-darwin` 与 `x86_64-apple-darwin` 两个 Rust target
- 需要同时准备 arm64 / x64 两份 ffmpeg 资源

### Windows x64

请在 Windows 机器上执行：

```bash
npm run build:win
```

主要产物：

- `src-tauri/target/x86_64-pc-windows-msvc/release/bundle/nsis/*.exe`

## macOS `.app` 手动压缩

如果你要分发 `.app` 而不是 `.dmg`，请先打 zip，不要直接拷贝 `.app` 文件夹。

```bash
npm run package:mac:zip:arm
npm run package:mac:zip:intel
```

## GitHub Actions 自动打包

工作流文件：

```text
.github/workflows/build.yml
```

当前工作流支持：

- macOS Apple Silicon 构建
- macOS Intel 构建
- Windows x64 NSIS 构建
- `workflow_dispatch` 手动触发
- `v*` tag 触发 Draft Release 上传
- 非 tag 手动触发时上传 Actions Artifact

触发发布示例：

```bash
git tag v0.1.0
git push origin v0.1.0
```

## 关于签名 / 公证

当前项目暂不做 macOS 签名与公证。

这意味着：

- 用户首次打开应用时，macOS 可能阻止运行
- 这不代表安装包损坏，通常只是 Gatekeeper 拦截
- 当前分发策略是让用户在系统“隐私与安全性”中手动放行

这是当前项目的明确选择，而不是构建失败。

## 常见问题

### 1. `cargo` / Rust 编译报错 `cmake not installed`

安装后重试：

```bash
brew install cmake
```

### 2. 为什么在 macOS 上没有 Windows `.exe`

因为 macOS 不能原生产出 Windows NSIS 安装包。

正确做法：

- 在 Windows 本机运行 `npm run build:win`
- 或使用 GitHub Actions 的 Windows job

### 3. 为什么 `build:win` 提示必须在 Windows 上运行

这是当前脚本的主动保护。

原因：

- Windows 包必须在 Windows 环境准备 `ffmpeg-windows-x64.exe`
- 同时需要 Windows Rust / linker / NSIS 环境

### 4. 打包后分享 `.app` 为什么不推荐直接发送文件夹

因为很多传输方式会破坏 macOS 应用包元数据。

建议：

1. 优先分享 `.dmg`
2. 或使用 `npm run package:mac:zip:arm` / `npm run package:mac:zip:intel`

### 5. 用户双击后提示“已损坏”或“无法验证开发者”

这是未签名 / 未公证应用的常见系统拦截。

推荐用户操作：

1. 在 Finder 中右键应用，选择“打开”
2. 如果仍被拦截，进入“系统设置 -> 隐私与安全性”
3. 在底部找到被拦截提示后点击“仍要打开”或类似按钮

如果仍无法打开，可临时执行：

```bash
xattr -dr com.apple.quarantine /Applications/WhisperDesktop.app
```

说明：
- 这是测试分发时的临时绕过方式
- 当前项目不做签名 / 公证，因此需要接受这一步的存在

### 6. Windows 卸载后模型为什么还在 / 不在

当前 NSIS 卸载钩子会尝试删除模型目录，但最终结果仍取决于：

- 文件是否被占用
- 用户是否手动改过路径或数据

若要完全确认，可手动检查：

```text
%APPDATA%\com.example.whisper-desktop\models
```

### 7. 转写完成但没有任何文本

可能原因：

- 音频本身无可识别语音
- 过滤了类似 `[music]` / `[applause]` 的非语音标签

建议：

- 关闭“过滤非语音标签”后重试
- 改用更大的模型
- 明确指定语言
