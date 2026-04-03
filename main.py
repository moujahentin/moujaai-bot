import discord
from config import DISCORD_TOKEN, INTENTS
from events.reactions import handle_raw_reaction_add
from events.messages import handle_message

client = discord.Client(intents=INTENTS)

@client.event
async def on_ready():
    print(f"Bot connected as {client.user}")

@client.event
async def on_raw_reaction_add(payload):
    await handle_raw_reaction_add(client, payload)

@client.event
async def on_message(message):
    await handle_message(client, message)

client.run(DISCORD_TOKEN)
