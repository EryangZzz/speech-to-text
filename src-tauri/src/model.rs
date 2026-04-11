use anyhow::{Context, Result};
use sha2::{Digest, Sha256};
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use tauri::{AppHandle, Emitter, Manager};

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub enum ModelSize {
    Tiny,
    Base,
    Small,
    Medium,
    Big,
}

impl ModelSize {
    pub fn filename(&self) -> &'static str {
        match self {
            ModelSize::Tiny => "ggml-tiny.bin",
            ModelSize::Base => "ggml-base.bin",
            ModelSize::Small => "ggml-small.bin",
            ModelSize::Medium => "ggml-medium.bin",
            ModelSize::Big => "ggml-large-v3.bin",
        }
    }

    pub fn download_url(&self) -> &'static str {
        match self {
            ModelSize::Tiny => {
                "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin"
            }
            ModelSize::Base => {
                "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
            }
            ModelSize::Small => {
                "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"
            }
            ModelSize::Medium => {
                "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin"
            }
            ModelSize::Big => {
                "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin"
            }
        }
    }

    pub fn expected_size_bytes(&self) -> u64 {
        match self {
            ModelSize::Tiny => 75_000_000,
            ModelSize::Base => 142_000_000,
            ModelSize::Small => 466_000_000,
            ModelSize::Medium => 1_530_000_000,
            ModelSize::Big => 3_090_000_000,
        }
    }

    pub fn expected_sha256(&self) -> Option<&'static str> {
        match self {
            ModelSize::Tiny => None,
            ModelSize::Base => None,
            ModelSize::Small => None,
            ModelSize::Medium => None,
            ModelSize::Big => None,
        }
    }
}

pub fn models_dir(app: &AppHandle) -> Result<PathBuf> {
    let data_dir = app
        .path()
        .app_data_dir()
        .with_context(|| "无法获取 AppData 目录")?;
    let dir = data_dir.join("models");
    std::fs::create_dir_all(&dir)?;
    Ok(dir)
}

pub fn model_path(app: &AppHandle, size: &ModelSize) -> Result<PathBuf> {
    Ok(models_dir(app)?.join(size.filename()))
}

pub fn model_exists(app: &AppHandle, size: &ModelSize) -> Result<bool> {
    let path = model_path(app, size)?;
    if !path.exists() {
        return Ok(false);
    }
    let actual_size = std::fs::metadata(path)?.len();
    let threshold = size.expected_size_bytes() * 9 / 10;
    Ok(actual_size >= threshold)
}

pub async fn download_model(app: AppHandle, size: ModelSize) -> Result<PathBuf> {
    use futures_util::StreamExt;
    use reqwest::{Client, StatusCode};

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
        .timeout(std::time::Duration::from_secs(3600))
        .build()?;

    let mut request = client.get(url);
    if resumed > 0 {
        request = request.header("Range", format!("bytes={}-", resumed));
    }

    let response = request
        .send()
        .await
        .with_context(|| format!("连接模型下载地址失败: {}", url))?;

    if !(response.status().is_success() || response.status() == StatusCode::PARTIAL_CONTENT) {
        anyhow::bail!("下载请求失败，HTTP {}", response.status());
    }

    let fresh_start = resumed > 0 && response.status() == StatusCode::OK;
    if fresh_start {
        let _ = std::fs::remove_file(&tmp_path);
    }

    let start = if fresh_start { 0 } else { resumed };
    let total = response
        .content_length()
        .unwrap_or(expected.saturating_sub(start))
        + start;

    let mut downloaded = start;
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

        let _ = app.emit(
            "model-download-progress",
            serde_json::json!({
                "downloaded": downloaded,
                "total": total,
                "percent": percent,
            }),
        );
    }
    file.flush()?;
    drop(file);

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

    if let Some(expected_hash) = size.expected_sha256() {
        let mut hasher = Sha256::new();
        let bytes = std::fs::read(&tmp_path)?;
        hasher.update(bytes);
        let actual_hash = format!("{:x}", hasher.finalize());
        if actual_hash != expected_hash {
            let _ = std::fs::remove_file(&tmp_path);
            anyhow::bail!("模型哈希校验失败，文件已删除，请重试下载");
        }
    }

    std::fs::rename(&tmp_path, &dest).with_context(|| "模型文件重命名失败")?;

    Ok(dest)
}
