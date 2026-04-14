# WhisperDesktop

A local desktop speech/video-to-text app built with Tauri + Rust + Vue 3.

Supports:
- Local file drag-and-drop / file picker
- URL download and transcription
- Whisper model download and management
- Export to TXT / SRT

## 1. Requirements

### macOS development/packaging
- Node.js 20+
- Rust stable
- `cmake` (required by `whisper-rs` build)
- Xcode Command Line Tools

Install example:
```bash
xcode-select --install
brew install cmake
```

### Windows packaging
- Recommended: build in GitHub Actions (`windows-latest`)
- Or run `npm run build:win` on a Windows machine

## 2. Install Dependencies

```bash
npm install
```

## 3. Run in Development

```bash
npm run tauri dev
```

## 4. Model Storage and Uninstall Behavior

### Model download location
Models are downloaded to the `models` subdirectory under the app data directory.
Current app identifier: `com.example.whisper-desktop`.
Default paths:
- macOS: `~/Library/Application Support/com.example.whisper-desktop/models`
- Windows: `%APPDATA%\\com.example.whisper-desktop\\models`

### User-visible / cleanup actions
The app UI provides:
- Show model directory
- Open model directory
- Clear models (delete downloaded models)

### Uninstall behavior
- macOS (`.dmg` drag-and-drop install): user data directory is not removed automatically. It is recommended to click "Clear Models" in the app before uninstalling.
- Windows (NSIS): uninstall hook is configured to remove `%APPDATA%\\com.example.whisper-desktop\\models`.

## 5. Resource Files (ffmpeg)

Before packaging, prepare platform-specific ffmpeg binaries:
- `src-tauri/resources/ffmpeg-macos-arm64`
- `src-tauri/resources/ffmpeg-macos-x64` (required only for universal mac package)
- `src-tauri/resources/ffmpeg-windows-x64.exe`

This project includes resource-switch scripts so each package only includes required platform resources.

## 6. Packaging

### macOS (can be built directly on current machine)
```bash
npm run build:mac
```
Outputs:
- `src-tauri/target/release/bundle/macos/WhisperDesktop.app`
- `src-tauri/target/release/bundle/dmg/WhisperDesktop_0.1.0_aarch64.dmg`

### macOS Intel (x64)
```bash
npm run build:mac:intel
```
Outputs:
- `src-tauri/target/x86_64-apple-darwin/release/bundle/macos/WhisperDesktop.app`
- `src-tauri/target/x86_64-apple-darwin/release/bundle/dmg/WhisperDesktop_0.1.0_x64.dmg`

If you want to share `.app` (instead of `.dmg`), do not copy the app folder directly. Package it as zip first:
```bash
npm run package:mac:zip
```
Output:
- `src-tauri/target/release/bundle/macos/WhisperDesktop.app.zip`

### macOS Universal (CI recommended)
```bash
npm run prepare:bundle:mac:universal
npm run tauri build -- --target universal-apple-darwin
```

### Windows (run on Windows machine)
```bash
npm run build:win
```
Output (on Windows machine):
- `src-tauri/target/release/bundle/nsis/*.exe`

## 7. GitHub Actions Auto Packaging

Workflow file: `.github/workflows/build.yml`

Included:
- macOS arm64 build
- macOS Intel (x64) build
- Windows x64 NSIS `.exe` build
- Automatic ffmpeg resource preparation before build
- macOS automatic signing + notarization (when all secrets are configured)

### Secrets required for macOS signing/notarization

In GitHub repo `Settings -> Secrets and variables -> Actions`, add:
- `APPLE_CERTIFICATE`: base64 content of Developer ID Application certificate (`.p12`)
- `APPLE_CERTIFICATE_PASSWORD`: password for `.p12`
- `APPLE_SIGNING_IDENTITY`: signing identity, for example `Developer ID Application: Your Name (TEAMID)`
- `APPLE_ID`: Apple ID email
- `APPLE_PASSWORD`: app-specific password (not Apple account login password)
- `APPLE_TEAM_ID`: Apple Developer Team ID

Note: if these secrets are not provided, build can still run, but formal signing/notarization will not be completed.

Trigger:
```bash
git tag v0.1.0
git push origin v0.1.0
```

## 8. FAQ

### `cargo check` error: `cmake not installed`
Install `cmake` and retry:
```bash
brew install cmake
```

### Why no Windows `.exe` on my local macOS build
macOS cannot natively produce Windows NSIS installers. Use:
- A Windows machine with `npm run build:win`
- Or GitHub Actions Windows job (recommended)

### How to share `bundle/macos` with others
Do not send `WhisperDesktop.app` folder directly (metadata may break during transfer). Recommended:
1. Prefer sharing `.dmg`
2. Or generate zip with `npm run package:mac:zip` and share the zip

### What if others see "App is damaged" on macOS
This is usually a Gatekeeper block on unsigned/unnotarized apps, not actual file corruption.

Try GUI-first (no command line):
1. In Finder, right-click `WhisperDesktop.app` -> `Open`
2. In the dialog, click `Open`
3. If still blocked, go to `System Settings -> Privacy & Security`
4. Find the blocked app message at the bottom, then click `Open Anyway` / `Allow`

If `Open Anyway` / `Allow` does not appear, use command line (temporary testing workaround):
```bash
xattr -dr com.apple.quarantine /Applications/WhisperDesktop.app
```
Then open the app again.

You may also temporarily enable "Allow apps from anywhere" (not recommended for normal users):
```bash
sudo spctl --master-disable
```
After this, in `System Settings -> Privacy & Security`, you should see the "Anywhere" option.
After testing, re-enable protection:
```bash
sudo spctl --master-enable
```

Notes:
- `xattr` / "Anywhere" are temporary bypasses for testing distribution only.
- "Allow from anywhere" reduces system security and should not be left enabled.
- For production distribution, use Developer ID signing + Apple notarization so users do not need manual commands.
