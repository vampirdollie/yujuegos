import os
import logging
import random
import psycopg2

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =========================================================
# CONFIGURACIÓN
# =========================================================

TOKEN = os.getenv("TELEGRAM_TOKEN")

# Render nos dará este puerto automáticamente
PORT = int(os.environ.get("PORT", 10000))

# URL pública de Render
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

DATABASE_URL = os.environ.get("DATABASE_URL")

def _get_conn():
    return psycopg2.connect(
        DATABASE_URL,
        connect_timeout=10
    )

# =========================================================
# RULETA
# =========================================================

ruleta = {
    "activa": False,
    "id": None,
    "chat_id": None,
    "premio": 0,
    "duracion": 0,
    "participantes": [],
}

# =========================================================
# REFLEJOS
# =========================================================

reflejos = {
    "activa": False,
    "id": None,
    "chat_id": None,
    "premio": 0,
    "emojis": [],
    "correcto": None,
    "admin_id": None,
    "mensaje_id": None,
    "fase": None,
}

# =========================================================
# GUARDAR PARTIDA EN SUPABASE
# =========================================================

def guardar_partida():
    conn = None
    cur = None

    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO partidas (
                chat_id,
                premio,
                max_jugadores,
                estado,
                turno,
                turno_id,
                activa
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            partida["chat_id"],
            partida["premio"],
            partida["max_jugadores"],
            partida["estado"],
            partida["turno"],
            partida["turno_id"],
            partida["activa"]
        ))

        partida_id = cur.fetchone()[0]

        conn.commit()

        return partida_id

    except Exception as e:
        if conn:
            conn.rollback()

        logger.error(
            f"ERROR guardando partida en Supabase: {e}"
        )

        raise

    finally:
        if cur:
            cur.close()

        if conn:
            conn.close()

# =========================================================
# GUARDAR RULETA
# =========================================================

def guardar_ruleta():

    conn = None
    cur = None

    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO ruletas (
                chat_id,
                premio,
                duracion,
                activa
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            ruleta["chat_id"],
            ruleta["premio"],
            ruleta["duracion"],
            True
        ))

        ruleta_id = cur.fetchone()[0]

        conn.commit()

        return ruleta_id

    except Exception as e:

        if conn:
            conn.rollback()

        logger.error(
            f"ERROR guardando ruleta: {e}"
        )

        raise

    finally:

        if cur:
            cur.close()

        if conn:
            conn.close()

# =========================================================
# GUARDAR GANADOR DE RULETA
# =========================================================

def guardar_ganador_ruleta(jugador, premio):

    conn = None
    cur = None

    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO ganadores_ruleta (
                ruleta_id,
                chat_id,
                user_id,
                nombre,
                username,
                premio
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            ruleta["id"],
            ruleta["chat_id"],
            jugador["id"],
            jugador["nombre"],
            jugador["username"],
            premio
        ))

        conn.commit()

    except Exception as e:

        if conn:
            conn.rollback()

        logger.error(
            f"ERROR guardando ganador de ruleta: {e}"
        )

        raise

    finally:

        if cur:
            cur.close()

        if conn:
            conn.close()

# =========================================================
# GUARDAR GANADOR DE REFLEJOS
# =========================================================

def guardar_ganador_reflejos(jugador, premio):

    conn = None
    cur = None

    try:

        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO ganadores_ruleta (
                ruleta_id,
                chat_id,
                user_id,
                nombre,
                username,
                premio,
                tipo
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            None,
            reflejos["chat_id"],
            jugador["id"],
            jugador["nombre"],
            jugador["username"],
            premio,
            "reflejos"
        ))

        conn.commit()

    except Exception as e:

        if conn:
            conn.rollback()

        logger.error(
            f"ERROR guardando ganador de reflejos: {e}"
        )

        raise

    finally:

        if cur:
            cur.close()

        if conn:
            conn.close()

# =========================================================
# GUARDAR JUGADOR EN SUPABASE
# =========================================================

def guardar_jugador(partida_id, jugador):

    conn = _get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO jugadores (
            partida_id,
            user_id,
            nombre,
            username,
            emoji,
            posicion,
            escudo,
            perder_turno
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        partida_id,
        jugador["id"],
        jugador["nombre"],
        jugador["username"],
        jugador["emoji"],
        jugador["posicion"],
        jugador["escudo"],
        jugador["perder_turno"]
    ))

    conn.commit()
    cur.close()
    conn.close()

# =========================================================
# GUARDAR GANADOR EN SUPABASE
# =========================================================

def guardar_ganador(jugador):

    conn = None
    cur = None

    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO ganadores (
                partida_id,
                chat_id,
                user_id,
                nombre,
                username,
                emoji,
                premio
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            partida["id"],
            partida["chat_id"],
            jugador["id"],
            jugador["nombre"],
            jugador["username"],
            jugador["emoji"],
            partida["premio"]
        ))

        conn.commit()

        logger.info(
            f"GANADOR GUARDADO: "
            f"user_id={jugador['id']} "
            f"premio={partida['premio']}"
        )

    except Exception as e:

        if conn:
            conn.rollback()

        logger.error(
            f"ERROR GUARDANDO GANADOR: {e}"
        )

        raise

    finally:

        if cur:
            cur.close()

        if conn:
            conn.close()

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
    "id": None,
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

    await update.message.reply_photo(
        photo="yustart.jpg",
        caption=(
            "⠀⠀⠀⠀⠀ ⠀¡holi, jugador! (ㅅ´ ˘ `)\n\n"
            "⠀⠀⠀⠀⠀⠀aquí podrás participar\n"
            "⠀⠀⠀⠀⠀⠀en diferentes juegos.\n\n"
            "⠀⠀⠀๑ para conocer los comandos\n"
            "⠀⠀⠀⠀⠀⠀⠀⠀⠀usa /yucmds\n"
            "⠀⠀⠀\n"
        )
    )

# =========================================================
# /CMDS
# =========================================================

async def cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (
        "⠀⠀\n"

        "/yustart → bienvenida\n"
        "/yucmds → lista de comandos\n\n"

        "๑ 𝗝𝘂𝗲𝗴𝗼 𝗱𝗲 𝗠𝗲𝘀𝗮\n\n"
        "/juegomesa → crear una partida\n"
        "/unirmejuego → unirte a una partida\n"
        "/startjuego → iniciar la partida\n"
        "/cancelarjuego → cancelar la partida\n"
        "/limpiarmesa → borrar la partida guardada\n\n"

        "๑ 𝗥𝘂𝗹𝗲𝘁𝗮\n\n"
        "/yuruleta → iniciar una ruleta\n\n"

        "๑ 𝗥𝗲𝗳𝗹𝗲𝗷𝗼𝘀\n\n"
        "/reflejos → iniciar un juego de reflejos\n"
        "/stopreflejos → cancelar el juego de reflejos\n\n"

        "๑ 𝗛𝗶𝘀𝘁𝗼𝗿𝗶𝗮𝗹\n\n"
        "/yuhistorial → ver ganancias acumuladas\n"
        "/ganadores → ver ganadores del juego de mesa\n"
        "/limpiarhistorial → borrar el historial\n"
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

    # Máximo 11 jugadores
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

    # =====================================================
    # CREAR PARTIDA EN MEMORIA
    # =====================================================

    partida["chat_id"] = update.effective_chat.id
    partida["premio"] = robux
    partida["max_jugadores"] = max_jugadores
    partida["jugadores"] = []
    partida["estado"] = "esperando"
    partida["turno"] = 0
    partida["turno_id"] += 1
    partida["mensaje_turno"] = None
    partida["retroceso"] = None

    # =====================================================
    # GUARDAR EN SUPABASE
    # =====================================================

    try:

        partida["id"] = guardar_partida()

    except Exception as e:

        logger.error(
            f"ERROR EN JUEGOMESA AL GUARDAR: {e}"
        )

        # IMPORTANTE:
        # si falla la base de datos,
        # no dejamos una partida activa en memoria.
        partida["activa"] = False
        partida["chat_id"] = None
        partida["premio"] = 0
        partida["max_jugadores"] = 0
        partida["jugadores"] = []
        partida["estado"] = "esperando"
        partida["turno"] = 0
        partida["retroceso"] = None
        partida["id"] = None

        await update.message.reply_text(
            "🎲 ᛝ ocurrió un error al guardar la partida.\n\n"
            "revisa los logs del bot."
        )

        return

    # =====================================================
    # PARTIDA CREADA CORRECTAMENTE
    # =====================================================

    partida["activa"] = True

    logger.info(
        f"JUEGOMESA CREADO CORRECTAMENTE: "
        f"id={partida['id']} "
        f"chat={partida['chat_id']} "
        f"premio={robux} "
        f"jugadores={max_jugadores}"
    )

    # =====================================================
    # MENSAJE DE LA PARTIDA
    # =====================================================

    try:

        await update.message.reply_text(
            f"⠀⠀๑ 𝗝𝘂𝗲𝗴𝗼 𝗱𝗲 𝗠𝗲𝘀𝗮\n\n"
            f"⠀⠀premio: {robux} robux\n"
            f"⠀⠀jugadores: {max_jugadores}\n\n"
            f"⠀⠀usa /unirmejuego + emoji\n"
            f"⠀⠀para participar.\n\n"
            f"⠀⠀esperando jugadores..."
        )

    except Exception as e:

        logger.error(
            f"ERROR EN JUEGOMESA AL ENVIAR MENSAJE: {e}"
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

    # Crear jugador
    jugador = {
        "id": user_id,
        "nombre": update.effective_user.full_name,
        "username": update.effective_user.username,
        "emoji": emoji,
        "posicion": 0,
        "escudo": False,
        "perder_turno": False
    }

    # Guardar primero en Supabase
    try:

        guardar_jugador(
            partida["id"],
            jugador
        )

    except Exception as e:

        logger.error(
            f"ERROR GUARDANDO JUGADOR: {e}"
        )

        await update.message.reply_text(
            "🎲 ᛝ ocurrió un error al registrarte "
            "en la partida.\n\n"
            "inténtalo nuevamente."
        )

        return

    # Solo agregar a memoria si se guardó correctamente
    partida["jugadores"].append(jugador)

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
    # CASILLA 51 — GANADOR
    # =====================================================

    if nueva_posicion == 51:

        # =================================================
        # GUARDAR GANADOR
        # =================================================

        try:

            guardar_ganador(jugador_actual)

        except Exception as e:

            logger.error(
                f"ERROR GUARDANDO GANADOR: {e}"
            )

        await query.message.reply_text(
            f"ꉂ(˵˃ ᗜ ˂˵) ᛝ ¡{usuario} "
            f"{jugador_actual['emoji']} "
            f"ha llegado a la casilla 51!\n\n"
            f"¡ha ganado la partida! 🎉\n\n"
            f"premio: {partida['premio']} robux"
        )

        partida["activa"] = False
        partida["estado"] = "finalizada"
        partida["retroceso"] = None

        return

    # =====================================================
    # CASILLA 6 — AVANZA 3
    # =====================================================

    if jugador_actual["posicion"] == 6:

        posicion_especial = 9

        jugador_actual["posicion"] = posicion_especial

        await query.message.reply_text(
            f"🟣 ᛝ ¡AVANZA 3 CASILLAS! "
            f"⸜(｡˃ ᵕ ˂ )⸝\n\n"
            f"{usuario} {jugador_actual['emoji']} "
            f"avanza de la casilla 6 "
            f"a la casilla {posicion_especial}."
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

#=========================================================
# /LIMPIARMESA
# =========================================================

async def limpiarmesa(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Solo grupos
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "este comando solo puede utilizarse en un grupo."
        )
        return

    # Solo admins
    if not await es_admin(update, update.effective_user.id):
        await update.message.reply_text(
            "🎲 ᛝ solo los administradores pueden limpiar "
            "la mesa. ૮꒰ “. . ꒱ა"
        )
        return

    # Comprobar si existe una partida
    if not partida["activa"]:
        await update.message.reply_text(
            "🎲 ᛝ no hay ninguna partida activa que limpiar."
        )
        return

    # Eliminar la partida de Supabase
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM partidas WHERE id = %s",
        (partida["id"],)
    )

    conn.commit()
    cur.close()
    conn.close()

    # Limpiar completamente la partida
    partida["activa"] = False
    partida["chat_id"] = None
    partida["premio"] = 0
    partida["max_jugadores"] = 0
    partida["jugadores"] = []
    partida["estado"] = "esperando"
    partida["turno"] = 0
    partida["turno_id"] += 1
    partida["mensaje_turno"] = None
    partida["retroceso"] = None

    await update.message.reply_text(
        "🧹 ᛝ ¡mesa limpiada!\n\n"
        "se eliminó la partida actual "
        "y todos sus jugadores.\n\n"
        "ya puedes crear una nueva partida. 𖹭"
    )

# =========================================================
# /GANADORES
# =========================================================

async def ganadores(update: Update, context: ContextTypes.DEFAULT_TYPE):

    conn = None
    cur = None

    try:

        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                nombre,
                username,
                emoji,
                premio,
                fecha
            FROM ganadores
            WHERE chat_id = %s
            ORDER BY fecha DESC
            LIMIT 15
        """, (
            update.effective_chat.id,
        ))

        resultados = cur.fetchall()

    except Exception as e:

        logger.error(
            f"ERROR CONSULTANDO GANADORES: {e}"
        )

        await update.message.reply_text(
            "🏆 ᛝ no pude consultar el historial "
            "de ganadores."
        )

        return

    finally:

        if cur:
            cur.close()

        if conn:
            conn.close()

    # =====================================================
    # SIN GANADORES
    # =====================================================

    if not resultados:

        await update.message.reply_text(
            "🏆 ᛝ todavía no hay ganadores "
            "registrados en este grupo."
        )

        return

    # =====================================================
    # CREAR MENSAJE
    # =====================================================

    texto = (
        "🏆 ᛝ 𝗛𝗶𝘀𝘁𝗼𝗿𝗶𝗮𝗹 𝗱𝗲 𝗴𝗮𝗻𝗮𝗱𝗼𝗿𝗲𝘀\n\n"
    )

    for i, resultado in enumerate(resultados, start=1):

        nombre, username, emoji, premio, fecha = resultado

        if username:
            usuario = f"@{username}"
        else:
            usuario = nombre

        texto += (
            f"{i}. {usuario} {emoji}\n"
            f"   premio: {premio} robux\n"
            f"   fecha: {fecha.strftime('%d/%m/%Y')}\n\n"
        )

    await update.message.reply_text(
        texto
    )

# =========================================================
# /YURULETA
# =========================================================

async def yuruleta(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Solo grupos
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "este comando solo puede utilizarse en un grupo."
        )
        return

    # Solo admins
    if not await es_admin(update, update.effective_user.id):
        await update.message.reply_text(
            "🎲 ᛝ solo los administradores pueden iniciar "
            "una ruleta. ૮₍｡•̀ ﻌ •́｡₎ა"
        )
        return

    # Comprobar argumentos
    if len(context.args) != 2:
        await update.message.reply_text(
            "uso:\n"
            "/yuruleta <robux> <tiempo>\n\n"
            "ejemplo:\n"
            "/yuruleta 50 30"
        )
        return

    try:
        premio = int(context.args[0])
        duracion = int(context.args[1])

    except ValueError:
        await update.message.reply_text(
            "debes colocar números válidos."
        )
        return

    # Premio válido
    if premio <= 0:
        await update.message.reply_text(
            "el premio debe ser mayor que 0."
        )
        return

    # Tiempo válido
    if duracion <= 0:
        await update.message.reply_text(
            "el tiempo debe ser mayor que 0 segundos."
        )
        return

    # No permitir otra ruleta
    if ruleta["activa"]:
        await update.message.reply_text(
            "🎲 ᛝ ya hay una ruleta activa."
        )
        return

    # =====================================================
    # CREAR RULETA EN MEMORIA
    # =====================================================

    ruleta["activa"] = False
    ruleta["chat_id"] = update.effective_chat.id
    ruleta["premio"] = premio
    ruleta["duracion"] = duracion
    ruleta["participantes"] = []
    ruleta["id"] = None

    # =====================================================
    # GUARDAR RULETA EN SUPABASE
    # =====================================================

    try:

        ruleta["id"] = guardar_ruleta()

    except Exception as e:

        logger.error(
            f"ERROR EN YURULETA: {e}"
        )

        ruleta["activa"] = False
        ruleta["id"] = None
        ruleta["chat_id"] = None
        ruleta["premio"] = 0
        ruleta["duracion"] = 0
        ruleta["participantes"] = []

        await update.message.reply_text(
            "🎲 ᛝ ocurrió un error al crear la ruleta.\n\n"
            "revisa los logs del bot."
        )

        return

    # Activar solamente después de guardar correctamente
    ruleta["activa"] = True

    # =====================================================
    # BOTÓN PARA UNIRSE
    # =====================================================

    boton = InlineKeyboardButton(
        "unirme ‹𝟹",
        callback_data="ruleta:unirse"
    )

    teclado = InlineKeyboardMarkup([
        [boton]
    ])

    await update.message.reply_text(
        f"🎰 ᛝ ¡RULETA! ٩(^ᗜ^ )و ´-\n\n"
        f"premio: {premio} robux\n"
        f"tiempo: {duracion} segundos\n\n"
        f"pulsa el botón para entrar. ⤸",
        reply_markup=teclado
    )

    # =====================================================
    # PROGRAMAR FINALIZACIÓN
    # =====================================================

    context.job_queue.run_once(
        finalizar_ruleta,
        duracion,
        data={
            "ruleta_id": ruleta["id"]
        }
    )

# =========================================================
# /REFLEJOS
# =========================================================

async def reflejos_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Solo grupos
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "este comando solo puede utilizarse en un grupo."
        )
        return

    # Solo admins
    if not await es_admin(update, update.effective_user.id):
        await update.message.reply_text(
            "⚡ ᛝ solo los administradores pueden iniciar "
            "un juego de reflejos. ૮₍｡•̀ ﻌ •́｡₎ა"
        )
        return

    # Comprobar argumentos
    if len(context.args) != 1:
        await update.message.reply_text(
            "uso:\n"
            "/reflejos <robux>\n\n"
            "ejemplo:\n"
            "/reflejos 50"
        )
        return

    try:
        premio = int(context.args[0])

    except ValueError:
        await update.message.reply_text(
            "debes colocar un número válido."
        )
        return

    # Premio válido
    if premio <= 0:
        await update.message.reply_text(
            "el premio debe ser mayor que 0."
        )
        return

    # No permitir otro juego activo
    if reflejos["activa"]:
        await update.message.reply_text(
            "⚡ ᛝ ya hay un juego de reflejos activo."
        )
        return

    # Guardar configuración inicial
    reflejos["chat_id"] = update.effective_chat.id
    reflejos["premio"] = premio
    reflejos["admin_id"] = update.effective_user.id
    reflejos["emojis"] = []
    reflejos["correcto"] = None
    reflejos["mensaje_id"] = None
    reflejos["fase"] = "esperando_emojis"

    # Todavía no está activo en el grupo
    reflejos["activa"] = False

    # Intentar escribirle al admin por privado
    try:

        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=(
                "⚡ ᛝ 𝗝𝘂𝗲𝗴𝗼 𝗱𝗲 𝗿𝗲𝗳𝗹𝗲𝗷𝗼𝘀\n\n"
                f"๑ premio: {premio} robux\n\n"
                "envíame los 5 emojis que vamos a usar.\n"
                "๑ ejemplo:\n"
                "🐶 🐱 🐰 🐼 🦊"
            )
        )

        await update.message.reply_text(
            "⚡ ᛝ te envié un mensaje privado para configurar "
            "el juego."
        )

    except Exception as e:

        logger.error(
            f"ERROR ENVIANDO CONFIGURACIÓN DE REFLEJOS: {e}"
        )

        # Limpiar configuración
        reflejos["chat_id"] = None
        reflejos["premio"] = 0
        reflejos["admin_id"] = None
        reflejos["emojis"] = []
        reflejos["correcto"] = None
        reflejos["mensaje_id"] = None
        reflejos["fase"] = None

        await update.message.reply_text(
            "⚡ ᛝ no pude enviarte el mensaje privado.\n\n"
            "asegúrate de haber iniciado una conversación "
            "con el bot primero."
        )

# =========================================================
# RECIBIR EMOJIS DE REFLEJOS
# =========================================================

async def recibir_emojis_reflejos(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    # Solo mensajes privados
    if update.effective_chat.type != "private":
        return

    # Comprobar que haya una configuración esperando
    if reflejos["fase"] != "esperando_emojis":
        return

    # Solo el admin que inició el juego
    if update.effective_user.id != reflejos["admin_id"]:
        return

    texto = update.message.text.strip()

    # Separar los emojis por espacios
    emojis = texto.split()

    # Deben ser exactamente 5
    if len(emojis) != 5:
        await update.message.reply_text(
            "⚡ ᛝ necesito exactamente 5 emojis.\n\n"
            "envíalos separados por espacios.\n"
            "ejemplo:\n"
            "🐶 🐱 🐰 🐼 🦊"
        )
        return

    # No permitir emojis repetidos
    if len(set(emojis)) != 5:
        await update.message.reply_text(
            "⚡ ᛝ los 5 emojis deben ser diferentes."
        )
        return

    # Guardar emojis
    reflejos["emojis"] = emojis
    reflejos["fase"] = "elegir_correcto"

    # Crear botones para elegir el correcto
    botones = []

    for emoji in emojis:

        botones.append([
            InlineKeyboardButton(
                emoji,
                callback_data=f"reflejos:correcto:{emoji}"
            )
        ])

    teclado = InlineKeyboardMarkup(botones)

    await update.message.reply_text(
        "⚡ ᛝ perfecto.\n\n"
        "ahora elige cuál de estos 5 emojis "
        "será el correcto:",
        reply_markup=teclado
    )

# =========================================================
# ELEGIR EMOJI CORRECTO
# =========================================================

async def elegir_correcto_reflejos(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    # Solo aceptar durante la selección del emoji
    if reflejos["fase"] != "elegir_correcto":
        await query.answer(
            "esta configuración ya terminó. (╥﹏╥)",
            show_alert=True
        )
        return

    # Solo el admin que inició el juego
    if query.from_user.id != reflejos["admin_id"]:
        await query.answer(
            "solo el admin que creó el juego puede elegirlo.",
            show_alert=True
        )
        return

    # Obtener emoji seleccionado
    try:
        emoji_correcto = query.data.split(":", 2)[2]
    except (IndexError, AttributeError):
        await query.answer(
            "no pude identificar el emoji.",
            show_alert=True
        )
        return

    # Comprobar que el emoji esté entre los 5
    if emoji_correcto not in reflejos["emojis"]:
        await query.answer(
            "ese emoji no pertenece a este juego.",
            show_alert=True
        )
        return

    await query.answer(
        "¡emoji correcto seleccionado! ♡"
    )

    # Guardar el correcto
    reflejos["correcto"] = emoji_correcto

    # Activar juego
    reflejos["activa"] = True
    reflejos["fase"] = "activo"

    # =====================================================
    # CREAR BOTONES PARA EL GRUPO
    # =====================================================

    botones = []

    for emoji in reflejos["emojis"]:

        botones.append([
            InlineKeyboardButton(
                emoji,
                callback_data=f"reflejos:jugar:{emoji}"
            )
        ])

    teclado = InlineKeyboardMarkup(botones)

    # =====================================================
    # ENVIAR JUEGO AL GRUPO
    # =====================================================

    try:

        mensaje = await context.bot.send_message(
            chat_id=reflejos["chat_id"],
            text=(
                "⚡ ᛝ 𝗥𝗘𝗙𝗟𝗘𝗝𝗢𝗦\n"
                f"⠀๑ premio: {reflejos['premio']} robux\n\n"
                "elige el emoji correcto. . .\n"
                "¡rápido!"
            ),
            reply_markup=teclado
        )

        reflejos["mensaje_id"] = mensaje.message_id

    except Exception as e:

        logger.error(
            f"ERROR PUBLICANDO REFLEJOS EN EL GRUPO: {e}"
        )

        # Si no pudo publicarlo, cancelar la partida
        reflejos["activa"] = False
        reflejos["fase"] = None
        reflejos["chat_id"] = None
        reflejos["premio"] = 0
        reflejos["emojis"] = []
        reflejos["correcto"] = None
        reflejos["admin_id"] = None
        reflejos["mensaje_id"] = None

        await query.message.reply_text(
            "⚡ ᛝ ocurrió un error al publicar "
            "el juego en el grupo."
        )

        return

    # =====================================================
    # CONFIRMACIÓN PRIVADA AL ADMIN
    # =====================================================

    await query.message.reply_text(
        "⚡ ᛝ ¡listo!\n"
        "el juego ya fue publicado en el grupo. 𖹭"
    )

# =========================================================
# BOTÓN: JUGAR REFLEJOS
# =========================================================

async def jugar_reflejos(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    # Comprobar que el juego siga activo
    if not reflejos["activa"]:
        await query.answer(
            "este juego ya terminó. (╥﹏╥)",
            show_alert=True
        )
        return

    # Obtener el emoji seleccionado
    try:
        emoji_elegido = query.data.split(":", 2)[2]
    except (IndexError, AttributeError):
        await query.answer(
            "no pude identificar el emoji.",
            show_alert=True
        )
        return

    # Comprobar que el emoji pertenezca al juego
    if emoji_elegido not in reflejos["emojis"]:
        await query.answer(
            "ese emoji no pertenece a este juego.",
            show_alert=True
        )
        return

    # =====================================================
    # RESPUESTA INCORRECTA
    # =====================================================

    if emoji_elegido != reflejos["correcto"]:

        await query.answer(
            "❌ incorrecto, ¡sigue intentando!",
            show_alert=True
        )

        return

    # =====================================================
    # GANADOR
    # =====================================================

    # Desactivar inmediatamente
    # para evitar que dos personas ganen
    reflejos["activa"] = False
    reflejos["fase"] = "finalizado"

    jugador = {
        "id": query.from_user.id,
        "nombre": query.from_user.full_name,
        "username": query.from_user.username
    }

    premio = reflejos["premio"]

    if jugador["username"]:
        usuario = f"@{jugador['username']}"
    else:
        usuario = jugador["nombre"]

    # Responder al botón
    await query.answer(
        "⚡ ¡CORRECTO! ¡GANASTE! ♡",
        show_alert=True
    )

    # =====================================================
    # GUARDAR GANADOR
    # =====================================================

    try:

        guardar_ganador_reflejos(
            jugador,
            premio
        )

    except Exception as e:

        logger.error(
            f"ERROR GUARDANDO GANADOR DE REFLEJOS: {e}"
        )

        await context.bot.send_message(
            chat_id=reflejos["chat_id"],
            text=(
                "⚡ ᛝ ocurrió un error al guardar "
                "el resultado del juego."
            )
        )

        # Limpiar memoria
        reflejos["activa"] = False
        reflejos["fase"] = None
        reflejos["chat_id"] = None
        reflejos["premio"] = 0
        reflejos["emojis"] = []
        reflejos["correcto"] = None
        reflejos["admin_id"] = None
        reflejos["mensaje_id"] = None

        return

    # =====================================================
    # ANUNCIAR GANADOR
    # =====================================================

    await context.bot.send_message(
        chat_id=reflejos["chat_id"],
        text=(
            f"⚡ ᛝ ¡𝗥𝗘𝗙𝗟𝗘𝗝𝗢𝗦 𝗧𝗘𝗥𝗠𝗜𝗡𝗔𝗗𝗢!\n\n"
            f"𖹭 ganador: {usuario}\n"
            f"𖹭 premio: {premio} robux\n\n"
            f"¡qué reflejos! ᕙ(  •̀ ᗜ •́  )ᕗ"
        )
    )

    # =====================================================
    # LIMPIAR MEMORIA
    # =====================================================

    reflejos["chat_id"] = None
    reflejos["premio"] = 0
    reflejos["emojis"] = []
    reflejos["correcto"] = None
    reflejos["admin_id"] = None
    reflejos["mensaje_id"] = None

# =========================================================
# /STOPREFLEJOS
# =========================================================

async def stopreflejos(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Solo grupos
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "este comando solo puede utilizarse en un grupo."
        )
        return

    # Solo admins
    if not await es_admin(update, update.effective_user.id):
        await update.message.reply_text(
            "⚡ ᛝ solo los administradores pueden detener "
            "el juego de reflejos. ૮꒰ “. . ꒱ა"
        )
        return

    # Comprobar que exista un juego activo
    if not reflejos["activa"]:
        await update.message.reply_text(
            "⚡ ᛝ no hay ningún juego de reflejos activo."
        )
        return

    # Guardar el chat antes de limpiar
    chat_id = reflejos["chat_id"]

    # Detener juego
    reflejos["activa"] = False
    reflejos["fase"] = "cancelado"

    # Limpiar configuración
    reflejos["chat_id"] = None
    reflejos["premio"] = 0
    reflejos["emojis"] = []
    reflejos["correcto"] = None
    reflejos["admin_id"] = None
    reflejos["mensaje_id"] = None

    await update.message.reply_text(
        "🛑 ᛝ ¡juego de reflejos detenido!\n\n"
        "la partida ha sido cancelada."
    )

# =========================================================
# BOTÓN: UNIRSE A RULETA
# =========================================================

async def unirse_ruleta(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if not ruleta["activa"]:
        await query.answer(
            "esta ruleta ya terminó. (╥﹏╥)",
            show_alert=True
        )
        return

    user_id = query.from_user.id

    # Comprobar si ya está
    for participante in ruleta["participantes"]:

        if participante["id"] == user_id:

            await query.answer(
                "ya estás participando. ♡",
                show_alert=True
            )

            return

    # Crear jugador
    jugador = {
        "id": user_id,
        "nombre": query.from_user.full_name,
        "username": query.from_user.username
    }

    ruleta["participantes"].append(jugador)

    await query.answer(
        "¡te has unido a la ruleta! ♡"
    )

    if jugador["username"]:
        usuario = f"@{jugador['username']}"
    else:
        usuario = jugador["nombre"]

    await query.message.reply_text(
        f"🎰 ᛝ {usuario} se ha unido\n"
        f" con exito a la ruleta. 𖹭\n"
        f"participantes: {len(ruleta['participantes'])}"
    )

# =========================================================
# FINALIZAR RULETA
# =========================================================

async def finalizar_ruleta(context: ContextTypes.DEFAULT_TYPE):

    datos = context.job.data

    # Comprobar que sea la ruleta correcta
    if not ruleta["activa"]:
        return

    if datos["ruleta_id"] != ruleta["id"]:
        return

    # =====================================================
    # DESACTIVAR RULETA EN MEMORIA Y SUPABASE
    # =====================================================

    ruleta["activa"] = False

    conn = None
    cur = None

    try:

        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE ruletas
            SET activa = FALSE,
                finalizada_en = NOW()
            WHERE id = %s
        """, (
            ruleta["id"],
        ))

        conn.commit()

    except Exception as e:

        if conn:
            conn.rollback()

        logger.error(
            f"ERROR actualizando ruleta finalizada: {e}"
        )

    finally:

        if cur:
            cur.close()

        if conn:
            conn.close()

    # =====================================================
    # SIN PARTICIPANTES
    # =====================================================

    if not ruleta["participantes"]:

        await context.bot.send_message(
            chat_id=ruleta["chat_id"],
            text=(
                "🎰 ᛝ se acabó el tiempo.\n\n"
                "nadie se unió a la ruleta. (╥﹏╥)"
            )
        )

        # Limpiar memoria
        ruleta["chat_id"] = None
        ruleta["premio"] = 0
        ruleta["duracion"] = 0
        ruleta["participantes"] = []
        ruleta["id"] = None

        return

    # =====================================================
    # ELEGIR GANADOR
    # =====================================================

    ganador = random.choice(
        ruleta["participantes"]
    )

    premio = ruleta["premio"]

    if ganador["username"]:
        usuario = f"@{ganador['username']}"
    else:
        usuario = ganador["nombre"]

    # =====================================================
    # GUARDAR GANADOR
    # =====================================================

    try:

        guardar_ganador_ruleta(
            ganador,
            premio
        )

    except Exception as e:

        logger.error(
            f"ERROR guardando ganador: {e}"
        )

        await context.bot.send_message(
            chat_id=ruleta["chat_id"],
            text=(
                "🎰 ᛝ ocurrió un error al guardar "
                "el resultado de la ruleta."
            )
        )

        # Limpiar memoria aunque haya fallado el guardado
        ruleta["chat_id"] = None
        ruleta["premio"] = 0
        ruleta["duracion"] = 0
        ruleta["participantes"] = []
        ruleta["id"] = None

        return

    # =====================================================
    # ANUNCIAR GANADOR
    # =====================================================

    await context.bot.send_message(
        chat_id=ruleta["chat_id"],
        text=(
            f"🎰 ᛝ ¡resultado listo!\n\n"
            f"𖹭 ganador: {usuario}\n"
            f"𖹭 premio: {premio} robux\n\n"
            f"¡felicidades! ٩(ˊᗜˋ*)و "
        )
    )

    # =====================================================
    # LIMPIAR MEMORIA
    # =====================================================

    ruleta["chat_id"] = None
    ruleta["premio"] = 0
    ruleta["duracion"] = 0
    ruleta["participantes"] = []
    ruleta["id"] = None

# =========================================================
# /YUHISTORIAL
# =========================================================

async def yuhistorial(update: Update, context: ContextTypes.DEFAULT_TYPE):

    conn = None
    cur = None

    try:

        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                user_id,
                nombre,
                username,
                tipo,
                SUM(premio) AS total
            FROM ganadores_ruleta
            GROUP BY user_id, nombre, username, tipo
            ORDER BY total DESC
        """)

        resultados = cur.fetchall()

    except Exception as e:

        logger.error(
            f"ERROR consultando historial: {e}"
        )

        await update.message.reply_text(
            "๑ ᛝ ocurrió un error al consultar "
            "el historial."
        )

        return

    finally:

        if cur:
            cur.close()

        if conn:
            conn.close()

    # =====================================================
    # SIN GANADORES
    # =====================================================

    if not resultados:

        await update.message.reply_text(
            "๑ ᛝ todavía no hay ganadores registrados."
        )

        return

    # =====================================================
    # CREAR MENSAJE
    # =====================================================

    texto = (
        "⠀⠀𖹭 ⠀⠀⠀𝗛𝗶𝘀𝘁𝗼𝗿𝗶𝗮𝗹\n\n"
    )

    for resultado in resultados:

        user_id, nombre, username, tipo, total = resultado

        if username:
            usuario = f"@{username}"
        else:
            usuario = nombre

        # Identificar juego
        if tipo == "reflejos":
            icono = "𖹭"
            nombre_juego = "reflejos"
        else:
            icono = "๑"
            nombre_juego = "ruleta"

        texto += (
            f"{icono} {usuario} → {total} robux\n"
            f"   {nombre_juego}\n\n"
        )

    await update.message.reply_text(
        texto
    )

# =========================================================
# /LIMPIARHISTORIAL
# =========================================================

async def limpiarhistorial(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Solo grupos
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "este comando solo puede utilizarse en un grupo."
        )
        return

    # Solo admins
    if not await es_admin(update, update.effective_user.id):
        await update.message.reply_text(
            "🎲 ᛝ solo los administradores pueden "
            "limpiar el historial. ૮꒰ “. . ꒱ა"
        )
        return

    conn = None
    cur = None

    try:

        conn = _get_conn()
        cur = conn.cursor()

        cur.execute(
            "DELETE FROM ganadores_ruleta"
        )

        conn.commit()

    except Exception as e:

        if conn:
            conn.rollback()

        logger.error(
            f"ERROR limpiando historial: {e}"
        )

        await update.message.reply_text(
            "🎰 ᛝ ocurrió un error al limpiar "
            "el historial."
        )

        return

    finally:

        if cur:
            cur.close()

        if conn:
            conn.close()

    await update.message.reply_text(
        "🧹 ᛝ ¡historial limpiado!\n\n"
        "todos los registros de ganadores "
        "han sido eliminados."
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
    CommandHandler("limpiarmesa", limpiarmesa)
)

app.add_handler(
    CommandHandler("ganadores", ganadores)
)

app.add_handler(
    CommandHandler("yuruleta", yuruleta)
)

app.add_handler(
    CommandHandler("reflejos", reflejos_comando)
)

app.add_handler(
    CommandHandler("stopreflejos", stopreflejos)
)

app.add_handler(
    CommandHandler("yuhistorial", yuhistorial)
)

app.add_handler(
    CommandHandler("limpiarhistorial", limpiarhistorial)
)

app.add_handler(
    MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE,
        recibir_emojis_reflejos
    )
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

app.add_handler(
    CallbackQueryHandler(
        unirse_ruleta,
        pattern=r"^ruleta:unirse$"
    )
)

app.add_handler(
    CallbackQueryHandler(
        elegir_correcto_reflejos,
        pattern=r"^reflejos:correcto:"
    )
)

app.add_handler(
    CallbackQueryHandler(
        jugar_reflejos,
        pattern=r"^reflejos:jugar:"
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
