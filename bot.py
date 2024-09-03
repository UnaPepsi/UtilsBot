from dotenv import load_dotenv
load_dotenv()
import discord
from discord import Intents, CustomActivity, BaseActivity
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

class UtilsBot(commands.Bot):
	def __init__(self,intents: Intents,activity: Optional[BaseActivity] = None) -> None:
		super().__init__(command_prefix=commands.when_mentioned_or('ub'),intents=intents,activity=activity,help_command=None)
	
	async def setup_hook(self) -> None:
		tasks = []
		for item in listdir('cogs'):
			if item.endswith('.py'):
				tasks.append(asyncio.create_task(self.load_extensions(f'cogs.{item.strip(".py")}')))
		asyncio.gather(*tasks)
		await self.load_extension('jishaku')
		self.add_dynamic_items(GiveawayJoinDynamicButton)
	
	async def load_extensions(self, ext: str) -> None:
		await self.load_extension(ext)

	async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
		if isinstance(error, (commands.CommandNotFound,commands.NotOwner)):
			return
		else: raise error

if __name__ == '__main__':
	bot = UtilsBot(intents=Intents(dm_messages = True, guild_messages = True,guilds = True),activity=CustomActivity(name="New commands! check them out"))
	try:
		asyncio.run(bot.start(environ['TOKEN']))
	except KeyboardInterrupt:
		asyncio.run(bot.close())
		logger.info(f"Closing bot, bot closed: {bot.is_closed()}")
		exit()