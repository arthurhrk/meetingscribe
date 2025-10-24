# 🔍 Verificar Configuração do Raycast

## Passo 1: Verificar Preferências

1. Abra Raycast
2. Digite: `Start Recording`
3. Pressione `Cmd + ,` (vírgula) ou `Ctrl + ,`
4. Verifique os campos:

### Python Path
Deve ser UM destes:

**Opção A (Recomendado):**
```
C:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe\.venv\Scripts\python.exe
```

**Opção B:**
```
C:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe\venv\Scripts\python.exe
```

### Project Path
```
C:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe
```

## Passo 2: Verificar se o Script Existe

No PowerShell:
```powershell
Test-Path "C:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe\gravar_raycast.py"
```

Deve retornar: `True`

## Passo 3: Verificar Logs do Raycast

Quando você tenta gravar no Raycast, olhe os logs:

No Raycast:
- Pressione `Cmd + Shift + D` (ou `Ctrl + Shift + D`)
- Veja o console

Ou no PowerShell, veja os logs enquanto testa:
```powershell
# Em uma janela separada, deixe rodando:
Get-Content "C:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe\logs\*.log" -Wait
```

## Passo 4: Teste Manual que SEI que Funciona

```powershell
cd "C:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe"

# Deletar arquivo antigo
Remove-Item storage\recordings\recording_*.wav -ErrorAction SilentlyContinue

# Executar
.\venv\Scripts\python.exe gravar_raycast.py 10

# AGUARDAR 12 SEGUNDOS

# Verificar
Get-ChildItem storage\recordings\ | Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

## Passo 5: Se Manual Funciona mas Raycast Não

O problema é a configuração do Raycast. Vamos criar um script de diagnóstico:

```powershell
# Criar script de teste
@'
import sys
print("DIAGNOSTIC INFO:")
print(f"Python: {sys.executable}")
print(f"Version: {sys.version}")
print(f"CWD: {sys.path[0]}")
'@ | Out-File -FilePath diagnostic.py -Encoding utf8

# Executar via Raycast (temporariamente edite record.tsx para usar diagnostic.py)
# Ou execute manualmente:
.\venv\Scripts\python.exe diagnostic.py
```

## Resultado Esperado

✅ Teste manual funciona
✅ Arquivo criado
✅ Você consegue ouvir o áudio

Se manual funciona mas Raycast não:
- Problema é nas preferências do Raycast
- Ou problema é no caminho do Python
- Ou processo está sendo morto muito cedo

Me envie:
1. Screenshot das preferências do Raycast
2. Output do teste manual do gravar_raycast.py
3. Logs do Raycast quando tenta gravar
