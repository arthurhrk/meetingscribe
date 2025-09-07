# Agents Status — MeetingScribe v2

Visão rápida do backlog do projeto e o que está em andamento agora. Itens marcados com [Codex: in-progress] estão sob trabalho ativo neste momento.

## Fase 1 — Fundações do Client–Daemon
- [Done] README refatorado para v2 e visão geral
  - Arquivo: `README.md`
- [Done] Skeleton do cliente v2 (CLI) com fallback transparente
  - Arquivos: `client/cli_main.py`, `client/rich_ui.py`, `client/fallback_runner.py`, `client/daemon_client.py`
- [Done] Daemon stub via STDIO (JSON‑RPC) com métodos básicos
  - Arquivo: `daemon/stdio_core.py`
  - Métodos: `ping`, `system.status`, `devices.list`, `record.start`, `record.stop`, `transcribe.start`, `export.run`
- [Done] Checklist de aceitação por UC
  - Arquivo: `docs/v2-client-daemon/acceptance-checklist.md`

## Fase 2 — Daemon “Always‑Ready”
- [Codex: in-progress] Transporte por Named Pipes (cliente + daemon) mantendo STDIO como fallback
  - Impacto: multi‑cliente real (CLI + Raycast) e menor latência
  - Alvo: `client/transport/namedpipe_transport.py` (novo) e listener no daemon
- [Next] Comandos de serviço (repair/restart) expostos na CLI v2
  - Alvo: `client/cli_main.py` (subcomando `service`), integração com `daemon/service.py`
- [Next] Windows Service wrapper funcional (instalar/iniciar/parar/status)
  - Arquivo: `daemon/service.py` (base existente), ajustes e docs de instalação
- [Next] Pré‑carregamento de modelo base + gestão de memória inicial
  - Alvo: `daemon/resource_manager.py` (novo)

## Fase 3 — Paridade ampliada e UX
- [Next] Transcrição assíncrona com progresso e fila (queue list/status/cancel)
- [Next] Exportações batch e organização por padrões (data/cliente)
- [Next] Integração Raycast v2 (daemon‑connector + fallback)

## Links úteis
- Especificações v2: `docs/v2-client-daemon/`
- CLI v2: `client/cli_main.py:1`
- Daemon (STDIO): `daemon/stdio_core.py:1`
- Fluxo v1 (compatível): `main.py:1`

## Como testar agora
- Status (daemon ou fallback): `python -m client.cli_main status`
- Dispositivos: `python -m client.cli_main devices`
- Gravação: `python -m client.cli_main record-start --duration 10` → `python -m client.cli_main record-stop`
- Transcrever: `python -m client.cli_main transcribe caminho\audio.wav`
- Exportar: `python -m client.cli_main export caminho\audio.wav --format srt`

Atualização: este arquivo será mantido ao fim de cada checkpoint relevante.
