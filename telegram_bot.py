"""
Danny Toolkit — Telegram Bot.

Stuur berichten naar je Telegram bot en ontvang antwoorden
van de SwarmEngine. Admin-only beveiliging.

Gebruik:
    python telegram_bot.py
    Of: danny-bot  (als entry point)

Setup:
    1. Open Telegram, zoek @BotFather
    2. Stuur /newbot en volg de stappen
    3. Kopieer het token naar .env (TELEGRAM_BOT_TOKEN)
    4. Stuur /start naar @userinfobot voor je ID
    5. Zet je ID in .env (TELEGRAM_ADMIN_ID)
"""

import atexit
import asyncio
import io
import logging
import os
import sys
import time
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Windows UTF-8 fix
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# .env laden
load_dotenv(Path(__file__).parent / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_ID = int(
    os.getenv("TELEGRAM_ADMIN_ID", "0")
)

# Logging
logging.basicConfig(
    format="%(asctime)s [%(name)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("DannyBot")


def _shutdown():
    """Flush CorticalStack op shutdown."""
    try:
        from danny_toolkit.brain.cortical_stack import (
            get_cortical_stack,
        )
        get_cortical_stack().flush()
    except Exception:
        pass

atexit.register(_shutdown)


# ─── SINGLETON BRAIN ───────────────────────────────

_brain = None


def _get_brain():
    """Lazy-load PrometheusBrain (1x)."""
    global _brain
    if _brain is None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            from danny_toolkit.brain.trinity_omega import (
                PrometheusBrain,
            )
            _brain = PrometheusBrain()
        logger.info("PrometheusBrain geladen.")
    return _brain


# ─── ADMIN CHECK ───────────────────────────────────

def _is_admin(user_id: int) -> bool:
    """Controleer of de gebruiker de admin is."""
    return user_id == TELEGRAM_ADMIN_ID


# ─── BOT HANDLERS ─────────────────────────────────

async def cmd_start(update, context):
    """Handler voor /start command."""
    from telegram import Update

    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text(
            "Geen toegang. Deze bot is privé."
        )
        return

    await update.message.reply_text(
        "Danny Toolkit Bot\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Stuur een bericht en ik verwerk het via "
        "de SwarmEngine.\n\n"
        "Commando's:\n"
        "  /ping      — Response check\n"
        "  /status    — Systeem gezondheid\n"
        "  /agents    — Beschikbare agents\n"
        "  /heartbeat — Daemon status\n"
        "  /help      — Dit bericht\n"
    )


async def cmd_ping(update, context):
    """Handler voor /ping command — meet response tijd."""
    start = time.time()
    latency = (time.time() - start) * 1000
    nu = datetime.now().strftime("%H:%M:%S")
    await update.message.reply_text(
        f"PONG — {latency:.1f}ms\n"
        f"Tijd: {nu}\n"
        f"Bot is online."
    )


async def cmd_status(update, context):
    """Handler voor /status command."""
    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text(
            "Geen toegang."
        )
        return

    brain = _get_brain()

    # Governor info
    gov_status = "ONBEKEND"
    cb_status = "ONBEKEND"
    try:
        gov = brain.governor
        gov_status = "ACTIEF"
        failures = getattr(gov, "_api_failures", 0)
        max_f = getattr(gov, "MAX_API_FAILURES", 3)
        if failures >= max_f:
            cb_status = "OPEN (geblokkeerd)"
        elif failures > 0:
            cb_status = f"HALF_OPEN ({failures} fouten)"
        else:
            cb_status = "CLOSED (gezond)"
    except Exception:
        gov_status = "NIET BESCHIKBAAR"

    # Node stats
    actief = 0
    totaal = 0
    if hasattr(brain, "nodes"):
        totaal = len(brain.nodes)
        actief = sum(
            1 for n in brain.nodes.values()
            if n.status == "ACTIVE"
        )

    nu = datetime.now().strftime("%H:%M:%S")

    tekst = (
        "SYSTEEM STATUS\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Brain: {'ONLINE' if brain.is_online else 'OFFLINE'}\n"
        f"Governor: {gov_status}\n"
        f"Circuit Breaker: {cb_status}\n"
        f"Nodes: {actief}/{totaal} actief\n"
        f"Versie: 6.0.0\n"
        f"Tijd: {nu}\n"
    )
    await update.message.reply_text(tekst)


async def cmd_agents(update, context):
    """Handler voor /agents command."""
    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text(
            "Geen toegang."
        )
        return

    brain = _get_brain()

    if not hasattr(brain, "nodes") or not brain.nodes:
        await update.message.reply_text(
            "Geen agents beschikbaar."
        )
        return

    regels = ["AGENTS OVERZICHT\n━━━━━━━━━━━━━━━━━━━━\n"]

    for role, node in brain.nodes.items():
        role_naam = (
            role.value
            if hasattr(role, "value")
            else str(role)
        )
        tier_naam = (
            node.tier.value
            if hasattr(node.tier, "value")
            else str(node.tier)
        )
        status_icon = (
            "●" if node.status == "ACTIVE" else "○"
        )
        regels.append(
            f"{status_icon} {node.name}\n"
            f"  Rol: {role_naam} | "
            f"Tier: {tier_naam}\n"
            f"  Energie: {node.energy}% | "
            f"Taken: {node.tasks_completed}\n"
        )

    # Telegram bericht limiet is 4096 chars
    tekst = "\n".join(regels)
    if len(tekst) > 4000:
        tekst = tekst[:4000] + "\n\n...(afgekapt)"

    await update.message.reply_text(tekst)


async def cmd_heartbeat(update, context):
    """Handler voor /heartbeat command."""
    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text(
            "Geen toegang."
        )
        return

    tekst = (
        "HEARTBEAT DAEMON\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Geplande taken:\n"
        "  1. RAG Health Check (elke 120s)\n"
        "  2. System Heartbeat (elke 60s)\n\n"
        "Start de daemon met:\n"
        "  python daemon_heartbeat.py\n"
        "  Of: kies #52 in de launcher\n"
    )
    await update.message.reply_text(tekst)


async def handle_message(update, context):
    """Verwerk gewone tekstberichten via SwarmEngine."""
    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text(
            "Geen toegang. Deze bot is privé."
        )
        return

    tekst = update.message.text
    if not tekst or not tekst.strip():
        return

    # Toon "aan het typen..."
    await update.message.chat.send_action("typing")

    brain = _get_brain()

    from swarm_engine import SwarmEngine
    engine = SwarmEngine(brain=brain)

    start = time.time()
    try:
        payloads = await engine.run(tekst)
    except Exception as e:
        await update.message.reply_text(
            f"Fout in SwarmEngine: {e}"
        )
        return

    elapsed = round(time.time() - start, 1)

    if not payloads:
        await update.message.reply_text(
            "Geen resultaat ontvangen."
        )
        return

    # Stuur per payload een antwoord
    for p in payloads:
        antwoord = _format_payload(p)
        if antwoord:
            # Split lange berichten
            for deel in _split_bericht(antwoord):
                await update.message.reply_text(deel)

    # Executietijd
    await update.message.reply_text(
        f"[{elapsed}s | {len(payloads)} agent(s)]"
    )


def _format_payload(payload) -> str:
    """Formatteer een SwarmPayload voor Telegram."""
    agent = payload.agent
    ptype = payload.type
    tekst = str(payload.display_text).strip()

    if not tekst:
        tekst = str(payload.content).strip()

    if not tekst:
        return ""

    header = f"[{agent}]"

    if ptype == "code":
        return f"{header}\n```\n{tekst}\n```"
    elif ptype == "metrics":
        return f"{header} (metrics)\n{tekst}"
    elif ptype == "research_report":
        # Bronnen toevoegen als beschikbaar
        bronnen = ""
        if isinstance(payload.content, dict):
            src = payload.content.get(
                "sources_list", []
            )
            if src:
                bronnen = (
                    "\n\nBronnen:\n"
                    + "\n".join(
                        f"  • {s}" for s in src
                    )
                )
        return f"{header} (onderzoek)\n{tekst}{bronnen}"
    else:
        return f"{header}\n{tekst}"


def _split_bericht(
    tekst: str, limiet: int = 4000
) -> list:
    """Splits een bericht in stukken van max 4000 chars."""
    if len(tekst) <= limiet:
        return [tekst]

    delen = []
    while len(tekst) > limiet:
        # Zoek een goed breekpunt
        knip = tekst.rfind("\n", 0, limiet)
        if knip == -1:
            knip = limiet
        delen.append(tekst[:knip])
        tekst = tekst[knip:].lstrip("\n")
    if tekst:
        delen.append(tekst)
    return delen


# ─── NOTIFY FUNCTIE ────────────────────────────────

_bot_app = None


async def notify(bericht: str):
    """Stuur een notificatie naar de admin via Telegram.

    Gebruik vanuit andere modules:
        from telegram_bot import notify
        await notify("HeartbeatDaemon: taak voltooid")
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ADMIN_ID:
        return

    try:
        from telegram import Bot
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=TELEGRAM_ADMIN_ID,
            text=bericht,
        )
    except Exception as e:
        logger.error(f"Notificatie mislukt: {e}")


def notify_sync(bericht: str):
    """Synchrone wrapper voor notify().

    Gebruik:
        from telegram_bot import notify_sync
        notify_sync("Taak voltooid!")
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(notify(bericht))
        else:
            loop.run_until_complete(notify(bericht))
    except RuntimeError:
        asyncio.run(notify(bericht))


# ─── MAIN ──────────────────────────────────────────

def main():
    """Start de Telegram bot (polling)."""
    if (
        not TELEGRAM_BOT_TOKEN
        or TELEGRAM_BOT_TOKEN == "VULT-JE-TOKEN-IN"
    ):
        print(
            "\n  [FOUT] TELEGRAM_BOT_TOKEN niet ingesteld."
            "\n  Vul je token in .env in."
            "\n  Zie: telegram_bot.py header voor setup.\n"
        )
        return

    if TELEGRAM_ADMIN_ID == 0:
        print(
            "\n  [FOUT] TELEGRAM_ADMIN_ID niet ingesteld."
            "\n  Stuur /start naar @userinfobot in Telegram"
            "\n  en zet je ID in .env.\n"
        )
        return

    from telegram.ext import (
        ApplicationBuilder,
        CommandHandler,
        MessageHandler,
        filters,
    )

    print(
        "\n  Danny Toolkit Telegram Bot wordt gestart..."
        f"\n  Admin ID: {TELEGRAM_ADMIN_ID}\n"
    )

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # Command handlers
    application.add_handler(
        CommandHandler("start", cmd_start)
    )
    application.add_handler(
        CommandHandler("help", cmd_start)
    )
    application.add_handler(
        CommandHandler("ping", cmd_ping)
    )
    application.add_handler(
        CommandHandler("status", cmd_status)
    )
    application.add_handler(
        CommandHandler("agents", cmd_agents)
    )
    application.add_handler(
        CommandHandler("heartbeat", cmd_heartbeat)
    )

    # Gewone berichten
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    logger.info("Bot gestart. Wachten op berichten...")
    application.run_polling(
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
