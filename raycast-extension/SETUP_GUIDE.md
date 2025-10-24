# 🚀 Guia de Configuração do MeetingScribe no Raycast

## 📋 Pré-requisitos

Antes de começar, certifique-se de ter:

- ✅ **Raycast** instalado ([Download aqui](https://www.raycast.com/))
- ✅ **Python 3.8+** instalado no sistema
- ✅ **MeetingScribe** instalado e funcionando
- ✅ **Node.js** e **npm** instalados (para desenvolvimento)

---

## 🔧 Passo a Passo de Instalação

### 1️⃣ Preparar o Projeto Python

Primeiro, certifique-se de que o MeetingScribe está funcionando corretamente:

```bash
# Navegue até o diretório do projeto
cd C:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe

# Ative o ambiente virtual (se estiver usando)
venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Teste o sistema
python system_check.py
```

### 2️⃣ Preparar a Extensão do Raycast

```bash
# Entre no diretório da extensão
cd raycast-extension

# Instale as dependências do Node.js
npm install

# Compile a extensão
npm run build
```

### 3️⃣ Importar no Raycast (Modo Desenvolvimento)

#### **Opção A: Via Linha de Comando**

```bash
# No diretório raycast-extension/
npm run dev
```

Este comando abrirá o Raycast automaticamente em modo desenvolvimento.

#### **Opção B: Manualmente no Raycast**

1. Abra o Raycast (`Cmd + Espaço` no macOS ou `Alt + Espaço` no Windows)
2. Digite: `Import Extension`
3. Selecione a pasta: `raycast-extension/`
4. O Raycast importará a extensão automaticamente

---

## ⚙️ Configuração das Preferências

Após importar a extensão, você precisa configurar os caminhos:

### 1️⃣ Abrir Configurações

1. Abra o Raycast
2. Digite: `MeetingScribe` (qualquer comando)
3. Pressione `Cmd + ,` (vírgula) para abrir as configurações

### 2️⃣ Configurar os Caminhos

Preencha os seguintes campos:

#### **Python Path** (Caminho do Python)
- **Windows com venv:**
  ```
  C:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe\venv\Scripts\python.exe
  ```
- **Windows sem venv:**
  ```
  python
  ```
- **Linux/Mac com venv:**
  ```
  /full/path/to/meetingscribe/venv/bin/python
  ```

#### **Project Path** (Caminho do Projeto) ⚠️ **OBRIGATÓRIO**
```
C:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe
```

> **⚠️ IMPORTANTE**: Use o caminho absoluto completo do seu projeto!

#### **Default Whisper Model** (Modelo Padrão)
Escolha um dos modelos disponíveis:
- `tiny` - Mais rápido, menor precisão
- `base` - **Recomendado** - Balanço entre velocidade e precisão
- `small` - Boa precisão
- `medium` - Alta precisão
- `large-v3` - Máxima precisão (mais lento)

#### **Runner Mode** (Modo de Execução)
- `STDIO Daemon (recommended)` - **Recomendado** - Mais rápido e eficiente
- `Exec-Once CLI JSON` - Modo legado

---

## 🎯 Comandos Disponíveis

Após configurar, você terá acesso aos seguintes comandos no Raycast:

### 🎙️ **Start Recording**
Inicia uma gravação de áudio escolhendo o dispositivo.

**Como usar:**
1. Abra Raycast
2. Digite: `Start Recording`
3. Escolha o dispositivo de áudio:
   - **🎯 Auto-detect (System Default)** - ⭐ **Recomendado!** O sistema escolhe automaticamente
   - Ou selecione um dispositivo específico (use **Loopback** para capturar áudio do sistema)
4. Selecione a duração (30s, 60s, 5min, 10min)

> **💡 Modo Auto-Detecção:** Se houver problemas ao listar dispositivos, a extensão usa automaticamente o modo de **Auto-Detecção**, que funciona perfeitamente para a maioria dos casos! Você verá "⚡ Modo Rápido - Auto-Detecção" na interface.

### 📄 **Recent Transcriptions**
Lista as transcrições recentes com preview.

**Como usar:**
1. Digite: `Recent Transcriptions`
2. Navegue pelas transcrições
3. Pressione Enter para visualizar detalhes

### 📝 **Transcribe File**
Transcreve um arquivo de áudio específico.

**Como usar:**
1. Digite: `Transcribe File`
2. Selecione o arquivo de áudio
3. Aguarde o processo de transcrição

### ⚡ **Quick Export**
Exporta rapidamente a última transcrição em vários formatos.

**Formatos suportados:** TXT, JSON, SRT, VTT, XML, CSV

### 📊 **System Status**
Verifica o status do sistema e dispositivos.

### 👔 **Teams Auto Monitor**
Monitora automaticamente reuniões do Microsoft Teams e inicia gravação.

**Como usar:**
1. Digite: `Teams Auto Monitor`
2. Clique em "Start Monitoring"
3. O sistema detectará automaticamente quando você entrar em uma reunião do Teams
4. A gravação iniciará automaticamente

### 📈 **Performance Dashboard**
Dashboard de métricas de performance e status do sistema.

---

## 🐛 Resolução de Problemas

### ❌ Erro: "Python não encontrado"

**Solução:**
1. Verifique se o Python está instalado: `python --version`
2. Configure o caminho completo do Python nas preferências
3. Use o caminho do executável do venv se estiver usando ambiente virtual

### ❌ Erro: "Project Path inválido"

**Solução:**
1. Certifique-se de usar o caminho **completo e absoluto**
2. Verifique se o caminho existe no sistema
3. No Windows, use barras invertidas `\` ou barras duplas `\\`

### ❌ Erro: "Nenhum dispositivo de áudio encontrado"

**Solução:**
1. Execute `python device_manager.py --list-json` no terminal
2. Verifique se o pyaudiowpatch está instalado: `pip install pyaudiowpatch`
3. Reinicie o sistema se necessário

### ❌ Erro: "Gravação falhou"

**Possíveis causas:**
1. Dispositivo de áudio não disponível
2. Permissões de áudio não concedidas
3. Daemon não está rodando

**Solução:**
```bash
# Teste manualmente primeiro
python main.py record-start --duration 10

# Verifique o status
python main.py status

# Repare o serviço se necessário
python main.py service repair
```

### ❌ Erro: "STDIO server not running"

**Solução:**
1. Verifique se o daemon está rodando
2. Tente reiniciar a extensão no Raycast
3. Use o modo "Exec-Once CLI JSON" como fallback nas preferências

---

## 🔄 Atualizando a Extensão

Quando houver mudanças no código:

```bash
cd raycast-extension

# Reconstruir
npm run build

# Recarregar no Raycast
npm run dev
```

Ou no Raycast:
1. Digite: `Reload Extension`
2. Selecione "MeetingScribe"

---

## 📚 Recursos Adicionais

### Arquivos de Configuração
- **Projeto Python:** `config.py` ou `.env`
- **Extensão Raycast:** `raycast-extension/package.json`

### Logs e Debugging
- **Logs Python:** `logs/` no diretório do projeto
- **Console Raycast:** Pressione `Cmd + Shift + D` no Raycast para abrir DevTools

### Estrutura de Diretórios
```
meetingscribe/
├── storage/
│   ├── recordings/      # Gravações de áudio (.wav)
│   ├── transcriptions/  # Transcrições brutas
│   └── exports/         # Arquivos exportados
├── models/              # Modelos Whisper baixados
├── logs/                # Logs da aplicação
└── raycast-extension/   # Extensão do Raycast
```

---

## 💡 Dicas Úteis

### 🎯 **Atalhos de Teclado**
- `Cmd + R` - Atualizar lista de dispositivos
- `Cmd + ,` - Abrir preferências
- `Enter` - Executar ação principal
- `Cmd + K` - Abrir menu de ações

### 🔊 **Melhor Dispositivo para Gravação**
Para gravar áudio do sistema (reuniões, chamadas):
- Use dispositivos com "**Loopback**" no nome
- Geralmente aparecem como "Speakers (Loopback)" ou similar
- Ícone: 🔄

### ⚡ **Performance**
- Modelo `base` oferece melhor custo-benefício
- Modelo `tiny` para transcrições rápidas
- Use `large-v3` apenas quando precisar de máxima precisão

### 🔐 **Privacidade**
- **100% processamento local** - nada enviado para nuvem
- Todos os dados ficam em `storage/`
- Você controla quando gravar e o que transcrever

---

## ✅ Checklist de Verificação

Antes de reportar problemas, verifique:

- [ ] Python instalado e funcionando
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] `system_check.py` executa sem erros
- [ ] Caminhos configurados corretamente no Raycast
- [ ] Extensão compilada (`npm run build`)
- [ ] Dispositivos de áudio detectados (`device_manager.py --list-json`)
- [ ] Permissões de áudio concedidas ao Python/Raycast

---

## 🆘 Suporte

Se encontrar problemas:

1. **Verifique os logs:** `logs/` no diretório do projeto
2. **Execute diagnósticos:** `python system_check.py`
3. **Teste manualmente:** Use `python main.py` antes do Raycast
4. **Consulte a documentação:** `README.md` e `CLAUDE.md`

---

## 🎉 Pronto!

Agora você está pronto para usar o MeetingScribe com Raycast!

Para começar:
1. Abra o Raycast
2. Digite: `Start Recording`
3. Escolha um dispositivo
4. Selecione a duração
5. Sua gravação será salva automaticamente! 🎊
