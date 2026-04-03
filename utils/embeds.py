import discord


def make_embed(title: str, description: str = "", color: int = 0x5865F2) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)
