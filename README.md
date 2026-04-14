# WhisperDesktop

基于 Tauri + Rust + Vue 3 的本地语音/视频转文本桌面应用。

支持：
- 本地文件拖拽/选择
- URL 下载后转写
- Whisper 模型下载与管理
- 导出 TXT / SRT

## 1. 环境要求

### macOS 开发/打包
- Node.js 20+
- Rust stable
- `cmake`（`whisper-rs` 构建依赖）
- Xcode Command Line Tools

安装示例：
```bash
xcode-select --install
brew install cmake
```

### Windows 打包
- 建议在 GitHub Actions（`windows-latest`）中构建
- 或在 Windows 本机执行 `npm run build:win`

## 2. 安装依赖

```bash
npm install
```

## 3. 本地开发运行

```bash
npm run tauri dev
```

## 4. 模型存储与卸载说明

### 模型下载位置
模型下载到应用数据目录 `models` 子目录。
当前应用标识符是 `com.example.whisper-desktop`，默认路径：
- macOS: `~/Library/Application Support/com.example.whisper-desktop/models`
- Windows: `%APPDATA%\\com.example.whisper-desktop\\models`

### 用户可见/可清理
应用内已提供：
- 显示模型目录
- 打开模型目录
- 清理模型（删除已下载模型）

### 卸载行为
- macOS (`.dmg` 拖拽安装)：系统不会自动清理用户数据目录，建议在应用内点“清理模型”后再卸载。
- Windows (NSIS)：已配置卸载钩子，卸载时会删除 `%APPDATA%\\com.example.whisper-desktop\\models`。

## 5. 资源文件（ffmpeg）

打包前需要准备对应平台 ffmpeg：
- `src-tauri/resources/ffmpeg-macos-arm64`
- `src-tauri/resources/ffmpeg-macos-x64`（仅 universal mac 包需要）
- `src-tauri/resources/ffmpeg-windows-x64.exe`

项目提供了按平台切换资源的脚本，避免把多平台资源打进同一个安装包。

## 6. 打包说明

### macOS（当前机器可直接执行）
```bash
npm run build:mac
```
产物：
- `src-tauri/target/release/bundle/macos/WhisperDesktop.app`
- `src-tauri/target/release/bundle/dmg/WhisperDesktop_0.1.0_aarch64.dmg`

### macOS Intel（x64）
```bash
npm run build:mac:intel
```
产物：
- `src-tauri/target/x86_64-apple-darwin/release/bundle/macos/WhisperDesktop.app`
- `src-tauri/target/x86_64-apple-darwin/release/bundle/dmg/WhisperDesktop_0.1.0_x64.dmg`

如果要分享 `.app`（不是 `.dmg`），请不要直接拷贝文件夹，先打 zip：
```bash
npm run package:mac:zip
```
产物：
- `src-tauri/target/release/bundle/macos/WhisperDesktop.app.zip`

### macOS Universal（CI 推荐）
```bash
npm run prepare:bundle:mac:universal
npm run tauri build -- --target universal-apple-darwin
```

### Windows（本机为 Windows 时）
```bash
npm run build:win
```
产物（Windows 机器）：
- `src-tauri/target/release/bundle/nsis/*.exe`

## 7. GitHub Actions 自动打包

工作流文件：`.github/workflows/build.yml`

已包含：
- macOS arm64 产物构建
- macOS Intel (x64) 产物构建
- Windows x64 NSIS `.exe` 构建
- 构建前自动准备 ffmpeg 资源
- macOS 自动签名 + 自动公证（当 secrets 配置完整时）

### macOS 自动签名/公证所需 Secrets

在 GitHub 仓库 `Settings -> Secrets and variables -> Actions` 添加：
- `APPLE_CERTIFICATE`：Developer ID Application 证书（`.p12`）的 base64 内容
- `APPLE_CERTIFICATE_PASSWORD`：`.p12` 密码
- `APPLE_SIGNING_IDENTITY`：签名身份，例如 `Developer ID Application: Your Name (TEAMID)`
- `APPLE_ID`：Apple ID 邮箱
- `APPLE_PASSWORD`：App-specific password（不是 Apple 登录密码）
- `APPLE_TEAM_ID`：Apple Developer Team ID

注意：没有这些 secrets 时，流程仍可构建，但不会完成正式签名/公证。

触发方式：
```bash
git tag v0.1.0
git push origin v0.1.0
```

## 8. 常见问题

### `cargo check` 报错 `cmake not installed`
安装 `cmake` 后重试：
```bash
brew install cmake
```

### 为什么本地没有 Windows `.exe`
因为 macOS 不能原生产出 Windows NSIS 包。请使用：
- Windows 本机执行 `npm run build:win`
- 或 GitHub Actions 的 Windows job（推荐）

### `bundle/macos` 目录怎么分享给别人
不建议直接发送 `WhisperDesktop.app` 文件夹（很多传输工具会破坏元数据）。推荐：
1. 优先分享 `.dmg`
2. 或使用 `npm run package:mac:zip` 生成 zip 后再分享

### 给别人后提示“已损坏”怎么办
这通常是 Gatekeeper 对未公证应用的拦截，不一定是文件真的损坏。  

优先尝试图形化方式（无命令行）：
1. 在 Finder 中右键 `WhisperDesktop.app` -> `打开`
2. 弹窗里点击 `打开`
3. 如果仍被拦截，进入 `系统设置 -> 隐私与安全性`
4. 在页面底部找到被拦截提示，点击 `仍要打开` / `允许打开`

如果看不到 `仍要打开` / `允许打开`，再使用命令行方式（临时测试）：
```bash
xattr -dr com.apple.quarantine /Applications/WhisperDesktop.app
```
然后再打开应用。

还可以临时开启“允许任何来源”（不推荐普通用户长期使用）：
```bash
sudo spctl --master-disable
```
执行后到 `系统设置 -> 隐私与安全性`，可看到“允许从以下位置下载的 App：任何来源”选项。  
测试完成后建议恢复：
```bash
sudo spctl --master-enable
```

注意：
- `xattr` / “任何来源”都属于临时绕过方式，仅用于测试分发。
- “允许任何来源”会降低系统安全性，不建议长期开启。
- 正式发布应使用 Developer ID 签名 + Apple notarization，避免用户手动执行命令。
