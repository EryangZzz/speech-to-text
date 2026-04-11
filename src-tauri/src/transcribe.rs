use anyhow::{Context, Result};
use tauri::{AppHandle, Emitter};
use whisper_rs::{FullParams, SamplingStrategy, WhisperContext, WhisperContextParameters};

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Segment {
    pub start_ms: i64,
    pub end_ms: i64,
    pub text: String,
}

#[derive(Debug, serde::Deserialize)]
pub struct TranscribeOptions {
    pub model_path: String,
    pub audio_path: String,
    pub language: Option<String>,
    pub translate: bool,
}

pub fn transcribe(app: AppHandle, opts: TranscribeOptions) -> Result<Vec<Segment>> {
    let ctx =
        WhisperContext::new_with_params(&opts.model_path, WhisperContextParameters::default())
            .with_context(|| format!("无法加载模型: {}", opts.model_path))?;

    let samples = crate::audio::decode_audio(&app, &opts.audio_path)
        .with_context(|| format!("音视频解码失败: {}", opts.audio_path))?;

    let mut params = FullParams::new(SamplingStrategy::Greedy { best_of: 1 });

    match opts.language.as_deref() {
        Some(lang) => params.set_language(Some(lang)),
        None => params.set_language(None),
    }

    params.set_translate(opts.translate);
    params.set_print_realtime(false);
    params.set_print_progress(false);
    params.set_print_timestamps(true);

    let app_clone = app.clone();
    let cb: Box<dyn FnMut(i32)> = Box::new(move |progress: i32| {
        let _ = app_clone.emit(
            "transcribe-progress",
            serde_json::json!({ "percent": progress }),
        );
    });
    params.set_progress_callback_safe::<Option<Box<dyn FnMut(i32)>>, Box<dyn FnMut(i32)>>(Some(cb));

    let mut state = ctx
        .create_state()
        .with_context(|| "创建 whisper state 失败")?;
    state
        .full(params, &samples)
        .with_context(|| "whisper 推理失败")?;

    let num_segments = state.full_n_segments().with_context(|| "获取片段数失败")?;
    let mut segments = Vec::with_capacity(num_segments as usize);

    for i in 0..num_segments {
        let text = state
            .full_get_segment_text(i)
            .with_context(|| format!("获取第 {} 段文本失败", i))?;
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
