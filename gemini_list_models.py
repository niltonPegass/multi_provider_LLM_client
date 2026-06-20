"""
Script utilitário para listar todos os modelos disponíveis para sua API Key.
Execute antes de configurar o MODEL em config.py.

Uso:
    python3 listar_modelos.py
"""

from google import genai
from gemini_config import API_KEY

client = genai.Client(api_key=API_KEY)

print("Modelos disponíveis:\n")
for modelo in client.models.list():
    print(f"  {modelo.name}")
