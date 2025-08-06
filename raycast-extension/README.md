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

## 📋 Bridge Python-TypeScript

A extensão se comunica com o MeetingScribe Python via:

- **CLI Commands**: Execução de comandos Python via `child_process`
- **JSON Output**: Parsing de saídas estruturadas
- **File System**: Leitura de arquivos de transcrição para preview

### Comandos Python Esperados

```bash
# Listar dispositivos de áudio
python device_manager.py --list-json

# Iniciar gravação
python main.py --record --device "device_id"

# Listar transcrições
python main.py --list-transcriptions --json

# Transcrever arquivo
python main.py --transcribe "arquivo.mp3" --model base --language pt

# Verificar status do sistema
python system_check.py --json

# Exportar transcrição
python main.py --export "arquivo" --format txt
```

## 🎯 Features

### ✅ Implementado

- Comandos básicos (record, recent, transcribe, status, export)
- Interface visual com listas e formulários
- Preview inline de transcrições
- Actions contextuais
- Configurações integradas
- Comunicação Python-TypeScript

### 🟡 Em Desenvolvimento

- Notificações de progresso em tempo real
- Cache de dados para performance
- Validação de configurações
- Error handling avançado

### 🔴 Planejado

- Drag & drop de arquivos
- Shortcuts customizáveis
- Temas e personalização
- Integração com outras ferramentas

## 🐛 Troubleshooting

### Erro: "Command not found"
- Verifique se o Python Path está correto nas preferências
- Certifique-se que o MeetingScribe está instalado e funcionando

### Erro: "Project path not found"
- Configure o caminho completo para o diretório do MeetingScribe
- Use barras invertidas duplas no Windows: `C:\\Users\\...`

### Preview não carrega
- Verifique se os arquivos de transcrição existem
- Confirme as permissões de leitura dos arquivos

## 📄 Licença

MIT - Mesmo que o projeto MeetingScribe principal.