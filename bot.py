import os
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from utils.log_config import setup_logging
load_dotenv()
TOKEN = os.getenv('TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))

log = setup_logging()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    # test_guild = discord.Object(id=GUILD_ID) //Teste em servidor específico
    # await bot.tree.sync(guild=test_guild)
    await bot.tree.sync()
    log.info(f"Bot está pronto! Conectado como {bot.user}")

async def load_extensions():
    extensions = [
        'cogs.music',
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            log.info(f"✅ Extensão '{extension}' carregada com sucesso")
        except Exception as e:
            log.error(f"❌ Erro ao carregar extensão '{extension}': {e}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
