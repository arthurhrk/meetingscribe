# Organização do Repositório (MeetingScribe)

Este documento resume a organização aplicada para priorizar o uso da extensão do Raycast e manter o restante do código disponível sem perdas (nada foi deletado — somente movido e/ou reorganizado).

## Foco dos comandos no Raycast

1. Start Recording (src/record.tsx)
2. Recording Status (src/recording-status.tsx)
3. Recent Recordings (src/recent.tsx)
4. Import Google (src/import-google.tsx)
5. Transcript Status (src/transcript-status.tsx)

Pré‑requisitos nas Preferências da extensão:
- pythonPath (por ex.: `python` ou `./.venv/Scripts/python.exe`)
- projectPath (caminho para a raiz deste repositório)
- geminiApiKey (para Import Google)
- geminiModel (opcional, default: models/gemini-2.0-flash-exp)
- optimizeAudio (opcional)

## Arquivos essenciais na raiz

- `quick_record.py` — script de gravação rápida (usado pelo Start Recording)
- `transcribe_audio.py` — transcrição via Google Gemini (usado pelo Import Google)
- `audio_recorder.py`, `device_manager.py`, `config.py` — núcleo de captura de áudio e seleção de dispositivo
- `requirements.txt` — dependências Python (inclui pyaudiowpatch, loguru, google-generativeai etc.)
- `storage/` — saídas: `recordings/` (WAV, transcrições .txt) e `transcriptions/` (se aplicável)
- `raycast-extension/` — extensão Raycast (manifesto, ícone e comandos)

## Itens reorganizados (sem deletar)

- Utilitários e geradores de ícone → `tools/icons/`
  - `_gen_icon_teams.py`, `_gen_icon.py`, `_gen_icon2.py`
- Scripts auxiliares → `tools/recording/`, `tools/google/`
  - `record_manual.py`, `teste-model-import.py`
- Comandos antigos/alternativos do Raycast → `archive/raycast-commands-old/`
- Markdown avulsos → `docs/notes/`
  - `MANUAL_MODE_AND_STATUS.md`, `QUICK_START_TRANSCRIPTION.md`,
    `RECENT_RECORDINGS_FIX.md`, `RECORDING_IMPROVEMENTS.md`, `TRANSCRIPTION_FEATURE.md`

## Ícone

- O manifesto (`raycast-extension/package.json`) aponta para `raycast-extension/icon.png`.
- O arquivo `raycast-extension/assets/icon_meetingscribe.png` é a fonte aprovada; ele é sincronizado para `icon.png`.

## Garantia de não‑quebra

- Mantivemos presentes e no caminho esperado todos os scripts que os comandos do Raycast chamam (quick_record.py, transcribe_audio.py).
- O manifesto JSON foi validado (UTF‑8 sem BOM) e contém apenas keywords ASCII.
- As pastas e arquivos movidos continuam versionados (somente realocados para nomes autoexplicativos).

## Como iniciar rapidamente

1) Python
```
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate # macOS/Linux
pip install -r requirements.txt
```

2) Raycast
```
cd raycast-extension
npm install
npm run dev    # ou: ray develop
```
- Configure nas preferências: `pythonPath`, `projectPath` e (se usar Import Google) `geminiApiKey`.

3) Teste rápido por terminal
```
python quick_record.py 5                 # grava 5s (auto loopback→mic)
python transcribe_audio.py <arquivo> --api-key <GEMINI_API_KEY>
```

Se desejar reverter/ajustar qualquer realocação, tudo está em pastas autoexplicativas e permanece no histórico do Git.
