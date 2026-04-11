use anyhow::{Context, Result};
use futures_util::StreamExt;
use reqwest::Client;
use std::io::Write;
use std::path::PathBuf;
use tauri::{AppHandle, Emitter};
use tempfile::Builder;

pub async fn download_media_from_url(app: AppHandle, url: String) -> Result<PathBuf> {
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

    let ext = guess_extension(&url, &response);

    let tmp_file = Builder::new()
        .prefix("whisper_media_")
        .suffix(&format!(".{}", ext))
        .tempfile()
        .with_context(|| "创建媒体临时文件失败")?;

    let (mut file, tmp_path) = tmp_file.keep().with_context(|| "持久化媒体临时文件失败")?;

    let total = response.content_length();
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
            _ => (0.0, true),
        };

        let _ = app.emit(
            "media-download-progress",
            serde_json::json!({
                "downloaded": downloaded,
                "total": total.unwrap_or(0),
                "percent": percent,
                "indeterminate": indeterminate,
            }),
        );
    }

    file.flush()?;
    drop(file);

    if downloaded == 0 {
        let _ = std::fs::remove_file(&tmp_path);
        anyhow::bail!("下载的媒体文件为空: {}", url);
    }

    Ok(tmp_path)
}

fn guess_extension(url: &str, response: &reqwest::Response) -> String {
    if let Some(ct) = response.headers().get("content-type") {
        if let Ok(ct_str) = ct.to_str() {
            let ext = match ct_str.split(';').next().unwrap_or("").trim() {
                "audio/mpeg" | "audio/mp3" => "mp3",
                "audio/mp4" | "video/mp4" => "mp4",
                "audio/x-m4a" | "audio/m4a" => "m4a",
                "audio/ogg" | "video/ogg" => "ogg",
                "audio/flac" => "flac",
                "audio/wav" | "audio/x-wav" => "wav",
                "video/webm" => "webm",
                "video/x-matroska" => "mkv",
                _ => "",
            };
            if !ext.is_empty() {
                return ext.to_string();
            }
        }
    }

    if let Some(last_segment) = url.split('?').next().and_then(|u| u.split('/').next_back()) {
        if let Some(dot_pos) = last_segment.rfind('.') {
            let ext = &last_segment[dot_pos + 1..];
            if matches!(
                ext,
                "mp3" | "mp4" | "m4a" | "ogg" | "flac" | "wav" | "webm" | "mkv" | "avi" | "mov"
            ) {
                return ext.to_string();
            }
        }
    }

    "mp4".to_string()
}
