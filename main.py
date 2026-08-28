import os
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)


# =========================================================
# CONFIGURACIÓN
# =========================================================

TOKEN = os.getenv("TELEGRAM_TOKEN")

# Render nos dará este puerto automáticamente
PORT = int(os.environ.get("PORT", 10000))

# URL pública de Render
WEBHOOK_URL = os.getenv("WEBHOOK_URL")


# =========================================================
# LOGS
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# =========================================================
# COMPROBAR SI ES ADMIN
# =========================================================

async def es_admin(update: Update, user_id: int) -> bool:
    """
    Comprueba si el usuario es administrador
    del grupo donde se está usando el comando.
    """

    if not update.effective_chat:
        return False

    try:
        miembro = await update.effective_chat.get_member(user_id)

        return miembro.status in ["administrator", "creator"]

    except Exception as e:
        logger.error(f"Error comprobando admin: {e}")
        return False


# =========================================================
# /START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "𖹭 ¡holaa! soy yujuega 🎲\n\n"
        "aquí podrás participar en diferentes juegos.\n\n"
        "usa /yucmds para ver los comandos disponibles."
    )


# =========================================================
# /CMDS
# =========================================================

async def cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (
        "𖹭 𝗖𝗼𝗺𝗮𝗻𝗱𝗼𝘀\n\n"

        "/start → bienvenida\n"
        "/yucmds → lista de comandos\n\n"

        "๑ 𝗝𝘂𝗲𝗴𝗼 𝗱𝗲 𝗠𝗲𝘀𝗮\n"
        "/juegomesa → crear una partida\n"
        "/unirmejuego → unirte a una partida\n"
        "/startjuego → iniciar la partida\n"
        "/cancelarjuego → cancelar la partida"
    )

    await update.message.reply_text(
        texto
    )


# =========================================================
# /JUEGOMESA
# =========================================================

async def juegomesa(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Solo grupos
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "este comando solo puede utilizarse en un grupo."
        )
        return

    # Solo admins
    if not await es_admin(update, update.effective_user.id):
        await update.message.reply_text(
            "🎲 ᛝ solo los administradores del grupo "
            "pueden crear juegos. ૮₍｡•̀ ﻌ •́｡₎ა"
        )
        return

    # Comprobar argumentos
    if len(context.args) != 2:
        await update.message.reply_text(
            "uso:\n"
            "/juegomesa <robux> <jugadores>\n\n"
            "ejemplo:\n"
            "/juegomesa 10 5"
        )
        return

    try:
        robux = int(context.args[0])
        max_jugadores = int(context.args[1])

    except ValueError:
        await update.message.reply_text(
            "debes colocar números válidos."
        )
        return

    # Mínimo 3 jugadores
    if max_jugadores < 3:
        await update.message.reply_text(
            "el juego necesita mínimo 3 jugadores."
        )
        return

    await update.message.reply_text(
        f"⠀⠀๑ 𝗝𝘂𝗲𝗴𝗼 𝗱𝗲 𝗠𝗲𝘀𝗮\n\n"
        f"⠀⠀premio: {robux} robux\n"
        f"⠀⠀jugadores: {max_jugadores}\n\n"
        f"⠀⠀usa /unirmejuego + emoji\n"
        f"⠀⠀para participar.\n\n"
        f"⠀⠀esperando jugadores..."
    )


# =========================================================
# /UNIRMEJUEGO
# =========================================================

async def unirmejuego(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "💘 te has unido al juego.\n"
        "la lógica de jugadores la agregaremos aquí."
    )


# =========================================================
# /STARTJUEGO
# =========================================================

async def startjuego(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Solo grupos
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "este comando solo puede utilizarse en un grupo."
        )
        return

    # Solo admins
    if not await es_admin(update, update.effective_user.id):
        await update.message.reply_text(
            "🎲 ᛝ solo los administradores pueden iniciar el juego. "
            "૮₍｡•̀ ﻌ •́｡₎ა"
        )
        return

    await update.message.reply_text(
        "🎲 el juego comenzará aquí.\n"
        "todavía estamos construyendo esta parte. 👀"
    )


# =========================================================
# /CANCELARJUEGO
# =========================================================

async def cancelarjuego(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Solo grupos
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "este comando solo puede utilizarse en un grupo."
        )
        return

    # Solo admins
    if not await es_admin(update, update.effective_user.id):
        await update.message.reply_text(
            "🎲 ᛝ solo los administradores pueden cancelar "
            "el juego. ૮꒰ “. . ꒱ა"
        )
        return

    await update.message.reply_text(
        "🗑️ ᛝ juego cancelado."
    )


# =========================================================
# MAIN
# =========================================================

app = Application.builder().token(TOKEN).build()

app.add_handler(
    CommandHandler("start", start)
)

app.add_handler(
    CommandHandler("yucmds", cmds)
)

app.add_handler(
    CommandHandler("juegomesa", juegomesa)
)

app.add_handler(
    CommandHandler("unirmejuego", unirmejuego)
)

app.add_handler(
    CommandHandler("startjuego", startjuego)
)

app.add_handler(
    CommandHandler("cancelarjuego", cancelarjuego)
)


# =========================================================
# WEBHOOK
# =========================================================

if not TOKEN:
    raise ValueError(
        "No se encontró TELEGRAM_TOKEN en las variables de entorno."
    )

if not WEBHOOK_URL:
    raise ValueError(
        "No se encontró WEBHOOK_URL en las variables de entorno."
    )


app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
)
