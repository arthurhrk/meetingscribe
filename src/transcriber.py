import google.generativeai as genai
import os
import time
import json
from pathlib import Path
import soundfile as sf
import numpy as np
from scipy import signal
from google.api_core import retry
from google.api_core import exceptions

import argparse

# --- Configuration ---
# Configuration is now passed via command line arguments

# Audio optimization configuration
# NOTE: Optimization requires ffmpeg installed for formats like M4A
# If ffmpeg is not available, set to False
OPTIMIZE_AUDIO = False  # If True, converts to mono 16kHz WAV before sending
TARGET_SAMPLE_RATE = 16000  # 16kHz is sufficient for voice transcription
TARGET_CHANNELS = 1  # Mono (voice does not need stereo)

# Timeout in seconds (adjust as needed)
REQUEST_TIMEOUT = 300  # 5 minutes

# --------------------

def write_status(status_file_path, step: int, total_steps: int, step_name: str, message: str = ""):
    """Write progress status to a file for UI monitoring."""
    if not status_file_path:
        return

    try:
        progress = int((step / total_steps) * 100)
        status_data = {
            "step": step_name,
            "step_number": step,
            "total_steps": total_steps,
            "progress": progress,
            "message": message,
        }
        Path(status_file_path).parent.mkdir(parents=True, exist_ok=True)
        Path(status_file_path).write_text(json.dumps(status_data), encoding="utf-8")
    except Exception as e:
        # Log error for debugging purposes
        print(f"[Status] Error writing status file to {status_file_path}: {e}", file=__import__('sys').stderr)


def optimize_audio(input_path: str) -> tuple[str, float]:
    """
    Converts and optimizes audio file to reduce size while maintaining quality.

    Applied optimizations:
    - Conversion to mono (1 channel)
    - Reduction to 16kHz (sufficient for human voice)
    - WAV format (compatible and lossless)

    Returns:
        tuple: (path to optimized file, size in MB)
    """
    print(f"[Optimization] Loading original file...")

    file_path = Path(input_path)
    original_size = file_path.stat().st_size / (1024 * 1024)

    try:
        # Try to read audio file with soundfile (WAV, FLAC, OGG)
        audio_data, sample_rate = sf.read(str(file_path))
    except Exception as e:
        # If it fails, try with pydub (supports more formats, but requires ffmpeg)
        print(f"[Optimization] soundfile failed, trying pydub...")
        try:
            from pydub import AudioSegment

            # Load the audio file
            audio_segment = AudioSegment.from_file(str(file_path))

            # Convert to mono
            if audio_segment.channels > 1 and TARGET_CHANNELS == 1:
                audio_segment = audio_segment.set_channels(1)

            # Resample
            if audio_segment.frame_rate != TARGET_SAMPLE_RATE:
                audio_segment = audio_segment.set_frame_rate(TARGET_SAMPLE_RATE)

            # Save as temporary WAV
            temp_path = file_path.parent / f"{file_path.stem}_optimized.wav"
            audio_segment.export(str(temp_path), format="wav", parameters=["-ac", "1", "-ar", str(TARGET_SAMPLE_RATE)])

            optimized_size = temp_path.stat().st_size / (1024 * 1024)
            reduction = ((original_size - optimized_size) / original_size) * 100

            print(f"[Optimization] Original: {audio_segment.frame_rate}Hz, {audio_segment.channels}ch, {original_size:.2f}MB")
            print(f"[Optimization] Optimized: {TARGET_SAMPLE_RATE}Hz, {TARGET_CHANNELS}ch, {optimized_size:.2f}MB")
            print(f"[Optimization] Reduction: {reduction:.1f}%")

            return str(temp_path), optimized_size

        except ImportError:
            raise Exception("pydub is not installed. Install with: pip install pydub")
        except Exception as pydub_error:
            raise Exception(f"Error processing audio with pydub (ffmpeg may be missing): {pydub_error}")

    # Detect number of channels
    if len(audio_data.shape) > 1:
        channels = audio_data.shape[1]
    else:
        channels = 1

    print(f"[Optimization] Original: {sample_rate}Hz, {channels}ch, {original_size:.2f}MB")

    # Convert to mono if necessary
    if len(audio_data.shape) > 1 and TARGET_CHANNELS == 1:
        audio_data = np.mean(audio_data, axis=1)

    # Resample if necessary
    if sample_rate != TARGET_SAMPLE_RATE:
        # Calculate number of samples at new rate
        num_samples = int(len(audio_data) * TARGET_SAMPLE_RATE / sample_rate)
        audio_data = signal.resample(audio_data, num_samples)

    # Normalize to 16-bit integer range
    audio_data = np.clip(audio_data, -1.0, 1.0)
    audio_data = (audio_data * 32767).astype(np.int16)

    # Save as optimized WAV
    temp_path = file_path.parent / f"{file_path.stem}_optimized.wav"
    sf.write(str(temp_path), audio_data, TARGET_SAMPLE_RATE, subtype='PCM_16')

    optimized_size = temp_path.stat().st_size / (1024 * 1024)
    reduction = ((original_size - optimized_size) / original_size) * 100

    print(f"[Optimization] Optimized: {TARGET_SAMPLE_RATE}Hz, {TARGET_CHANNELS}ch, {optimized_size:.2f}MB")
    print(f"[Optimization] Reduction: {reduction:.1f}%")

    return str(temp_path), optimized_size

def main():
    """Main function to execute transcription."""
    parser = argparse.ArgumentParser(description="Transcribes an audio file using the Google Gemini API.")
    parser.add_argument("audio_file", help="Path to the audio file to be transcribed.")
    parser.add_argument("--api-key", required=True, help="Google Gemini API Key.")
    parser.add_argument("--model", default="models/gemini-1.5-flash", help="Model to be used for transcription.")
    parser.add_argument("--optimize", action="store_true", help="Optimizes the audio before sending.")
    parser.add_argument("--output-file", help="Path to save the transcription file.")
    parser.add_argument("--session-id", help="Session ID for progress tracking.")
    args = parser.parse_args()

    # Set the audio file path from arguments
    AUDIO_FILE_PATH = args.audio_file
    API_KEY = args.api_key
    MODEL_NAME = args.model
    OPTIMIZE_AUDIO = args.optimize

    # Prepare status file path for progress tracking
    STATUS_FILE = None
    if args.session_id:
        # Get project path from current working directory
        project_path = Path.cwd()
        status_dir = project_path / "storage" / "status"
        STATUS_FILE = str(status_dir / f"{args.session_id}.json")

    try:
        # Check file information before starting
        file_path = Path(AUDIO_FILE_PATH)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {AUDIO_FILE_PATH}")

        original_size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"Original file: {file_path.name}")
        print(f"Size: {original_size_mb:.2f} MB")
        print(f"Format: {file_path.suffix}")
        print()

        # Optimize audio if configured
        upload_file_path = AUDIO_FILE_PATH
        optimized_file = None

        if OPTIMIZE_AUDIO:
            print("=" * 60)
            print("AUDIO OPTIMIZATION")
            print("=" * 60)
            optimized_file, optimized_size = optimize_audio(AUDIO_FILE_PATH)
            upload_file_path = optimized_file
            print(f"\nFile to be sent: {Path(optimized_file).name}")
            print(f"Final size: {optimized_size:.2f} MB")
            print("=" * 60)
            print()

        # 1. Configure API Key in the library
        genai.configure(api_key=API_KEY)

        # 2. Upload your audio file to the Gemini API
        #    This is necessary so the model can "hear" the audio.
        write_status(STATUS_FILE, 1, 4, "uploading", "Uploading file to Gemini API...")
        print(f"[1/4] Uploading file...")
        upload_start = time.time()

        # Try upload with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                audio_file = genai.upload_file(path=upload_file_path)
                upload_time = time.time() - upload_start
                print(f"      Upload completed in {upload_time:.1f}s")
                print(f"      URI: {audio_file.uri}")
                break
            except exceptions.ServiceUnavailable as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 2s, 4s, 6s
                    print(f"      Connection error (attempt {attempt + 1}/{max_retries})")
                    print(f"      Waiting {wait_time}s before trying again...")
                    time.sleep(wait_time)
                else:
                    raise
            except Exception as e:
                raise

        print()

        # Wait for file processing
        write_status(STATUS_FILE, 2, 4, "processing", "Processing file by Gemini API...")
        print(f"[2/4] Waiting for file processing...")
        process_start = time.time()
        while audio_file.state.name == "PROCESSING":
            print("      Processing...", end="\r")
            time.sleep(2)
            audio_file = genai.get_file(audio_file.name)

        process_time = time.time() - process_start

        if audio_file.state.name == "FAILED":
            raise Exception(f"File processing failed: {audio_file.state.name}")

        print(f"      Processing completed in {process_time:.1f}s")
        print()

        # 3. Select the model
        model = genai.GenerativeModel(MODEL_NAME)

        # Configuration with timeout
        generation_config = {
            "temperature": 0.1,  # Low temperature for more accurate transcription
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }

        # 4. Send the audio and text prompt together
        #    The prompt tells the model which task to perform.
        write_status(STATUS_FILE, 3, 4, "transcribing", "Generating transcription from audio...")
        print(f"[3/4] Sending transcription request to the model...")
        prompt = '''Please process the attached audio file and provide the following two sections in markdown format:

**1. Raw Transcription:**

*   Detect the language spoken in the audio.
*   Transcribe the audio verbatim in the detected language, word for word, exactly as spoken.
*   Use appropriate punctuation.
*   Indicate long pauses with [...].
*   If there are multiple speakers, label them as "Speaker 1:", "Speaker 2:", etc.

**2. Key Topics Discussed:**

*   Analyze the raw transcription.
*   Identify the main subjects, decisions, and action items.
*   Organize these points into a summary with clear headings for each topic.
*   Describe the key topics in the same language as identified in the raw transcription.
*   Ensure no critical information is lost.

Your entire response should be a single markdown document.'''

        transcription_start = time.time()
        response = model.generate_content(
            [prompt, audio_file],
            generation_config=generation_config,
            request_options={"timeout": REQUEST_TIMEOUT}
        )
        transcription_time = time.time() - transcription_start
        print(f"      Transcription completed in {transcription_time:.1f}s")
        print()

        # 5. Print the transcription result and save
        write_status(STATUS_FILE, 4, 4, "saving", "Saved transcript to file")
        print("[4/4] Result:")
        print("\n" + "="*80)
        print("TRANSCRIPTION")
        print("="*80)
        print(response.text)
        print("="*80)
        print()

        # Timing summary
        total_time = upload_time + process_time + transcription_time
        print(f"Total time: {total_time:.1f}s")
        print(f"  - Upload: {upload_time:.1f}s")
        print(f"  - Processing: {process_time:.1f}s")
        print(f"  - Transcription: {transcription_time:.1f}s")
        print()

        # Save the transcription to a file, if specified
        if args.output_file:
            output_path = Path(args.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(response.text, encoding="utf-8")
            print(f"Transcription saved to: {output_path}")

            # Return JSON with success and file path
            import json
            print(json.dumps({
                "success": True,
                "transcript_file": str(output_path)
            }))

    except FileNotFoundError as e:
        print(json.dumps({"success": False, "error": str(e)}))
        print(f"\n--- ERROR ---")
    except TimeoutError as e:
        import json
        print(json.dumps({"success": False, "error": f"Timeout: {e}"}))
        print(f"\n--- TIMEOUT ---")
        print(f"The operation exceeded the time limit of {REQUEST_TIMEOUT}s")
        print("Possible solutions:")
        print("  1. Increase the REQUEST_TIMEOUT value in the code")
        print("  2. Use a smaller audio file")
        print("  3. Try again later")
    except exceptions.ResourceExhausted as e:
        import json
        print(json.dumps({"success": False, "error": f"Rate Limited: {e}"}))
        print(f"\n--- RATE LIMIT ERROR (429) ---")
        print(f"Google Gemini API quota exceeded. Please wait before retrying.")
        print()
        print("Possible causes:")
        print("  1. API quota limit reached for your account")
        print("  2. Too many requests sent in a short time")
        print("  3. Concurrent transcription requests")
        print()
        print("Suggested solutions:")
        print("  1. Wait at least 60 seconds before trying again")
        print("  2. Check your Google Cloud API quota at https://console.cloud.google.com/quotas")
        print("  3. Consider upgrading your Google Cloud plan if quota is insufficient")
        print("  4. Avoid running multiple transcriptions simultaneously")
        print("  5. Use a smaller audio file to reduce API usage")
    except exceptions.ServiceUnavailable as e:
        import json
        print(json.dumps({"success": False, "error": f"Service Unavailable: {e}"}))
        print(f"\n--- CONNECTION ERROR ---")
        print(f"Could not connect to Google API (503 Service Unavailable)")
        print()
        print("Possible causes:")
        print("  1. Corporate firewall or proxy blocking the connection")
        print("  2. Google API temporarily unavailable")
        print("  3. File too large (30MB) for current connection")
        print()
        print("Suggested solutions:")
        print("  1. Check if you are connected to corporate VPN and try disconnecting")
        print("  2. Try using a different network (non-corporate)")
        print("  3. Enable OPTIMIZE_AUDIO = True in the code (reduces file size)")
        print("     NOTE: Requires ffmpeg installed")
        print("  4. Use a smaller audio file for testing")
        print("  5. Wait a few minutes and try again")
    except Exception as e:
        import json
        print(json.dumps({"success": False, "error": f"{type(e).__name__}: {e}"}))
        # Capture other errors (ex: Invalid API Key, permission issue)
        print(f"\n--- ERROR ---")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {e}")

        # Try to clean up files if they were created
        try:
            if 'audio_file' in locals():
                genai.delete_file(audio_file.name)
                print(f"\nTemporary file removed from API after error.")
        except:
            pass

        try:
            if 'optimized_file' in locals() and optimized_file and Path(optimized_file).exists():
                Path(optimized_file).unlink()
                print(f"Optimized local file removed after error.")
        except:
            pass

if __name__ == "__main__":
    main()
