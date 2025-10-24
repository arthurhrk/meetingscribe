# MeetingScribe Raycast Extension

Extensão oficial do MeetingScribe para Raycast - acesso instantâneo a todas as funcionalidades via ⌘ Space.

## 🚀 Comandos Disponíveis

- **`ms record`** - Inicia nova gravação de áudio
- **`ms recent`** - Lista transcrições recentes com preview
- **`ms transcribe`** - Transcreve arquivo de áudio existente
- **`ms status`** - Verifica status do sistema e dispositivos
- **`ms export`** - Exporta transcrições rapidamente

## ⚙️ Configuração

### Pré-requisitos

1. **MeetingScribe** instalado e funcionando
2. **Raycast** instalado
3. **Node.js** 18+ para desenvolvimento

### Instalação

1. Clone este diretório ou baixe os arquivos
2. Configure as preferências no Raycast:
   - **Python Path**: Caminho para Python (ex: `python` ou caminho completo)
   - **Project Path**: Caminho completo para o diretório do MeetingScribe
   - **Default Model**: Modelo Whisper padrão (recomendado: `base`)

### Configuração de Preferências

```
Python Path: python
Project Path: C:\Users\seu-usuario\MeetingScribe
Default Model: base
```

## 🔧 Desenvolvimento

### Setup Local

```bash
cd raycast-extension
npm install
npm run dev
```

### Build para Produção

```bash
npm run build
npm run publish
```

## 📋 Bridge Python-TypeScript (Agnóstico de Transporte)

A extensão se comunica com o MeetingScribe Python de forma transporte-agnóstica:

- **STDIO Runner (preferido para progresso)**: Processo persistente (`python -m src.core.stdio_server`) com mensagens JSON por stdin/stdout. Usado para gravação/transcrição com progresso em tempo real e menor latência (mantém modelos carregados).
- **CLI JSON (exec-once)**: Comandos pontuais via `python -m src.core.runtime_cli ...` retornando JSON puro. Usado para listagens/exports e status rápidos quando não há necessidade de manter processo vivo.
- **File System**: Leitura leve para previews (quando aplicável).

### Métodos/Comandos Esperados

```bash
# STDIO (processo persistente)
python -m src.core.stdio_server

# Exemplos de requests por linha (JSON):
{"id":1, "method":"devices.list"}
{"id":2, "method":"record.start", "params": {"device_id":"17", "stream":true}}
{"id":3, "method":"transcription.start", "params": {"audio_path":"file.wav", "model":"base", "stream":true}}
{"id":4, "method":"files.list", "params": {"type":"transcriptions", "limit":20}}
{"id":5, "method":"export.run", "params": {"filename":"<base>", "format":"srt"}}

# CLI JSON (execução única)
python -m src.core.runtime_cli devices
python -m src.core.runtime_cli system
python -m src.core.runtime_cli files transcriptions --limit 20
python -m src.core.runtime_cli export "<base>" --format srt
```

## 🎯 Features

### ✅ Implementado

- Comandos básicos (record, recent, transcribe, status, export)
- Interface visual com listas e formulários
- Preview inline de transcrições
- Actions contextuais
- Configurações integradas
- Comunicação Python-TypeScript (STDIO + CLI JSON)

### 🟡 Em Desenvolvimento

- Notificações de progresso em tempo real (via STDIO events)
- Cache de dados para performance
- Validação de configurações
- Error handling avançado

### 🔴 Planejado

- Drag & drop de arquivos
- Shortcuts customizáveis
- Temas e personalização
- Integração com outras ferramentas

## 🐛 Troubleshooting

### Erro: "STDIO server not running"
- Confirme `Python Path` e `Project Path` nas preferências
- Reinicie a extensão para religar o STDIO runner

### Erro: "Project path not found"
- Configure o caminho completo para o diretório do MeetingScribe
- Use barras invertidas duplas no Windows: `C:\\Users\\...`

### Preview não carrega
- Verifique se os arquivos de transcrição existem
- Confirme as permissões de leitura dos arquivos

## ⚙️ Runner Mode

- **Exec-once (CLI JSON)**: usado para listagens e exportações. Baixa sobrecarga, inicia e termina a cada chamada.
- **STDIO Daemon**: usado para gravação/transcrição. Processo persistente que emite eventos de progresso em JSONL. Reduz latência por manter modelos carregados.

Preferências necessárias:
- `Python Path`: caminho do binário do Python (ex.: `python`)
- `Project Path`: diretório do repositório MeetingScribe
- `Default Model`: modelo default do Whisper (ex.: `base`)

## 📄 Licença

MIT - Mesmo que o projeto MeetingScribe principal.
