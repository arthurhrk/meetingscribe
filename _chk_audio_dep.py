import sys
print('PY', sys.version)
try:
    import pyaudiowpatch as pyaudio
    print('OK_PYAUDIOWPATCH')
except Exception as e:
    print('ERR_PYAUDIOWPATCH', e)
try:
    import pyaudio
    print('OK_PYAUDIO')
except Exception as e:
    print('ERR_PYAUDIO', e)
