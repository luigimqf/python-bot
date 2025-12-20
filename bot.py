import os
import discord
import logging
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    # test_guild = discord.Object(id=GUILD_ID) //Teste em servidor específico
    # await bot.tree.sync(guild=test_guild)
    await bot.tree.sync()
    print(f"Bot está pronto! Conectado como {bot.user}")

async def load_extensions():
    extensions = [
        'cogs.music',
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            print(f"✅ Extensão '{extension}' carregada com sucesso")
        except Exception as e:
            print(f"❌ Erro ao carregar extensão '{extension}': {e}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
