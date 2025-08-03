# 🎤 MeetingScribe

> Sistema inteligente de transcrição para reuniões Microsoft Teams com processamento 100% local

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Rich](https://img.shields.io/badge/Rich-Interface-ff69b4)](https://github.com/Textualize/rich)
[![Whisper](https://img.shields.io/badge/OpenAI-Whisper-orange)](https://github.com/openai/whisper)

## 📋 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Features](#-features)
- [Tecnologias](#-tecnologias)
- [Instalação](#-instalação)
- [Uso](#-uso)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Configuração](#-configuração)
- [Desenvolvimento](#-desenvolvimento)
- [Release Notes](#-release-notes)
- [Roadmap](#-roadmap)
- [Contribuição](#-contribuição)
- [Licença](#-licença)

## 🚀 Sobre o Projeto

O **MeetingScribe** é uma solução completa para transcrição automática de reuniões do Microsoft Teams, desenvolvido com foco em **privacidade** e **processamento local**. O sistema utiliza tecnologias de ponta como OpenAI Whisper para garantir transcrições precisas sem enviar dados para serviços externos.

### 🎯 Principais Objetivos

- **Privacidade Total**: Processamento 100% local, sem envio de dados
- **Qualidade Superior**: Transcrição precisa com identificação de speakers
- **Interface Moderna**: CLI rica e colorida com Rich
- **Facilidade de Uso**: Setup automatizado e configuração simples
- **Extensibilidade**: Arquitetura modular para futuras expansões

## ✨ Features

### 🟢 Implementadas (v0.1.0)

- ✅ **Sistema de Configuração Centralizada**
  - Configuração com Pydantic BaseSettings
  - Carregamento automático de variáveis de ambiente
  - Validação de tipos e valores

- ✅ **Interface Rica e Intuitiva**
  - CLI colorida com Rich
  - Mensagens de status em tempo real
  - Progress bars e spinners

- ✅ **Sistema de Logging Avançado**
  - Logs estruturados com Loguru
  - Rotação automática de arquivos
  - Diferentes níveis de log

- ✅ **Verificação de Sistema**
  - Diagnóstico completo de dependências
  - Verificação de estrutura de diretórios
  - Relatório visual de status

- ✅ **Gerenciamento de Diretórios**
  - Criação automática de estrutura
  - Organização de gravações e transcrições
  - Separação por tipos de arquivo

### 🟡 Em Desenvolvimento (v0.2.0)

- 🔄 **Captura de Áudio**
  - Gravação de áudio do sistema
  - Suporte a múltiplos dispositivos
  - Filtros de ruído

- 🔄 **Engine de Transcrição**
  - Integração com OpenAI Whisper
  - Suporte a múltiplos idiomas
  - Otimização de performance

- 🔄 **Identificação de Speakers**
  - Detecção automática de participantes
  - Separação por voz
  - Timestamps precisos

### 🔴 Planejadas (v0.3.0+)

- 📋 **Exportação de Resultados**
  - Formatos: TXT, DOCX, PDF, JSON
  - Templates personalizáveis
  - Integração com ferramentas de produtividade

- 🌐 **API REST**
  - Endpoints para automação
  - Webhook support
  - Documentação interativa

- 🤖 **Processamento com IA**
  - Resumo automático de reuniões
  - Extração de action items
  - Análise de sentimentos

## 🛠 Tecnologias

### Core Technologies
- **Python 3.8+** - Linguagem principal
- **Pydantic** - Validação de dados e configuração
- **Rich** - Interface CLI moderna e colorida
- **Loguru** - Sistema de logging avançado
- **python-dotenv** - Gerenciamento de variáveis de ambiente

### Futuras Integrações
- **OpenAI Whisper** - Engine de transcrição
- **pyannote.audio** - Identificação de speakers
- **FastAPI** - API REST
- **SQLite/PostgreSQL** - Persistência de dados

## 📦 Instalação

### Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Git

### Instalação Rápida

```bash
# Clone o repositório
git clone https://github.com/arthurhrk/meetingscribe.git
cd meetingscribe

# Instale as dependências
pip install -r requirements.txt

# Execute a verificação do sistema
python system_check.py

# Inicie a aplicação
python main.py
```

### Instalação com Ambiente Virtual (Recomendado)

```bash
# Clone o repositório
git clone https://github.com/arthurhrk/meetingscribe.git
cd meetingscribe

# Crie um ambiente virtual
python -m venv venv

# Ative o ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt

# Execute a verificação
python system_check.py
```

## 🚀 Uso

### Iniciando a Aplicação

```bash
python main.py
```

### Verificação do Sistema

```bash
python system_check.py
```

### Menu Principal

O MeetingScribe oferece um menu interativo com as seguintes opções:

1. **🎙️ Iniciar nova gravação** *(Em desenvolvimento)*
2. **📝 Transcrever arquivo existente** *(Em desenvolvimento)*
3. **📁 Gerenciar transcrições** *(Em desenvolvimento)*
4. **⚙️ Configurações** *(Em desenvolvimento)*
5. **📊 Relatórios** *(Em desenvolvimento)*
6. **❌ Sair**

## 📁 Estrutura do Projeto

```
meetingscribe/
├── 📄 README.md              # Documentação principal
├── 📄 requirements.txt       # Dependências Python
├── 📄 config.py             # Configurações centralizadas
├── 📄 main.py               # Entry point da aplicação
├── 📄 system_check.py       # Verificação de sistema
├── 📄 .env                  # Variáveis de ambiente (exemplo)
├── 📁 src/                  # Código fonte principal
│   ├── 📁 api/             # Endpoints da API
│   ├── 📁 audio/           # Processamento de áudio
│   ├── 📁 core/            # Funcionalidades centrais
│   └── 📁 transcription/   # Engine de transcrição
├── 📁 storage/             # Armazenamento de dados
│   ├── 📁 recordings/      # Arquivos de áudio
│   ├── 📁 transcriptions/  # Transcrições geradas
│   └── 📁 exports/         # Arquivos exportados
├── 📁 models/              # Modelos de IA
├── 📁 logs/                # Arquivos de log
└── 📁 tests/               # Testes automatizados
    ├── 📁 unit/           # Testes unitários
    └── 📁 integration/    # Testes de integração
```

## ⚙️ Configuração

### Arquivo `.env`

Crie um arquivo `.env` na raiz do projeto:

```env
# Configurações da Aplicação
APP_NAME=MeetingScribe
APP_VERSION=0.1.0
DEBUG=true
LOG_LEVEL=INFO

# Caminhos
STORAGE_DIR=./storage
MODELS_DIR=./models
LOGS_DIR=./logs

# Configurações de Áudio
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
CHUNK_DURATION=30

# Configurações do Whisper
WHISPER_MODEL=base
WHISPER_LANGUAGE=pt
WHISPER_DEVICE=auto
```

### Configurações Avançadas

Edite o arquivo `config.py` para ajustes mais específicos:

- Caminhos de diretórios
- Configurações de logging
- Parâmetros de áudio
- Configurações do Whisper

## 🔧 Desenvolvimento

### Setup do Ambiente de Desenvolvimento

```bash
# Clone e configure
git clone https://github.com/arthurhrk/meetingscribe.git
cd meetingscribe

# Ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Dependências de desenvolvimento
pip install -r requirements.txt
```

### Executando Testes

```bash
# Verificação completa do sistema
python system_check.py

# Testes unitários (quando implementados)
python -m pytest tests/unit/

# Testes de integração (quando implementados)
python -m pytest tests/integration/
```

### Contribuindo

1. Fork o projeto
2. Crie uma feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📊 Release Notes

### v0.1.0 - Base Foundation (Atual)

**🎉 Release Inicial - 03/08/2025**

#### ✨ Novidades
- Sistema de configuração centralizada com Pydantic
- Interface CLI rica e colorida com Rich
- Sistema de logging estruturado com Loguru
- Verificação automática de sistema e dependências
- Criação automática de estrutura de diretórios
- Menu interativo placeholder para futuras funcionalidades

#### 🛠 Tecnologias
- Python 3.8+ support
- Rich 13.7.0 para interface
- Loguru 0.7.2 para logging
- Pydantic 2.5.0 para configuração
- python-dotenv 1.0.0 para variáveis de ambiente

#### 📁 Estrutura
- Organização modular de código
- Separação clara de responsabilidades
- Testes preparados para futuras implementações
- Documentação completa

#### 🐛 Correções
- Tratamento de encoding para terminais Windows
- Validação robusta de configurações
- Error handling abrangente

### Próximas Versões

#### v0.2.0 - Audio Processing (Planejado)
- Implementação de captura de áudio
- Integração com OpenAI Whisper
- Identificação básica de speakers

#### v0.3.0 - Advanced Features (Planejado)
- Exportação em múltiplos formatos
- API REST
- Interface web básica

## 🗺 Roadmap

### Q3 2025
- [ ] Implementação de captura de áudio
- [ ] Integração com Whisper
- [ ] Identificação de speakers
- [ ] Testes automatizados

### Q4 2025
- [ ] API REST
- [ ] Exportação avançada
- [ ] Interface web
- [ ] Integração com Teams

### 2026
- [ ] IA para resumos
- [ ] Múltiplos idiomas
- [ ] Plugins e extensões
- [ ] Versão empresarial

## 🤝 Contribuição

Contribuições são sempre bem-vindas! Veja como você pode ajudar:

### Tipos de Contribuição
- 🐛 Reportar bugs
- ✨ Sugerir novas features
- 📝 Melhorar documentação
- 💻 Contribuir com código
- 🧪 Escrever testes

### Guidelines
1. Verifique issues existentes antes de criar novas
2. Siga o padrão de código existente
3. Inclua testes para novas funcionalidades
4. Atualize a documentação quando necessário

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 👥 Autores

- **Arthur Andrade** - *Desenvolvimento inicial* - [@arthurhrk](https://github.com/arthurhrk)

## 🙏 Agradecimentos

- [OpenAI](https://openai.com/) pelo Whisper
- [Textualize](https://www.textualize.io/) pelo Rich
- [Delgan](https://github.com/Delgan) pelo Loguru
- [Pydantic](https://pydantic-docs.helpmanual.io/) pela validação de dados
- Comunidade Python pela inspiração e ferramentas

---

**🤖 Generated with [Claude Code](https://claude.ai/code)**

**Co-Authored-By: Claude <noreply@anthropic.com>**

