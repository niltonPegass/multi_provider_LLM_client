"""
================================================================================
📡 GEMINI_API_CLIENT.PY — Cliente de Comunicação com a API Gemini
================================================================================

🎯 PROPÓSITO:
    Encapsular TODA a lógica de comunicação com a API do Google Gemini.
    Este módulo não sabe sobre interface ou apresentação — apenas faz requisições
    e retorna resultados estruturados.

🏗️  PADRÃO DE DESIGN (Encapsulação):
    ✓ api_client.py contém APENAS lógica de API
    ✓ gemini_config.py contém APENAS configurações
    ✓ gemini_main.py contém APENAS UI/orquestração
    
    Separação de responsabilidades → fácil de testar, manter e reutilizar

📦 SDK UTILIZADO:
    Nome: google-genai (versão NOVA, 2024+)
    Instalação: pip install google-genai
    Documentação: https://github.com/googleapis/python-genai

⚠️  NOTA HISTÓRICA — Migração de SDK:
    
    ❌ ANTIGO (descontinuado):
        • Pacote: google.generativeai
        • Já não recebe atualizações
        • Sintaxe: genai.configure(api_key=...) → genai.GenerativeModel()
    
    ✅ NOVO (recomendado):
        • Pacote: google-genai (este projeto)
        • Totalmente reestruturado
        • Sintaxe: genai.Client(api_key=...) → client.models.generate_content()
        • Melhor tratamento de erros integrado

🗂️  ESTRUTURA DESTE MÓDULO:

    NÍVEL 1 — Fábrica (Factory Pattern)
    ├── criar_cliente()        → Instancia genai.Client autenticado
    └── criar_config()         → Monta GenerateContentConfig reutilizável
    
    NÍVEL 2 — Operações Básicas (Stateless)
    ├── chat_simples()         → 1 mensagem, resposta completa
    ├── chat_streaming()       → 1 mensagem, resposta em chunks
    └── chat_multi_turno()     → Múltiplas mensagens com histórico
    
    NÍVEL 3 — Wrappers com Tratamento de Erros
    ├── chat_com_tratamento_erros()
    ├── chat_streaming_com_tratamento_erros()
    └── chat_multi_turno_com_tratamento_erros()

🔐 TRATAMENTO DE ERROS INTEGRADO:
    
    Hierarquia de Exceções do google-genai:
    
        APIError (classe base)
        ├── ClientError (erros 4xx — problema do cliente)
        │   ├── 400 — Argumento inválido (ex: modelo inexistente)
        │   ├── 403 — Autenticação falhou (API Key inválida)
        │   └── 429 — Rate limit / cota atingida
        │
        └── ServerError (erros 5xx — problema do servidor Google)
            └── 503 — Serviço indisponível (temporário)

================================================================================
"""

from google import genai
from google.genai import types
from google.genai import errors as gemini_errors

from gemini_config import API_KEY, MODEL, MAX_TOKENS, TEMPERATURE, SYSTEM_PROMPT


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  CAMADA 1 — FÁBRICA DE OBJETOS                                             ║
# ║  (Instanciam cliente e configuração — padrão Factory)                       ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def criar_cliente() -> genai.Client:
    """
    🏭 FÁBRICA: Instancia e retorna o cliente autenticado.
    
    ◆ O QUE ELA FAZ:
        1. Recebe API_KEY de gemini_config.py
        2. Cria uma instância de genai.Client (autenticada)
        3. Retorna esse cliente para usar nas requisições
    
    ◆ DIFERENÇA DO SDK ANTIGO → NOVO:
        
        ❌ ANTES (google.generativeai — descontinuado):
            genai.configure(api_key=API_KEY)  # configuração GLOBAL
            model = genai.GenerativeModel(model_name="gemini-1.5-pro")
        
        ✅ AGORA (google-genai — novo):
            client = genai.Client(api_key=API_KEY)  # objeto EXPLÍCITO
            response = client.models.generate_content(...)
    
    ◆ POR QUE USAR FACTORY?
        • Separação de responsabilidades
        • Testável: pode mockar criar_cliente() em testes
        • Reutilizável: múltiplas funções precisam do cliente
        • Manutenível: mudança de autenticação só afeta 1 função
    
    ◆ FLUXO:
        criar_cliente() ──→ genai.Client(api_key) ──→ Objeto autenticado
                              ↓
                          Internamente:
                          • Valida a API Key
                          • Configura endpoints
                          • Prepara headers HTTP
    
    RETORNO:
        genai.Client: Instância autenticada e pronta para requisições.
    
    ERROS POSSÍVEIS:
        (Não lança aqui — erros virão em generate_content())
    
    EXEMPLO DE USO:
        client = criar_cliente()
        response = client.models.generate_content(model=MODEL, contents="...")
    """
    # Instancia o cliente do Google Gemini com a API Key
    # Isso cria um objeto que mantém a autenticação e pode fazer múltiplas requisições
    # Alternativas: Se você tivesse múltiplas contas, criaria múltiplos clientes com keys diferentes
    return genai.Client(api_key=API_KEY)


def criar_config(**kwargs) -> types.GenerateContentConfig:
    """
    ⚙️  FÁBRICA: Monta e retorna a configuração de geração reutilizável.
    
    ◆ O QUE ELA FAZ:
        1. Recebe parâmetros de gemini_config.py (defaults)
        2. Permite sobrescrever com kwargs (para ajuste fino)
        3. Retorna um objeto GenerateContentConfig pronto
    
    ◆ POR QUE SEPARAR EM FUNÇÃO?
        • Configuração em um só lugar (fácil de encontrar)
        • Reutilizável em múltiplas requisições
        • Permite ajustes dinâmicos sem duplicar código
        • Legibilidade: deixa claro quais parâmetros estão sendo usados
    
    ◆ DIFERENÇA DO SDK ANTIGO → NOVO:
        
        ❌ ANTES (google.generativeai):
            model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2048,
                )
            )
        
        ✅ AGORA (google-genai):
            config = GenerateContentConfig(
                system_instruction="...",
                temperature=0.7,
                max_output_tokens=2048,
            )
            client.models.generate_content(model=MODEL, contents=..., config=config)
    
    ◆ PARÂMETROS:
        **kwargs: Dicionário de parâmetros opcionais que sobrescrevem defaults.
        
        Aceita:
        • temperature=0.5        → Sobrescreve TEMPERATURE de config.py
        • max_output_tokens=1024 → Sobrescreve MAX_TOKENS
        • Qualquer outro parâmetro de GenerateContentConfig
    
    ◆ FLUXO COM KWARGS:
        
        # Uso normal (usa defaults):
        config = criar_config()
        # Resultado: temperature=0.3 (de TEMPERATURE)
        
        # Uso com override (ajuste fino):
        config = criar_config(temperature=0.9)
        # Resultado: temperature=0.9 (sobrescreve TEMPERATURE)
    
    ◆ PADRÃO KWARGS:
        Este padrão permite FLEXIBILIDADE sem quebrar compatibilidade:
        • Chamada simples: criar_config()
        • Chamada com ajuste: criar_config(temperature=0.9)
        • Múltiplos ajustes: criar_config(temperature=0.9, max_output_tokens=512)
    
    RETORNO:
        types.GenerateContentConfig: Configuração montada e pronta.
    
    EXEMPLO DE USO:
        # Config padrão:
        config1 = criar_config()
        
        # Config criativa para brainstorming:
        config2 = criar_config(temperature=1.5)
        
        # Config econômica para tarefas repetitivas:
        config3 = criar_config(temperature=0.0, max_output_tokens=256)
    """
    # Monta a configuração de geração usando GenerateContentConfig
    # Isso encapsula TODOS os parâmetros que controlam como o modelo gera respostas
    # 
    # system_instruction: Define o "papel" ou comportamento do modelo para TODA a conversa
    #   • Todas as respostas serão influenciadas por isso
    #   • Não é um histórico — é uma diretriz permanente
    #   • Caso de uso: "Você é um professor", "Responda em português", etc.
    # 
    # temperature: Controla a criatividade/aleatoriedade
    #   • 0.0 = sempre a resposta mais provável (determinístico)
    #   • 1.0 = balanceado (padrão)
    #   • 2.0 = muito criativo (potencialmente absurdo)
    #   • Padrão técnico: 0.0-0.5 para respostas determinísticas
    # 
    # max_output_tokens: Limita o tamanho MÁXIMO da resposta
    #   • Não força a resposta ter esse tamanho
    #   • Apenas garante que não vai ultrapassar
    #   • Tokens são contados na cota da API
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        # Usa kwargs para permitir override, com fallback aos defaults de config.py
        # Padrão: kwargs.get("chave", valor_padrao)
        temperature=kwargs.get("temperature", TEMPERATURE),
        max_output_tokens=kwargs.get("max_output_tokens", MAX_TOKENS),
    )


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  CAMADA 2 — OPERAÇÕES BÁSICAS (STATELESS)                                  ║
# ║  (Três formas de conversar com a API)                                       ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def chat_simples(pergunta: str) -> str:
    """
    💬 OPERAÇÃO 1 — Chat Simples: Uma mensagem, resposta completa.
    
    ◆ QUANDO USAR:
        • Perguntas isoladas (sem contexto anterior)
        • Exemplos: "Qual é a capital da França?", "Explique embeddings"
        • Não é uma conversa — é uma pergunta única
    
    ◆ FLUXO TÉCNICO:
        
        Cliente → Requisição HTTP
                    ├── Model: "gemini-2.5-flash-lite"
                    ├── Contents: "sua pergunta"
                    ├── Config: (temperature=0.3, max_tokens=2048, ...)
                    └── Headers: API Key
                    
                  ↓ (Google Gemini processa)
                  
        Resposta HTTP ← Response
                    ├── candidates[0].content.parts[0].text ← RESPOSTA
                    ├── usage_metadata ← tokens gastos
                    └── finish_reason ← por que parou (STOP, LENGTH, etc)
    
    ◆ ESTRUTURA INTERNA DA RESPOSTA (response object):
        
        response.text  ← ATALHO para a resposta (o que queremos)
        
        response.candidates[0]  ← Lista de gerações alternativas
                    └── .content  ← Conteúdo da resposta
                        └── .parts[0]  ← Partes (pode ter múltiplas)
                            └── .text  ← Texto da parte
        
        response.usage_metadata  ← Contadores de tokens
                    ├── .prompt_token_count ← Tokens da pergunta
                    ├── .candidates_token_count ← Tokens da resposta
                    └── .total_token_count ← Total (entrada + saída)
    
    ◆ EQUIVALÊNCIA COM OUTROS SDKS:
        
        OpenAI:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "..."}]
            )
        
        Anthropic:
            response = client.messages.create(
                model="claude-3-sonnet",
                messages=[{"role": "user", "content": "..."}]
            )
        
        Gemini (novo):
            response = client.models.generate_content(
                model=MODEL,
                contents=pergunta,
                config=config
            )
    
    ◆ PARÂMETRO:
        pergunta (str): A pergunta do usuário.
            Exemplo: "Explique o que é machine learning"
    
    ◆ RETORNO:
        str: Apenas o texto da resposta.
            Exemplo: "Machine learning é uma subárea da IA que..."
    
    ⚠️  IMPORTANTE:
        Esta função NÃO trata erros. Se falhar, lança exceção.
        Use chat_com_tratamento_erros() se quiser captura de erros.
    
    EXEMPLO DE USO:
        try:
            resposta = chat_simples("O que é embeddings?")
            print(resposta)
        except Exception as e:
            print(f"Erro: {e}")
    """
    # Cria o cliente autenticado para esta requisição
    # Nota: Criamos um novo cliente cada vez. Em produção, você poderia reutilizar
    # o mesmo cliente para múltiplas requisições (mais eficiente em recursos)
    client = criar_cliente()
    
    # Monta a configuração com parâmetros padrão
    # Se precisar de temperatura diferente apenas para esta pergunta:
    #   config = criar_config(temperature=0.9)  ← override
    config = criar_config()

    # CHAMADA PRINCIPAL DA API
    # client.models.generate_content() é a função que faz a requisição HTTP real
    # 
    # Parâmetros:
    #   model=MODEL              → Qual modelo usar (ex: "models/gemini-2.5-flash-lite")
    #   contents=pergunta        → A pergunta (pode ser string ou lista de tipos.Part)
    #   config=config            → Configuração (temperature, max_tokens, system_instruction)
    # 
    # O que acontece internamente:
    #   1. Monta um payload JSON com: model, contents, config
    #   2. Adiciona headers: Authorization, Content-Type, Accept-Encoding
    #   3. Faz POST para: https://generativelanguage.googleapis.com/v1beta/models/...
    #   4. Aguarda resposta (pode levar 1-30 segundos)
    #   5. Retorna objeto response com candidates e metadata
    # 
    # Alternativas:
    #   - client.models.generate_content_stream() para streaming
    #   - Passar contents como lista de tipos.Part para multimodal (texto + imagem)
    response = client.models.generate_content(
        model=MODEL,
        contents=pergunta,
        config=config,
    )

    # Extrai apenas o texto da resposta
    # response.text é um atalho para response.candidates[0].content.parts[0].text
    # 
    # Alternativas para acessar a resposta completa:
    #   - response.candidates[0].content.parts[0].text  (caminho longo)
    #   - response.candidates[0].finish_reason  (por que parou? STOP, LENGTH, SAFETY)
    #   - response.usage_metadata.prompt_token_count  (tokens da entrada)
    #   - response.usage_metadata.candidates_token_count  (tokens da saída)
    # 
    # Debug: Se quiser ver tudo:
    #   print(response)  # mostra toda a estrutura
    #   print(vars(response))  # atributos do objeto
    return response.text


def chat_streaming(pergunta: str, callback=None) -> str:
    """
    🌊 OPERAÇÃO 2 — Streaming: Receber resposta em chunks (progressiva).
    
    ◆ QUANDO USAR:
        • Respostas longas (para não deixar o usuário esperando)
        • Interfaces em tempo real (chatbot, assistente)
        • Melhor experiência UX (progressão visual)
    
    ◆ QUANDO NÃO USAR:
        • Respostas curtas (overhead de streaming não compensa)
        • Processamento automático sem visualização
    
    ◆ DIFERENÇA: Simples vs Streaming:
        
        SIMPLES:
        Pergunta ──────────→ [Processamento...] ──────────→ Resposta completa
        ├─ Espera todo o processamento
        └─ Ideal para respostas curtas
        
        STREAMING:
        Pergunta ──→ [Processo...] → Chunk 1 → Chunk 2 → Chunk 3 → Fim
        ├─ Vê progressão em tempo real
        └─ Ideal para respostas longas
    
    ◆ COMO FUNCIONA:
        
        HTTP Connection (mantida aberta)
        ├─ Chunk 1: "Machine"
        ├─ Chunk 2: " learning"
        ├─ Chunk 3: " é"
        ├─ ...
        └─ [FIM]
    
    ◆ PARÂMETROS:
        pergunta (str): A pergunta do usuário.
        callback (callable, opcional): Função chamada a cada chunk.
            
            Assinatura esperada: callback(fragmento: str) -> None
            
            Exemplos:
            • lambda x: print(x, end="", flush=True)  ← imprime progressivamente
            • lambda x: widgets.append(x)  ← acumula em widget
            • lambda x: socketio.emit("chunk", x)  ← envia por WebSocket
    
    ◆ FLUXO:
        
        for chunk in client.models.generate_content_stream(...):
            fragmento = chunk.text  ← Texto do chunk (pode ser vazio)
            texto_completo += fragmento  ← Acumula
            
            if callback:
                callback(fragmento)  ← Chama função do usuário (ex: imprime)
            else:
                print(fragmento, end="", flush=True)  ← Comportamento padrão
    
    ◆ RETORNO:
        str: Texto completo acumulado (igual ao chat_simples).
            Diferença: é ACUMULADO ao longo do tempo (progressivo)
    
    ⚠️  IMPORTANTE:
        • flush=True garante que print mostra imediatamente
        • chunk.text pode ser vazio — sempre verificar
        • Esta função NÃO trata erros (use wrapper)
    
    EXEMPLO DE USO:
        # Imprime progressivamente no console:
        resposta = chat_streaming("Explique deep learning")
        # Saída: "Deep" → " learning" → " é" → ...
        
        # Com callback customizado:
        def meu_callback(chunk):
            print(f"[CHUNK] {len(chunk)} caracteres recebidos")
        
        resposta = chat_streaming("...", callback=meu_callback)
    """
    client = criar_cliente()
    config = criar_config()

    # Inicializa string vazia para acumular os chunks
    # Alternativa: usar io.StringIO() para melhor performance com muitos chunks
    texto_completo = ""

    # STREAMING: Em vez de esperar a resposta completa, recebemos fragmentos progressivamente
    # generate_content_stream() retorna um iterador (generator)
    # 
    # Como funciona internamente:
    #   1. Abre conexão HTTP com keep-alive (Server-Sent Events ou chunked transfer)
    #   2. Começa a enviar tokens conforme são gerados no servidor
    #   3. Cada chunk é um objeto com atributo .text
    #   4. Continua até o servidor enviar [FIM] ou timeout
    # 
    # Performance vs chat_simples():
    #   - chat_simples: Mais rápido para respostas curtas (sem overhead)
    #   - chat_streaming: Melhor para respostas longas (feedback visual)
    # 
    # Casos de uso do streaming:
    #   - Interfaces web em tempo real (WebSocket)
    #   - Chatbots (mostrar resposta conforme digita)
    #   - Processamento progressivo (não precisa guardar tudo em memória)
    for chunk in client.models.generate_content_stream(
        model=MODEL,
        contents=pergunta,
        config=config,
    ):
        # Extrai texto do chunk (pode estar vazio em alguns chunks)
        # chunk pode ter outros atributos como finish_reason, index, etc.
        fragmento = chunk.text
        
        # Acumula o fragmento no texto completo
        # Nota: Isso não é necessário para streaming, mas retornamos no final
        texto_completo += fragmento

        # Se callback foi fornecido, chama a função do usuário
        # Caso de uso: enviar chunk para WebSocket, UI, arquivo, etc.
        # Exemplo de callback útil:
        #   def salvar_em_arquivo(chunk):
        #       with open("saida.txt", "a") as f:
        #           f.write(chunk)
        if callback:
            callback(fragmento)
        else:
            # Comportamento padrão: imprime progressivamente no console
            # end="" garante que não quebra linha a cada chunk
            # flush=True força impressão imediata (não aguarda buffer)
            print(fragmento, end="", flush=True)

    # Retorna o texto acumulado (mesma coisa que chat_simples)
    # Uso posterior: salvar em BD, processar, etc.
    return texto_completo


def chat_multi_turno(historico: list, nova_mensagem: str) -> tuple[str, list]:
    """
    🔄 OPERAÇÃO 3 — Multi-turno: Conversa com contexto / histórico.
    
    ◆ QUANDO USAR:
        • Conversas longas (mantém contexto entre turnos)
        • Referências a mensagens anteriores ("o que dissemos antes?")
        • Refinamento iterativo ("explique melhor", "mais detalhes")
    
    ◆ QUANDO NÃO USAR:
        • Perguntas isoladas (use chat_simples)
        • Queries rápidas (overhead de histórico)
    
    ◆ PADRÃO STATELESS (API Google é assim):
        
        ❌ ERRADO — Esperar manutenção automática de estado:
        msg1 = session.send_message("Olá")  ← Cliente guarda contexto
        msg2 = session.send_message("Tudo bem?")  ← Session lembra msg1
        
        ✅ CORRETO — Reenviar histórico completo cada vez:
        historico = [msg1]
        msg2 = api(historico + [nova_msg])  ← Reenviamos tudo
        historico = [msg1, msg2]
        msg3 = api(historico + [nova_msg])  ← Reenviamos tudo novamente
    
    ◆ ESTRUTURA DO HISTÓRICO (types.Content):
        
        Cada turno é um objeto types.Content:
        
            types.Content(
                role="user",                           # Quem enviou
                parts=[types.Part(text="mensagem")]   # Conteúdo
            )
        
        ROLES DIFERENTES NO GEMINI:
        • "user" ← Mensagem do usuário
        • "model" ← Resposta do Gemini (vs "assistant" em OpenAI)
        
        Histórico é uma LISTA desses objetos:
        historico = [
            types.Content(role="user", parts=[...]),
            types.Content(role="model", parts=[...]),
            types.Content(role="user", parts=[...]),
            ...
        ]
    
    ◆ FLUXO STEP-BY-STEP:
        
        # Turno 1:
        historico = []
        nova_msg = "Explique o que é RL"
        historico.append(Content(role="user", text=nova_msg))
        response = api.generate_content(contents=historico)
        historico.append(Content(role="model", text=response))
        # historico agora tem 2 elementos
        
        # Turno 2:
        nova_msg = "Como aplicar em robótica?"
        historico.append(Content(role="user", text=nova_msg))
        response = api.generate_content(contents=historico)  ← reenvia tudo!
        historico.append(Content(role="model", text=response))
        # historico agora tem 4 elementos
    
    ◆ IMPLICAÇÕES DE PERFORMANCE:
        
        Vantagem:
        • Modelo sempre tem contexto completo
        • Mais preciso em referências
        
        Desvantagem:
        • Cada requisição fica maior (quanto mais histórico, maior)
        • Tokens aumentam (todo histórico é contado)
        • Para conversas muuuito longas, considere resumos
    
    ◆ PARÂMETROS:
        historico (list): Lista de types.Content anteriores.
            • Passe [] para iniciar uma nova conversa
            • Será MODIFICADA (append) — cuidado se reutilizar
        
        nova_mensagem (str): Texto da nova pergunta do usuário.
    
    ◆ RETORNO:
        tuple[str, list]: Tupla com 2 elementos:
            1. str: Texto da resposta do modelo
            2. list: Histórico ATUALIZADO (com a nova mensagem e resposta)
    
    ⚠️  IMPORTANTE:
        • historico é uma lista MUTÁVEL — será modificada
        • Sempre atualizar: resposta, historico = chat_multi_turno(...)
        • Esta função NÃO trata erros (use wrapper)
    
    EXEMPLO DE USO:
        historico = []
        
        # Turno 1:
        resposta, historico = chat_multi_turno(historico, "O que é ML?")
        print(f"Bot: {resposta}")
        
        # Turno 2:
        resposta, historico = chat_multi_turno(historico, "Como usar em produção?")
        print(f"Bot: {resposta}")
        
        # Turno 3:
        resposta, historico = chat_multi_turno(historico, "Mais exemplos")
        print(f"Bot: {resposta}")
        
        print(f"Total de mensagens no histórico: {len(historico)}")  # = 6
    """
    client = criar_cliente()
    config = criar_config()

    # CONSTRUINDO O HISTÓRICO
    # Antes de enviar a nova mensagem, precisamos adicionar a mensagem do usuário ao histórico
    # Isso garante que TODA a conversa anterior + nova mensagem será enviada à API
    # 
    # tipos.Content é a estrutura que o Gemini usa para representar mensagens
    # Estrutura:
    #   types.Content(
    #       role="user" ou "model",        # Quem enviou
    #       parts=[types.Part(text="...")]  # Conteúdo (pode ter múltiplas parts)
    #   )
    # 
    # Exemplo de histórico após 2 turnos:
    #   [
    #       Content(role="user", parts=[Part(text="O que é ML?")]),
    #       Content(role="model", parts=[Part(text="ML é...")]),
    #       Content(role="user", parts=[Part(text="Exemplos?")])
    #   ]
    # 
    # Nota: "model" é o papel do Gemini (não "assistant" como em OpenAI)
    historico.append(
        types.Content(role="user", parts=[types.Part(text=nova_mensagem)])
    )

    # ENVIANDO O HISTÓRICO COMPLETO À API
    # A API recebe TUDO o que foi conversado até agora + a nova mensagem
    # Isso é STATELESS — o servidor não guarda contexto, nós reenviamos tudo
    # 
    # Implicações:
    #   - Vantagem: Nenhuma state no servidor, mais seguro, fácil de replicar
    #   - Desvantagem: Cada requisição cresce (tokens aumentam)
    #   - Limite: Conversas muito longas podem exceder max_tokens ou limite de entrada
    # 
    # Para conversas muito longas (>50 turnos), considere:
    #   - Resumir histórico antigo ("Resumidamente: conversamos sobre ...")
    #   - Usar sliding window (manter apenas últimos N turnos)
    #   - Mover para BD com embedding search
    response = client.models.generate_content(
        model=MODEL,
        contents=historico,  # ← Enviamos TODA a conversa
        config=config,
    )

    # Extrai a resposta do modelo
    resposta_texto = response.text

    # ATUALIZAR HISTÓRICO COM A RESPOSTA
    # Adicionamos a resposta do modelo ao histórico para o próximo turno
    # No próximo turno, reenviremos isto + nova mensagem
    historico.append(
        types.Content(role="model", parts=[types.Part(text=resposta_texto)])
    )

    # RETORNA TUPLA (resposta, histórico_atualizado)
    # A função MODIFICA a lista histórico que você passou
    # Também retorna a mesma lista atualizada (redundante mas explícito)
    # 
    # Padrão em Python:
    #   resposta, historico = chat_multi_turno(historico, pergunta)
    # 
    # Cuidado: Se usar a mesma lista com múltiplas conversas, elas se misturarão
    #   historico = [...]  # Conversa 1
    #   resposta, historico = chat_multi_turno(historico, "...")  # Mistura!
    #   resposta, historico = chat_multi_turno(historico, "...")  # Continua a mesma
    # 
    # Solução: Criar novo histórico para cada conversa
    #   historico1 = []
    #   historico2 = []
    return resposta_texto, historico


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  CAMADA 3 — WRAPPERS COM TRATAMENTO DE ERROS                               ║
# ║  (Adicionam captura de exceções às operações básicas)                       ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def chat_com_tratamento_erros(pergunta: str) -> dict:
    """
    🛡️  WRAPPER 1 — chat_simples() com tratamento de erros.
    
    ◆ O QUE FAZ:
        Chama chat_simples() internamente, mas CAPTURA exceções
        e as converte em dicts estruturados (em vez de lançar).
    
    ◆ HIERARQUIA DE ERROS DO GEMINI (google.genai.errors):
        
        APIError (base)
        ├── ClientError (4xx — erro do CLIENTE)
        │   ├── 400: Argumento inválido
        │   │   └─ Ex: modelo não existe, parâmetro ilegal
        │   ├── 403: Autenticação falhou
        │   │   └─ Ex: API Key inválida, sem permissão
        │   └── 429: Rate limit / cota atingida
        │       └─ Ex: pediu demais em pouco tempo
        │
        └── ServerError (5xx — erro do SERVIDOR Google)
            ├── 500: Erro interno (raro)
            ├── 502: Bad Gateway (raro)
            ├── 503: Serviço indisponível (temporário)
            │   └─ Ex: manutenção, overload
            └── 504: Gateway timeout (raro)
    
    ◆ MAPA DE TRATAMENTO:
        
        ClientError 403:
        └─ "❌ Erro de autenticação: verifique sua API_KEY"
        
        ClientError 429:
        └─ "⏳ Cota ou rate limit atingido. Aguarde alguns segundos..."
        
        ClientError (outras):
        └─ "❌ Erro na requisição (4xx): {detalhes}"
        
        ServerError 503:
        └─ "⏳ Serviço temporariamente indisponível. Aguarde..."
        
        ServerError (outras):
        └─ "❌ Erro no servidor Google (5xx): {detalhes}"
        
        Exception (desconhecida):
        └─ "❌ Erro inesperado: {detalhes}"
    
    ◆ RETORNO:
        dict com 3 campos:
        {
            "sucesso": bool,       # True se OK, False se erro
            "resposta": str,       # Texto ou mensagem de erro
            "erro_tipo": str|None  # Tipo de erro ou None se sucesso
        }
    
    ◆ EXEMPLO DE USO:
        resultado = chat_com_tratamento_erros("Explique ML")
        
        if resultado["sucesso"]:
            print(f"✅ {resultado['resposta']}")
        else:
            print(f"❌ [{resultado['erro_tipo']}]: {resultado['resposta']}")
    
    ⚠️  NOTA:
        Esta função SEMPRE retorna um dict (nunca lança exceção).
        Você decide o que fazer com o resultado.
    """
    try:
        # Tenta fazer a requisição normal (sem tratamento de erros)
        # Se der certo, retorna sucesso
        texto = chat_simples(pergunta)
        return {"sucesso": True, "resposta": texto, "erro_tipo": None}

    # CAMADA 1 — Captura erros do CLIENTE (4xx)
    # ClientError pode ser:
    #   - 400 INVALID_ARGUMENT: Parâmetro inválido ou modelo não existe
    #   - 403 PERMISSION_DENIED: API Key inválida, token expirou, sem permissão
    #   - 429 RESOURCE_EXHAUSTED: Cota diária atingida ou rate limit
    except gemini_errors.ClientError as e:
        # Converte a exceção para string para inspecionar o código de erro
        codigo = str(e)

        # Verifica se é erro de autenticação (403)
        # Pode aparecer como "403" ou "PERMISSION_DENIED" na mensagem
        if "403" in codigo or "PERMISSION_DENIED" in codigo:
            return {
                "sucesso": False,
                "resposta": "❌ Erro de autenticação: verifique sua API_KEY em config.py.",
                "erro_tipo": "ClientError_403"
            }
        # Verifica se é erro de rate limit / cota (429)
        # Pode aparecer como "429" ou "RESOURCE_EXHAUSTED" na mensagem
        elif "429" in codigo or "RESOURCE_EXHAUSTED" in codigo:
            return {
                "sucesso": False,
                "resposta": (
                    "⏳ Cota ou rate limit atingido.\n"
                    "   → Aguarde alguns segundos e tente novamente.\n"
                    "   → Se persistir, verifique os limites em https://ai.dev/rate-limit"
                ),
                "erro_tipo": "ClientError_429"
            }
        # Qualquer outro erro 4xx (400, etc)
        else:
            return {
                "sucesso": False,
                "resposta": f"❌ Erro na requisição (4xx): {str(e)}",
                "erro_tipo": "ClientError"
            }

    # CAMADA 2 — Captura erros do SERVIDOR (5xx)
    # ServerError pode ser:
    #   - 500 INTERNAL: Erro interno do servidor Google (raro)
    #   - 502 BAD_GATEWAY: Problema de gateway (raro)
    #   - 503 SERVICE_UNAVAILABLE: Serviço em manutenção ou overload (temporário)
    #   - 504 DEADLINE_EXCEEDED: Timeout (raro)
    except gemini_errors.ServerError as e:
        codigo = str(e)
        # Verifica se é erro 503 (indisponibilidade)
        # Este é o erro mais comum e geralmente é temporário
        if "503" in codigo or "UNAVAILABLE" in codigo:
            return {
                "sucesso": False,
                "resposta": (
                    "⏳ Serviço temporariamente indisponível (503).\n"
                    "   → Aguarde alguns segundos e tente novamente.\n"
                    "   → Se persistir, verifique o status do serviço em https://status.cloud.google.com"
                ),
                "erro_tipo": "ServerError_503"
            }
        # Qualquer outro erro 5xx
        return {
            "sucesso": False,
            "resposta": f"❌ Erro no servidor Google (5xx): {str(e)}",
            "erro_tipo": "ServerError"
        }

    # CAMADA 3 — Captura QUALQUER exceção inesperada
    # Pode ser: timeout de rede, erro de biblioteca, erro de configuração, etc.
    except Exception as e:
        return {
            "sucesso": False,
            "resposta": f"❌ Erro inesperado: {str(e)}",
            "erro_tipo": "UnexpectedError"
        }


def chat_streaming_com_tratamento_erros(pergunta: str, callback=None) -> dict:
    """
    🛡️  WRAPPER 2 — chat_streaming() com tratamento de erros.
    
    ◆ O QUE FAZ:
        Igual a chat_com_tratamento_erros(), mas para streaming.
        Captura exceções durante processamento de chunks.
    
    ◆ PARÂMETROS:
        pergunta (str): A pergunta do usuário.
        callback (callable, opcional): Função de callback.
    
    ◆ RETORNO:
        dict com: "sucesso", "resposta", "erro_tipo"
        (Mesmo formato de chat_com_tratamento_erros)
    
    ◆ EXEMPLO DE USO:
        resultado = chat_streaming_com_tratamento_erros(
            "Explique deep learning",
            callback=lambda x: print(x, end="", flush=True)
        )
        
        if not resultado["sucesso"]:
            print(f"\n❌ Erro: {resultado['resposta']}")
    """
    try:
        # Tenta fazer streaming
        # O erro pode ocorrer:
        #   - Antes do streaming (validação da API Key)
        #   - Durante o streaming (desconexão, timeout)
        # Em ambos os casos, capturamos aqui
        texto = chat_streaming(pergunta, callback)
        return {"sucesso": True, "resposta": texto, "erro_tipo": None}

    except gemini_errors.ClientError as e:
        codigo = str(e)

        if "403" in codigo or "PERMISSION_DENIED" in codigo:
            return {
                "sucesso": False,
                "resposta": "❌ Erro de autenticação: verifique sua API_KEY em config.py.",
                "erro_tipo": "ClientError_403"
            }
        elif "429" in codigo or "RESOURCE_EXHAUSTED" in codigo:
            return {
                "sucesso": False,
                "resposta": (
                    "⏳ Cota ou rate limit atingido.\n"
                    "   → Aguarde alguns segundos e tente novamente.\n"
                    "   → Se persistir, verifique os limites em https://ai.dev/rate-limit"
                ),
                "erro_tipo": "ClientError_429"
            }
        else:
            return {
                "sucesso": False,
                "resposta": f"❌ Erro na requisição (4xx): {str(e)}",
                "erro_tipo": "ClientError"
            }

    except gemini_errors.ServerError as e:
        codigo = str(e)
        if "503" in codigo or "UNAVAILABLE" in codigo:
            return {
                "sucesso": False,
                "resposta": (
                    "⏳ Serviço temporariamente indisponível (503).\n"
                    "   → Aguarde alguns segundos e tente novamente.\n"
                    "   → Se persistir, verifique o status do serviço em https://status.cloud.google.com"
                ),
                "erro_tipo": "ServerError_503"
            }
        return {
            "sucesso": False,
            "resposta": f"❌ Erro no servidor Google (5xx): {str(e)}",
            "erro_tipo": "ServerError"
        }

    except Exception as e:
        return {
            "sucesso": False,
            "resposta": f"❌ Erro inesperado: {str(e)}",
            "erro_tipo": "UnexpectedError"
        }


def chat_multi_turno_com_tratamento_erros(historico: list, nova_mensagem: str) -> dict:
    """
    🛡️  WRAPPER 3 — chat_multi_turno() com tratamento de erros.
    
    ◆ O QUE FAZ:
        Igual aos anteriores, mas para conversas multi-turno.
        Preserva o histórico mesmo em caso de erro.
    
    ◆ PARÂMETROS:
        historico (list): Lista de types.Content anteriores.
        nova_mensagem (str): Texto da nova pergunta.
    
    ◆ RETORNO:
        dict com: "sucesso", "resposta", "historico", "erro_tipo"
        
        Se sucesso:
        {
            "sucesso": True,
            "resposta": "Texto da resposta",
            "historico": [...],  ← Histórico ATUALIZADO
            "erro_tipo": None
        }
        
        Se erro:
        {
            "sucesso": False,
            "resposta": "Mensagem de erro",
            "historico": [...],  ← Histórico ORIGINAL (não foi adicionada a resposta)
            "erro_tipo": "ServerError_503"
        }
    
    ◆ EXEMPLO DE USO:
        historico = []
        
        resultado = chat_multi_turno_com_tratamento_erros(historico, "O que é RL?")
        
        if resultado["sucesso"]:
            historico = resultado["historico"]
            print(f"Bot: {resultado['resposta']}")
        else:
            print(f"❌ Erro: {resultado['resposta']}")
            # historico não foi modificado — tente novamente
    """
    try:
        # Tenta fazer o chat multi-turno
        # Internamente, isso:
        #   1. Adiciona nova_mensagem ao histórico
        #   2. Reenvia todo o histórico à API
        #   3. Adiciona a resposta ao histórico
        resposta_texto, historico_atualizado = chat_multi_turno(historico, nova_mensagem)
        return {
            "sucesso": True,
            "resposta": resposta_texto,
            "historico": historico_atualizado,  # ← Histórico NOVO, com a resposta adicionada
            "erro_tipo": None
        }

    except gemini_errors.ClientError as e:
        codigo = str(e)

        if "403" in codigo or "PERMISSION_DENIED" in codigo:
            return {
                "sucesso": False,
                "resposta": "❌ Erro de autenticação: verifique sua API_KEY em config.py.",
                "historico": historico,  # ← Histórico ORIGINAL (não foi modificado)
                "erro_tipo": "ClientError_403"
            }
        elif "429" in codigo or "RESOURCE_EXHAUSTED" in codigo:
            return {
                "sucesso": False,
                "resposta": (
                    "⏳ Cota ou rate limit atingido.\n"
                    "   → Aguarde alguns segundos e tente novamente.\n"
                    "   → Se persistir, verifique os limites em https://ai.dev/rate-limit"
                ),
                "historico": historico,  # ← Histórico ORIGINAL
                "erro_tipo": "ClientError_429"
            }
        else:
            return {
                "sucesso": False,
                "resposta": f"❌ Erro na requisição (4xx): {str(e)}",
                "historico": historico,  # ← Histórico ORIGINAL
                "erro_tipo": "ClientError"
            }

    except gemini_errors.ServerError as e:
        codigo = str(e)
        if "503" in codigo or "UNAVAILABLE" in codigo:
            return {
                "sucesso": False,
                "resposta": (
                    "⏳ Serviço temporariamente indisponível (503).\n"
                    "   → Aguarde alguns segundos e tente novamente.\n"
                    "   → Se persistir, verifique o status do serviço em https://status.cloud.google.com"
                ),
                "historico": historico,  # ← Histórico ORIGINAL (pode tentar novamente depois)
                "erro_tipo": "ServerError_503"
            }
        return {
            "sucesso": False,
            "resposta": f"❌ Erro no servidor Google (5xx): {str(e)}",
            "historico": historico,  # ← Histórico ORIGINAL
            "erro_tipo": "ServerError"
        }

    except Exception as e:
        return {
            "sucesso": False,
            "resposta": f"❌ Erro inesperado: {str(e)}",
            "historico": historico,  # ← Histórico ORIGINAL
            "erro_tipo": "UnexpectedError"
        }


# ════════════════════════════════════════════════════════════════════════════════
# FÁBRICA DO CLIENTE
# ════════════════════════════════════════════════════════════════════════════════

def criar_cliente() -> genai.Client:
    """
    Instancia e retorna o cliente autenticado do novo SDK google-genai.

    Mudança principal em relação ao SDK antigo:
        Antes : genai.configure(api_key=API_KEY)  →  configuração global
        Agora : genai.Client(api_key=API_KEY)      →  objeto explícito

    Retorno:
        Instância configurada de genai.Client.
    """
    return genai.Client(api_key=API_KEY)


def criar_config(**kwargs) -> types.GenerateContentConfig:
    """
    Monta e retorna o objeto de configuração de geração reutilizável.

    No novo SDK, os parâmetros (temperature, max_output_tokens, system_instruction)
    são agrupados em GenerateContentConfig e passados como `config=` em cada chamada.

    Parâmetros opcionais (**kwargs):
        Permitem sobrescrever os defaults de config.py para chamadas específicas.
        Ex: criar_config(temperature=0.9) para uma chamada mais criativa.

    Retorno:
        Instância de types.GenerateContentConfig.
    """
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=kwargs.get("temperature", TEMPERATURE),
        max_output_tokens=kwargs.get("max_output_tokens", MAX_TOKENS),
    )


# ════════════════════════════════════════════════════════════════════════════════
# FUNÇÃO 1 — Chamada Simples (síncrona, resposta completa)
# ════════════════════════════════════════════════════════════════════════════════

def chat_simples(pergunta: str) -> str:
    """
    Envia uma mensagem única e aguarda a resposta completa antes de retornar.

    Equivalência com a Anthropic:
        Anthropic : client.messages.create(messages=[{"role":"user","content":...}])
        Gemini    : client.models.generate_content(model=MODEL, contents=pergunta, ...)

    Estrutura interna da resposta:
        response.text                    → Atalho para o texto da resposta
        response.candidates[0].content  → Objeto de conteúdo completo
        response.usage_metadata          → Tokens consumidos (prompt + resposta)

    Parâmetros:
        pergunta : Texto da mensagem do usuário (str).

    Retorno:
        Texto da resposta do modelo (str).
    """
    client = criar_cliente()
    config = criar_config()

    response = client.models.generate_content(
        model=MODEL,
        contents=pergunta,
        config=config,
    )

    return response.text


# ════════════════════════════════════════════════════════════════════════════════
# FUNÇÃO 2 — Streaming (tokens progressivos)
# ════════════════════════════════════════════════════════════════════════════════

def chat_streaming(pergunta: str, callback=None) -> str:
    """
    Envia uma mensagem e recebe os tokens progressivamente (streaming).

    Como funciona no novo SDK:
        client.models.generate_content_stream() retorna um iterável de chunks.
        Cada chunk tem um atributo .text com o fragmento de token recebido.

    Parâmetro `callback`:
        Função opcional chamada a cada fragmento. Se não fornecida,
        os fragmentos são impressos diretamente no stdout.
        Assinatura esperada: callback(fragmento: str) -> None

    Parâmetros:
        pergunta : Texto da mensagem do usuário (str).
        callback : Função opcional para processar cada fragmento.

    Retorno:
        Texto completo acumulado (str).
    """
    client = criar_cliente()
    config = criar_config()

    texto_completo = ""

    for chunk in client.models.generate_content_stream(
        model=MODEL,
        contents=pergunta,
        config=config,
    ):
        fragmento = chunk.text
        texto_completo += fragmento

        if callback:
            callback(fragmento)
        else:
            print(fragmento, end="", flush=True)

    return texto_completo


# ════════════════════════════════════════════════════════════════════════════════
# FUNÇÃO 3 — Conversa Multi-turno (histórico manual)
# ════════════════════════════════════════════════════════════════════════════════

def chat_multi_turno(historico: list, nova_mensagem: str) -> tuple[str, list]:
    """
    Gerencia uma conversa com múltiplos turnos reenviando o histórico completo.

    Estrutura de um turno (types.Content):
        types.Content(
            role="user",                           # "user" ou "model"
            parts=[types.Part(text="mensagem")]
        )
        Atenção: no Gemini o papel do assistente é "model" (vs "assistant" na Anthropic).

    A API continua STATELESS: cada chamada recebe o histórico completo.

    Parâmetros:
        historico     : Lista de types.Content anteriores. Passe [] para iniciar.
        nova_mensagem : Texto da nova mensagem do usuário.

    Retorno:
        Tupla (resposta_str, historico_atualizado).
    """
    client = criar_cliente()
    config = criar_config()

    historico.append(
        types.Content(role="user", parts=[types.Part(text=nova_mensagem)])
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=historico,
        config=config,
    )

    resposta_texto = response.text

    historico.append(
        types.Content(role="model", parts=[types.Part(text=resposta_texto)])
    )

    return resposta_texto, historico


# ════════════════════════════════════════════════════════════════════════════════
# FUNÇÃO 4 — Wrapper com Tratamento de Erros
# ════════════════════════════════════════════════════════════════════════════════

def chat_com_tratamento_erros(pergunta: str) -> dict:
    """
    Executa chat_simples() com captura estruturada das exceções da API Gemini.

    Hierarquia de erros do novo SDK (google.genai.errors):
        APIError          → classe base para todos os erros da API
        ├── ClientError   → erros 4xx (problema na requisição do cliente)
        │     • 400 → argumento inválido, model inexistente
        │     • 403 → API Key inválida, sem permissão
        │     • 429 → rate limit ou cota atingida
        └── ServerError   → erros 5xx (problema no servidor do Google)
              • 503 → serviço temporariamente indisponível

    Diferença em relação ao SDK antigo:
        Antes : google.api_core.exceptions (pacote separado, precisava instalar)
        Agora : google.genai.errors (embutido — sem dependência extra)

    Retorno:
        dict com campos:
            "sucesso"   : bool
            "resposta"  : str (texto do modelo ou mensagem de erro)
            "erro_tipo" : str | None
    """
    try:
        texto = chat_simples(pergunta)
        return {"sucesso": True, "resposta": texto, "erro_tipo": None}

    except gemini_errors.ClientError as e:
        codigo = str(e)

        if "403" in codigo or "PERMISSION_DENIED" in codigo:
            return {
                "sucesso": False,
                "resposta": "❌ Erro de autenticação: verifique sua API_KEY em config.py.",
                "erro_tipo": "ClientError_403"
            }
        elif "429" in codigo or "RESOURCE_EXHAUSTED" in codigo:
            return {
                "sucesso": False,
                "resposta": (
                    "⏳ Cota ou rate limit atingido.\n"
                    "   → Aguarde alguns segundos e tente novamente.\n"
                    "   → Se persistir, verifique os limites em https://ai.dev/rate-limit"
                ),
                "erro_tipo": "ClientError_429"
            }
        else:
            return {
                "sucesso": False,
                "resposta": f"❌ Erro na requisição (4xx): {str(e)}",
                "erro_tipo": "ClientError"
            }

    except gemini_errors.ServerError as e:
        codigo = str(e)
        if "503" in codigo or "UNAVAILABLE" in codigo:
            return {
                "sucesso": False,
                "resposta": (
                    "⏳ Serviço temporariamente indisponível (503).\n"
                    "   → Aguarde alguns segundos e tente novamente.\n"
                    "   → Se persistir, verifique o status do serviço em https://status.cloud.google.com"
                ),
                "erro_tipo": "ServerError_503"
            }
        return {
            "sucesso": False,
            "resposta": f"❌ Erro no servidor Google (5xx): {str(e)}",
            "erro_tipo": "ServerError"
        }

    except Exception as e:
        return {
            "sucesso": False,
            "resposta": f"❌ Erro inesperado: {str(e)}",
            "erro_tipo": "UnexpectedError"
        }


# ════════════════════════════════════════════════════════════════════════════════
# FUNÇÃO 5 — Streaming com Tratamento de Erros
# ════════════════════════════════════════════════════════════════════════════════

def chat_streaming_com_tratamento_erros(pergunta: str, callback=None) -> dict:
    """
    Executa chat_streaming() com captura estruturada das exceções da API Gemini.

    Parâmetros:
        pergunta : Texto da mensagem do usuário (str).
        callback : Função opcional para processar cada fragmento.

    Retorno:
        dict com campos:
            "sucesso"   : bool
            "resposta"  : str (texto acumulado ou mensagem de erro)
            "erro_tipo" : str | None
    """
    try:
        texto = chat_streaming(pergunta, callback)
        return {"sucesso": True, "resposta": texto, "erro_tipo": None}

    except gemini_errors.ClientError as e:
        codigo = str(e)

        if "403" in codigo or "PERMISSION_DENIED" in codigo:
            return {
                "sucesso": False,
                "resposta": "❌ Erro de autenticação: verifique sua API_KEY em config.py.",
                "erro_tipo": "ClientError_403"
            }
        elif "429" in codigo or "RESOURCE_EXHAUSTED" in codigo:
            return {
                "sucesso": False,
                "resposta": (
                    "⏳ Cota ou rate limit atingido.\n"
                    "   → Aguarde alguns segundos e tente novamente.\n"
                    "   → Se persistir, verifique os limites em https://ai.dev/rate-limit"
                ),
                "erro_tipo": "ClientError_429"
            }
        else:
            return {
                "sucesso": False,
                "resposta": f"❌ Erro na requisição (4xx): {str(e)}",
                "erro_tipo": "ClientError"
            }

    except gemini_errors.ServerError as e:
        codigo = str(e)
        if "503" in codigo or "UNAVAILABLE" in codigo:
            return {
                "sucesso": False,
                "resposta": (
                    "⏳ Serviço temporariamente indisponível (503).\n"
                    "   → Aguarde alguns segundos e tente novamente.\n"
                    "   → Se persistir, verifique o status do serviço em https://status.cloud.google.com"
                ),
                "erro_tipo": "ServerError_503"
            }
        return {
            "sucesso": False,
            "resposta": f"❌ Erro no servidor Google (5xx): {str(e)}",
            "erro_tipo": "ServerError"
        }

    except Exception as e:
        return {
            "sucesso": False,
            "resposta": f"❌ Erro inesperado: {str(e)}",
            "erro_tipo": "UnexpectedError"
        }


# ════════════════════════════════════════════════════════════════════════════════
# FUNÇÃO 6 — Multi-turno com Tratamento de Erros
# ════════════════════════════════════════════════════════════════════════════════

def chat_multi_turno_com_tratamento_erros(historico: list, nova_mensagem: str) -> dict:
    """
    Executa chat_multi_turno() com captura estruturada das exceções da API Gemini.

    Parâmetros:
        historico     : Lista de types.Content anteriores.
        nova_mensagem : Texto da nova mensagem do usuário.

    Retorno:
        dict com campos:
            "sucesso"    : bool
            "resposta"   : str (texto da resposta ou mensagem de erro)
            "historico"  : list | None (histórico atualizado se sucesso)
            "erro_tipo"  : str | None
    """
    try:
        resposta_texto, historico_atualizado = chat_multi_turno(historico, nova_mensagem)
        return {
            "sucesso": True,
            "resposta": resposta_texto,
            "historico": historico_atualizado,
            "erro_tipo": None
        }

    except gemini_errors.ClientError as e:
        codigo = str(e)

        if "403" in codigo or "PERMISSION_DENIED" in codigo:
            return {
                "sucesso": False,
                "resposta": "❌ Erro de autenticação: verifique sua API_KEY em config.py.",
                "historico": historico,
                "erro_tipo": "ClientError_403"
            }
        elif "429" in codigo or "RESOURCE_EXHAUSTED" in codigo:
            return {
                "sucesso": False,
                "resposta": (
                    "⏳ Cota ou rate limit atingido.\n"
                    "   → Aguarde alguns segundos e tente novamente.\n"
                    "   → Se persistir, verifique os limites em https://ai.dev/rate-limit"
                ),
                "historico": historico,
                "erro_tipo": "ClientError_429"
            }
        else:
            return {
                "sucesso": False,
                "resposta": f"❌ Erro na requisição (4xx): {str(e)}",
                "historico": historico,
                "erro_tipo": "ClientError"
            }

    except gemini_errors.ServerError as e:
        codigo = str(e)
        if "503" in codigo or "UNAVAILABLE" in codigo:
            return {
                "sucesso": False,
                "resposta": (
                    "⏳ Serviço temporariamente indisponível (503).\n"
                    "   → Aguarde alguns segundos e tente novamente.\n"
                    "   → Se persistir, verifique o status do serviço em https://status.cloud.google.com"
                ),
                "historico": historico,
                "erro_tipo": "ServerError_503"
            }
        return {
            "sucesso": False,
            "resposta": f"❌ Erro no servidor Google (5xx): {str(e)}",
            "historico": historico,
            "erro_tipo": "ServerError"
        }

    except Exception as e:
        return {
            "sucesso": False,
            "resposta": f"❌ Erro inesperado: {str(e)}",
            "historico": historico,
            "erro_tipo": "UnexpectedError"
        }
