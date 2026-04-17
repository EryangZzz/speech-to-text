# WhisperDesktop

WhisperDesktop is a local desktop speech / video transcription app built with Tauri + Rust + Vue 3.

The goal is a practical desktop tool that supports local files, remote URL fetching, Whisper model management, and TXT / SRT export.

## Features

- Drag and drop local audio / video files
- Download media from URL before transcription
- Download, open, and clear Whisper models
- `memory`, `balanced`, and `fast` performance modes
- Full timeline preview plus editable transcript text
- Export to TXT / SRT
- Packaging for macOS Apple Silicon, macOS Intel, and Windows x64

## Stack

- Frontend: Vue 3 + TypeScript + Vite
- Desktop shell: Tauri 2
- Backend: Rust
- Inference: `whisper-rs`
- Audio decoding: bundled `ffmpeg`

## Project Layout

- `src/`: Vue frontend
- `src-tauri/src/`: Rust commands, transcription, model, and export logic
- `src-tauri/resources/`: platform-specific ffmpeg binaries
- `scripts/`: build, resource preparation, and packaging helpers
- `.github/workflows/build.yml`: multi-platform GitHub Actions workflow

## Requirements

### Common

- Node.js 20+
- Rust stable
- `npm`

### macOS development / packaging

- Xcode Command Line Tools
- `cmake`

Install example:

```bash
xcode-select --install
brew install cmake
```

### Windows local packaging

- Windows 10/11 x64
- PowerShell 5+ or PowerShell 7+
- Visual Studio C++ Build Tools / Rust Windows toolchain

Notes:

- `npm run build:win` automatically downloads and prepares `ffmpeg-windows-x64.exe`
- Windows NSIS installers cannot be built natively on macOS

## Install Dependencies

```bash
npm install
```

## Run in Development

```bash
npm run tauri dev
```

Notes:

- In development, the frontend is served by Vite
- The first Rust build can take a while

## How the App Works

### Input Sources

- Local file: drag and drop, or click to choose a file
- URL: provide a directly downloadable audio / video URL

### Model and Language

- Model sizes: `tiny`, `base`, `small`, `medium`, `big`
- Language: auto-detect or select manually
- Performance modes:
  - `memory`: lower memory usage, slower
  - `balanced`: default recommended mode
  - `fast`: faster, with one automatic fallback to `balanced` if inference fails

### Results

- The main transcript text area is editable
- The timeline panel shows all segments
- TXT export uses the edited text when available
- SRT export always uses the original segment timestamps

## Model Storage and Cleanup

Models are stored in the `models` directory under the app data directory.

Current app identifier:

```text
com.example.whisper-desktop
```

Default paths:

- macOS: `~/Library/Application Support/com.example.whisper-desktop/models`
- Windows: `%APPDATA%\com.example.whisper-desktop\models`

The app UI provides:

- Open model directory
- Clear models

Uninstall behavior:

- macOS: removing the app does not remove downloaded models automatically
- Windows: the NSIS uninstall hook attempts to remove `%APPDATA%\com.example.whisper-desktop\models`

## Packaging Resources

Packaging requires the matching ffmpeg binary for the target platform:

- `src-tauri/resources/ffmpeg-macos-arm64`
- `src-tauri/resources/ffmpeg-macos-x64`
- `src-tauri/resources/ffmpeg-windows-x64.exe`

Current strategy:

- macOS arm64: copied from `ffmpeg-static`
- macOS x64: prepared by script or CI
- Windows x64: downloaded automatically in local Windows builds and in GitHub Actions

## Manual Packaging

### macOS Apple Silicon

```bash
npm run build:mac:arm
```

Main output:

- `src-tauri/target/aarch64-apple-darwin/release/bundle/dmg/WhisperDesktop_0.1.0_aarch64.dmg`

### macOS Intel

```bash
npm run build:mac:intel
```

Main output:

- `src-tauri/target/x86_64-apple-darwin/release/bundle/dmg/WhisperDesktop_0.1.0_x64.dmg`

### macOS Universal

```bash
npm run build:mac:universal
```

Notes:

- Both Rust targets must be installed
- Both macOS ffmpeg binaries must be available

### Windows x64

Run this on a Windows machine:

```bash
npm run build:win
```

Main output:

- `src-tauri/target/x86_64-pc-windows-msvc/release/bundle/nsis/*.exe`

## Zip the `.app` for Distribution

If you want to distribute a `.app` instead of a `.dmg`, zip it first. Do not send the raw `.app` bundle directly.

```bash
npm run package:mac:zip:arm
npm run package:mac:zip:intel
```

## GitHub Actions Packaging

Workflow file:

```text
.github/workflows/build.yml
```

Current workflow behavior:

- Builds macOS Apple Silicon
- Builds macOS Intel
- Builds Windows x64 NSIS installer
- Supports `workflow_dispatch`
- Uploads to a Draft Release for `v*` tags
- Uploads Actions Artifacts for manual non-tag runs

Release trigger example:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## About Signing and Notarization

This project currently does not sign or notarize macOS builds.

That means:

- macOS may block the app on first launch
- This does not necessarily mean the app is corrupted
- The current delivery model expects users to allow the app manually in Privacy & Security

This is an intentional project decision for now.

## FAQ

### 1. `cargo` fails with `cmake not installed`

Install `cmake` and retry:

```bash
brew install cmake
```

### 2. Why do I not get a Windows `.exe` on macOS

Because macOS cannot natively build Windows NSIS installers.

Use:

- A Windows machine with `npm run build:win`
- Or the Windows GitHub Actions job

### 3. Why does `build:win` say it must run on Windows

That is an intentional guard.

Reasons:

- The build needs to prepare `ffmpeg-windows-x64.exe`
- The Windows Rust / linker / NSIS environment is required

### 4. Why should I not send the raw `.app` folder directly

Many transfer tools break macOS app bundle metadata.

Recommended:

1. Prefer `.dmg`
2. Or use `npm run package:mac:zip:arm` / `npm run package:mac:zip:intel`

### 5. What if macOS says the app is damaged or from an unidentified developer

This is common for unsigned / unnotarized apps.

Recommended user flow:

1. Right-click the app in Finder and choose `Open`
2. If still blocked, go to `System Settings -> Privacy & Security`
3. Find the blocked app message and click `Open Anyway` or the equivalent button

If necessary, use this temporary command:

```bash
xattr -dr com.apple.quarantine /Applications/WhisperDesktop.app
```

Notes:

- This is a temporary workaround for testing distribution
- Since this project does not currently sign or notarize, this step is expected in some environments

### 6. Why are models still there after uninstall on Windows

The uninstall hook attempts to remove the model directory, but the final result still depends on:

- File locks
- Manual user changes
- Runtime state during uninstall

To verify manually, check:

```text
%APPDATA%\com.example.whisper-desktop\models
```

### 7. Why did transcription finish with no visible text

Possible reasons:

- The media contains no recognizable speech
- Non-speech markers such as `[music]` / `[applause]` were filtered out

Try:

- Disable non-speech filtering and retry
- Use a larger model
- Select the language explicitly
