# 🚀 Instalação da Extensão MeetingScribe para Raycast

## Pré-requisitos

### 1. MeetingScribe Core
- **MeetingScribe** instalado e funcionando
- Python 3.8+ com todas as dependências
- Sistema de áudio WASAPI configurado

### 2. Raycast
- **Raycast** instalado no Windows
- Versão mínima: 1.75.2

### 3. Node.js (Para desenvolvimento)
- **Node.js** 18+ (apenas se for desenvolver/compilar)

## 📦 Instalação Rápida

### Opção 1: Instalação via Raycast Store (Recomendado)
```
1. Abra o Raycast (⌘ Space)
2. Digite "store" e selecione "Raycast Store"
3. Procure por "MeetingScribe"
4. Clique em "Install"
5. Configure as preferências (veja seção abaixo)
```

### Opção 2: Instalação Manual
```bash
# 1. Clone ou baixe os arquivos da extensão
cd raycast-extension

# 2. Instale dependências
npm install

# 3. Construa a extensão
npm run build

# 4. Instale no Raycast
npm run publish
```

## ⚙️ Configuração

### Passo 1: Configurar Preferências no Raycast

Abra o Raycast e vá em **Extensions > MeetingScribe > Configure Extension**:

#### Configurações Obrigatórias:

**Python Path:**
```
python
```
*Ou caminho completo se Python não estiver no PATH:*
```
C:\Python311\python.exe
```

**Project Path:**
```
C:\Users\seu-usuario\Documents\GitHub\meetingscribe
```
*Substitua pelo caminho real do seu projeto MeetingScribe*

#### Configurações Opcionais:

**Default Whisper Model:**
- `tiny` - Mais rápido (39MB)
- `base` - Equilibrado (74MB) **[Recomendado]**
- `small` - Boa precisão (244MB)
- `medium` - Alta precisão (769MB)
- `large-v3` - Máxima precisão (1550MB)

### Passo 2: Testar Configuração

1. Abra o Raycast (⌘ Space)
2. Digite `ms status`
3. Pressione Enter
4. Verifique se todos os componentes estão ✅

## 🎯 Comandos Disponíveis

### Comandos Principais

- **`ms record`** - Inicia nova gravação
- **`ms recent`** - Lista transcrições recentes
- **`ms transcribe`** - Transcreve arquivo de áudio
- **`ms status`** - Status do sistema
- **`ms export`** - Exporta transcrições

### Atalhos Rápidos

- **⌘ + R** - Atualizar listas
- **Enter** - Executar ação principal
- **⌘ + Enter** - Ação secundária
- **⌘ + ←** - Voltar

## 🐛 Resolução de Problemas

### Erro: "Python command not found"

**Solução:**
1. Verifique se Python está instalado: `python --version`
2. Se não estiver no PATH, use caminho completo nas preferências:
```
C:\Users\SeuUsuario\AppData\Local\Programs\Python\Python311\python.exe
```

### Erro: "Project path not found"

**Solução:**
1. Verifique se o caminho está correto
2. Use barras normais (`/`) ao invés de invertidas (`\`)
3. Exemplo correto:
```
C:/Users/seu-usuario/Documents/GitHub/meetingscribe
```

### Erro: "No audio devices found"

**Solução:**
1. Execute `ms status` para verificar WASAPI
2. Execute o MeetingScribe diretamente: `python main.py`
3. Verifique se pyaudiowpatch está instalado

### Preview de transcrições não funciona

**Solução:**
1. Verifique permissões de leitura dos arquivos
2. Confirme se os arquivos estão em `storage/transcriptions/`
3. Execute uma transcrição de teste primeiro

## 🔧 Desenvolvimento Local

### Setup para Desenvolvimento

```bash
# Clone o repositório
git clone https://github.com/arthurhrk/meetingscribe.git
cd meetingscribe/raycast-extension

# Instale dependências
npm install

# Modo de desenvolvimento
npm run dev
```

### Estrutura de Arquivos

```
raycast-extension/
├── package.json          # Configuração da extensão
├── src/
│   ├── record.tsx        # Comando de gravação
│   ├── recent.tsx        # Transcrições recentes
│   ├── transcribe.tsx    # Transcrever arquivo
│   ├── status.tsx        # Status do sistema
│   └── export.tsx        # Exportar transcrições
├── README.md             # Documentação técnica
└── INSTALL.md            # Este arquivo
```

### Comandos de Build

```bash
npm run lint          # Verificar código
npm run fix-lint      # Corrigir problemas automaticamente
npm run build         # Construir extensão
npm run publish       # Publicar na Raycast Store
```

## 📋 Checklist de Instalação

- [ ] MeetingScribe instalado e funcionando
- [ ] Raycast instalado e funcionando
- [ ] Extensão MeetingScribe instalada
- [ ] **Python Path** configurado corretamente
- [ ] **Project Path** configurado corretamente
- [ ] Teste `ms status` passou ✅
- [ ] Teste de gravação funcionando
- [ ] Preview de transcrições funcionando

## 🆘 Suporte

### Logs e Debug

**Logs do MeetingScribe:**
```
{project_path}/logs/meetingscribe.log
```

**Logs do Raycast:**
- Abra Raycast
- ⌘ + K → "Open Extension Logs"

### Contato

- **GitHub Issues**: [meetingscribe/issues](https://github.com/arthurhrk/meetingscribe/issues)
- **Discord**: Link do servidor (se disponível)
- **Email**: suporte@meetingscribe.dev

---

## 🎉 Pronto!

Após a configuração, você pode usar o MeetingScribe diretamente pelo Raycast:

1. **⌘ + Space** (abre Raycast)
2. Digite **`ms`** + **comando**
3. Aproveite a transcriação instantânea! 🎤✨