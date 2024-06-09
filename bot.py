from dotenv import load_dotenv
load_dotenv()
import discord
from discord import Intents, Game
from discord.ext import commands
from os import environ, listdir
from typing import Optional
import asyncio
from cogs.giveawayCog import GiveawayJoinDynamicButton
import logging
import logging.handlers

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.handlers.RotatingFileHandler(
    filename='bot.log',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,
    backupCount=5
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('{asctime} {levelname:<8} {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

discord.utils.setup_logging(handler=console_handler)

class Bot(commands.Bot):
	def __init__(self,command_prefix: str,intents: Intents,activity: Optional[Game] = None):
		super().__init__(command_prefix=command_prefix,intents=intents,activity=activity)
	
	async def setup_hook(self):
		tasks = []
		for item in listdir('cogs'):
			if item.endswith('.py'):
				tasks.append(asyncio.create_task(self.load_extensions(f'cogs.{item.strip(".py")}')))
		asyncio.gather(*tasks)
		self.add_dynamic_items(GiveawayJoinDynamicButton)
	
	async def load_extensions(self, ext: str):
		await self.load_extension(ext)

bot = Bot(command_prefix='xd',intents=Intents(dm_messages = False, guild_messages = True,members = True,guilds = True,message_content = True),activity=Game(name="New commands! check them out"))

if __name__ == '__main__':
	try:
		asyncio.run(bot.start(environ['TOKEN']))
	except KeyboardInterrupt:
		asyncio.run(bot.close())
		logger.info(f"Closing bot, bot closed: {bot.is_closed()}")
		exit()