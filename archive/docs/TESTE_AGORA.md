# 🧪 Teste Rápido - Recording via Raycast

## O Que Foi Corrigido

Mudei de `exec()` para `spawn()` no [record.tsx](raycast-extension/src/record.tsx). Isso mantém o processo Python vivo até completar a gravação.

## Como Testar

### 1. Abrir Raycast
```
Alt + Espaço (ou seu atalho do Raycast)
```

### 2. Iniciar Gravação
- Digite: **"Start Recording"**
- Escolha: **"Gravar 30s"**
- Deve aparecer: **"✅ Gravação iniciada! 30s — recording_..."**

### 3. Aguardar ⏱️
**IMPORTANTE**: Espere **32 segundos completos** (30s + 2s de buffer)

### 4. Verificar Arquivo
```powershell
cd "c:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe"
ls storage/recordings/ -Sort LastWriteTime -First 1
```

### 5. Verificar Conteúdo
```powershell
$latest = ls storage/recordings/recording_*.wav -Sort LastWriteTime -First 1
ffprobe $latest.FullName 2>&1 | Select-String "Duration|Stream"
```

## O Que Deve Acontecer

### ✅ Sucesso
- Toast aparece imediatamente
- Processo Python continua rodando
- Após 32 segundos: arquivo WAV criado
- Arquivo é reproduzível

### ❌ Se Falhar
Verifique as configurações do Raycast:
1. Abra Raycast Settings
2. Extensions → MeetingScribe
3. Confirme os caminhos:
   - **Python Path**: `c:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe\venv\Scripts\python.exe`
   - **Project Path**: `c:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe`

## Teste Manual (Se Raycast Falhar)
```powershell
.\venv\Scripts\python.exe gravar_raycast.py 10
```

Deve imprimir JSON imediatamente e criar arquivo após 12 segundos.

## Diferença da Versão Anterior

**ANTES**:
- `exec()` → processo morria antes de salvar
- JSON retornava, mas arquivo não era criado

**AGORA**:
- `spawn()` → processo continua até completar
- Referência armazenada em `activeRecordings` Map
- Processo só termina após salvar o arquivo

## Detalhes Técnicos

Ver documentação completa: [FIX_RECORDING_PROCESS.md](FIX_RECORDING_PROCESS.md)

**Build Status**: ✅ Extension built successfully

**Arquivos Modificados**:
- [raycast-extension/src/record.tsx](raycast-extension/src/record.tsx)
  - Linha 12: Mudou import de `exec` para `spawn`
  - Linha 33: Adicionou `activeRecordings` Map
  - Linha 87-92: Mudou de exec() para spawn()
  - Linha 114-120: Armazena referência do processo

**Confiança**: 🎯 ALTA - Esta é a solução correta
