# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planejado
- Captura de áudio do sistema
- Integração com OpenAI Whisper
- Identificação de speakers
- API REST
- Interface web

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