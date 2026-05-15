"""
agente.py — Agente de dados com Groq API (Llama 3).
Usa o SDK oficial da Groq para chat e function calling.

Funções:
  chat(pergunta)       → Groq + function calling SQL → resposta em português
  gerar_relatorio()    → 4 queries fixas → Groq → relatório Markdown
  enviar_telegram()    → API HTTP do Telegram (sem bot rodando)

Uso standalone:
  python agente.py     → gera relatório + imprime + salva + envia (se CHAT_ID)
"""

import os
import json
import urllib.request
from datetime import datetime, date

from groq import Groq
import pandas as pd
from dotenv import load_dotenv

from db import execute_query, get_schema

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM", "")
CHAT_ID        = os.getenv("CHAT_ID", "")
MODEL          = "llama3-70b-8192"   # Groq Free Tier model
MAX_TOOL_ITER  = 10


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def _get_client():
    return Groq(api_key=GROQ_API_KEY)


# ─── Tool definition ─────────────────────────────────────────────────────────
tools = [
    {
        "type": "function",
        "function": {
            "name": "executar_sql",
            "description": "Executa query SQL SELECT no banco de dados do e-commerce.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "Query SQL SELECT ou WITH para executar.",
                    }
                },
                "required": ["sql"],
            },
        },
    }
]


# ─── Chat livre ───────────────────────────────────────────────────────────────
def chat(pergunta: str) -> str:
    """Responde uma pergunta usando Groq + function calling SQL."""
    client = _get_client()

    system_prompt = f"""Você é um analista de dados de um e-commerce brasileiro.
Responda perguntas usando os dados do banco de dados.
Use a ferramenta executar_sql para consultar os dados necessários.
Formate valores monetários em R$. Responda sempre em português.
Seja conciso e direto. Use emojis para tornar a resposta mais amigável.

{get_schema()}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": pergunta}
    ]

    for _ in range(MAX_TOOL_ITER):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        
        # Se não há tool calls, retornar o texto final
        if not response_message.tool_calls:
            return response_message.content or "Não consegui gerar uma resposta."

        # Adicionar a mensagem do assistente (incluindo tool_calls) ao histórico
        messages.append(response_message)

        # Processar cada function call
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name == "executar_sql":
                sql = function_args.get("sql", "")
                _log(f"Function call: executar_sql({sql[:80]}...)")
                try:
                    df = execute_query(sql)
                    resultado = df.to_markdown(index=False) if not df.empty else "Query retornou 0 linhas."
                except Exception as e:
                    resultado = f"Erro ao executar SQL: {e}"
                
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": resultado,
                })

    return "⚠️ Limite de iterações atingido. Tente reformular a pergunta."


# ─── Relatório executivo ──────────────────────────────────────────────────────
def gerar_relatorio() -> str:
    """Gera relatório diário executivo com 4 queries fixas."""
    _log("Iniciando geração do relatório...")
    client = _get_client()

    _log("Consultando vendas...")
    try:
        dados_vendas = execute_query("""
            SELECT data_venda, dia_semana_nome,
                SUM(receita_total)          AS receita,
                COUNT(DISTINCT id_venda)    AS vendas,
                COUNT(DISTINCT id_cliente)  AS clientes,
                AVG(preco_unitario * quantidade) AS ticket_medio
            FROM public_gold_sales.vendas_temporais
            GROUP BY data_venda, dia_semana_nome
            ORDER BY data_venda DESC LIMIT 7
        """)
    except Exception as e:
        dados_vendas = pd.DataFrame({"erro": [str(e)]})

    _log("Consultando clientes...")
    try:
        dados_clientes = execute_query("""
            SELECT segmento_cliente,
                COUNT(*)              AS total_clientes,
                SUM(receita_total)    AS receita_total,
                AVG(ticket_medio)     AS ticket_medio_avg,
                AVG(total_compras)    AS compras_avg
            FROM public_gold_cs.clientes_segmentacao
            GROUP BY segmento_cliente ORDER BY receita_total DESC
        """)
    except Exception as e:
        dados_clientes = pd.DataFrame({"erro": [str(e)]})

    _log("Consultando pricing...")
    try:
        dados_pricing = execute_query("""
            SELECT classificacao_preco,
                COUNT(*)                               AS total_produtos,
                AVG(diferenca_percentual_vs_media)     AS dif_media_pct,
                SUM(receita_total)                     AS receita_impactada
            FROM public_gold_pricing.precos_competitividade
            GROUP BY classificacao_preco ORDER BY total_produtos DESC
        """)
    except Exception as e:
        dados_pricing = pd.DataFrame({"erro": [str(e)]})

    _log("Consultando produtos críticos...")
    try:
        dados_criticos = execute_query("""
            SELECT nome_produto, categoria, nosso_preco,
                preco_medio_concorrentes,
                diferenca_percentual_vs_media, receita_total
            FROM public_gold_pricing.precos_competitividade
            WHERE classificacao_preco = 'MAIS_CARO_QUE_TODOS'
            ORDER BY diferenca_percentual_vs_media DESC LIMIT 10
        """)
    except Exception as e:
        dados_criticos = pd.DataFrame({"erro": [str(e)]})

    system_prompt = """Você é um analista de dados senior de um e-commerce brasileiro.
Gere um relatório executivo diário para 3 diretores:
1. Diretor Comercial: receita, vendas, ticket médio e tendências.
2. Diretora de Customer Success: segmentação de clientes, VIPs e riscos.
3. Diretor de Pricing: posicionamento de preço vs concorrência e alertas.

Regras: seja direto e acionável, use números reais, formate em R$, use Markdown com emojis."""

    user_prompt = f"""Gere o relatório diário. Data: {date.today().strftime('%d/%m/%Y')}

## Dados de Vendas (últimos 7 dias)
{dados_vendas.to_markdown(index=False)}

## Segmentação de Clientes
{dados_clientes.to_markdown(index=False)}

## Posicionamento de Preços
{dados_pricing.to_markdown(index=False)}

## Produtos Críticos (mais caros que todos os concorrentes)
{dados_criticos.to_markdown(index=False)}

Gere:
1. Resumo executivo (3 linhas)
2. Seção Comercial
3. Seção Customer Success
4. Seção Pricing"""

    _log("Enviando para Groq API...")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        relatorio = response.choices[0].message.content
    except Exception as e:
        relatorio = (
            f"# Relatório Diário\nData: {date.today()}\n\n"
            f"⚠️ Erro ao gerar com IA: {e}\n\n"
            f"## Vendas\n{dados_vendas.to_markdown()}\n\n"
            f"## Clientes\n{dados_clientes.to_markdown()}"
        )

    nome_arquivo = f"relatorio_{date.today()}.md"
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write(relatorio)
    _log(f"Relatório salvo em: {nome_arquivo}")

    return relatorio


# ─── Envio Telegram ───────────────────────────────────────────────────────────
def enviar_telegram(texto: str, chat_id: str = None):
    """Envia mensagem via API HTTP do Telegram (sem bot rodando)."""
    token = TELEGRAM_TOKEN
    cid   = chat_id or CHAT_ID

    if not token:
        print("⚠️  TELEGRAM não configurado no .env")
        return
    if not cid:
        print("⚠️  CHAT_ID não configurado. Rode bot.py primeiro e envie /start.")
        return

    partes = [texto[i:i+4096] for i in range(0, len(texto), 4096)]
    url    = f"https://api.telegram.org/bot{token}/sendMessage"

    for idx, parte in enumerate(partes):
        payload = {"chat_id": cid, "text": parte, "parse_mode": "Markdown"}
        data    = json.dumps(payload).encode("utf-8")
        req     = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            urllib.request.urlopen(req, timeout=15)
            _log(f"Mensagem {idx+1}/{len(partes)} enviada para chat_id={cid}")
        except Exception as e:
            _log(f"Markdown falhou ({e}), tentando texto puro...")
            payload["parse_mode"] = ""
            data = json.dumps(payload).encode("utf-8")
            req  = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}
            )
            try:
                urllib.request.urlopen(req, timeout=15)
            except Exception as e2:
                _log(f"❌ Falha ao enviar: {e2}")


# ─── Standalone ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    relatorio = gerar_relatorio()
    print("\n" + "="*60)
    print(relatorio)
    print("="*60 + "\n")
    enviar_telegram(relatorio)
