"""
bot.py — Bot Telegram assíncrono (python-telegram-bot v20+).

Handlers:
  /start      → boas-vindas + auto-registro CHAT_ID
  /relatorio  → gera e envia relatório executivo
  texto livre → chat() responde com Claude + tool use
"""

import os
import re
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv, set_key
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from agente import chat, gerar_relatorio, enviar_telegram

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM", "")
ENV_FILE       = Path(__file__).parent / ".env"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─── Auto-registro do CHAT_ID ────────────────────────────────────────────────
def salvar_chat_id(chat_id: int):
    """Salva CHAT_ID no .env se ainda não estiver registrado ou for diferente."""
    chat_id_str = str(chat_id)
    atual = os.getenv("CHAT_ID", "")

    if atual == chat_id_str:
        return  # já correto

    if not ENV_FILE.exists():
        ENV_FILE.write_text(f"CHAT_ID={chat_id_str}\n", encoding="utf-8")
    else:
        conteudo = ENV_FILE.read_text(encoding="utf-8")
        if "CHAT_ID=" in conteudo:
            conteudo = re.sub(r"CHAT_ID=.*", f"CHAT_ID={chat_id_str}", conteudo)
        else:
            conteudo = conteudo.rstrip("\n") + f"\nCHAT_ID={chat_id_str}\n"
        ENV_FILE.write_text(conteudo, encoding="utf-8")

    os.environ["CHAT_ID"] = chat_id_str
    logger.info(f"CHAT_ID={chat_id_str} salvo no .env")


def _auto_registro(update: Update):
    if update.message:
        salvar_chat_id(update.message.chat_id)


# ─── Helpers ─────────────────────────────────────────────────────────────────
async def _split_send(update: Update, texto: str):
    """Envia texto com split automático para o limite do Telegram (4096 chars)."""
    for parte in [texto[i:i+4096] for i in range(0, len(texto), 4096)]:
        try:
            await update.message.reply_text(parte, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(parte)


# ─── Handlers ────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _auto_registro(update)
    mensagem = (
        "👋 *Olá! Sou o agente de dados do e-commerce.*\n\n"
        "Posso responder qualquer pergunta sobre vendas, clientes e preços.\n\n"
        "*Exemplos:*\n"
        "• Qual foi a receita desta semana?\n"
        "• Quem são os clientes VIP?\n"
        "• Quais produtos estão mais caros que os concorrentes?\n\n"
        "Use /relatorio para gerar o relatório executivo completo.\n\n"
        f"✅ Chat ID registrado: `{update.message.chat_id}`"
    )
    await update.message.reply_text(mensagem, parse_mode="Markdown")
    logger.info(f"[{_ts()}] /start — chat_id={update.message.chat_id}")


async def cmd_relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _auto_registro(update)
    logger.info(f"[{_ts()}] /relatorio solicitado — chat_id={update.message.chat_id}")
    await update.message.reply_text("⏳ Gerando relatório executivo... Aguarde.")
    await context.bot.send_chat_action(update.message.chat_id, "typing")

    try:
        relatorio = await asyncio.get_event_loop().run_in_executor(None, gerar_relatorio)
        await _split_send(update, relatorio)
    except Exception as e:
        logger.error(f"Erro no relatório: {e}")
        await update.message.reply_text(f"❌ Erro ao gerar relatório: {e}")


async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _auto_registro(update)
    pergunta = update.message.text
    logger.info(f"[{_ts()}] Pergunta: {pergunta[:80]} — chat_id={update.message.chat_id}")

    await context.bot.send_chat_action(update.message.chat_id, "typing")

    try:
        resposta = await asyncio.get_event_loop().run_in_executor(None, chat, pergunta)
        await _split_send(update, resposta)
    except Exception as e:
        logger.error(f"Erro no chat: {e}")
        await update.message.reply_text(f"❌ Erro ao processar pergunta: {e}")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM não configurado no .env")

    logger.info(f"[{_ts()}] Iniciando bot Telegram...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("relatorio", cmd_relatorio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))

    logger.info(f"[{_ts()}] Bot rodando! Ctrl+C para parar.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
