from discord import Intents, Game
from discord.ext.commands import Bot
import discord
from os import environ
import asyncio
from dotenv import load_dotenv
load_dotenv()

from cogs.reminder import RemindCog
from cogs.giveawayCog import GiveawayCog
from cogs.randomCog import RandomCog

bot = Bot(command_prefix="xd",intents=Intents.all(),activity=Game(name="Check 'About me'"))
discord.utils.setup_logging()
async def main():
	await bot.add_cog(RemindCog(bot))
	await bot.add_cog(GiveawayCog(bot))
	await bot.add_cog(RandomCog(bot))
	await bot.start(environ['TOKEN'])

if __name__ == '__main__':
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		asyncio.run(bot.close())
		print("bot closed",bot.is_closed())
		exit()