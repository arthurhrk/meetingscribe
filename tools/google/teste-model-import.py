import google.generativeai as genai
from importlib import metadata  # Usado para checar a versão
import os

# --- Configuração ---
# Coloque sua API Key aqui
API_KEY = "AIzaSyAX3uH8jFWJP1wXeZ21UvfgUmRwbXV-wIc" 
# --------------------

try:
    genai.configure(api_key=API_KEY)

    # 1. Vamos checar a versão da biblioteca que está instalada
    print("--- Diagnóstico ---")
    try:
        version = metadata.version('google-generativeai')
        print(f"Versão da biblioteca 'google-generativeai': {version}")
    except metadata.PackageNotFoundError:
        print("Erro: Biblioteca 'google-generativeai' não encontrada.")
    except Exception as e:
        print(f"Erro ao checar versão: {e}")

    # 2. Vamos listar os modelos que a SUA API Key pode ver
    #    e que suportam o método 'generateContent' (que áudio precisa)
    print("\n--- Modelos disponíveis que suportam 'generateContent' ---")
    count = 0
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            count += 1
    
    if count == 0:
        print("Nenhum modelo com suporte a 'generateContent' foi encontrado.")
    
    print("---------------------------------------------------------")

except Exception as e:
    print(f"\n--- ERRO GERAL ---")
    print(f"Ocorreu um erro ao tentar conectar ou listar modelos: {e}")
    print("Verifique se sua API Key é válida e se as permissões estão corretas.")