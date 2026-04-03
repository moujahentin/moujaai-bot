from config import DELETE_AFTER_SECONDS, TRANSLATE_REACTIONS
from services.translator import translate_text


async def handle_raw_reaction_add(client, payload):
    if payload.user_id == client.user.id:
        return

    emoji = str(payload.emoji)
    if emoji not in TRANSLATE_REACTIONS or payload.guild_id is None:
        return

    guild = client.get_guild(payload.guild_id)
    if guild is None:
        return

    channel = guild.get_channel(payload.channel_id)
    if channel is None:
        channel = await client.fetch_channel(payload.channel_id)

    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception as exc:
        print(f"Message fetch error: {exc}")
        return

    if message.author.bot or not message.content.strip():
        return

    target = TRANSLATE_REACTIONS[emoji]

    try:
        translated_text = translate_text(message.content, target["lang"])
    except Exception as exc:
        print(f"Translation error: {exc}")
        return

    if not translated_text:
        return

    try:
        await message.reply(
            f"{emoji} **{target['label']}:** {translated_text}",
            mention_author=False,
            delete_after=DELETE_AFTER_SECONDS,
        )
    except Exception as exc:
        print(f"Send error: {exc}")
