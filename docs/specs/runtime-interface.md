# Especificação da Interface de Runtime (Transporte-Agnóstica)

## Princípios

- Transporte-agnóstico: o core não depende de HTTP nem de Raycast.
- Ports & Adapters: contratos no centro; adapters em volta (CLI, STDIO, Raycast, HTTP opcional).
- Uma fonte de verdade: comandos, respostas e eventos JSON estáveis.
- Compatibilidade progressiva: CLI atual continua; novos adapters são plugáveis.

## Visão Geral

Esta especificação define os contratos de interação com o sistema em tempo de execução. Qualquer adapter (Raycast, CLI, STDIO, HTTP opcional) deve seguir estes contratos.

- Campo comum em todas as respostas: `interface_version` (ex.: "1.0").
- Modos de operação:
  - Execução única via CLI com `--json` (stdout JSON puro e exit codes padronizados)
  - Runner persistente via `--serve-stdio` (daemon em stdin/stdout) com eventos opcionais `--stream`

## Comandos (Métodos)

Os métodos a seguir são a fonte de verdade. Adapters mapeiam 1:1 para estes métodos.

1) devices.list
- Request: `{ "method": "devices.list" }`
- Response sucesso:
  ```json
  {
    "interface_version": "1.0",
    "status": "success",
    "data": { "devices": [ {"index":17,"name":"Speakers [Loopback]","host_api":"Windows WASAPI","is_loopback":true,"default_sample_rate":48000.0} ] }
  }
  ```

2) record.start
- Params: `{ "device_id": "17", "duration": 30, "output": "optional.wav" }`
- Response: `{ "status":"success", "data": { "session_id": "rec_123", "filename": ".../recordings/file.wav" } }`

3) record.stop
- Params: `{ "session_id": "rec_123" }`
- Response: `{ "status":"success", "data": { "audio_file": {"path":".../file.wav","duration": 30.1} } }`

4) transcription.start
- Params: `{ "audio_path": ".../file.wav", "model": "base", "language": "auto", "options": { "vad": true } }`
- Response: `{ "status":"success", "data": { "job_id": "job_abc" } }`

5) job.status
- Params: `{ "job_id": "job_abc" }`
- Response: `{ "status":"success", "data": { "job_id": "job_abc", "state": "running", "progress": 0.42 } }`

6) job.cancel
- Params: `{ "job_id": "job_abc" }`
- Response: `{ "status":"success", "data": { "job_id": "job_abc", "state": "canceled" } }`

7) files.list
- Params: `{ "type": "recordings|transcriptions|exports" }`
- Response: `{ "status":"success", "data": { "items": [ {"filename":"...","path":"...","created":"2025-08-06T10:00:00"} ] } }`

8) export.run
- Params: `{ "filename": "<base-name>", "format": "txt|json|srt|vtt|xml|csv" }`
- Response: `{ "status":"success", "data": { "export_path": ".../exports/file.txt" } }`

9) system.status
- Request: `{ "method": "system.status" }`
- Response: `{ "status":"success", "data": { "hardware": {"gpu": false}, "health": "ok" } }`

10) cache.status (se aplicável)
- Request: `{ "method": "cache.status" }`
- Response: `{ "status":"success", "data": { "overview": {"hit_rate":"92%"}, "file_cache": {"entries": 12} } }`

Observação: Campos adicionais podem ser incluídos desde que não quebrem compatibilidade. Campos obrigatórios devem existir conforme os exemplos.

## Eventos de Progresso (JSONL)

Quando `--stream` estiver ativo (ou via STDIO), o sistema pode emitir uma linha JSON por evento no stdout:

```json
{ "event":"progress", "job_id":"job_abc", "ts":"2025-08-06T10:00:01Z", "progress":0.25, "message":"carregando modelo" }
{ "event":"progress", "job_id":"job_abc", "ts":"2025-08-06T10:00:04Z", "progress":0.60, "message":"processando segmentos" }
{ "event":"state_change", "job_id":"job_abc", "ts":"2025-08-06T10:00:10Z", "state":"completed" }
```

Alternativa de polling: arquivo `storage/tmp/jobs/<job_id>.json` com último estado.

## Erros Padronizados

- Resposta de erro:
```json
{
  "interface_version": "1.0",
  "status": "error",
  "error": { "code": "E_VALIDATION", "message": "Parâmetro inválido: device_id", "details": {"field":"device_id"} }
}
```

- Códigos sugeridos: `E_AUDIO_DEVICE`, `E_WASAPI_UNAVAILABLE`, `E_MODEL_MISSING`, `E_TIMEOUT`, `E_VALIDATION`, `E_INTERNAL`.

- Exit codes:
  - 0: sucesso
  - 10: erro de validação/entrada
  - 20: dependências/ambiente
  - 30: erro interno/inesperado

## Runner Persistente via STDIO (`--serve-stdio`)

- Modo: processo permanece ativo, aceitando requests via stdin e emitindo respostas via stdout.
- Protocolo: JSON-RPC 2.0 (recomendado) ou requests/answers linha-a-linha.
- Exemplo (linha-a-linha):
  - Input: `{ "id":1, "method":"transcription.start", "params": {"audio_path":"..."} }\n`
  - Output: `{ "id":1, "result": {"status":"success", "data": {"job_id":"job_abc"}, "interface_version":"1.0" } }\n`
  - Eventos (intercalados): linhas JSON com `{ "event": ... }` (o cliente deve filtrar por presença de `event` vs `id`).

## Versionamento da Interface

- Campo `interface_version` obrigatório nas respostas e recomendado em eventos.
- Aumentar versão apenas em mudanças breaking; preferir adições compatíveis.

