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
# PARTIDA ACTIVA
# =========================================================

partida = {
    "activa": False,
    "chat_id": None,
    "premio": 0,
    "max_jugadores": 0,
    "jugadores": [],
    "estado": "esperando",
    "turno": 0
}


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
        "𖹭 ¡holaa! ₍₍⚞(˶>ᗜ<˶)⚟⁾⁾\n\n"
        "aquí podrás participar en diferentes juegos.\n\n"
        "usa /yucmds para ver los comandos disponibles."
    )


# =========================================================
# /CMDS
# =========================================================

async def cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (
        "𖹭 𝗖𝗼𝗺𝗮𝗻𝗱𝗼𝘀\n\n"

        "/yustart → bienvenida\n"
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

    # El premio debe ser mayor que 0
    if robux <= 0:
        await update.message.reply_text(
            "el premio debe ser mayor que 0."
        )
        return

    # Mínimo 3 jugadores
    if max_jugadores < 3:
        await update.message.reply_text(
            "el juego necesita mínimo 3 jugadores."
        )
        return

    # Máximo 10 jugadores
    if max_jugadores > 11:
        await update.message.reply_text(
            "el juego permite máximo 11 jugadores."
        )
        return

    # No permitir otra partida activa
    if partida["activa"]:
        await update.message.reply_text(
            "ups, ya hay una partida activa."
        )
        return

    # Crear partida
    partida["activa"] = True
    partida["chat_id"] = update.effective_chat.id
    partida["premio"] = robux
    partida["max_jugadores"] = max_jugadores
    partida["jugadores"] = []

    # Mensaje de la partida
await update.message.reply_text(
    f"⠀⠀๑ 𝗝𝘂𝗲𝗴𝗼 𝗱𝗲 𝗠𝗲𝘀𝗮\n\n"
    f"⠀⠀premio: {robux} robux\n"
    f"⠀⠀jugadores: 0/{max_jugadores}\n\n"
    f"⠀⠀usa /unirmejuego + emoji\n"
    f"⠀⠀para participar.\n\n"
    f"⠀⠀esperando jugadores..."
)

# =========================================================
# /UNIRMEJUEGO
# =========================================================

async def unirmejuego(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Comprobar que existe una partida
    if not partida["activa"]:
        await update.message.reply_text(
            "🎲 ᛝ no hay ninguna partida activa en este momento."
        )
        return

    # Comprobar que haya un emoji
    if len(context.args) != 1:
        await update.message.reply_text(
            "debes elegir un emoji para participar.\n\n"
            "ejemplo:\n"
            "/unirmejuego 🐶"
        )
        return

    emoji = context.args[0]

    # Comprobar si el emoji ya está ocupado
    for jugador in partida["jugadores"]:

        if jugador["emoji"] == emoji:
            await update.message.reply_text(
                "ese emoji ya está ocupado. ૮꒰ “. . ꒱ა\n"
                "elige otro para participar."
            )
            return

    # Comprobar si el usuario ya está dentro
    user_id = update.effective_user.id

    for jugador in partida["jugadores"]:

        if jugador["id"] == user_id:
            await update.message.reply_text(
                f"🎲 ᛝ ya estás dentro de la partida.\n"
                f"tu emoji es {jugador['emoji']}."
            )
            return

    # Comprobar si quedan cupos
    if len(partida["jugadores"]) >= partida["max_jugadores"]:
        await update.message.reply_text(
            "🎲 ᛝ la partida ya está llena."
        )
        return

    # Registrar jugador
    partida["jugadores"].append({
        "id": user_id,
        "nombre": update.effective_user.full_name,
        "username": update.effective_user.username,
        "emoji": emoji
    })

    # Calcular cupos restantes
    cupos_restantes = (
        partida["max_jugadores"] - len(partida["jugadores"])
    )

# Confirmación de unión
username = update.effective_user.username

if username:
    usuario = f"@{username}"
else:
    usuario = update.effective_user.full_name

await update.message.reply_text(
    f"{usuario} se ha unido con {emoji}.\n"
    f"¡quedan {cupos_restantes} cupos!"
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
    CommandHandler("yustart", start)
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
