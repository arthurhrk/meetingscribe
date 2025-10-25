#!/usr/bin/env python3
"""
Transcribe audio files using Google Gemini API.
Designed to be called from Raycast extension.

Usage:
    python transcribe_audio.py <audio_file_path> --api-key <key> [options]

Returns JSON with transcription status and results.
"""

import google.generativeai as genai
import argparse
import json
import sys
import time
from pathlib import Path
import soundfile as sf
import numpy as np
from scipy import signal
from google.api_core import exceptions


def optimize_audio(input_path: str, target_sample_rate: int = 16000, target_channels: int = 1) -> tuple[str, float]:
    """
    Convert and optimize audio file to reduce size while maintaining quality.

    Optimizations:
    - Convert to mono (1 channel)
    - Reduce to 16kHz (sufficient for human voice)
    - WAV format (compatible and lossless)

    Returns:
        tuple: (path to optimized file, size in MB)
    """
    file_path = Path(input_path)
    original_size = file_path.stat().st_size / (1024 * 1024)

    try:
        # Try reading with soundfile (WAV, FLAC, OGG)
        audio_data, sample_rate = sf.read(str(file_path))
    except Exception:
        # Fallback to pydub for other formats (requires ffmpeg)
        try:
            from pydub import AudioSegment

            audio_segment = AudioSegment.from_file(str(file_path))

            # Convert to mono
            if audio_segment.channels > 1 and target_channels == 1:
                audio_segment = audio_segment.set_channels(1)

            # Resample
            if audio_segment.frame_rate != target_sample_rate:
                audio_segment = audio_segment.set_frame_rate(target_sample_rate)

            # Save as temporary WAV
            temp_path = file_path.parent / f"{file_path.stem}_optimized.wav"
            audio_segment.export(str(temp_path), format="wav")

            optimized_size = temp_path.stat().st_size / (1024 * 1024)

            return str(temp_path), optimized_size

        except ImportError:
            raise Exception("pydub not installed. Install with: pip install pydub")
        except Exception as pydub_error:
            raise Exception(f"Error processing audio with pydub (ffmpeg may be missing): {pydub_error}")

    # Detect number of channels
    if len(audio_data.shape) > 1:
        channels = audio_data.shape[1]
    else:
        channels = 1

    # Convert to mono if needed
    if len(audio_data.shape) > 1 and target_channels == 1:
        audio_data = np.mean(audio_data, axis=1)

    # Resample if needed
    if sample_rate != target_sample_rate:
        num_samples = int(len(audio_data) * target_sample_rate / sample_rate)
        audio_data = signal.resample(audio_data, num_samples)

    # Normalize to 16-bit integer range
    audio_data = np.clip(audio_data, -1.0, 1.0)
    audio_data = (audio_data * 32767).astype(np.int16)

    # Save as optimized WAV
    temp_path = file_path.parent / f"{file_path.stem}_optimized.wav"
    sf.write(str(temp_path), audio_data, target_sample_rate, subtype='PCM_16')

    optimized_size = temp_path.stat().st_size / (1024 * 1024)

    return str(temp_path), optimized_size


def transcribe_audio(
    audio_path: str,
    api_key: str,
    model_name: str = "models/gemini-2.0-flash-exp",
    optimize: bool = False,
    timeout: int = 300
) -> dict:
    """
    Transcribe audio file using Google Gemini API.

    Args:
        audio_path: Path to audio file
        api_key: Google API key
        model_name: Gemini model to use
        optimize: Whether to optimize audio before upload
        timeout: Request timeout in seconds

    Returns:
        dict: JSON response with status and transcription
    """
    try:
        file_path = Path(audio_path)
        if not file_path.exists():
            return {
                "success": False,
                "error": "File not found",
                "file": audio_path
            }

        original_size_mb = file_path.stat().st_size / (1024 * 1024)

        # Optimize audio if requested
        upload_file_path = audio_path
        optimized_file = None

        if optimize:
            try:
                optimized_file, optimized_size = optimize_audio(audio_path)
                upload_file_path = optimized_file
            except Exception as e:
                # If optimization fails, continue with original file
                pass

        # Configure API
        genai.configure(api_key=api_key)

        # Upload file with retry logic
        upload_start = time.time()
        max_retries = 3

        for attempt in range(max_retries):
            try:
                audio_file = genai.upload_file(path=upload_file_path)
                break
            except exceptions.ServiceUnavailable:
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                else:
                    raise

        upload_time = time.time() - upload_start

        # Wait for processing
        process_start = time.time()
        while audio_file.state.name == "PROCESSING":
            time.sleep(2)
            audio_file = genai.get_file(audio_file.name)

        if audio_file.state.name == "FAILED":
            raise Exception(f"File processing failed: {audio_file.state.name}")

        process_time = time.time() - process_start

        # Transcribe
        model = genai.GenerativeModel(model_name)

        generation_config = {
            "temperature": 0.1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }

        prompt = """Transcreva este áudio em português brasileiro palavra por palavra, exatamente como foi dito.

Formato da transcrição:
- Use pontuação adequada
- Mantenha a ordem cronológica
- Indique pausas longas com [...]
- Se houver múltiplos falantes, indique com "Pessoa 1:", "Pessoa 2:", etc.
"""

        transcription_start = time.time()
        response = model.generate_content(
            [prompt, audio_file],
            generation_config=generation_config,
            request_options={"timeout": timeout}
        )
        transcription_time = time.time() - transcription_start

        # Clean up
        genai.delete_file(audio_file.name)

        if optimized_file and Path(optimized_file).exists():
            Path(optimized_file).unlink()

        # Save transcription to file
        transcript_path = file_path.parent / f"{file_path.stem}_transcription.txt"
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(f"TRANSCRIÇÃO - {file_path.name}\n")
            f.write("=" * 80 + "\n")
            f.write(f"Modelo: {model_name}\n")
            f.write(f"Tempo de upload: {upload_time:.1f}s\n")
            f.write(f"Tempo de processamento: {process_time:.1f}s\n")
            f.write(f"Tempo de transcrição: {transcription_time:.1f}s\n")
            f.write("=" * 80 + "\n\n")
            f.write(response.text)

        return {
            "success": True,
            "transcription": response.text,
            "transcript_file": str(transcript_path),
            "timings": {
                "upload": round(upload_time, 1),
                "processing": round(process_time, 1),
                "transcription": round(transcription_time, 1),
                "total": round(upload_time + process_time + transcription_time, 1)
            },
            "file": {
                "original": audio_path,
                "size_mb": round(original_size_mb, 2)
            },
            "model": model_name
        }

    except exceptions.ServiceUnavailable as e:
        return {
            "success": False,
            "error": "Connection error (503 Service Unavailable)",
            "details": "Firewall/proxy may be blocking connection or API temporarily unavailable",
            "file": audio_path
        }
    except TimeoutError:
        return {
            "success": False,
            "error": f"Timeout exceeded ({timeout}s)",
            "file": audio_path
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "file": audio_path
        }
    finally:
        # Clean up optimized file if it exists
        try:
            if 'optimized_file' in locals() and optimized_file and Path(optimized_file).exists():
                Path(optimized_file).unlink()
        except:
            pass


def main():
    parser = argparse.ArgumentParser(description='Transcribe audio using Google Gemini API')
    parser.add_argument('audio_file', help='Path to audio file')
    parser.add_argument('--api-key', required=True, help='Google API key')
    parser.add_argument('--model', default='models/gemini-2.0-flash-exp',
                        choices=['models/gemini-2.0-flash-exp', 'models/gemini-1.5-pro'],
                        help='Gemini model to use')
    parser.add_argument('--optimize', action='store_true',
                        help='Optimize audio before upload (reduces size)')
    parser.add_argument('--timeout', type=int, default=300,
                        help='Request timeout in seconds (default: 300)')

    args = parser.parse_args()

    result = transcribe_audio(
        audio_path=args.audio_file,
        api_key=args.api_key,
        model_name=args.model,
        optimize=args.optimize,
        timeout=args.timeout
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
