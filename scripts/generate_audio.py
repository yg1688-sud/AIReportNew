"""Generate Chinese voice-over audio for AIExport presentation video.

Uses Microsoft Edge TTS (free, no API key) — Xiaoxiao Natural voice.
Merges generated audio with the existing video file.
"""
import os
import sys
import time
import asyncio
import tempfile
import structlog

log = structlog.get_logger()

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
OUTPUT_DIR  = os.path.join(PROJECT_ROOT, "output")
VIDEO_IN    = os.path.join(OUTPUT_DIR, "AIExport_项目讲解.mp4")
VIDEO_OUT   = os.path.join(OUTPUT_DIR, "AIExport_项目讲解_配音版.mp4")
AUDIO_DIR   = os.path.join(OUTPUT_DIR, "audio_clips")

# ── Scene timing (must match generate_video.py) ──
SCENE_DURATION = 9.0     # seconds per scene
FPS = 24
FFMPEG = os.path.join(os.path.dirname(sys.executable), "Scripts", "ffmpeg.exe")
if not os.path.isfile(FFMPEG):
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# ── Narration text for each scene ──
# Keep each short enough to speak in < 8 seconds at normal Chinese pace
NARRATIONS = [
    # Scene 1 — Cover
    "AIExport，AI 智能导出与分析系统，将手工数据报表全面自动化。",

    # Scene 2 — Background
    "传统月报耗时两到四小时，AIExport 一键自动化，三十秒内完成。",

    # Scene 3 — Architecture
    "管道式架构：配置加载、数据导出、智能分析、报告生成，支持两种工作模式。",

    # Scene 4 — Export
    "功能一：YAML 配置驱动，密码环境变量保护，参数化查询防注入，一键导出。",

    # Scene 5 — Analysis
    "功能二：自动生成模版，按门店员工分组汇总，占比精确计算，偏差为零。",

    # Scene 6 — Report
    "功能三：一键生成 Markdown、Excel 和 PDF 报告，图表高清嵌入适合打印归档。",

    # Scene 7 — Charts
    "功能四：自动生成柱状图、饼图和漏斗图，中文字体完美，无需手工配置。",

    # Scene 8 — File Analysis
    "功能五：任意文件拖入即分析，智能检测列结构，一键生成报告和图表。",

    # Scene 9 — Tech
    "技术：Python 3.11 加 pandas，九个核心模块，四十一个测试全部通过。",

    # Scene 10 — CLI
    "五个命令涵盖全部功能：run、export、analyze file、show queries、validate。",

    # Scene 11 — Highlights
    "亮点：密码安全、零人工、高扩展、生产级可靠，四十一项测试保障。",

    # Scene 12 — Summary
    "三小时手工压缩至三十秒，百分之百精确。感谢观看，期待交流！",
]


async def generate_audio(text: str, output_path: str, voice: str = "zh-CN-YunyangNeural"):
    """Generate TTS audio for a single text using edge-tts."""
    import edge_tts
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate="+0%",        # Normal speed
        pitch="+0Hz",
    )
    await communicate.save(output_path)
    return output_path


async def generate_all_audio():
    """Generate audio files for all scenes."""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    audio_paths = []

    for i, text in enumerate(NARRATIONS):
        path = os.path.join(AUDIO_DIR, f"audio_{i:02d}.mp3")
        if os.path.isfile(path):
            log.info("audio.cached", idx=i)
        else:
            log.info("audio.generating", idx=i, chars=len(text))
            await generate_audio(text, path)
        # Get actual duration
        import subprocess
        dur = get_audio_duration(path)
        log.info("audio.ready", idx=i, duration=f"{dur:.1f}s", text=text[:40])
        audio_paths.append(path)

    return audio_paths


def get_media_duration(path: str) -> float:
    """Get media file duration in seconds using ffmpeg stderr output."""
    import subprocess, re
    cmd = [FFMPEG, "-i", path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # ffmpeg prints duration info to stderr
    output = result.stderr
    match = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", output)
    if match:
        h, m, s, ms = map(int, match.groups())
        return h * 3600 + m * 60 + s + ms / 100.0
    return 0.0


# Alias for clarity
get_audio_duration = get_media_duration
get_video_duration = get_media_duration


def get_audio_duration_fast(path: str) -> float:
    """Alias kept for compatibility."""
    return get_media_duration(path)


def create_audio_timeline(audio_paths: list[str]) -> str:
    """Create a combined audio track with proper timing for each scene.

    Each audio clip plays at the start of its corresponding scene.
    Returns path to the combined audio WAV file.
    """
    import subprocess

    # Build input args: -i path1 -i path2 ...
    input_args = []
    for path in audio_paths:
        input_args.extend(["-i", path])

    filter_str = ""
    for i in range(len(audio_paths)):
        start_ms = int(i * SCENE_DURATION * 1000)
        filter_str += f"[{i}:a]adelay={start_ms}|{start_ms}[a{i}];"
    # Mix all delayed tracks
    mix_inputs = "".join(f"[a{i}]" for i in range(len(audio_paths)))
    filter_str += f"{mix_inputs}amix=inputs={len(audio_paths)}:duration=longest:dropout_transition=0[aout]"

    total_duration = len(audio_paths) * SCENE_DURATION
    audio_concat = os.path.join(AUDIO_DIR, "combined_audio.aac")

    cmd = [
        FFMPEG, "-y",
        *input_args,
        "-filter_complex", filter_str,
        "-map", "[aout]",
        "-t", str(total_duration),
        "-c:a", "aac", "-b:a", "192k",
        audio_concat
    ]

    log.info("audio.mixing", scenes=len(audio_paths))
    subprocess.run(cmd, check=True, capture_output=True)
    return audio_concat


def merge_audio_video(video_path: str, audio_path: str, output_path: str):
    """Merge the combined audio track with the video."""
    import subprocess

    # Copy video stream, use new audio stream
    cmd = [
        FFMPEG, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",        # Copy video without re-encoding
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0",       # Take video from first input
        "-map", "1:a:0",       # Take audio from second input
        "-shortest",           # End at shorter stream
        output_path
    ]

    log.info("video.merging")
    subprocess.run(cmd, check=True, capture_output=True)


def main():
    print("=" * 60)
    print("AIExport — 配音生成 (Edge TTS — 免费)")
    print("=" * 60)

    if not os.path.isfile(VIDEO_IN):
        print(f"[ERROR] 视频文件不存在: {VIDEO_IN}")
        sys.exit(1)

    vid_dur = get_video_duration(VIDEO_IN)
    print(f"[INFO] 视频时长: {vid_dur:.1f}s")

    # Generate audio for each scene
    print("\n[AUDIO] 生成 TTS 配音...")
    t0 = time.time()
    audio_paths = asyncio.run(generate_all_audio())
    print(f"[OK] {len(audio_paths)} 段配音生成完成 ({time.time() - t0:.1f}s)")

    # Show durations
    total_audio = sum(get_audio_duration(p) for p in audio_paths)
    print(f"[INFO] 总配音时长: {total_audio:.1f}s")

    # Create timed audio mix
    print("\n[MIX] 合成时间轴音频...")
    t0 = time.time()
    combined_audio = create_audio_timeline(audio_paths)
    print(f"[OK] 音频合成完成 ({time.time() - t0:.1f}s)")

    # Merge with video
    print("\n[MERGE] 合并视频与配音...")
    t0 = time.time()
    merge_audio_video(VIDEO_IN, combined_audio, VIDEO_OUT)
    elapsed = time.time() - t0

    size_mb = os.path.getsize(VIDEO_OUT) / (1024 * 1024)
    print(f"[OK] 配音版视频: {VIDEO_OUT}")
    print(f"     大小: {size_mb:.1f} MB")
    print(f"     合并耗时: {elapsed:.1f}s")

    # Cleanup
    import shutil
    if os.path.isdir(AUDIO_DIR):
        shutil.rmtree(AUDIO_DIR)
        print(f"[OK] 已清理临时音频文件")

    print("\n[DONE] 配音版视频生成完成！")


if __name__ == "__main__":
    main()
