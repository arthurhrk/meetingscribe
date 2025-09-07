#! Agents Status — MeetingScribe v2

Visao rapida do backlog do projeto e o que esta em andamento agora. Itens marcados com [Codex: in-progress] estao sob trabalho ativo neste momento.

## Fase 1 — Fundacoes do Client–Daemon
- [Done] README refatorado para v2 e visao geral
  - Arquivo: `README.md`
- [Done] Skeleton do cliente v2 (CLI) com fallback transparente
  - Arquivos: `client/cli_main.py`, `client/rich_ui.py`, `client/fallback_runner.py`, `client/daemon_client.py`
- [Done] Daemon stub via STDIO (JSON-RPC) com metodos basicos
  - Arquivo: `daemon/stdio_core.py`
  - Metodos: `ping`, `system.status`, `devices.list`, `record.start`, `record.stop`, `transcribe.start`, `export.run`
- [Done] Checklist de aceitacao por UC
  - Arquivo: `docs/v2-client-daemon/acceptance-checklist.md`

## Fase 2 — Daemon “Always-Ready”
- [Done] Transporte por Named Pipes (cliente + servidor) — skeleton entregue; STDIO mantido como fallback
  - Arquivos: `client/transport/namedpipe_transport.py`, `daemon/named_pipe_server.py`
- [Done] CLI v2: utilitarios de servico (status/repair/restart) — stubs
  - Arquivo: `client/cli_main.py` (subcomando `service`)
- [Codex: in-progress] Integrar NamedPipeServer ao lifecycle do daemon (iniciar/parar junto ao processo)
  - Alvo: `daemon/daemon_main.py` (inicializar named pipe server)
- [Next] Windows Service wrapper funcional (instalar/iniciar/parar/status)
  - Arquivo: `daemon/service.py` (base existente), ajustes e docs de instalacao
- [Next] Pre-carregamento de modelo base + gestao de memoria inicial
  - Alvo: `daemon/resource_manager.py` (novo)

## Fase 3 — Paridade ampliada e UX
- [Next] Transcricao assincrona com progresso e fila (queue list/status/cancel)
- [Next] Exportacoes batch e organizacao por padroes (data/cliente)
- [Next] Integracao Raycast v2 (daemon-connector + fallback)

## Links uteis
- Especificacoes v2: `docs/v2-client-daemon/`
- CLI v2: `client/cli_main.py:1`
- Daemon (STDIO): `daemon/stdio_core.py:1`
- Fluxo v1 (compatível): `main.py:1`

## Como testar agora
- Status (daemon ou fallback): `python -m client.cli_main status`
- Dispositivos: `python -m client.cli_main devices`
- Gravacao: `python -m client.cli_main record-start --duration 10` -> `python -m client.cli_main record-stop`
- Transcrever: `python -m client.cli_main transcribe caminho\audio.wav`
- Exportar: `python -m client.cli_main export caminho\audio.wav --format srt`
- Servico (stubs): `python -m client.cli_main service status`

Atualizacao: este arquivo sera mantido ao fim de cada checkpoint relevante.
