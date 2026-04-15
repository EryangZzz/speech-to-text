use anyhow::{Context, Result};
use std::path::PathBuf;
use std::process::Command;
use tauri::AppHandle;
use tauri::Manager;
use tempfile::NamedTempFile;

pub fn ffmpeg_path(app: &AppHandle) -> Result<PathBuf> {
    let resource_dir = app
        .path()
        .resource_dir()
        .with_context(|| "无法获取资源目录")?;

    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    let name = "ffmpeg-macos-arm64";
    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    let name = "ffmpeg-macos-x64";
    #[cfg(target_os = "windows")]
    let name = "ffmpeg-windows-x64.exe";
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    let name = "ffmpeg";

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

    let dev_candidates = [
        std::env::current_dir()
            .ok()
            .map(|p| p.join("resources").join(name)),
        std::env::current_dir()
            .ok()
            .map(|p| p.join("../resources").join(name)),
    ];

    for path in dev_candidates.into_iter().flatten() {
        if path.exists() {
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let mut perms = std::fs::metadata(&path)?.permissions();
                perms.set_mode(0o755);
                std::fs::set_permissions(&path, perms)?;
            }
            return Ok(path);
        }
    }

    anyhow::bail!("内嵌 ffmpeg 未找到，请检查 resources 目录是否包含目标平台二进制");
}

pub fn decode_audio(app: &AppHandle, file_path: &str) -> Result<Vec<f32>> {
    let ffmpeg = ffmpeg_path(app)?;
    let tmp_pcm = NamedTempFile::new().with_context(|| "创建 PCM 临时文件失败")?;
    let tmp_pcm_path = tmp_pcm.path().to_path_buf();
    let tmp_pcm_out = tmp_pcm_path.to_string_lossy().to_string();

    let output = Command::new(&ffmpeg)
        .args([
            "-y",
            "-threads",
            "0",
            "-i",
            file_path,
            "-vn",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-f",
            "f32le",
            tmp_pcm_out.as_str(),
        ])
        .output()
        .with_context(|| format!("执行 ffmpeg 失败: {:?}", ffmpeg))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("ffmpeg 解码失败: {}", stderr);
    }

    let raw = std::fs::read(&tmp_pcm_path).with_context(|| "读取 PCM 临时文件失败")?;
    if raw.len() % 4 != 0 {
        anyhow::bail!("PCM 数据长度异常: {}", raw.len());
    }

    let samples = raw
        .chunks_exact(4)
        .map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]]))
        .collect();

    Ok(samples)
}
