from dotenv import load_dotenv
load_dotenv()
from discord import Intents, Game
from discord.ext import commands
import discord
from os import environ
import asyncio
from cogs.giveawayCog import GiveawayJoinDynamicButton


discord.utils.setup_logging()

class Bot(commands.Bot):
	def __init__(self,command_prefix: str,intents: Intents,activity: Game = None):
		super().__init__(command_prefix=command_prefix,intents=intents,activity=activity)
	
	async def setup_hook(self):
		await bot.load_extension('cogs.randomCog')
		await bot.load_extension('cogs.giveawayCog')
		await bot.load_extension('cogs.reminderCog')
		await bot.load_extension('cogs.customEmbedCog')
		bot.add_dynamic_items(GiveawayJoinDynamicButton)

bot = Bot(command_prefix='xd',intents=Intents.all(),activity=Game(name="Check 'About me'"))

if __name__ == '__main__':
	try:
		asyncio.run(bot.start(environ['TOKEN']))
	except KeyboardInterrupt:
		asyncio.run(bot.close())
		print("bot closed",bot.is_closed())
		exit()