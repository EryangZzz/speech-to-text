use crate::transcribe::Segment;
use anyhow::Result;

pub fn to_txt(segments: &[Segment]) -> String {
    segments
        .iter()
        .map(|s| s.text.as_str())
        .collect::<Vec<_>>()
        .join("\n")
}

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

fn format_srt_time(ms: i64) -> String {
    let ms = ms.max(0);
    let hours = ms / 3_600_000;
    let minutes = (ms % 3_600_000) / 60_000;
    let seconds = (ms % 60_000) / 1_000;
    let millis = ms % 1_000;
    format!("{:02}:{:02}:{:02},{:03}", hours, minutes, seconds, millis)
}

pub fn write_file(path: &str, content: &str) -> Result<()> {
    std::fs::write(path, content.as_bytes())?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::transcribe::Segment;

    fn seg(start_ms: i64, end_ms: i64, text: &str) -> Segment {
        Segment {
            start_ms,
            end_ms,
            text: text.to_string(),
        }
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
