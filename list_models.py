"""
================================================================================
list_models.py — List Available Models for Your API Key
================================================================================
Purpose:
    Utility script to inspect which Gemini models your API key can access.
    Run this before setting MODEL in config.py.

    Model availability depends on your account tier (free vs. paid) and region.
    The name shown here is the EXACT string to use in config.py — including
    the "models/" prefix, which is required by the google-genai SDK.

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
