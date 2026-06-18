"""
================================================================================
main.py — Ponto de Entrada da Aplicação
================================================================================
Responsabilidade:
    Orquestrar a execução dos diferentes modos de uso da API.
    Este módulo não contém lógica de negócio nem de comunicação —
    apenas chama as funções do api_client e exibe os resultados.

Estrutura do projeto:
    anthropic_project/
    ├── config.py       → Credenciais e parâmetros (API Key, modelo, temperatura)
    ├── api_client.py   → Funções de comunicação com a API da Anthropic
    ├── main.py         → Ponto de entrada: orquestra e exibe os resultados  ← você está aqui
    └── requirements.txt → Dependências do projeto

Como executar:
    python main.py
================================================================================
"""

# Importa apenas as funções necessárias do módulo de API
from api_client import (
    chat_com_tratamento_erros,
    chat_streaming,
    chat_multi_turno,
)


# ── Helpers de apresentação ───────────────────────────────────────────────────

def cabecalho(titulo: str) -> None:
    """Imprime um cabeçalho formatado para separar os testes no terminal."""
    print(f"\n{'=' * 60}")
    print(f"  {titulo}")
    print(f"{'=' * 60}")


def rodape(info: str = "") -> None:
    """Imprime um rodapé opcional."""
    if info:
        print(f"\n  ℹ {info}")
    print("─" * 60)


# ════════════════════════════════════════════════════════════════════════════════
# DEMO 1 — Chamada Simples com Tratamento de Erros
# ════════════════════════════════════════════════════════════════════════════════

def demo_chamada_simples() -> None:
    """
    Demonstra uma chamada única à API com retorno de resposta completa.
    Usa o wrapper com tratamento de erros para capturar falhas de auth/rede.
    """
    cabecalho("DEMO 1 — Chamada Simples")

    pergunta = "O que é temperature em modelos de linguagem e como ela afeta as respostas?"
    print(f"\nPergunta:\n  {pergunta}\n")

    resultado = chat_com_tratamento_erros(pergunta)

    if resultado["sucesso"]:
        print(f"Resposta:\n{resultado['resposta']}")
    else:
        print(f"Erro [{resultado['erro_tipo']}]: {resultado['resposta']}")

    rodape()


# ════════════════════════════════════════════════════════════════════════════════
# DEMO 2 — Streaming de Tokens
# ════════════════════════════════════════════════════════════════════════════════

def demo_streaming() -> None:
    """
    Demonstra o modo streaming, onde tokens chegam progressivamente.
    Os fragmentos são impressos conforme chegam via Server-Sent Events (SSE).
    """
    cabecalho("DEMO 2 — Streaming de Tokens")

    pergunta = "Em três frases, explique o que é um endpoint de API REST."
    print(f"\nPergunta:\n  {pergunta}\n")
    print("Resposta (tokens chegando progressivamente):\n")

    # Sem callback: chat_streaming imprime direto no stdout por padrão
    chat_streaming(pergunta)

    rodape("Cada fragmento acima foi recebido e impresso individualmente via SSE.")


# ════════════════════════════════════════════════════════════════════════════════
# DEMO 3 — Conversa Multi-turno
# ════════════════════════════════════════════════════════════════════════════════

def demo_multi_turno() -> None:
    """
    Demonstra uma conversa com múltiplos turnos.
    O histórico é acumulado e reenviado a cada chamada (API stateless).
    """
    cabecalho("DEMO 3 — Conversa Multi-turno")

    historico = []   # inicia sem contexto

    # Turno 1
    pergunta_1 = "O que é XGBoost?"
    print(f"\n[Turno 1]\nUsuário: {pergunta_1}\n")
    resposta_1, historico = chat_multi_turno(historico, pergunta_1)
    print(f"Claude : {resposta_1}")

    # Turno 2 — Claude recebe o contexto do turno 1 automaticamente
    pergunta_2 = "Qual é a diferença principal em relação ao Random Forest?"
    print(f"\n[Turno 2]\nUsuário: {pergunta_2}\n")
    resposta_2, historico = chat_multi_turno(historico, pergunta_2)
    print(f"Claude : {resposta_2}")

    rodape(f"Histórico acumulado: {len(historico)} mensagens reenviadas na última requisição.")


# ════════════════════════════════════════════════════════════════════════════════
# EXECUÇÃO
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  CLIENTE API ANTHROPIC — DEMONSTRAÇÃO MODULAR")
    print("=" * 60)

    demo_chamada_simples()
    demo_streaming()
    demo_multi_turno()

    print("\nDemonstração concluída.\n")
