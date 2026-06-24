"""
================================================================================
config.py — Configuração Central do Projeto
================================================================================
Responsabilidade:
    Centralizar todas as configurações da aplicação em um único lugar.
    Qualquer ajuste de modelo, temperatura ou comportamento do assistente
    deve ser feito aqui — sem precisar tocar nos outros módulos.

ATENÇÃO — sobre a API Key:
    Esta versão expõe a chave diretamente no código para fins didáticos.
    Em projetos reais, substitua pelo padrão com variável de ambiente:

        import os
        API_KEY = os.environ.get("ANTHROPIC_API_KEY")

    Nunca suba um arquivo com chave real para um repositório público.
================================================================================
"""


# ── Autenticação ──────────────────────────────────────────────────────────────
# A API Key identifica sua conta na Anthropic e autoriza as requisições.
# Header HTTP gerado pelo SDK: "x-api-key: <API_KEY>"
# Formato da chave: "sk-ant-..."

API_KEY: str = "COLE_SUA_CHAVE_AQUI"


# ── Modelo ────────────────────────────────────────────────────────────────────
# Define qual LLM será utilizado nas requisições.
# Opções disponíveis (do mais leve ao mais capaz):
#   "claude-haiku-4-5"   → Rápido e barato, ótimo para testes e prototipagem
#   "claude-sonnet-4-6"  → Equilíbrio custo/inteligência, uso geral em produção
#   "claude-opus-4-6"    → Máxima capacidade, tarefas complexas de raciocínio

MODEL: str = "claude-haiku-4-5"


# ── Limite de tokens da resposta ──────────────────────────────────────────────
# max_tokens define o teto de tokens que o modelo pode gerar na resposta.
# Parâmetro OBRIGATÓRIO na API da Anthropic.
# Referência rápida de tamanho:
#   ~100 tokens  → resposta curta (2–3 parágrafos)
#   ~500 tokens  → resposta média
#   ~1024 tokens → resposta longa (artigo curto)
#   ~4096 tokens → resposta muito longa (relatório)

MAX_TOKENS: int = 1024


# ── Temperatura ───────────────────────────────────────────────────────────────
# Controla o grau de aleatoriedade/criatividade das respostas.
# Escala: 0.0 (determinístico) → 1.0 (mais criativo/variado)
#
# Guia prático:
#   0.0 – 0.3 → Análises técnicas, código, respostas factuais
#   0.4 – 0.7 → Uso geral, explicações, resumos
#   0.8 – 1.0 → Escrita criativa, brainstorming, geração de ideias

TEMPERATURE: float = 0.3


# ── System Prompt ─────────────────────────────────────────────────────────────
# Instrução de comportamento entregue ao modelo antes de qualquer mensagem
# do usuário. Define a persona, restrições, idioma e estilo de resposta.
#
# Na API da Anthropic, o system prompt é um campo separado — não entra no
# array `messages`. Isso é diferente do OpenAI, onde ele aparece como
# {"role": "system", "content": "..."} dentro do array.

SYSTEM_PROMPT: str = """
Você é um assistente técnico especializado em Data Science e Machine Learning.
Responda de forma direta e estruturada, priorizando clareza para um profissional
de nível pleno que está consolidando conhecimentos em MLOps e integração de APIs.
Use exemplos práticos quando pertinente. Responda em português.
""".strip()
