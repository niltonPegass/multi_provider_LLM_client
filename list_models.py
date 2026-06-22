"""
================================================================================
list_models.py — List Available Models for Your API Key
================================================================================
Purpose:
    Utility script to inspect which Gemini models are accessible with your
    current API key. Run this before setting MODEL in config.py.

    The available models depend on your account tier (free vs. paid) and
    region. The name returned here is the exact string to use in config.py —
    the "models/" prefix is required by the new SDK.

Usage:
    python list_models.py
================================================================================
"""

from google import genai
from config import API_KEY

client = genai.Client(api_key=API_KEY)

print("\nAvailable models for your API key:\n")
for model in client.models.list():
    print(f"  {model.name}")
