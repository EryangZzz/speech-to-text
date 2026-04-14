#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod audio;
mod export;
mod media_fetch;
mod model;
mod transcribe;

use model::{download_model, model_exists, model_path, ModelSize};
use std::path::PathBuf;
use std::sync::Arc;
use tauri::{AppHandle, State};
use tokio::sync::Mutex;

struct AppState {
    transcribing: Arc<Mutex<bool>>,
}

#[tauri::command]
async fn check_model(app: AppHandle, size: String) -> Result<bool, String> {
    let size = parse_model_size(&size)?;
    model_exists(&app, &size).map_err(|e| e.to_string())
}

#[tauri::command]
async fn download_model_cmd(app: AppHandle, size: String) -> Result<(), String> {
    let size = parse_model_size(&size)?;
    download_model(app, size)
        .await
        .map(|_| ())
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn get_models_dir(app: AppHandle) -> Result<String, String> {
    let dir = model::models_dir(&app).map_err(|e| e.to_string())?;
    Ok(dir.to_string_lossy().to_string())
}

#[tauri::command]
async fn open_models_dir(app: AppHandle) -> Result<(), String> {
    let dir = model::models_dir(&app).map_err(|e| e.to_string())?;
    open_dir_in_file_manager(&dir).map_err(|e| e.to_string())
}

#[tauri::command]
async fn clear_models(app: AppHandle) -> Result<(), String> {
    let dir = model::models_dir(&app).map_err(|e| e.to_string())?;
    if dir.exists() {
        std::fs::remove_dir_all(&dir).map_err(|e| e.to_string())?;
    }
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
async fn transcribe_audio(
    app: AppHandle,
    state: State<'_, AppState>,
    audio_input: String,
    input_type: String,
    model_size: String,
    language: Option<String>,
    clean_noise: Option<bool>,
) -> Result<Vec<transcribe::Segment>, String> {
    {
        let mut is_transcribing = state.transcribing.lock().await;
        if *is_transcribing {
            return Err("已有转写任务进行中，请等待完成后再试".to_string());
        }
        *is_transcribing = true;
    }

    let flag = state.transcribing.clone();
    let result = do_transcribe(
        app,
        audio_input,
        input_type,
        model_size,
        language,
        clean_noise.unwrap_or(true),
    )
    .await;
    *flag.lock().await = false;

    result
}

async fn do_transcribe(
    app: AppHandle,
    audio_input: String,
    input_type: String,
    model_size: String,
    language: Option<String>,
    clean_noise: bool,
) -> Result<Vec<transcribe::Segment>, String> {
    let size = parse_model_size(&model_size)?;
    let exists = model_exists(&app, &size).map_err(|e| e.to_string())?;
    if !exists {
        return Err(format!("模型未下载: {}", model_size));
    }
    let mp = model_path(&app, &size).map_err(|e| e.to_string())?;

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
        clean_noise,
    };

    let app_clone = app.clone();
    let result = tokio::task::spawn_blocking(move || transcribe::transcribe(app_clone, opts))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string());

    if is_temp {
        let _ = std::fs::remove_file(&audio_path);
    }

    result
}

#[tauri::command]
async fn export_result(
    segments: Vec<transcribe::Segment>,
    result_text: Option<String>,
    output_path: String,
    format: String,
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
        "tiny" => Ok(ModelSize::Tiny),
        "base" => Ok(ModelSize::Base),
        "small" => Ok(ModelSize::Small),
        "medium" => Ok(ModelSize::Medium),
        "big" | "large" | "large-v3" => Ok(ModelSize::Big),
        other => Err(format!("未知模型规格: {}", other)),
    }
}

fn open_dir_in_file_manager(path: &PathBuf) -> anyhow::Result<()> {
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open").arg(path).spawn()?;
    }
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("explorer").arg(path).spawn()?;
    }
    #[cfg(target_os = "linux")]
    {
        std::process::Command::new("xdg-open").arg(path).spawn()?;
    }
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(AppState {
            transcribing: Arc::new(Mutex::new(false)),
        })
        .invoke_handler(tauri::generate_handler![
            check_model,
            download_model_cmd,
            get_models_dir,
            open_models_dir,
            clear_models,
            transcribe_audio,
            export_result,
        ])
        .run(tauri::generate_context!())
        .expect("Tauri 启动失败");
}
