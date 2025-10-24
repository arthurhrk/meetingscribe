import time
from device_manager import DeviceManager
from audio_recorder import PYAUDIO_AVAILABLE

print('PYAUDIO_AVAILABLE', PYAUDIO_AVAILABLE)

with DeviceManager() as dm:
    devs = dm.get_recording_capable_devices()
    print('rec-capable count', len(devs))
    for d in devs:
        print('cand', d.index, d.name, d.max_input_channels, d.default_sample_rate, d.host_api, d.is_loopback)
    if not devs:
        raise SystemExit('no devices')
    device = devs[0]

import pyaudiowpatch as pyaudio
pa = pyaudio.PyAudio()
config = dict(format=pyaudio.paInt16, channels=min(2, max(1, device.max_input_channels)), rate=int(device.default_sample_rate), input=True, input_device_index=device.index, frames_per_buffer=512)
print('try open without as_loopback', config)
try:
    s = pa.open(**config)
    print('opened')
    for i in range(10):
        data = s.read(512, exception_on_overflow=False)
        print('read len', len(data))
        time.sleep(0.05)
    s.stop_stream(); s.close()
except Exception as e:
    print('open failed', e)

print('try open with as_loopback flag (if supported)')
try:
    s = pa.open(**config, as_loopback=True)
    print('opened LB')
    for i in range(10):
        data = s.read(512, exception_on_overflow=False)
        print('read len', len(data))
        time.sleep(0.05)
    s.stop_stream(); s.close()
except Exception as e:
    print('open LB failed', e)
finally:
    pa.terminate()
