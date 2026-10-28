import os
import re
import glob
import shutil
import tempfile
import logging
import subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional, Tuple

import config
from services import llm_service

logger = logging.getLogger(__name__)

YOUTUBE_REGEX = re.compile(
    r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
)

def get_ffmpeg_binary() -> str:
    """Finds the best available ffmpeg binary (system PATH or imageio_ffmpeg bundled)."""
    cmd = shutil.which("ffmpeg")
    if cmd:
        return cmd
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    return "ffmpeg"

def clean_transcript_text(text: str) -> str:
    """Cleans subtitle tokens, music notes, and formats text into readable paragraphs."""
    if not text:
        return ""
    # Remove caption noise like [Music], [Applause], (cheers), ♪ symbols
    text = re.sub(r'\[.*?\]|\(.*?\)|♪', ' ', text)
    # Collapse multiple whitespaces and newlines
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_youtube_id(url: str) -> Optional[str]:
    """Robustly extracts 11-char YouTube ID from any format (shorts, embed, youtu.be, live, mobile)."""
    if not url:
        return None
    url = url.strip()

    try:
        parsed = urlparse(url)
        if "youtube" in parsed.netloc or "youtu.be" in parsed.netloc:
            # Query param ?v=
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                return qs["v"][0][:11]
            # Path based /shorts/ID, /embed/ID, /live/ID, /v/ID
            path_parts = [p for p in parsed.path.split("/") if p]
            if "youtu.be" in parsed.netloc and path_parts:
                return path_parts[0][:11]
            if len(path_parts) >= 2 and path_parts[0] in ("shorts", "embed", "v", "live"):
                return path_parts[1][:11]
            if len(path_parts) == 1 and len(path_parts[0]) == 11:
                return path_parts[0]
    except Exception:
        pass

    # Regex fallbacks
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:[&?#\/]|$)',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/shorts\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None

def get_youtube_transcript_fast(video_id: str) -> Optional[str]:
    """Fetches YouTube subtitles/captions directly with comprehensive language and translation fallbacks."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        target_languages = ['en', 'en-US', 'en-GB', 'hi', 'en-IN']

        ytt = YouTubeTranscriptApi()

        # 1. Try direct fetch with target languages
        try:
            fetched = ytt.fetch(video_id, languages=target_languages)
            snippets = getattr(fetched, 'snippets', fetched)
            parts = [s.text.strip() for s in snippets if getattr(s, 'text', '').strip()]
            full = " ".join(parts).strip()
            if full and len(full) > 20:
                logger.info(f"Direct fast transcript fetched for {video_id} ({len(full)} chars)")
                return clean_transcript_text(full)
        except Exception as e:
            logger.debug(f"Direct ytt.fetch failed for {video_id}: {e}")

        # 2. Try listing all transcripts (manual & generated)
        try:
            transcript_list = ytt.list(video_id)
            selected_transcript = None

            # 2a. Look for manual transcript in target languages
            for lang in target_languages:
                try:
                    selected_transcript = transcript_list.find_manually_created_transcript([lang])
                    if selected_transcript:
                        break
                except Exception:
                    pass

            # 2b. Look for generated transcript in target languages
            if not selected_transcript:
                for lang in target_languages:
                    try:
                        selected_transcript = transcript_list.find_generated_transcript([lang])
                        if selected_transcript:
                            break
                    except Exception:
                        pass

            # 2c. Look for ANY transcript that can be translated to English
            if not selected_transcript:
                for t in transcript_list:
                    if getattr(t, 'is_translatable', False):
                        try:
                            selected_transcript = t.translate('en')
                            break
                        except Exception:
                            pass

            # 2d. Fallback to the first available transcript in the list
            if not selected_transcript:
                for t in transcript_list:
                    selected_transcript = t
                    break

            if selected_transcript:
                fetched = selected_transcript.fetch()
                snippets = getattr(fetched, 'snippets', fetched)
                parts = []
                for s in snippets:
                    if hasattr(s, 'text'):
                        t_str = s.text.strip()
                    elif isinstance(s, dict):
                        t_str = s.get('text', '').strip()
                    else:
                        t_str = str(s).strip()
                    if t_str:
                        parts.append(t_str)
                full = " ".join(parts).strip()
                if full and len(full) > 20:
                    logger.info(f"Listed transcript fetched ({selected_transcript.language_code}) for {video_id}")
                    return clean_transcript_text(full)
        except Exception as e:
            logger.debug(f"ytt.list failed for {video_id}: {e}")

    except Exception as e:
        logger.warning(f"Fast transcript fetch failed for {video_id}: {e}")
    return None

def download_youtube_audio_fallback(url: str) -> Tuple[str, str, int]:
    """Downloads YouTube audio and returns (mp3_path, title, duration_seconds)"""
    import yt_dlp
    workdir = tempfile.mkdtemp(prefix="nexora_yt_")
    ffmpeg_exe = get_ffmpeg_binary()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe) if ffmpeg_exe and os.path.isabs(ffmpeg_exe) else None

    opts = {
        "format": "ba[ext=m4a]/ba/b",
        "outtmpl": os.path.join(workdir, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "ffmpeg_location": ffmpeg_dir or ffmpeg_exe,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"]
            }
        },
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
    }
    title = "YouTube Video Lecture"
    duration = 0
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title") or title
            duration = int(info.get("duration") or 0)
    except Exception as e:
        logger.warning(f"yt_dlp primary audio download failed, attempting simple audio format: {e}")
        opts_fallback = {
            "format": "worstaudio/worst",
            "outtmpl": os.path.join(workdir, "lecture.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
        }
        with yt_dlp.YoutubeDL(opts_fallback) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title") or title
            duration = int(info.get("duration") or 0)

    files = glob.glob(os.path.join(workdir, "*.mp3")) or glob.glob(os.path.join(workdir, "*.*"))
    if not files:
        shutil.rmtree(workdir, ignore_errors=True)
        raise RuntimeError("Failed to produce audio file from YouTube URL")
    return files[0], title, duration

def extract_audio_from_video(video_path: str) -> str:
    """Extracts compact 16kHz mono MP3 audio from a video file."""
    out_audio = str(Path(video_path).with_suffix(".mp3"))
    ffmpeg_exe = get_ffmpeg_binary()
    try:
        r = subprocess.run(
            [ffmpeg_exe, "-y", "-i", video_path, "-vn", "-ar", "16000", "-ac", "1", "-b:a", "64k", out_audio],
            capture_output=True,
            text=True
        )
        if r.returncode == 0 and os.path.exists(out_audio) and os.path.getsize(out_audio) > 0:
            return out_audio
    except Exception as e:
        logger.warning(f"ffmpeg extraction failed: {e}")

    # Fallback to moviepy if needed
    try:
        from moviepy import VideoFileClip
        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(out_audio, bitrate="64k", verbose=False, logger=None)
        clip.close()
        if os.path.exists(out_audio) and os.path.getsize(out_audio) > 0:
            return out_audio
    except Exception as e:
        logger.error(f"moviepy audio extraction failed: {e}")

    raise RuntimeError("Could not extract audio from video. Ensure the video contains an audio track.")

def ensure_compact_audio(audio_path: str) -> Tuple[str, bool]:
    """Ensures audio file is under 24MB for Groq Whisper. Returns (path, is_temp)."""
    size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if size_mb <= 24.0 and audio_path.lower().endswith((".mp3", ".m4a", ".webm", ".wav")):
        return audio_path, False

    # Compress to 48k mono mp3
    ffmpeg_exe = get_ffmpeg_binary()
    compact_path = str(Path(audio_path).parent / f"compact_{Path(audio_path).stem}.mp3")
    try:
        r = subprocess.run(
            [ffmpeg_exe, "-y", "-i", audio_path, "-vn", "-ar", "16000", "-ac", "1", "-b:a", "48k", compact_path],
            capture_output=True,
            text=True
        )
        if r.returncode == 0 and os.path.exists(compact_path) and os.path.getsize(compact_path) > 0:
            return compact_path, True
    except Exception as e:
        logger.warning(f"Audio compaction failed: {e}")

    return audio_path, False

def transcribe_with_groq(audio_path: str) -> Optional[str]:
    """Transcribes an audio file using Groq Whisper Large v3 Turbo."""
    api_key = config.GROQ_API_KEY
    if not api_key:
        return None

    try:
        import groq
        client = groq.Groq(api_key=api_key)
    except Exception as e:
        logger.warning(f"Groq client init error: {e}")
        return None

    size_mb = os.path.getsize(audio_path) / (1024 * 1024)

    # 1. Under 24MB -> transcribe directly
    if size_mb <= 24.0:
        for model in ["whisper-large-v3-turbo", "whisper-large-v3"]:
            try:
                with open(audio_path, "rb") as f:
                    transcription = client.audio.transcriptions.create(
                        file=f,
                        model=model,
                        response_format="text"
                    )
                    text = transcription if isinstance(transcription, str) else getattr(transcription, "text", "")
                    if text and text.strip():
                        return text.strip()
            except Exception as e:
                logger.warning(f"Groq model {model} failed: {e}")
                continue

    # 2. Over 24MB -> split into 10-minute segments
    ffmpeg_exe = get_ffmpeg_binary()
    chunk_dir = tempfile.mkdtemp(prefix="nexora_audio_chunks_")
    try:
        chunk_pattern = os.path.join(chunk_dir, "seg_%03d.mp3")
        subprocess.run([
            ffmpeg_exe, "-y", "-i", audio_path,
            "-f", "segment", "-segment_time", "600",
            "-c", "copy", chunk_pattern
        ], capture_output=True, text=True)

        chunks = sorted(glob.glob(os.path.join(chunk_dir, "seg_*.mp3")))
        if not chunks:
            return None

        transcripts = []
        for chunk in chunks:
            chunk_done = False
            for model in ["whisper-large-v3-turbo", "whisper-large-v3"]:
                try:
                    with open(chunk, "rb") as f:
                        transcription = client.audio.transcriptions.create(
                            file=f,
                            model=model,
                            response_format="text"
                        )
                        chunk_text = transcription if isinstance(transcription, str) else getattr(transcription, "text", "")
                        if chunk_text and chunk_text.strip():
                            transcripts.append(chunk_text.strip())
                            chunk_done = True
                            break
                except Exception as e:
                    logger.warning(f"Chunk transcription failed with {model}: {e}")
                    continue
            if not chunk_done:
                logger.warning(f"Failed to transcribe audio chunk: {chunk}")

        full_transcript = " ".join(transcripts).strip()
        if full_transcript:
            return full_transcript
    except Exception as e:
        logger.error(f"Chunked transcription error: {e}")
    finally:
        shutil.rmtree(chunk_dir, ignore_errors=True)

    return None

def transcribe_audio_file(audio_path: str) -> str:
    """
    Transcribes audio using high-accuracy Groq Whisper Large v3 (multilingual, exact words),
    with intelligent local and cloud fallbacks.
    """
    compact_path, is_temp = ensure_compact_audio(audio_path)
    target_path = compact_path if (compact_path and os.path.exists(compact_path)) else audio_path

    try:
        # 1. Primary: Groq Whisper Large v3 (ultra-fast, exact transcription in English/Hindi/etc.)
        groq_text = transcribe_with_groq(target_path)
        if groq_text and groq_text.strip():
            logger.info("Successfully transcribed audio via Groq Whisper Large v3")
            return groq_text.strip()

        # 2. Deepgram fallback if configured
        if config.DEEPGRAM_API_KEY:
            try:
                import requests
                headers = {"Authorization": f"Token {config.DEEPGRAM_API_KEY}", "Content-Type": "audio/mp3"}
                with open(target_path, "rb") as f:
                    r = requests.post("https://api.deepgram.com/v1/listen?smart_format=true&model=nova-2", headers=headers, data=f, timeout=60)
                    if r.status_code == 200:
                        data = r.json()
                        dg_text = data.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
                        if dg_text and dg_text.strip():
                            return dg_text.strip()
            except Exception as e:
                logger.warning(f"Deepgram transcription error: {e}")

        # 3. Local faster-whisper fallback
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("tiny", compute_type="int8", cpu_threads=4)
            segments, _ = model.transcribe(target_path, beam_size=1, vad_filter=True)
            text = " ".join([seg.text.strip() for seg in segments])
            if text.strip():
                return text.strip()
        except Exception as e:
            logger.warning(f"faster-whisper failed: {e}")

        raise RuntimeError(
            "Could not transcribe audio from media file. Please ensure the file has audible speech and that GROQ_API_KEY is configured."
        )
    finally:
        if is_temp and os.path.exists(compact_path):
            try:
                os.remove(compact_path)
            except Exception:
                pass

def process_youtube_notes(url: str) -> Dict[str, Any]:
    video_id = extract_youtube_id(url)
    title = "YouTube Video Lecture"
    transcript = None
    duration = 0

    # 1. Quick title & transcript attempt
    if video_id:
        transcript = get_youtube_transcript_fast(video_id)
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "nocheckcertificate": True, "extract_flat": True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get("title") or title
                duration = int(info.get("duration") or 0)
        except Exception:
            pass

    # 2. Fallback to audio download and Groq Whisper if no subtitles available
    if not transcript:
        audio_path = None
        try:
            audio_path, extracted_title, extracted_duration = download_youtube_audio_fallback(url)
            title = extracted_title or title
            duration = extracted_duration or duration
            transcript = transcribe_audio_file(audio_path)
        except Exception as e:
            logger.error(f"YouTube audio download failed: {e}")
            if not transcript:
                raise RuntimeError(f"Could not retrieve transcript or audio for YouTube URL: {e}")
        finally:
            if audio_path and os.path.exists(audio_path):
                shutil.rmtree(os.path.dirname(audio_path), ignore_errors=True)

    # 3. Infer specific topic title if default
    if not title or title == "YouTube Video Lecture":
        title = llm_service.generate_title_from_content(transcript, "YouTube Lecture")

    # 4. Generate summary, structured notes, and practice quiz via LLM
    summary_data = llm_service.generate_summary(f"Lecture Title: {title}\nTranscript:\n{transcript}")
    notes = llm_service.generate_structured_notes(f"Lecture Title: {title}\nTranscript:\n{transcript}")
    quiz = llm_service.generate_quiz_json(f"Lecture Title: {title}\n{notes}", num_questions=3)

    return {
        "title": title,
        "duration": duration,
        "transcript": transcript,
        "summary": summary_data.get("summary", ""),
        "notes": notes,
        "quiz": quiz
    }

def process_media_file_notes(file_path: str, filename: str) -> Dict[str, Any]:
    ext = Path(filename).suffix.lower()
    video_exts = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv"}
    audio_path = file_path
    cleanup_audio = False

    # Extract audio if video
    if ext in video_exts:
        audio_path = extract_audio_from_video(file_path)
        cleanup_audio = True

    try:
        # Transcribe audio verbatim with Whisper Large v3
        transcript = transcribe_audio_file(audio_path)
        if not transcript or not transcript.strip():
            raise RuntimeError("No audible speech or transcript could be extracted from this media file.")

        # Infer topic title based on actual content
        title = llm_service.generate_title_from_content(transcript, filename)

        # Generate specific summary, detailed notes, and quiz based on actual transcript
        summary_data = llm_service.generate_summary(f"Lecture Title: {title}\nFile: {filename}\nTranscript:\n{transcript}")
        notes = llm_service.generate_structured_notes(f"Lecture Title: {title}\nFile: {filename}\nTranscript:\n{transcript}")
        quiz = llm_service.generate_quiz_json(notes, num_questions=3)

        return {
            "title": title,
            "transcript": transcript,
            "summary": summary_data.get("summary", ""),
            "notes": notes,
            "quiz": quiz
        }
    finally:
        if cleanup_audio and audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass
