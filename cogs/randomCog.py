import importlib
import discord
from discord import app_commands
from discord.ext import commands
from utils.bypassUrl import bypass
from utils.websiteSS import get_ss, BadURL, BadResponse
from typing import Literal
import os
import logging
from time import perf_counter
from asyncio import TimeoutError
logger = logging.getLogger(__name__)

class RandomCog(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
	
	@commands.Cog.listener()
	async def on_ready(self):
		logger.info(f'Logged in as {self.bot.user}. Bot in {len(self.bot.guilds)} guilds')

	@app_commands.checks.cooldown(2,5,key=lambda i: i.user.id)
	@app_commands.command(name='bypassurl')
	async def bypassurl(self, interaction: discord.Interaction, url: str):
		"""Tries to unshorten a URL

		Args:
			url (str): The URL to unshorten
		"""
		await interaction.response.defer()
		try:
			await interaction.followup.send(await bypass(url))
		except (KeyError,TimeoutError):
			await interaction.followup.send('Could not unshorten that link')
		except ValueError:
			await interaction.followup.send('Invalid URL')

	@app_commands.command(name='pfp')
	async def pfp(self, interaction: discord.Interaction, user: discord.User):
		"""Shows someone's profile picture

		Args:
			user (discord.User): The user to check
		"""
		embed = discord.Embed(
			title = f"{user.display_name}'s profile picture",
			colour=discord.Colour.random())
		embed.set_image(url=user.display_avatar.url)
		await interaction.response.send_message(embed=embed)

	@app_commands.checks.cooldown(2,5,key=lambda i: i.user.id)
	@app_commands.command(name='suggestion')
	async def suggest(self, interaction: discord.Interaction, suggestion: str):
		"""Gives a suggestion to the bot's author :)

		Args:
			suggestion (str): The suggestion to give
		"""
		if len(suggestion) > 4000:
			await interaction.response.send_message("A suggestion can't be larger than 4000 characters :<")
			return
		owner = await self.bot.fetch_user(624277615951216643)
		dm_channel = await owner.create_dm()
		embed = discord.Embed(
			title = f'New suggestion!',
			description=suggestion,color=discord.Colour.green())
		embed.add_field(name='Author:',value=f'{interaction.user.mention}')
		await dm_channel.send(embed=embed)
		await interaction.response.send_message('Suggestion sent. Thank you :D',ephemeral=True)
	
	@app_commands.checks.cooldown(2,12,key=lambda i: i.user.id)
	@app_commands.command(name='screenshot')
	@app_commands.choices()
	async def screenshot(self, interaction: discord.Interaction, link: str,
					resolution: Literal['240p','360p','480p','720p','1080p','1440p','2160p'] = '1080p'):
		"""Takes a screenshot of a given website

		Args:
			link (str): The URL of the desired website screenshot
			resolution (Literal['240p','360p','480p','720p','1080p','1440p','2160p'], optional): The resolution of the screenshot. Defaults to 1080p.
		"""
		if interaction.channel is None: return
		if isinstance(interaction.channel,(discord.DMChannel,discord.GroupChannel)) or not interaction.channel.is_nsfw():
			await interaction.response.send_message('This command is only available for channels with NSFW enabled')
			return
		await interaction.response.defer()
		height = int(resolution[:-1])
		width = int(height*(16/9))
		try:
			fbytes = await get_ss(link,width,height)
		except BadURL:
			await interaction.followup.send('Must be a valid link. Valid link example: `http(s)://example.com`')
		except BadResponse:
			await interaction.followup.send('An error happened :(')
		else:
			embed = discord.Embed(
				title = f'Screenshot taken from {link}',
				colour = discord.Colour.green(),
			)
			embed.set_footer(text=f"If the resolution is not the one specified, it's because I couldn't screenshot normally :<")
			embed.set_image(url='attachment://image.png')
			await interaction.followup.send(file=discord.File(fbytes,filename='image.png'),embed=embed)

	async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
		if isinstance(error, discord.app_commands.errors.CommandOnCooldown):
			await interaction.response.send_message("Please don't spam this command :(",ephemeral=True)
		else: raise error

	@commands.command(name='mrl')
	async def reload_module(self, ctx: commands.Context):
		if ctx.author.id != 624277615951216643:
			return
		await ctx.send('trying')
		start = perf_counter()
		for item in ['cogs','utils']:
			for file in os.listdir(item):
				if file.endswith('.py'):
					# module = importlib.import_module
					importlib.reload(importlib.import_module(f'{item}.{file[:-3]}'))
					if item == 'cogs':
						await self.bot.reload_extension('cogs.'+file[:-3])
		await ctx.send(f'done. took {perf_counter()-start}s')

	@commands.command(name='rl')
	@commands.is_owner()
	async def reload_ext(self, ctx: commands.Context, ext: str):
		if ctx.author.id != 624277615951216643: #useless but just incase
			logger.warning(f'{ctx.author.id} somehow got here')
			return
		async def rl_ext(ext: str) -> None:
			try:
				await self.bot.reload_extension('cogs.'+ext)
				await ctx.send(f'Reloaded {ext}')
			except commands.ExtensionNotFound:
				await ctx.send(f"Couldn't reload {ext}. Typo?")
		if ext == 'all':
			for file in os.listdir('cogs'):
				if file.endswith('.py'):
					await rl_ext(file[:-3])
		else:
			await rl_ext(ext)
		
	@reload_ext.error
	async def reload_bad_command(self, ctx: commands.Context, error: commands.CommandError):
		if isinstance(error,commands.BadLiteralArgument):
			await ctx.send('bad argument')
			return
		if isinstance(error,commands.NotOwner):
			return
		raise error
		
	@commands.command(name='git')
	@commands.is_owner()
	async def git_cmd(self, ctx:commands.Context, *, command: str):
		if ctx.author.id != 624277615951216643:
			logger.warning(f'{ctx.author.id} somehow got here')
			return
		code = os.popen(f'git {command}').read()
		await ctx.send(code)

	@git_cmd.error
	async def git_bad_command(self, ctx: commands.Context, error: commands.CommandError):
		if isinstance(error,commands.NotOwner):
			return
		raise error
		
async def setup(bot: commands.Bot):
	await bot.add_cog(RandomCog(bot))