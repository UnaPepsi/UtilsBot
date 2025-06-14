from dotenv import load_dotenv
load_dotenv()
import discord
from discord import Intents, CustomActivity, BaseActivity, Emoji
from discord.ext import commands
from os import environ, listdir
from typing import Optional
import asyncio
from dataclasses import dataclass
from cogs.giveawayCog import GiveawayJoinDynamicButton
from cogs.customEmbedCog import EmbedMakerSaveButton, EmbedMakerClearButton, EmbedMakerDropdown
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

class UtilsBot(commands.Bot):
	def __init__(self,intents: Intents,activity: Optional[BaseActivity] = None) -> None:
		super().__init__(command_prefix=commands.when_mentioned_or('ub'),intents=intents,activity=activity,help_command=None)

	async def is_owner(self, user: discord.abc.User): #useless but just in case
		return environ['OWNER_ID'] == str(user.id)

	async def setup_hook(self) -> None:
		tasks = []
		for item in listdir('cogs'):
			if item.endswith('.py'):
				tasks.append(asyncio.create_task(self.load_extension(f'cogs.{item.strip(".py")}')))
		asyncio.gather(*tasks)
		await self.load_extension('jishaku')
		self.add_dynamic_items(GiveawayJoinDynamicButton,EmbedMakerSaveButton,EmbedMakerClearButton,EmbedMakerDropdown)
		emojis = {e.name:e for e in await self.fetch_application_emojis()}
		self.custom_emojis = MyEmojis(**{k: emojis[k] for k in MyEmojis.__annotations__})

	async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
		if isinstance(error, (commands.CommandNotFound,commands.NotOwner)):
			return
		else: raise error

@dataclass
class MyEmojis:
	youtube: Emoji
	spotify: Emoji
	apple_music: Emoji
	shazam: Emoji
	github: Emoji
	light: Emoji
	ash: Emoji
	dark: Emoji
	onyx: Emoji
	legacy: Emoji
	old: Emoji
	mobile_dark: Emoji

if __name__ == '__main__':
	discord.utils.setup_logging(handler=console_handler)
	bot = UtilsBot(intents=Intents(dm_messages = True, guild_messages = True,guilds = True),activity=CustomActivity(name=environ['ACTIVITY']))
	try:
		asyncio.run(bot.start(environ['TOKEN']))
	except KeyboardInterrupt:
		asyncio.run(bot.close())
		logger.info(f"Closing bot, bot closed: {bot.is_closed()}")
		exit()