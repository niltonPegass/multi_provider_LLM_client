"""
================================================================================
api_client.py — Módulo de Comunicação com a API da Anthropic
================================================================================
Responsabilidade:
    Encapsular toda a lógica de comunicação com a API da Anthropic.
    Este módulo não sabe nada sobre interface, apresentação ou regras de negócio —
    só sabe fazer requisições e retornar resultados.

    Funções disponíveis:
        criar_cliente()            → Instancia e retorna o cliente autenticado
        chat_simples()             → Chamada única, aguarda resposta completa
        chat_streaming()           → Tokens chegam progressivamente (SSE)
        chat_multi_turno()         → Mantém histórico entre turnos
        chat_com_tratamento_erros() → Wrapper com captura de exceções da API

Conceitos cobertos:
    • Autenticação via API Key passada explicitamente ao cliente
    • Parâmetros principais: model, system, messages, max_tokens, temperature
    • Streaming via Server-Sent Events (SSE)
    • API stateless: histórico deve ser reenviado a cada requisição
    • Tratamento de erros: AuthenticationError, RateLimitError, APIStatusError
================================================================================
"""

import anthropic

# Importa todas as configurações do módulo central
from config import API_KEY, MODEL, MAX_TOKENS, TEMPERATURE, SYSTEM_PROMPT


# ════════════════════════════════════════════════════════════════════════════════
# FÁBRICA DO CLIENTE
# ════════════════════════════════════════════════════════════════════════════════

def criar_cliente() -> anthropic.Anthropic:
    """
    Instancia e retorna o cliente da API Anthropic com autenticação explícita.

    Por que uma função fábrica?
        Centraliza a criação do cliente. Se a forma de autenticar mudar
        (ex: OAuth, variável de ambiente, vault de segredos), a alteração
        ocorre em um único ponto — aqui.

    Autenticação:
        A API Key é passada diretamente ao construtor via `api_key=`.
        O SDK a utiliza no header HTTP: "x-api-key: <API_KEY>"

    Retorno:
        Instância configurada de anthropic.Anthropic.
    """
    return anthropic.Anthropic(api_key=API_KEY)


# ════════════════════════════════════════════════════════════════════════════════
# FUNÇÃO 1 — Chamada Simples (síncrona, resposta completa)
# ════════════════════════════════════════════════════════════════════════════════

def chat_simples(pergunta: str) -> str:
    """
    Envia uma mensagem única e aguarda a resposta completa antes de retornar.

    Fluxo:
        Script → SDK monta POST /v1/messages → Anthropic processa → JSON completo

    Quando usar:
        Scripts batch, pipelines de processamento, casos onde a latência
        de início de resposta não é crítica.

    Parâmetros:
        pergunta : Texto da mensagem do usuário (str).

    Retorno:
        Texto da resposta do modelo (str).

    Estrutura interna da resposta (response):
        response.id              → ID único da requisição (útil para logs/suporte)
        response.content         → Lista de blocos de conteúdo
        response.content[0].text → Texto da resposta (bloco principal)
        response.usage           → Tokens consumidos (input + output)
        response.stop_reason     → Motivo do fim: "end_turn", "max_tokens", etc.
    """
    client = criar_cliente()

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": pergunta}
        ]
    )

    return response.content[0].text


# ════════════════════════════════════════════════════════════════════════════════
# FUNÇÃO 2 — Streaming (tokens progressivos via SSE)
# ════════════════════════════════════════════════════════════════════════════════

def chat_streaming(pergunta: str, callback=None) -> str:
    """
    Envia uma mensagem e recebe os tokens progressivamente (streaming).

    O que é streaming aqui?
        Em vez de aguardar a resposta completa, o servidor envia fragmentos
        de tokens via Server-Sent Events (SSE) conforme o modelo os gera.
        O SDK encapsula os eventos SSE no context manager `client.messages.stream()`.

    Parâmetro `callback`:
        Função opcional chamada a cada fragmento recebido.
        Se não fornecida, os fragmentos são impressos diretamente no stdout.
        Útil para integrar com interfaces web (ex: FastAPI + WebSocket).

        Assinatura esperada: callback(fragmento: str) -> None

    Parâmetros:
        pergunta : Texto da mensagem do usuário (str).
        callback : Função opcional para processar cada fragmento (callable | None).

    Retorno:
        Texto completo acumulado (str).
    """
    client = criar_cliente()

    texto_completo = ""

    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": pergunta}
        ]
    ) as stream:
        for fragmento in stream.text_stream:
            texto_completo += fragmento

            if callback:
                callback(fragmento)          # delega ao caller
            else:
                print(fragmento, end="", flush=True)   # fallback: stdout

    return texto_completo


# ════════════════════════════════════════════════════════════════════════════════
# FUNÇÃO 3 — Conversa Multi-turno (histórico stateless)
# ════════════════════════════════════════════════════════════════════════════════

def chat_multi_turno(historico: list[dict], nova_mensagem: str) -> tuple[str, list[dict]]:
    """
    Gerencia uma conversa com múltiplos turnos reenviando o histórico completo.

    Por que reenviar o histórico a cada chamada?
        A API da Anthropic é STATELESS: cada requisição é independente.
        O servidor não armazena contexto entre chamadas. Para simular memória,
        o cliente deve incluir todos os turnos anteriores no campo `messages`.

    Estrutura obrigatória de `messages`:
        Os papéis devem alternar estritamente: user → assistant → user → ...
        [
            {"role": "user",      "content": "primeira pergunta"},
            {"role": "assistant", "content": "primeira resposta"},
            {"role": "user",      "content": "segunda pergunta"},
            ...
        ]

    Parâmetros:
        historico     : Lista de turnos anteriores. Passe [] para iniciar.
        nova_mensagem : Texto da nova mensagem do usuário.

    Retorno:
        Tupla (resposta_str, historico_atualizado).
        O historico_atualizado já inclui o novo turno do usuário E a resposta
        do assistente, pronto para ser passado na próxima chamada.
    """
    client = criar_cliente()

    # Adiciona a nova mensagem do usuário ao histórico
    historico.append({"role": "user", "content": nova_mensagem})

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=historico         # histórico completo sempre reenviado
    )

    resposta_texto = response.content[0].text

    # Registra a resposta do assistente para o próximo turno
    historico.append({"role": "assistant", "content": resposta_texto})

    return resposta_texto, historico


# ════════════════════════════════════════════════════════════════════════════════
# FUNÇÃO 4 — Wrapper com Tratamento de Erros
# ════════════════════════════════════════════════════════════════════════════════

def chat_com_tratamento_erros(pergunta: str) -> dict:
    """
    Executa chat_simples() com captura estruturada das exceções da API.

    Erros cobertos:
        AuthenticationError  → HTTP 401: API Key inválida ou ausente
        RateLimitError       → HTTP 429: limite de requisições atingido
        APIStatusError       → Outros erros HTTP da API (4xx, 5xx)
        APIConnectionError   → Falha de rede, timeout

    Estratégia de retry para RateLimitError em produção:
        Implemente back-off exponencial (esperar 1s, 2s, 4s, ...) antes de
        retentar. Bibliotecas como `tenacity` facilitam isso.

    Retorno:
        dict com campos:
            "sucesso"   : bool
            "resposta"  : str (texto do modelo ou mensagem de erro)
            "erro_tipo" : str | None (nome da exceção, se ocorreu)
    """
    try:
        texto = chat_simples(pergunta)
        return {
            "sucesso": True,
            "resposta": texto,
            "erro_tipo": None
        }

    except anthropic.AuthenticationError:
        return {
            "sucesso": False,
            "resposta": "❌ Erro de autenticação: verifique sua API_KEY em config.py.",
            "erro_tipo": "AuthenticationError"
        }

    except anthropic.RateLimitError:
        return {
            "sucesso": False,
            "resposta": "⏳ Rate limit atingido. Aguarde alguns segundos e tente novamente.",
            "erro_tipo": "RateLimitError"
        }

    except anthropic.APIStatusError as e:
        return {
            "sucesso": False,
            "resposta": f"❌ Erro da API (HTTP {e.status_code}): {e.message}",
            "erro_tipo": "APIStatusError"
        }

    except anthropic.APIConnectionError:
        return {
            "sucesso": False,
            "resposta": "❌ Erro de conexão. Verifique sua internet.",
            "erro_tipo": "APIConnectionError"
        }
