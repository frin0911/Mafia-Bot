import os
import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv

load_dotenv()
intents = nextcord.Intents().default()
nextcord.Intents.members = True
bot = commands.Bot(command_prefix=os.getenv('PREFIX'),
                   case_insensitive=True,
                   intents=intents)


@bot.event
async def on_ready():
    print("Bot is running")


for e in [f for f in os.listdir('mafia') if f.endswith('.py')]:
    try:
        bot.load_extension(f'mafia.{e.replace(".py", "")}')
    except Exception as error:
        print(f'{e} 로드 실패.\n{error}')
bot.run(os.getenv('TOKEN'), reconnect=True)
