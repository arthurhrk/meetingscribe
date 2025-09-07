# MeetingScribe

Transcrição de reuniões com IA 100% local (Windows), com foco em privacidade e experiência rápida. Estamos iniciando a migração para a arquitetura v2 (Client–Daemon), mantendo compatibilidade total com a v1.

- Privacidade total: processamento local, sem rede
- Raycast como launcher; CLI completa com Rich UI
- Detecção inteligente do Teams e captura via WASAPI loopback

## Índice

- Sobre o Projeto
- Status do Projeto
- Início Rápido (Windows)
- Uso da CLI (v1)
- Extensão Raycast
- Configuração
- Arquitetura
- Roadmap v2
- Troubleshooting

## Sobre o Projeto

O MeetingScribe oferece transcrição de alta qualidade usando Whisper (faster‑whisper) com captura de áudio profissional no Windows (WASAPI loopback). A v2 transforma o MeetingScribe em um “serviço sempre pronto” em segundo plano, com múltiplos clientes (Raycast e CLI) e fallback transparente quando o daemon não estiver disponível.

Principais capacidades (v1 já disponível):
- Captura WASAPI loopback, seleção automática de dispositivos
- Transcrição com múltiplos modelos Whisper (tiny → large‑v3)
- Exportação em TXT/JSON/SRT/VTT/XML/CSV
- Integração Raycast para acesso rápido

Alvos da v2 (em andamento):
- Serviço em background com modelos pré‑carregados (start < 3s)
- Multi‑cliente (Raycast + CLI) com estado sincronizado
- Detecção/automação para Microsoft Teams (gravar? transcrever?)

## Status do Projeto

- v1 (estável): CLI funcional em `main.py` e extensão Raycast atual
- v2 (em migração): especificações e planos em `docs/v2-client-daemon/`
  - Começando pela Fase 1 (refactor do CLI e “Status” unificado)

Para visão completa: veja `docs/v2-client-daemon/architecture.md`, `client-interface.md`, `daemon-service.md`, `protocols.md`, `functional-requirements.md` e `use-cases.md`.

## Início Rápido (Windows)

Pré‑requisitos
- Python 3.10+ recomendado
- Windows 10/11 (WASAPI)
- Recomendado: 8GB+ RAM (modelos médios/grandes)

Instalação
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install psutil wmi pywin32
python system_check.py
```

Teste rápido (v1)
```
python main.py
```

## Uso da CLI (v1)

Exemplos comuns:
- Gravar do sistema (loopback automático) e salvar WAV:
  `python main.py` → Menu → “Iniciar nova gravação”
- Transcrever arquivo existente:
  Menu → “Transcrição de Arquivos” → selecione o WAV
- Exportar: escolha formatos (TXT/SRT/JSON/VTT/XML/CSV)
- Dispositivos: listar e verificar WASAPI

Entrypoint principal: `main.py:1`

## Extensão Raycast

Diretório: `raycast-extension/README.md:1`
- `npm install`
- Dev: `npx ray dev`
- Build/Publish: `npx ray build`

Na v2, a extensão detectará o daemon e fará fallback para o STDIO atual quando necessário. Veja `docs/v2-client-daemon/raycast-integration.md:1`.

## Configuração

Config central: `config.py:1`
- Diretórios: `storage/`, `models/`, `logs/`
- Áudio: `audio_sample_rate`, `audio_channels`, `chunk_duration`
- Whisper: `whisper_model`, `whisper_language`, `whisper_device`
- Suporte a `.env`

Arquivo de exemplo: `config/meetingscribe_config.json:1` (opcional)

Estrutura de armazenamento (padrão):
- `storage/recordings/` — WAVs gravados
- `storage/transcriptions/` — resultados
- `storage/exports/` — arquivos exportados

## Arquitetura

v1 (atual):
- CLI: `main.py:1`
- Áudio: `device_manager.py:1`, `audio_recorder.py:1`
- Transcrição: `src/transcription/`
- Core/otimizações: `src/core/`

v2 (em andamento):
- Especificações completas: `docs/v2-client-daemon/README.md:1`
- Componentes planejados:
  - Daemon: serviço Windows, modelo pré‑carregado, multi‑cliente
  - Client: CLI com Rich UI, detecção de daemon, fallback
  - Protocolos: JSON‑RPC via Named Pipes (primário) e STDIO (legado)

## Roadmap v2

Fase 1 — CLI refactor (prioridade)
- cli_main (assíncrono) com detecção de daemon e fallback
- Rich UI extraída de `main.py`
- Comando “Status” unificado (Ready, memória, modelos, dispositivos, fila)

Fase 2 — Daemon core
- Windows Service + lifecycle + resource manager (pré‑load)
- stdio_core/connection manager + health monitor

Fase 3 — Bridge + multi‑cliente
- Named Pipes + eventos em tempo real + fallback STDIO

Critérios de aceite por caso de uso: `docs/v2-client-daemon/acceptance-checklist.md:1`.

## Troubleshooting

- WASAPI não disponível: ver `device_manager.py:1` e `system_check.py:1`; instale `pyaudiowpatch` (preferível) ou use `pyaudio` com limitações.
- Torch/pyannote pesados: usar CPU primeiro; GPU requer drivers atualizados.
- Encoding no terminal: use UTF‑8 no Windows Terminal para evitar caracteres corrompidos.
- Logs: `logs/meetingscribe.log`

## Licença

MIT — veja `LICENSE:1`.

