import os
import logging
import random

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
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
    "turno": 0,
    "turno_id": 0,
    "mensaje_turno": None,
    "retroceso": None,
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
        "⠀⠀\n"

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
    # Crear partida
    partida["estado"] = "esperando"
    partida["turno"] = 0
    partida["turno_id"] += 1
    partida["mensaje_turno"] = None
    partida["retroceso"] = None

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
        "emoji": emoji,
        "posicion": 0,
        "escudo": False,
        "perder_turno": False
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

    # Comprobar que exista una partida
    if not partida["activa"]:
        await update.message.reply_text(
            "🎲 ᛝ no hay ninguna partida activa."
        )
        return

    # Comprobar que la partida siga esperando
    if partida["estado"] != "esperando":
        await update.message.reply_text(
            "🎲 ᛝ esta partida ya ha comenzado."
        )
        return

    # Mínimo 3 jugadores
    if len(partida["jugadores"]) < 3:
        await update.message.reply_text(
            "🎲 ᛝ se necesitan mínimo 3 jugadores para iniciar."
        )
        return

    # Cambiar estado de la partida
    partida["estado"] = "jugando"
    partida["turno"] = 0
    partida["turno_id"] += 1

    # Crear lista de jugadores
    jugadores_texto = ""

    for jugador in partida["jugadores"]:

        if jugador["username"]:
            usuario = f"@{jugador['username']}"
        else:
            usuario = jugador["nombre"]

        jugadores_texto += (
            f"{usuario} {jugador['emoji']}\n"
        )

    # Mensaje de inicio
    await update.message.reply_text(
        f"🎲 ᛝ ¡la partida ha comenzado!\n\n"
        f"{jugadores_texto}"
    )

    # Enviar primer turno
    await enviar_turno(
        context,
        partida["turno_id"]
    )

# =========================================================
# BOTÓN: LANZAR DADO
# =========================================================

async def lanzar_dado(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    # Comprobar que exista una partida
    if not partida["activa"]:
        await query.answer(
            "no hay una partida activa. (╥﹏╥)",
            show_alert=True
        )
        return

    # Comprobar que la partida esté jugando
    if partida["estado"] != "jugando":
        await query.answer(
            "la partida todavía no ha comenzado. (╥﹏╥)",
            show_alert=True
        )
        return

    # Jugador al que le corresponde el turno
    jugador_actual = partida["jugadores"][partida["turno"]]

    # Comprobar que quien pulsó sea el jugador de turno
    if query.from_user.id != jugador_actual["id"]:
        await query.answer(
            "no es tu turno. (╥﹏╥)",
            show_alert=True
        )
        return

    # Responder al botón
    await query.answer()

    # Este turno ya fue utilizado
    partida["turno_id"] += 1

    # Lanzar dado
    resultado = random.randint(1, 6)

    # Identificar jugador
    usuario = nombre_usuario(jugador_actual)

    # Posición actual
    posicion_actual = jugador_actual["posicion"]

    # Calcular nueva posición
    nueva_posicion = posicion_actual + resultado

    # =====================================================
    # NO PUEDE SUPERAR LA CASILLA 51
    # =====================================================

    if nueva_posicion > 51:

        await query.message.reply_text(
            f"🎲 . . . {usuario} {jugador_actual['emoji']} "
            f"ha sacado un {resultado}.\n\n"
            f"está en la casilla {posicion_actual} "
            f"y necesita exactamente "
            f"{51 - posicion_actual} para llegar a 51.\n\n"
            f"no avanza."
        )

        await pasar_turno(context)
        return

    # =====================================================
    # AVANZAR
    # =====================================================

    jugador_actual["posicion"] = nueva_posicion

    await query.message.reply_text(
        f"🎲 . . . {usuario} {jugador_actual['emoji']} "
        f"ha sacado un {resultado}.\n\n"
        f"avanza de la casilla {posicion_actual} "
        f"a la casilla {nueva_posicion}."
    )

    # =====================================================
    # VICTORIA
    # =====================================================

    if nueva_posicion == 51:

        await query.message.reply_text(
            f"ꉂ(˵˃ ᗜ ˂˵) ᛝ ¡{usuario} "
            f"{jugador_actual['emoji']} "
            f"ha llegado a la casilla 51!\n\n"
            f"¡ha ganado la partida! 🎉"
        )

        partida["activa"] = False
        partida["estado"] = "finalizada"
        partida["retroceso"] = None

        return

    # =====================================================
    # CASILLA 6 — AVANZA 3
    # =====================================================

    if jugador_actual["posicion"] == 6:

        posicion_anterior = jugador_actual["posicion"]
        posicion_especial = posicion_anterior + 3

        if posicion_especial <= 51:

            jugador_actual["posicion"] = posicion_especial

            await query.message.reply_text(
                f"🟣 ᛝ ¡AVANZA 3 CASILLAS! "
                f"⸜(｡˃ ᵕ ˂ )⸝\n\n"
                f"{usuario} {jugador_actual['emoji']} "
                f"avanza de la casilla {posicion_anterior} "
                f"a la casilla {posicion_especial}."
            )

            # Comprobar si llegó a 51 gracias al avance especial
            if posicion_especial == 51:

                await query.message.reply_text(
                    f"ꉂ(˵˃ ᗜ ˂˵) ᛝ ¡{usuario} "
                    f"{jugador_actual['emoji']} "
                    f"ha llegado a la casilla 51!\n\n"
                    f"¡ha ganado la partida! 🎉"
                )

                partida["activa"] = False
                partida["estado"] = "finalizada"
                partida["retroceso"] = None

                return

        else:

            await query.message.reply_text(
                f"🟣 ᛝ ¡AVANZA 3 CASILLAS! "
                f"⸜(｡˃ ᵕ ˂ )⸝\n\n"
                f"no puede avanzar porque "
                f"superaría la casilla 51."
            )

    # =====================================================
    # CASILLA 14 — DADO EXTRA
    # =====================================================

    if jugador_actual["posicion"] == 14:

        await query.message.reply_text(
            f"🟣 ᛝ ¡DADO EXTRA! "
            f"⸜(｡˃ ᵕ ˂ )⸝\n\n"
            f"{usuario} {jugador_actual['emoji']} "
            f"tiene la oportunidad de lanzar otra vez."
        )

        # Mantener el turno del mismo jugador
        partida["turno_id"] += 1

        await enviar_turno(
            context,
            partida["turno_id"]
        )

        return

    # =====================================================
    # CASILLA 26 — ESCUDO
    # =====================================================

    if jugador_actual["posicion"] == 26:

        jugador_actual["escudo"] = True

        await query.message.reply_text(
            f"🟣 ᛝ ¡ESCUDO! "
            f"⸜(｡˃ ᵕ ˂ )⸝\n\n"
            f"{usuario} {jugador_actual['emoji']} "
            f"ha conseguido un escudo. 🛡️"
        )

    # =====================================================
    # CASILLA 20 — ELEGIR JUGADOR
    # =====================================================

    if jugador_actual["posicion"] == 20:

        botones = []

        for jugador in partida["jugadores"]:

            # No puede elegirse a sí mismo
            if jugador["id"] == jugador_actual["id"]:
                continue

            botones.append([
                InlineKeyboardButton(
                    f"{nombre_usuario(jugador)} "
                    f"{jugador['emoji']}",
                    callback_data=(
                        f"juego:retroceder:{jugador['id']}"
                    )
                )
            ])

        teclado = InlineKeyboardMarkup(botones)

        await query.message.reply_text(
            f"🟠 ᛝ ¡ELIGES QUE ALGUIEN RETROCEDA! "
            f"(っ˕ -｡)\n\n"
            f"{usuario} {jugador_actual['emoji']}, "
            f"elige a quién hacer retroceder.",
            reply_markup=teclado
        )

        return

    # =====================================================
    # CASILLA 32 — LANZA DE NUEVO Y RETROCEDE
    # =====================================================

    if jugador_actual["posicion"] == 32:

        await query.message.reply_text(
            f"🟠 ᛝ ¡LANZA DE NUEVO! "
            f"(っ˕ -｡)\n\n"
            f"{usuario} {jugador_actual['emoji']} "
            f"debe lanzar otra vez y retroceder "
            f"esa cantidad. :("
        )

        boton_dado = InlineKeyboardButton(
            "lanzar ‹𝟹",
            callback_data="juego:retroceso_dado"
        )

        teclado = InlineKeyboardMarkup([
            [boton_dado]
        ])

        partida["retroceso"] = {
            "jugador_id": jugador_actual["id"],
            "atacante_id": jugador_actual["id"],
            "turno_id": partida["turno_id"]
        }

        await query.message.reply_text(
            f"{usuario} {jugador_actual['emoji']}, "
            f"lanza el dado.",
            reply_markup=teclado
        )

        context.job_queue.run_once(
            tiempo_retroceso_agotado,
            60,
            data={
                "turno_id": partida["turno_id"],
                "jugador_id": jugador_actual["id"]
            }
        )

        return

    # =====================================================
    # CASILLA 46 — PIERDE EL SIGUIENTE TURNO
    # =====================================================

    if jugador_actual["posicion"] == 46:

        jugador_actual["perder_turno"] = True

        await query.message.reply_text(
            f"🟠 ᛝ ¡OH, NO! "
            f"(っ˕ -｡)\n\n"
            f"{usuario} {jugador_actual['emoji']} "
            f"pierde su siguiente turno. :("
        )

    # =====================================================
    # PASAR AL SIGUIENTE JUGADOR
    # =====================================================

    await pasar_turno(context)

# =========================================================
# TIEMPO AGOTADO
# =========================================================

async def tiempo_agotado(context: ContextTypes.DEFAULT_TYPE):

    if not partida["activa"]:
        return

    if partida["estado"] != "jugando":
        return

    datos = context.job.data

    turno_id = datos["turno_id"]

    # Este temporizador pertenece a un turno anterior
    if turno_id != partida["turno_id"]:
        return

    jugador = partida["jugadores"][partida["turno"]]

    usuario = nombre_usuario(jugador)

    await context.bot.send_message(
        chat_id=partida["chat_id"],
        text=(
            f"⏱️ ᛝ se acabó el tiempo de {usuario} "
            f"{jugador['emoji']}.\n\n"
            f"pasa el turno."
        )
    )

    await pasar_turno(context)


# =========================================================
# MOSTRAR USUARIO
# =========================================================

def nombre_usuario(jugador):

    if jugador["username"]:
        return f"@{jugador['username']}"

    return jugador["nombre"]


# =========================================================
# PASAR AL SIGUIENTE JUGADOR
# =========================================================

async def pasar_turno(context: ContextTypes.DEFAULT_TYPE):

    partida["turno"] += 1

    if partida["turno"] >= len(partida["jugadores"]):
        partida["turno"] = 0

    partida["turno_id"] += 1

    await enviar_turno(
        context,
        partida["turno_id"]
    )


# =========================================================
# ENVIAR TURNO
# =========================================================

async def enviar_turno(
    context: ContextTypes.DEFAULT_TYPE,
    turno_id: int
):

    jugador = partida["jugadores"][partida["turno"]]

    usuario = nombre_usuario(jugador)

    # =====================================================
    # PERDER TURNO
    # =====================================================

    if jugador["perder_turno"]:

        jugador["perder_turno"] = False

        await context.bot.send_message(
            chat_id=partida["chat_id"],
            text=(
                f"🎲 ᛝ va {usuario} {jugador['emoji']}, "
                f"pero no tiene turno. :(\n\n"
                f"pasa al siguiente jugador."
            )
        )

        await pasar_turno(context)
        return

    # =====================================================
    # BOTÓN PARA LANZAR
    # =====================================================

    boton_dado = InlineKeyboardButton(
        "lanzar ‹𝟹",
        callback_data="juego:lanzar"
    )

    teclado = InlineKeyboardMarkup([
        [boton_dado]
    ])

    # =====================================================
    # MENSAJE DEL TURNO
    # =====================================================

    await context.bot.send_message(
        chat_id=partida["chat_id"],
        text=(
            f"𖹭 {usuario} {jugador['emoji']} "
            f"lanza el dado, ¡suerte!"
        ),
        reply_markup=teclado
    )

    # =====================================================
    # TEMPORIZADOR DE 1 MINUTO
    # =====================================================

    context.job_queue.run_once(
        tiempo_agotado,
        60,
        data={
            "turno_id": turno_id
        }
    )


# =========================================================
# CASILLA 20: ELEGIR JUGADOR
# =========================================================

async def elegir_retroceso(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if not partida["activa"]:
        await query.answer(
            "no hay una partida activa. (╥﹏╥)",
            show_alert=True
        )
        return

    if not query.data.startswith("juego:retroceder:"):
        return

    try:
        objetivo_id = int(
            query.data.split(":")[2]
        )
    except (ValueError, IndexError):
        await query.answer(
            "no pude identificar al jugador. (╥﹏╥)",
            show_alert=True
        )
        return

    jugador_actual = partida["jugadores"][partida["turno"]]

    # Solo quien cayó en la 20 puede elegir
    if query.from_user.id != jugador_actual["id"]:
        await query.answer(
            "no puedes elegir en este momento. (╥﹏╥)",
            show_alert=True
        )
        return

    objetivo = None

    for jugador in partida["jugadores"]:
        if jugador["id"] == objetivo_id:
            objetivo = jugador
            break

    if objetivo is None:
        await query.answer(
            "ese jugador ya no está disponible.",
            show_alert=True
        )
        return

    # No puede elegirse a sí mismo
    if objetivo["id"] == jugador_actual["id"]:
        await query.answer(
            "no puedes elegirte a ti mismo. (╥﹏╥)",
            show_alert=True
        )
        return

    await query.answer()

    # Si tiene escudo
    if objetivo["escudo"]:

        objetivo["escudo"] = False

        await query.message.reply_text(
            f"🛡️ ᛝ {nombre_usuario(objetivo)} "
            f"{objetivo['emoji']} tenía un escudo.\n\n"
            f"¡el escudo evitó el retroceso!"
        )

        await pasar_turno(context)
        return

    # Guardamos quién debe lanzar para retroceder
    partida["retroceso"] = {
        "jugador_id": objetivo["id"],
        "atacante_id": jugador_actual["id"],
        "turno_id": partida["turno_id"]
    }

    boton_dado = InlineKeyboardButton(
        "lanzar ‹𝟹",
        callback_data="juego:retroceso_dado"
    )

    teclado = InlineKeyboardMarkup([
        [boton_dado]
    ])

    await query.message.reply_text(
        f"🟠 ᛝ {nombre_usuario(jugador_actual)} "
        f"{jugador_actual['emoji']} ha elegido a "
        f"{nombre_usuario(objetivo)} {objetivo['emoji']}.\n\n"
        f"{nombre_usuario(objetivo)} {objetivo['emoji']}, "
        f"lanza el dado para saber cuánto retrocedes.",
        reply_markup=teclado
    )

    context.job_queue.run_once(
        tiempo_retroceso_agotado,
        60,
        data={
            "turno_id": partida["turno_id"],
            "jugador_id": objetivo["id"]
        }
    )


# =========================================================
# RETROCESO DE LA CASILLA 20
# =========================================================

async def lanzar_retroceso(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if not partida["activa"]:
        await query.answer(
            "no hay una partida activa. (╥﹏╥)",
            show_alert=True
        )
        return

    retroceso = partida.get("retroceso")

    if not retroceso:
        await query.answer(
            "este lanzamiento ya no está disponible.",
            show_alert=True
        )
        return

    if query.from_user.id != retroceso["jugador_id"]:
        await query.answer(
            "este dado no es para ti. (╥﹏╥)",
            show_alert=True
        )
        return

    await query.answer()

    # Invalidar temporizador
    partida["turno_id"] += 1

    jugador = None

    for participante in partida["jugadores"]:
        if participante["id"] == query.from_user.id:
            jugador = participante
            break

    if jugador is None:
        return

    resultado = random.randint(1, 6)

    usuario = nombre_usuario(jugador)

    if jugador["escudo"]:

        jugador["escudo"] = False

        await query.message.reply_text(
            f"🎲 . . . {usuario} {jugador['emoji']} "
            f"ha sacado un {resultado}.\n\n"
            f"🛡️ ᛝ pero tenía un escudo, así que "
            f"no retrocede."
        )

    else:

        posicion_anterior = jugador["posicion"]

        jugador["posicion"] = max(
            0,
            jugador["posicion"] - resultado
        )

        await query.message.reply_text(
            f"🎲 . . . {usuario} {jugador['emoji']} "
            f"ha sacado un {resultado}.\n\n"
            f"retrocede de la casilla {posicion_anterior} "
            f"a la casilla {jugador['posicion']}."
        )

    partida["retroceso"] = None

    await pasar_turno(context)


# =========================================================
# TIEMPO AGOTADO — RETROCESO
# =========================================================

async def tiempo_retroceso_agotado(context: ContextTypes.DEFAULT_TYPE):

    if not partida["activa"]:
        return

    retroceso = partida.get("retroceso")

    if not retroceso:
        return

    if retroceso["turno_id"] != partida["turno_id"]:
        return

    jugador = None

    for participante in partida["jugadores"]:
        if participante["id"] == retroceso["jugador_id"]:
            jugador = participante
            break

    if jugador is None:
        return

    usuario = nombre_usuario(jugador)

    # Si no lanzó, retrocede automáticamente 2
    if jugador["escudo"]:

        jugador["escudo"] = False

        await context.bot.send_message(
            chat_id=partida["chat_id"],
            text=(
                f"⏱️ ᛝ se acabó el tiempo de {usuario} "
                f"{jugador['emoji']}.\n\n"
                f"🛡️ ᛝ tenía un escudo, así que no retrocede."
            )
        )

    else:

        posicion_anterior = jugador["posicion"]

        jugador["posicion"] = max(
            0,
            jugador["posicion"] - 2
        )

        await context.bot.send_message(
            chat_id=partida["chat_id"],
            text=(
                f"⏱️ ᛝ se acabó el tiempo de {usuario} "
                f"{jugador['emoji']}.\n\n"
                f"retrocede automáticamente 2 casillas.\n\n"
                f"pasa de la casilla {posicion_anterior} "
                f"a la casilla {jugador['posicion']}."
            )
        )

    partida["retroceso"] = None

    await pasar_turno(context)

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

    # Comprobar que exista una partida
    if not partida["activa"]:
        await update.message.reply_text(
            "🎲 ᛝ no hay ninguna partida activa."
        )
        return

    # Cancelar partida
    partida["activa"] = False
    partida["chat_id"] = None
    partida["premio"] = 0
    partida["max_jugadores"] = 0
    partida["jugadores"] = []
    partida["estado"] = "esperando"
    partida["turno"] = 0
    partida["turno_id"] += 1
    partida["mensaje_turno"] = None

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

app.add_handler(
    CallbackQueryHandler(
        lanzar_dado,
        pattern=r"^juego:lanzar$"
    )
)

app.add_handler(
    CallbackQueryHandler(
        elegir_retroceso,
        pattern=r"^juego:retroceder:"
    )
)

app.add_handler(
    CallbackQueryHandler(
        lanzar_retroceso,
        pattern=r"^juego:retroceso_dado$"
    )
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
