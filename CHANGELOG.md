# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planejado
- Relatórios e Analytics avançados
- API REST para automação
- Interface web moderna
- Integração com Microsoft Teams

## [1.1.0] - 2025-08-06

### 🚀 Adicionado - Raycast Extension
- **Extensão Raycast nativa** para acesso instantâneo via ⌘ Space
- **5 comandos principais**: `ms record`, `ms recent`, `ms transcribe`, `ms status`, `ms export`
- **Bridge Python-TypeScript** via argumentos CLI com saídas JSON
- **Preview inline** de transcrições diretamente no Raycast
- **Actions contextuais** para abrir, exportar e deletar arquivos
- **Configurações integradas** nas preferências do Raycast
- **Documentação completa** com guia de instalação (INSTALL.md)
- **Interface CLI adaptada** com argumentos --json, --list-json para integração

### 🔧 Melhorado - Backend CLI
- **main.py** expandido com suporte a argumentos de linha de comando
- **device_manager.py** com saída JSON estruturada via --list-json
- **system_check.py** com output JSON para status do sistema via --json
- **Error handling** aprimorado para integração com extensões

### 📚 Documentação
- **README.md** atualizado com status da Raycast Extension (100% concluído)
- **raycast-extension/README.md** com documentação técnica
- **raycast-extension/INSTALL.md** com guia completo de instalação
- **Roadmap** reorganizado com marcos de desenvolvimento

### 📦 Estrutura
- **raycast-extension/** diretório completo com extensão TypeScript
- **package.json** configurado para Raycast Store
- **tsconfig.json** e **.gitignore** para desenvolvimento
- **5 componentes React** (record.tsx, recent.tsx, transcribe.tsx, status.tsx, export.tsx)

## [1.0.0] - 2025-08-05

### 🎉 Major Release - Sistema Completo de Transcrição IA

#### ✨ Adicionado - Core Features
- **Sistema de Transcrição IA completo** com OpenAI Whisper
- **5 modelos Whisper**: tiny, base, small, medium, large-v3
- **Auto-detecção de idioma** + suporte manual a 50+ idiomas
- **Captura de áudio WASAPI** profissional do sistema Windows
- **Identificação de speakers** com pyannote.audio (sistema híbrido)
- **Exportação multi-formato**: TXT, JSON, SRT, VTT, XML, CSV
- **Gerenciador de arquivos** com busca e estatísticas
- **Interface Rica** com Rich CLI colorida e interativa

#### 🤖 IA e Processamento
- **faster-whisper** para otimização CPU/GPU
- **Progress tracking** em tempo real para transcrições
- **Speaker Detection** com 5 modos: Auto, Reunião, Entrevista, Palestra, Custom
- **Análise de participação** com barras visuais
- **Estimativa inteligente** de tempo baseada no hardware

#### 🎵 Sistema de Áudio
- **Gravação WASAPI** de alta qualidade
- **Auto-detecção** de dispositivos de loopback
- **Suporte a múltiplos dispositivos** de entrada
- **Controle de qualidade** e taxa de amostragem
- **Monitoramento em tempo real** durante gravação

#### 📤 Exportação Avançada
- **6 formatos de exportação** com templates personalizáveis
- **Metadados completos** incluídos em todas as exportações
- **Timestamps precisos** para sincronização
- **Abertura automática** de arquivos exportados

#### ⚙️ Sistema e Configuração
- **Verificação automática** de 24 componentes do sistema
- **Detecção de hardware** e otimização automática
- **Presets de performance** baseados no hardware detectado
- **Backup e restore** automático de configurações
- **Logs estruturados** com Loguru e rotação automática

### 🛠 Tecnologias Integradas
- **OpenAI Whisper** via faster-whisper 1.1.1
- **pyannote.audio** para speaker detection
- **PyAudioWPatch** 0.2.12.7 para áudio WASAPI
- **Rich** 13.7.0 para interface CLI moderna
- **Pydantic** 2.5.0 para configuração robusta
- **Loguru** 0.7.2 para logging avançado

### 📈 Métricas v1.0.0
- **96% dos componentes funcionais** (23/24 verified)
- **100% das funcionalidades core** implementadas
- **Processamento 100% local** garantido
- **Suporte completo Windows** WASAPI

## [0.1.0] - 2025-08-03

### Adicionado
- Sistema de configuração centralizada com Pydantic BaseSettings
- Interface CLI rica e colorida usando Rich
- Sistema de logging estruturado com Loguru
- Verificação automática de sistema e dependências (`system_check.py`)
- Criação automática de estrutura de diretórios
- Menu interativo com placeholders para futuras funcionalidades
- Carregamento automático de variáveis de ambiente com python-dotenv
- Documentação completa no README
- Estrutura de projeto modular e organizada
- Error handling robusto com diferentes tipos de exceção
- Progress bars e spinners para feedback visual
- Configuração de logging com rotação automática de arquivos
- Validação de tipos e valores com Pydantic
- Support para modo debug com logs verbosos

### Técnico
- Python 3.8+ compatibility
- Rich 13.7.0 para interface CLI
- Loguru 0.7.2 para logging avançado
- Pydantic 2.5.0 para configuração e validação
- python-dotenv 1.0.0 para variáveis de ambiente
- Estrutura preparada para testes unitários e integração

### Correções
- Tratamento de encoding Unicode para terminais Windows
- Validação robusta de configurações de sistema
- Error handling abrangente para diferentes cenários de falha
- Fallbacks para interface quando há problemas de renderização

### Segurança
- Processamento 100% local sem envio de dados externos
- Validação de entrada de usuário
- Logs seguros sem exposição de dados sensíveis

## [0.0.1] - 2025-08-03

### Adicionado
- Configuração inicial do projeto
- Estrutura básica de diretórios
- Arquivo README inicial
- Setup básico do repositório Git

---

## Tipos de Mudanças

- `Adicionado` para novas funcionalidades
- `Alterado` para mudanças em funcionalidades existentes
- `Depreciado` para funcionalidades que serão removidas em breve
- `Removido` para funcionalidades removidas
- `Correções` para correção de bugs
- `Segurança` para vulnerabilidades corrigidas
- `Técnico` para mudanças técnicas que não afetam o usuário final