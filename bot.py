from discord import Intents, Game
from discord.ext import commands
import discord
from os import environ
import asyncio
from dotenv import load_dotenv
load_dotenv()


bot = commands.Bot(command_prefix="xd",intents=Intents.all(),activity=Game(name="Check 'About me'"))
discord.utils.setup_logging()

async def main():
	# await bot.add_cog(RemindCog(bot))
	# await bot.add_cog(GiveawayCog(bot))
	# await bot.add_cog(RandomCog(bot))
	await bot.load_extension('cogs.randomCog')
	await bot.load_extension('cogs.giveawayCog')
	await bot.load_extension('cogs.reminderCog')
	
	await bot.start(environ['TOKEN'])

if __name__ == '__main__':
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		asyncio.run(bot.close())
		print("bot closed",bot.is_closed())
		exit()