import discord

class EmbedColors:
    SUCCESS = 0x00FF00
    ERROR = 0xFF0000
    INFO = 0x3498db
    WARNING = 0xFFA500
    MUSIC = 0x9b59b6

def create_music_embed(title: str, description: str = None, color: int = EmbedColors.MUSIC) -> discord.Embed:
    """Cria um embed para mensagens relacionadas a música"""
    embed = discord.Embed(
        title=f"🎵 {title}",
        description=description,
        color=color
    )
    embed.set_footer(text="Bot de Música")
    return embed

def create_error_embed(message: str) -> discord.Embed:
    """Cria um embed para mensagens de erro"""
    embed = discord.Embed(
        title="❌ Erro",
        description=message,
        color=EmbedColors.ERROR
    )
    return embed

def create_success_embed(message: str) -> discord.Embed:
    """Cria um embed para mensagens de sucesso"""
    embed = discord.Embed(
        title="✅ Sucesso",
        description=message,
        color=EmbedColors.SUCCESS
    )
    return embed

def create_info_embed(title: str, description: str) -> discord.Embed:
    """Cria um embed para mensagens informativas"""
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=EmbedColors.INFO
    )
    return embed
