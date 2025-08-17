#!/usr/bin/env python3
"""
Teste básico do PyAudio para identificar problemas.
"""

import pyaudiowpatch as pyaudio
import time
import threading
from datetime import datetime

def test_basic_recording():
    print("=== TESTE BÁSICO PYAUDIO ===")
    
    try:
        # 1. Initialize PyAudio
        audio = pyaudio.PyAudio()
        print("PyAudio initialized")
        
        # 2. Open stream
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=2,
            rate=48000,
            input=True,
            input_device_index=10,
            frames_per_buffer=1024
        )
        print("Stream opened")
        
        # 3. Record for 3 seconds
        frames = []
        start_time = time.time()
        duration_limit = 3
        
        print("Starting recording...")
        
        while True:
            current_time = time.time()
            elapsed = current_time - start_time
            
            if elapsed >= duration_limit:
                print(f"Duration limit reached: {elapsed:.1f}s")
                break
                
            try:
                # Read with timeout
                data = stream.read(1024, exception_on_overflow=False)
                frames.append(data)
                
                if len(frames) % 10 == 0:  # Progress every ~0.2 seconds
                    print(f"Recording: {elapsed:.1f}s, frames: {len(frames)}")
                    
            except Exception as e:
                print(f"Read error: {e}")
                break
                
            time.sleep(0.01)  # Small pause
            
        # 4. Cleanup
        print("Stopping stream...")
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        print(f"SUCCESS: Recorded {len(frames)} frames in {elapsed:.1f}s")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    test_basic_recording()