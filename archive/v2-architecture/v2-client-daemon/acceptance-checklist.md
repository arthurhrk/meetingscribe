# MeetingScribe v2.0 — Acceptance Checklist (Use Cases)

Arquivo de validação funcional baseado nos casos de uso em `docs/v2-client-daemon/use-cases.md` e requisitos em `docs/v2-client-daemon/functional-requirements.md`.

## Traçabilidade (UC ↔ FR)
- UC-001 Morning System Check: FR-001, FR-006
- UC-002 Teams Auto-Detection & Recording: FR-001, FR-002, FR-003, FR-006
- UC-003 Dynamic Audio Device Management: FR-003, FR-006
- UC-004 Post-Meeting Processing: FR-004, FR-006
- UC-005 Batch Processing (End of day): FR-004, FR-005, FR-006
- UC-006 Raycast Command Center: FR-001, FR-005, FR-006

## UC-001 — Morning System Check
- Ready: Status exibe “Ready”, uptime, memória < 300MB, modelos carregados.
- Dispositivos: Lista fontes ativas/detectadas e destaca preferidas.
- Idioma: Mostra idioma padrão e auto-detect habilitado (se aplicável).
- Ações rápidas: Botões/ações “Repair/Restart” funcionam e recuperam em < 10s.
- Tempo: Usuário confirma prontidão em < 10s; todo fluxo < 30s.

## UC-002 — Teams Auto-Detection & Recording
- Detecção: Teams detectado em ≤ 10s do join (máx. aceitável 30s).
- Prompt: Notificação discreta com opções [Always for Teams] [Yes] [No] [Settings]; expira para “No” em 15s.
- Início: Gravação inicia ≤ 5s após “Yes”; indicador de estado visível.
- Prioridade de fonte: 1) Loopback speakers; 2) Microfone dedicado; 3) Default. Troca automática se indisponível.
- Estabilidade: Gravação persiste em reconexões/interrupções breves do Teams.
- Término: Fim detectado ≤ 30s após encerrar; prompt “Transcrever agora? [Yes/Later/Delete]”.
- Arquivo: Nomeação conforme padrão configurado e metadados básicos salvos.

## UC-3 — Dynamic Audio Device Management
- Monitoramento: Mudanças de dispositivo detectadas em ≤ 10s.
- Auto-reparo: Baixa amplitude/silêncio leva à troca para fonte reserva e notificação ao usuário.
- Preferências: Sistema recorda preferências por contexto (Teams, manual, etc.).
- Transparência: Mudança de dispositivo não interrompe gravação em andamento.

## UC-004 — Post-Meeting Processing
- Fila: Ao escolher “Transcrever agora”, job é enfileirado e visível nas interfaces.
- Início: Transcrição inicia ≤ 15s; progresso emitido em tempo real.
- Qualidade: Modelo e idioma conforme preferências; timestamps habilitados se configurado.
- Export: Geração de formatos (ex.: txt, srt) concluída dentro dos SLOs (txt ≤ 10–30s típ.).
- Notificação: Alerta de conclusão com links/ações rápidas.

## UC-005 — Batch Processing (End of Day)
- Seleção: Usuário escolhe 2+ itens; opções globais (idioma/modelo/formatos/organização) aplicadas.
- Execução: Jobs seguem com alocação ótima de recursos e progresso por item (n/m).
- Responsividade: Sistema permanece responsivo; sem degradação perceptível.
- Organização: Saídas organizadas por padrão (ex.: data/cliente) sem colisões de nome.
- Relato final: Sumário com sucesso/erros e caminhos de saída.

## UC-006 — Raycast Command Center
- Status: Estado refletido (Ready, modelos, dispositivos, fila, gravação ativa) idêntico ao daemon.
- Ações: Quick Record/Stop/Recent/Export funcionam com latências alvo (< 3s resposta de comando).
- Consistência: CLI e Raycast mostram estado sincronizado (mesmas sessões/fila).
- Acessibilidade: Atalhos e feedback visual padronizados; erros claros e acionáveis.

## Critérios Globais de Aceite
- SLOs percebidos: respostas CLI < 3s; detecção Teams < 10–30s; start rec < 5–10s; start transcrição < 5–15s; export < 10–30s.
- Qualidade: Acurácia > 95% (WER), timestamps ±0,5s; diarização > 85% quando habilitada.
- Confiabilidade: Disponibilidade 99,9% (horário comercial); sucesso de gravação 99,5%; sem vazamentos (drift < 10MB/h).
- Fallback: Daemon ausente → operação direta sem regressões; mensagens de status/recuperação orientam correção em 1 clique.

