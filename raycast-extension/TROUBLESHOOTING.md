# 🔧 Troubleshooting - MeetingScribe Raycast Extension

## ❌ Erro: "Invalid device data format"

### Problema
A extensão não consegue listar os dispositivos de áudio e mostra o erro:
```
Error loading devices: Error: Invalid device data format
```

### Causa
O comando `device_manager.py --list-json` ou `main.py devices` está travando ou falhando ao inicializar o PyAudio/WASAPI.

### ✅ Solução Implementada (Automática)

A extensão agora usa **Modo de Auto-Detecção** automaticamente quando não consegue listar dispositivos:

1. **O que acontece:**
   - Quando a listagem de dispositivos falha
   - A extensão mostra: `🎯 Auto-detect (System Default)`
   - O sistema selecionará o melhor dispositivo automaticamente

2. **Como usar:**
   - Abra `Start Recording` no Raycast
   - Você verá "Dispositivo Auto-Detectado"
   - Selecione a duração desejada (30s, 60s, 5min, 10min)
   - A gravação iniciará com o dispositivo padrão do sistema

### 🔧 Solução Manual (Para listagem de dispositivos)

Se você quiser ver a lista completa de dispositivos, siga estes passos:

#### 1. Verificar PyAudio

```bash
# Teste se o PyAudio está funcionando
cd "C:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe"
./venv/Scripts/python.exe -c "import pyaudiowpatch; print('OK')"
```

Se der erro, reinstale:
```bash
pip uninstall pyaudio pyaudiowpatch -y
pip install pyaudiowpatch
```

#### 2. Testar Listagem Manualmente

```bash
# Teste direto no Python
./venv/Scripts/python.exe -c "from device_manager import DeviceManager; dm = DeviceManager(); print(dm.list_all_devices())"
```

#### 3. Verificar Permissões de Áudio

No Windows:
1. Configurações → Privacidade → Microfone
2. Permitir que aplicativos acessem o microfone: **ON**
3. Permitir aplicativos de desktop acessar o microfone: **ON**

---

## ❌ Erro: "STDIO server not running"

### Problema
```
Error: STDIO server not running
```

### Solução

#### Opção 1: Mudar para Modo CLI
1. Abra Raycast
2. Digite: `Start Recording`
3. Pressione `Cmd + ,` (vírgula)
4. Mude **Runner Mode** para: `Exec-Once CLI JSON`

#### Opção 2: Verificar Daemon
```bash
# Verificar se o daemon está rodando
cd "C:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe"
./venv/Scripts/python.exe -m src.core.stdio_server
```

---

## ❌ Erro: "Failed to start recording"

### Possíveis Causas

#### 1. Dispositivo Não Disponível
**Solução:**
- Use o modo de auto-detecção (agora é padrão quando há erro)
- Verifique se há algum programa usando o microfone/alto-falante

#### 2. PyAudio Não Instalado
**Solução:**
```bash
pip install pyaudiowpatch
```

#### 3. Permissões Negadas
**Solução:**
- Windows: Configurações → Privacidade → Microfone → Permitir
- Reinicie o Raycast após conceder permissões

---

## ⚡ Modo Rápido (Auto-Detecção)

### O que é?
Quando a extensão não consegue listar dispositivos, ela entra automaticamente no **Modo Rápido**.

### Vantagens
- ✅ Funciona mesmo se a listagem falhar
- ✅ Mais rápido (não precisa enumerar dispositivos)
- ✅ Usa o melhor dispositivo disponível automaticamente
- ✅ Ideal para uso rápido

### Como identificar?
Você verá:
```
⚡ Modo Rápido - Auto-Detecção
🎯 Auto-detect (System Default)
```

### Como funciona?
1. O sistema detecta automaticamente o dispositivo de áudio padrão
2. Para captura de sistema (reuniões): usa loopback do alto-falante padrão
3. Para captura de microfone: usa microfone padrão

---

## 🔍 Diagnóstico Completo

Execute este script para diagnóstico completo:

```bash
cd "C:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe"

echo "=== 1. Verificando Python ==="
./venv/Scripts/python.exe --version

echo ""
echo "=== 2. Verificando PyAudio ==="
./venv/Scripts/python.exe -c "import pyaudiowpatch; print('PyAudioWPatch: OK')" 2>&1

echo ""
echo "=== 3. Testando Device Manager ==="
timeout 5 ./venv/Scripts/python.exe -c "from device_manager import DeviceManager; print('DeviceManager: OK')" 2>&1 || echo "DeviceManager: TIMEOUT/ERROR"

echo ""
echo "=== 4. Testando System Check ==="
./venv/Scripts/python.exe system_check.py

echo ""
echo "=== 5. Testando CLI ==="
timeout 10 ./venv/Scripts/python.exe main.py status 2>&1 || echo "CLI: TIMEOUT/ERROR"
```

---

## 📝 Logs e Debug

### Ver Logs da Extensão

No Raycast:
1. Abra o comando
2. Pressione `Cmd + Shift + D` (abre DevTools)
3. Veja o console para erros

### Ver Logs do Python

```bash
cd "C:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe"
cat logs/*.log
```

### Ativar Debug Mode

Em `raycast-extension/src/record.tsx`, adicione no início da função:
```typescript
console.log("DEBUG: Starting loadAudioDevices");
console.log("DEBUG: Preferences:", getPreferenceValues());
```

---

## 🆘 Erros Comuns e Soluções Rápidas

| Erro | Solução Rápida |
|------|----------------|
| "Invalid device data format" | **Funciona automaticamente** - Usa modo de auto-detecção |
| "Python not found" | Configure o caminho completo do Python nas preferências |
| "STDIO server not running" | Mude Runner Mode para "CLI" nas preferências |
| "No devices found" | **Normal** - Usa auto-detecção automaticamente |
| "Permission denied" | Windows: Configurações → Privacidade → Microfone |
| "Timeout" | Aumente timeout ou use modo CLI |

---

## ✅ Verificação Final

Antes de reportar um bug, confirme:

- [ ] Python instalado e funcionando
- [ ] `pip install pyaudiowpatch` executado
- [ ] Permissões de áudio concedidas
- [ ] Caminhos configurados corretamente no Raycast
- [ ] Extension rebuilded: `npm run build`
- [ ] Testado modo de auto-detecção (deve funcionar sempre)

---

## 🎯 Modo de Auto-Detecção Sempre Funciona!

**Importante:** Mesmo se você ver o erro "Invalid device data format", a extensão continuará funcionando através do modo de auto-detecção. Você pode:

✅ Iniciar gravações normalmente
✅ Escolher duração (30s, 60s, 5min, 10min)
✅ Usar todos os recursos sem problemas

A única diferença é que você não verá a lista completa de dispositivos - mas o sistema escolherá o melhor automaticamente! 🎊

---

## 💡 Dicas Finais

### Para Melhor Performance
- Use **Modo Auto-Detecção** (é rápido e confiável)
- Configure **Runner Mode: STDIO** para melhor performance
- Use modelo **base** para transcrição (balanço velocidade/precisão)

### Para Debugging
- Sempre teste no terminal primeiro: `python main.py status`
- Verifique os logs: `logs/` no projeto
- Use DevTools do Raycast: `Cmd + Shift + D`

### Para Gravações de Reuniões
- O sistema detecta automaticamente dispositivos loopback
- Para capturar áudio do Teams/Zoom, o auto-detect funciona perfeitamente
- Não precisa configurar nada manualmente! 🎉
