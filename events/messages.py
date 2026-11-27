import asyncio
import logging
from pathlib import Path
import textwrap
import time

import discord
from services.tts_service import synthesize_tts, cleanup_file_later

from config import (
    ADMIN_USER_IDS,
    ASK_COOLDOWN_SECONDS,
    ASK_MAX_CHARS,
    ASK_MAX_CONCURRENT,
    AI_MODEL,
    AI_PROVIDER,
    COMMAND_PREFIX,
    TRANSLATE_REACTIONS,
)
from services.ai_client import ask_ai
from utils.embeds import make_embed
from utils.number_guess import (
    cancel_game,
    get_active_game,
    get_leaderboard,
    get_user_stats,
    make_guess,
    start_game,
)
from utils.status import get_system_status

logger = logging.getLogger(__name__)

user_last_request: dict[int, float] = {}
semaphore = asyncio.Semaphore(ASK_MAX_CONCURRENT)


def build_help_embed() -> discord.Embed:
    embed = make_embed(
        "Bot Help",
        "AI, translation reactions, number guessing game, and lab status tools.",
    )

    translation_lines = [f"{emoji} → {data['label']}" for emoji, data in TRANSLATE_REACTIONS.items()]
    embed.add_field(
        name="Translation reactions",
        value="\n".join(translation_lines) if translation_lines else "No reactions configured.",
        inline=False,
    )
    embed.add_field(
        name="General commands",
        value=(
            f"`{COMMAND_PREFIX}help`\n"
            f"`{COMMAND_PREFIX}ping`\n"
            f"`{COMMAND_PREFIX}ask <question>`\n"
            f"`{COMMAND_PREFIX}status`\n"
            f"`{COMMAND_PREFIX}join`\n"
            f"`{COMMAND_PREFIX}leave`\n"
            f"`{COMMAND_PREFIX}vask <question>`\n"
            f"`{COMMAND_PREFIX}say`"

        ),
        inline=False,
    )




    embed.add_field(
        name="Number guessing game",
        value=(
            f"`{COMMAND_PREFIX}guess_start easy|medium|hard`\n"
            f"`{COMMAND_PREFIX}guess <number>`\n"
            f"`{COMMAND_PREFIX}guess_hint`\n"
            f"`{COMMAND_PREFIX}guess_cancel`\n"
            f"`{COMMAND_PREFIX}guess_stats`\n"
            f"`{COMMAND_PREFIX}guess_top`"
        ),
        inline=False,
    )
    embed.set_footer(text=f"Provider: {AI_PROVIDER} • Model: {AI_MODEL} • Ask cooldown: {ASK_COOLDOWN_SECONDS}s")
    return embed



def check_cooldown(user_id: int) -> int:
    now = time.time()
    last = user_last_request.get(user_id)
    if last is not None:
        diff = now - last
        if diff < ASK_COOLDOWN_SECONDS:
            return int(ASK_COOLDOWN_SECONDS - diff)
    user_last_request[user_id] = now
    return 0



def chunk_text(text: str, limit: int = 1800) -> list[str]:
    chunks = textwrap.wrap(text, width=limit, replace_whitespace=False, drop_whitespace=False)
    return chunks or [text]


async def send_embed(channel, embed: discord.Embed, delete_after: int | None = None):
    await channel.send(embed=embed, delete_after=delete_after)


async def handle_help(message: discord.Message):
    await send_embed(message.channel, build_help_embed(), delete_after=60)


async def handle_ping(client, message: discord.Message):
    bot_latency = round(client.latency * 1000)

    embed = make_embed(
        "🏓 Pong",
        f"Bot latency: **{bot_latency} ms**"
    )

    await send_embed(message.channel, embed, delete_after=20)

async def handle_ask(message: discord.Message, content: str):
    prompt = content[len(f"{COMMAND_PREFIX}ask"):].strip()
    if not prompt:
        await message.channel.send(f"Usage: `{COMMAND_PREFIX}ask <question>`", delete_after=15)
        return

    if len(prompt) > ASK_MAX_CHARS:
        await message.channel.send(f"Too long. Max: {ASK_MAX_CHARS} chars.", delete_after=15)
        return

    remaining = check_cooldown(message.author.id)
    if remaining > 0:
        return

    async with semaphore:
        try:
            async with message.channel.typing():
                answer = await asyncio.to_thread(ask_ai, prompt)
        except Exception as exc:
            logger.error("AI request failed: %s", type(exc).__name__)
            await message.channel.send("⚠️ AI request failed.", delete_after=10)
            return

    for index, part in enumerate(chunk_text(answer), start=1):
        title = "AI Reply" if index == 1 else f"AI Reply ({index})"
        embed = make_embed(title, part)
        await send_embed(message.channel, embed)


async def handle_status(message: discord.Message):
    status = await asyncio.to_thread(get_system_status)
    embed = make_embed("Lab Status", f"Host: **{status['hostname']}**")
    embed.add_field(name="Uptime", value=status["uptime"], inline=True)
    embed.add_field(name="CPU", value=f"{status['cpu_percent']}%", inline=True)
    embed.add_field(
        name="Memory",
        value=f"{status['memory_used_gb']} / {status['memory_total_gb']} GB ({status['memory_percent']}%)",
        inline=False,
    )
    embed.add_field(
        name="Disk /",
        value=f"{status['disk_used_gb']} / {status['disk_total_gb']} GB ({status['disk_percent']}%)",
        inline=False,
    )
    embed.add_field(
        name="Local IPs",
        value="\n".join(status["local_ips"]) if status["local_ips"] else "Not found",
        inline=False,
    )
    embed.add_field(name="Tailscale IP", value=status["tailscale_ip"] or "Not found", inline=True)
    embed.add_field(name="discord-bot service", value=status["service_status"] or "unknown", inline=True)
    await send_embed(message.channel, embed)


async def handle_guess_start(message: discord.Message, content: str):
    parts = content.split(maxsplit=1)
    difficulty = parts[1].strip().lower() if len(parts) > 1 else "easy"
    result = start_game(message.author.id, str(message.author), difficulty)
    color = 0x57F287 if result.kind == "started" else 0xED4245
    await send_embed(message.channel, make_embed("Number Guess", result.message, color=color))


async def handle_guess(message: discord.Message, content: str):
    parts = content.split(maxsplit=1)
    if len(parts) < 2:
        await message.channel.send(f"Usage: `{COMMAND_PREFIX}guess <number>`", delete_after=15)
        return

    try:
        value = int(parts[1].strip())
    except ValueError:
        await message.channel.send("Βάλε έγκυρο αριθμό.", delete_after=15)
        return

    result = make_guess(message.author.id, str(message.author), value)
    color_map = {
        "win": 0x57F287,
        "lose": 0xED4245,
        "higher": 0xFEE75C,
        "lower": 0xFEE75C,
        "error": 0xED4245,
        "no_game": 0xED4245,
    }
    await send_embed(message.channel, make_embed("Number Guess", result.message, color_map.get(result.kind, 0x5865F2)))


async def handle_guess_hint(message: discord.Message):
    game = get_active_game(message.author.id)
    if not game:
        await send_embed(message.channel, make_embed("Number Guess", "Δεν έχεις ενεργό game.", 0xED4245), delete_after=15)
        return

    embed = make_embed(
        "Number Guess Hint",
        (
            f"Difficulty: **{game['difficulty']}**\n"
            f"Προσπάθειες που έκανες: **{game['attempts']}**\n"
            f"Προσπάθειες που μένουν: **{game['chances']}**"
        ),
        0xFEE75C,
    )
    await send_embed(message.channel, embed, delete_after=20)


async def handle_guess_cancel(message: discord.Message):
    result = cancel_game(message.author.id)
    color = 0xFEE75C if result.kind == "cancelled" else 0xED4245
    await send_embed(message.channel, make_embed("Number Guess", result.message, color), delete_after=15)


async def handle_guess_stats(message: discord.Message):
    stats = get_user_stats(message.author.id)
    if not stats:
        await send_embed(message.channel, make_embed("Guess Stats", "Δεν υπάρχουν stats ακόμα.", 0xED4245), delete_after=15)
        return

    wins = stats.get("wins", 0)
    games = stats.get("games_played", 0)
    win_rate = round((wins / games) * 100, 1) if games else 0
    embed = make_embed("Guess Stats", f"Stats για **{stats.get('username', message.author)}**")
    embed.add_field(name="Games", value=str(games), inline=True)
    embed.add_field(name="Wins", value=str(wins), inline=True)
    embed.add_field(name="Losses", value=str(stats.get("losses", 0)), inline=True)
    embed.add_field(name="Win rate", value=f"{win_rate}%", inline=True)
    embed.add_field(name="Best attempts", value=str(stats.get("best_attempts") or "-"), inline=True)
    embed.add_field(name="Best time", value=f"{stats.get('best_time_seconds') or '-'} s", inline=True)
    await send_embed(message.channel, embed)


async def handle_guess_top(message: discord.Message):
    leaderboard = get_leaderboard()
    if not leaderboard:
        await send_embed(message.channel, make_embed("Guess Top", "Δεν υπάρχει leaderboard ακόμα.", 0xED4245), delete_after=15)
        return

    lines = []
    for index, user in enumerate(leaderboard, start=1):
        lines.append(
            f"**#{index}** {user['username']} — best: {user['best_attempts']} attempts, {user.get('best_time_seconds', '-')} s, wins: {user['wins']}"
        )
    await send_embed(message.channel, make_embed("Guess Top", "\n".join(lines), 0x57F287))


async def handle_admins(message: discord.Message):
    if not ADMIN_USER_IDS:
        await send_embed(message.channel, make_embed("Admins", "Δεν έχουν οριστεί ADMIN_USER_IDS στο .env.", 0xED4245), delete_after=20)
        return

    admin_mentions = [f"<@{user_id}>" for user_id in sorted(ADMIN_USER_IDS)]
    await send_embed(message.channel, make_embed("Admins", "\n".join(admin_mentions), 0x5865F2), delete_after=20)


async def handle_message(client, message: discord.Message):
    if message.author.bot:
        return


    content = message.content.strip()

    if content.startswith(f"{COMMAND_PREFIX}say"):
        await handle_say(message, content)
        return

    if content.startswith(f"{COMMAND_PREFIX}vask"):
        await handle_vask(message, content)
        return


    if message.content.startswith(f"{COMMAND_PREFIX}join"):
        if not message.author.voice:
            await message.channel.send("Μπες σε voice πρώτα")
            return

        channel = message.author.voice.channel

        if message.guild.voice_client:
            await message.guild.voice_client.move_to(channel)
        else:
            await channel.connect()

        await message.channel.send(f"Μπήκα στο {channel.name}")
        return


    if message.content.startswith(f"{COMMAND_PREFIX}leave"):
        if message.guild.voice_client:
            await message.guild.voice_client.disconnect()
            await message.channel.send("Έφυγα από το voice")
        else:
            await message.channel.send("Δεν είμαι σε voice")
        return




    content = message.content.strip()
    lowered = content.lower()
    if lowered == f"{COMMAND_PREFIX}help":
        await handle_help(message)
        return

    if lowered == f"{COMMAND_PREFIX}ping":
        await handle_ping(client, message)
        return

    if lowered.startswith(f"{COMMAND_PREFIX}ask"):
        await handle_ask(message, content)
        return

    if lowered == f"{COMMAND_PREFIX}status":
        await handle_status(message)
        return

    if lowered.startswith(f"{COMMAND_PREFIX}guess_start"):
        await handle_guess_start(message, content)
        return

    if lowered.startswith(f"{COMMAND_PREFIX}guess "):
        await handle_guess(message, content)
        return

    if lowered == f"{COMMAND_PREFIX}guess_hint":
        await handle_guess_hint(message)
        return

    if lowered == f"{COMMAND_PREFIX}guess_cancel":
        await handle_guess_cancel(message)
        return

    if lowered == f"{COMMAND_PREFIX}guess_stats":
        await handle_guess_stats(message)
        return

    if lowered == f"{COMMAND_PREFIX}guess_top":
        await handle_guess_top(message)
        return

    if lowered == f"{COMMAND_PREFIX}admins":
        await handle_admins(message)
        return
async def ensure_voice(message: discord.Message):
    if not message.author.voice or not message.author.voice.channel:
        await message.channel.send("Μπες πρώτα σε voice channel.")
        return None

    target_channel = message.author.voice.channel
    vc = message.guild.voice_client

    if vc is None:
        vc = await target_channel.connect()
    elif vc.channel != target_channel:
        await vc.move_to(target_channel)

    return vc


async def play_audio_file(message: discord.Message, file_path: str) -> bool:
    source = None

    try:
        vc = await ensure_voice(message)

        if vc is None:
            Path(file_path).unlink(missing_ok=True)
            return False

        if vc.is_playing() or vc.is_paused():
            vc.stop()

        source = discord.FFmpegPCMAudio(file_path)
        loop = asyncio.get_running_loop()

        def after_playback(error):
            if error:
                logger.error(
                    "Voice playback failed: %s",
                    type(error).__name__
                )

            loop.call_soon_threadsafe(
                asyncio.create_task,
                cleanup_file_later(file_path)
            )

        vc.play(source, after=after_playback)
        return True

    except Exception as exc:
        logger.error(
            "Unable to start voice playback: %s",
            type(exc).__name__
        )

        if source is not None:
            source.cleanup()

        Path(file_path).unlink(missing_ok=True)
        await message.channel.send("Αποτυχία αναπαραγωγής ήχου.")
        return False


async def handle_say(message: discord.Message, content: str):
    text = content[len(f"{COMMAND_PREFIX}say"):].strip()

    if not text:
        await message.channel.send("Χρήση: `!say <κείμενο>`")
        return

    if len(text) > 300:
        await message.channel.send("Το κείμενο είναι πολύ μεγάλο. Μέχρι 300 χαρακτήρες.")
        return

    if not getattr(message.author, "voice", None):
        await message.channel.send("Μπες πρώτα σε voice channel.")
        return

    try:
        tts_file = await synthesize_tts(text)
    except Exception as exc:
        logger.error("TTS failed: %s", type(exc).__name__)
        await message.channel.send("Η υπηρεσία φωνής δεν είναι προσωρινά διαθέσιμη.")
        return

    if await play_audio_file(message, tts_file):
        await message.channel.send("🗣️ Αναπαραγωγή φωνής.")


async def handle_vask(message: discord.Message, content: str):
    prompt = content[len(f"{COMMAND_PREFIX}vask"):].strip()

    if not prompt:
        await message.channel.send("Χρήση: `!vask <ερώτηση>`")
        return

    await message.channel.send("🤖 Σκέφτομαι...")

    try:
        async with semaphore:
            reply = await asyncio.to_thread(ask_ai, prompt)
    except Exception as exc:
        logger.error("AI request failed: %s", type(exc).__name__)
        await message.channel.send("Η υπηρεσία AI δεν είναι προσωρινά διαθέσιμη.")
        return

    if not reply:
        await message.channel.send("Δεν πήρα απάντηση από το AI.")
        return

    shown_reply = reply[:1800]
    await message.channel.send(f"🤖 **AI:**\n{shown_reply}")

    if not getattr(message.author, "voice", None):
        return

    try:
        tts_file = await synthesize_tts(reply[:350])
        await play_audio_file(message, tts_file)
    except Exception as exc:
        logger.error("AI voice response failed: %s", type(exc).__name__)
        await message.channel.send("Η φωνητική απάντηση δεν είναι προσωρινά διαθέσιμη.")
