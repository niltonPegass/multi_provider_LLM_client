"""
================================================================================
📋 GEMINI_CONFIG.PY — Configuração Central da Aplicação
================================================================================

PROPÓSITO:
    Centralizar TODAS as configurações da aplicação em um único arquivo.
    Dessa forma, alterações nos parâmetros não exigem modificação do código
    de negócio em api_client.py ou main.py.

PADRÃO DE DESIGN (Configuração Externa):
    ✓ Vantagem: Fácil ajuste sem recompilar a aplicação
    ✓ Vantagem: Legibilidade — ver todas as configs em um só lugar
    ✗ Desvantagem: Expõe a API Key no código (apenas para didática)

COMO OBTER A API KEY (gratuita, sem cartão de crédito):
    1. Acesse https://aistudio.google.com
    2. Clique em "Get API Key" → "Create API Key"
    3. Cole a chave no campo API_KEY abaixo

[!]  SEGURANÇA — Sobre a API Key:
    Esta versão expõe a chave DIRETAMENTE no código APENAS para fins didáticos.
    
    [!] NUNCA faça isso em produção!
    
    Em produção, use VARIÁVEIS DE AMBIENTE:
        import os
        API_KEY = os.environ.get("GEMINI_API_KEY")
        
        Depois execute com:
        export GEMINI_API_KEY="sua_chave_aqui"
        python gemini_main.py

CONCEITOS-CHAVE:
    • Tokens: Unidade fundamental. 1 token ≈ 4 caracteres.
    • RPM (Requests Per Minute): Limite de requisições por minuto
    • TPM (Tokens Per Minute): Limite de tokens por minuto
    • Free Tier: Plano gratuito com cota reduzida

================================================================================
"""

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                          1️⃣  AUTENTICAÇÃO (API KEY)                        ║
# ╚════════════════════════════════════════════════════════════════════════════╝

API_KEY: str = "SUA_API_KEY_AQUI"
"""
Chave de autenticação que identifica sua aplicação junto ao Google Gemini.

Fluxo de autenticação:
    1. Cliente (sua app) → envia API_KEY em cada requisição
    2. Google Gemini → valida a chave e verifica quotas
    3. Se válida e com cota → processa a requisição
    4. Se inválida → retorna erro 403 (PERMISSION_DENIED)

Obs: genai.Client(api_key=API_KEY) usa esta chave internamente.
"""


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                    2️⃣  MODELO — Qual IA vou usar?                          ║
# ╚════════════════════════════════════════════════════════════════════════════╝

MODEL: str = "models/gemini-2.5-flash-lite"
"""
Define qual versão do modelo Gemini será usado em cada requisição.

📊 COMPARAÇÃO DE MODELOS DISPONÍVEIS:

┌─────────────────────┬──────────┬─────────┬──────────────┐
│ Modelo              │ Tamanho  │ Capaci. │ Free Tier    │
├─────────────────────┼──────────┼─────────┼──────────────┤
│ gemini-1.5-flash    │ Pequeno  │ Média   │ ✅ Generoso  │
│ gemini-1.5-pro      │ Grande   │ Alta    │ ⚠️  Limitado │
│ gemini-2.0-flash    │ Pequeno  │ Alta    │ ⚠️  Limitado │
│ gemini-2.5-flash*   │ Pequeno  │ Alta    │ ✅ Generoso  │
└─────────────────────┴──────────┴─────────┴──────────────┘
* Mais recente (2025)

RECOMENDAÇÕES POR CASO DE USO:
    • Data Science / MLOps → gemini-2.5-flash-lite (padrão, rápido)
    • Análise de documentos / Código → gemini-1.5-pro (mais preciso)
    • Prototipagem rápida → gemini-1.5-flash (cota maior)

COMO ALTERAR:
    1. Mude o valor em MODEL = "models/novo-modelo"
    2. Não precisa mudar api_client.py — já usa MODEL de aqui
    3. Reinicie a aplicação
"""


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║              3️⃣  MAX_TOKENS — Tamanho máximo da resposta                   ║
# ╚════════════════════════════════════════════════════════════════════════════╝

MAX_TOKENS: int = 2048
"""
Define o tamanho MÁXIMO da resposta (em tokens), não o tamanho esperado.

🔍 ENTENDENDO TOKENS:
    1 token ≈ 4 caracteres (valor médio)
    
    Exemplos:
    • "Olá" = 1 token
    • "Explicar embeddings em NLP" = ~8 tokens
    • Um parágrafo = 50-100 tokens
    
RELAÇÃO COM A COTA:
    Total de tokens gastos = tokens_entrada + tokens_saida
    
    Requisição:
    ┌──────────────────────┐
    │ Seu prompt: "Explique ML"    │ = 4 tokens (entrada)
    │ Resposta max: 2048 tokens    │ ≤ 2048 tokens (saída)
    │ ─────────────────────────────│
    │ Total de tokens consumidos ≤ 2052 tokens
    └──────────────────────┘

COMO AJUSTAR:
    • Para respostas curtas → MAX_TOKENS = 512 (economiza cota)
    • Para análises longas → MAX_TOKENS = 4096 (usa mais cota)
    • Padrão balanceado → MAX_TOKENS = 2048 (escolhido)

IMPACTO NA COTA:
    Usar MAX_TOKENS = 4096 não significa gastar 2x mais tokens.
    Gasta apenas se o modelo realmente produzir 4096 tokens.
    Essa é apenas a LIMITE máximo.
"""


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                4️⃣  TEMPERATURE — Criatividade vs Determinismo              ║
# ╚════════════════════════════════════════════════════════════════════════════╝

TEMPERATURE: float = 0.3
"""
Controla o NÍVEL DE ALEATORIEDADE nas respostas do modelo.

[!] ESCALA DE TEMPERATURA NO GEMINI:
    
    0.0 (Determinístico)
    ├─→ Respostas idênticas para mesma entrada
    ├─→ Cada palavra é a "mais provável" apenas
    └─→ Ideal para: consultas técnicas, cálculos, fatos
    
    0.3 - 0.7 (Balanceado) > PADRÃO
    ├─→ Respostas consistentes com variação natural
    ├─→ Bom para maioria dos casos
    └─→ Ideal para: análise, explicações, diálogos
    
    1.0 (Criativo)
    ├─→ Respostas diferentes cada vez
    ├─→ Explora alternativas interessantes
    └─→ Ideal para: brainstorming, poesia, criatividade
    
    2.0 (Muito Criativo)
    ├─→ Máxima aleatoriedade, respostas muito variadas
    ├─→ Pode gerar respostas nonsense
    └─→ Ideal para: caso extremo (geralmente não use)

COMO USAMOS:
    temperature = 0.3  → Resposta técnica determinística
    
    Mesma pergunta 3 vezes:
    • "Explicar embeddings" → sempre resposta similar (~80% igual)
    
AJUSTE FINO:
    • Para dados científicos → 0.0 - 0.2
    • Para help desk / FAQ → 0.3 - 0.5
    • Para conversas normais → 0.7 - 0.9
    • Para criatividade → 1.0 - 1.5

⚙️  IMPLEMENTAÇÃO:
    Passado em criar_config(temperature=TEMPERATURE)
    Depois enviado ao modelo: config=GenerateContentConfig(temperature=...)
"""


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║               5️⃣  SYSTEM_PROMPT — Instrução de Sistema                     ║
# ╚════════════════════════════════════════════════════════════════════════════╝

SYSTEM_PROMPT: str = """
Você é um assistente técnico especializado em Data Science e Machine Learning.
Responda de forma direta e estruturada, priorizando clareza para um profissional
de nível pleno que está consolidando conhecimentos em MLOps e integração de APIs.
Use exemplos práticos quando pertinente. Responda em português.
""".strip()
"""
Instrução de SISTEMA que define a "personalidade" e comportamento do modelo.

PROPÓSITO:
O System Prompt é como a "instrução operacional" que o modelo recebe.
Define como ele deve se comportar para TODAS as requisições.

ARQUITETURA DA CONVERSA:
    
    1. Sistema (System Prompt)
       └→ "Você é um assistente técnico..."
    
    2. Usuário (user)
       └→ "Explique embeddings em NLP"
    
    3. Assistente (model/response)
       └→ Responde CONSIDERANDO o system prompt
    
    ┌──────────────────────────────────────────────┐
    │ A resposta é influenciada pelo contexto do   │
    │ system prompt, mesmo que não seja mencionado │
    │ explicitamente na pergunta do usuário.       │
    └──────────────────────────────────────────────┘

NOSSO SYSTEM PROMPT DEFINE:
    ✓ Especialidade: Data Science e Machine Learning
    ✓ Tom: Direto e estruturado
    ✓ Público-alvo: Profissional sênior (nível pleno)
    ✓ Idioma: Português
    ✓ Estilo: Exemplos práticos quando relevante

EXEMPLO PRÁTICO:
    Mesma pergunta com 2 system prompts diferentes:
    
    Pergunta: "O que é overfitting?"
    
    System Prompt 1: "Você é um professor de IA infantil"
    Resposta: "Imagine que você decorou a prova e não aprendeu nada..."
    
    System Prompt 2: "Você é um professor de MLOps sênior"
    Resposta: "Overfitting ocorre quando... o modelo se adequa ao ruído..."

NO NOVO SDK (google-genai):
    • Passado como: system_instruction em GenerateContentConfig
    • Não é um "primeiro turno" — é configuração do modelo
    • Permanece consistente em toda conversa multi-turno

COMO ALTERAR:
    1. Edite o SYSTEM_PROMPT aqui
    2. Não precisa mudar api_client.py
    3. Próxima requisição usará o novo prompt
"""
