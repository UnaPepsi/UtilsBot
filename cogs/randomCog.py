import importlib
import discord
from discord import app_commands, ui
from discord.ext import commands
from utils.bypassUrl import bypass
from utils.websiteSS import get_ss, BadURL, BadResponse
from utils.dearrow import dearrow, VideoNotFound
from utils import animalapi, translate
from typing import Literal, Sequence, Optional
import os
import logging
from time import perf_counter
from asyncio import TimeoutError
import re
from io import BytesIO
logger = logging.getLogger(__name__)

class Paginator(ui.View):
	message: Optional[discord.InteractionMessage] = None
	def __init__(self, user_view: int, seq: Sequence, starting_index = 0, timeout: Optional[int] = 180):
		super().__init__(timeout=timeout)
		self.user_view = user_view
		self.index = starting_index
		self.seq = seq
		self.edit_children()
	
	async def on_timeout(self):
		if self.message is not None:
			try:
				await self.message.edit(view=None)
			except discord.NotFound: ...

	async def update(self, interaction: discord.Interaction):
		embed = discord.Embed(
			title=f'Translation {self.index+1}/{len(self.seq)}',
			description=f'\n • _{self.seq[self.index]}_', #using "-" as vignette breaks italic formatting. Thanks Discord
			color=discord.Color.green()
		)
		embed.set_thumbnail(url='https://fun.guimx.me/r/3797961.png?compress=false')
		embed.set_footer(text='Translated to your Discord language')
		self.edit_children()
		await interaction.response.edit_message(embed=embed,view=self)

	def edit_children(self):
		self.go_first.disabled = self.seq[0] == self.seq[self.index]
		self.go_back.disabled = self.seq[0] == self.seq[self.index]
		self.go_forward.disabled = self.seq[-1] == self.seq[self.index]
		self.go_last.disabled = self.seq[-1] == self.seq[self.index]

	@ui.button(label='<<',style=discord.ButtonStyle.primary)
	async def go_first(self, interaction: discord.Interaction, button: ui.Button):
		self.index = 0
		await self.update(interaction)
	
	
	@ui.button(label='<',style=discord.ButtonStyle.secondary)
	async def go_back(self, interaction: discord.Interaction, button: ui.Button):
		self.index -= 1
		await self.update(interaction)
	
	
	@ui.button(label='>',style=discord.ButtonStyle.primary)
	async def go_forward(self, interaction: discord.Interaction, button: ui.Button):
		self.index += 1
		await self.update(interaction)
	
	
	@ui.button(label='>>',style=discord.ButtonStyle.primary)
	async def go_last(self, interaction: discord.Interaction, button: ui.Button):
		self.index = len(self.seq)-1
		self.edit_children()
		await self.update(interaction)	

class RandomCog(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.clickbait_ctx_menu = app_commands.ContextMenu(
			name = 'Remove clickbait',
			callback = self.remove_clickbait
		)
		self.translate_ctx_menu = app_commands.ContextMenu(
			name = 'Translate',
			callback = self.translate_text
		)
		@self.clickbait_ctx_menu.error
		async def translate_ctx_menu_error(interaction, error):
			await self.cog_app_command_error(interaction,error)
		@self.translate_ctx_menu.error
		async def clickbait_ctx_menu_error(interaction, error):
			await self.cog_app_command_error(interaction,error)

		self.bot.tree.add_command(self.clickbait_ctx_menu)
		self.bot.tree.add_command(self.translate_ctx_menu)
	
	async def cog_unload(self):
		self.bot.tree.remove_command(self.clickbait_ctx_menu.name,type=self.clickbait_ctx_menu.type)
		self.bot.tree.remove_command(self.translate_ctx_menu.name,type=self.translate_ctx_menu.type)
	
	@app_commands.checks.cooldown(2,10,key=lambda i: i.user.id)
	async def remove_clickbait(self, interaction: discord.Interaction, msg: discord.Message):
		if (vid_re := re.search(r'(?P<url>http(s)?:\/\/(w{3}\.)?(youtu.be\/|youtube.com\/watch\?v=))(?P<video_id>.*)',msg.content)) is None:
			await interaction.response.send_message(
			'Message must contain a valid YouTube video link. Example links:\n'
			'`https://www.youtube.com/watch?v=6NQHtVrP3gE\n'+
			'https://youtu.be/6NQHtVrP3gE`')
			return
		await interaction.response.defer()
		try:
			d = await dearrow(vid_re.group('video_id'))
		except VideoNotFound as e:
			await interaction.followup.send(str(e))
			return
		embed = discord.Embed(
			title=d.title or 'No video title found',
			description=f'Original Message: {msg.jump_url}',
			url=vid_re.group('url')+vid_re.group('video_id'),
			color=0xff0000)
		file = discord.utils.MISSING
		if d.thumbnail is not None:
			embed.set_image(url='attachment://image.png')
			file = discord.File(BytesIO(d.thumbnail),filename='image.png')
		else:
			embed.set_footer(text="No thumbnail found or hasn't been processed yet")
		embed.set_author(name='Attempt on removing clickbait. Using DeArrow API',url='https://dearrow.ajay.app/',icon_url='http://fun.guimx.me/r/9CPk7o.png?compress=false')
		await interaction.followup.send(embed=embed,file=file)

	@app_commands.checks.cooldown(rate=1,per=5,key=lambda i: i.user.id)
	async def translate_text(self, interaction: discord.Interaction, msg: discord.Message):
		await interaction.response.defer()
		translations = await translate.translate_text(target=interaction.locale.value[:2],q=msg.content)
		if len(translations) != 0:
			embed = discord.Embed(
				title=f'Translation 1/{len(translations)}',
				description=f'\n• _{translations[0]}_',
				color=discord.Color.green()
			)
			embed.set_thumbnail(url='https://fun.guimx.me/r/3797961.png?compress=false')
			embed.set_footer(text='Translated to your Discord language')
			view = Paginator(interaction.user.id,translations)
			await interaction.followup.send(embed=embed,view=view)
			view.message = await interaction.original_response()
		else:
			await interaction.followup.send('Something wrong happened D:')

	@commands.Cog.listener()
	async def on_ready(self):
		logger.info(f'Logged in as {self.bot.user}. Bot in {len(self.bot.guilds)} guilds')

	@app_commands.allowed_installs(guilds=True,users=True)
	@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
	@app_commands.checks.cooldown(2,5,key=lambda i: i.user.id)
	@app_commands.command(name='bypassurl')
	async def bypassurl(self, interaction: discord.Interaction, url: str):
		"""Tries to unshorten a URL

		Args:
			url (str): The URL to unshorten
		"""
		await interaction.response.defer(ephemeral=not interaction.is_guild_integration() and bool(interaction.guild))
		try:
			await interaction.followup.send(await bypass(url))
		except (KeyError,TimeoutError):
			await interaction.followup.send('Could not unshorten that link')
		except ValueError:
			await interaction.followup.send('Invalid URL')

	@app_commands.allowed_installs(guilds=True,users=True)
	@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
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

	@app_commands.allowed_installs(guilds=True,users=True)
	@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
	@app_commands.checks.cooldown(2,5,key=lambda i: i.user.id)
	@app_commands.command(name='suggestion')
	async def suggest(self, interaction: discord.Interaction, suggestion: str):
		"""Gives a suggestion to the bot's author :)

		Args:
			suggestion (str): The suggestion to give
		"""
		if len(suggestion) > 4000:
			await interaction.response.send_message("A suggestion can't be larger than 4000 characters :<",ephemeral=True)
			return
		owner = await self.bot.fetch_user(624277615951216643)
		embed = discord.Embed(
			title = 'New suggestion!',
			description=suggestion,
			color=discord.Colour.green())
		embed.add_field(name='Author:',value=f'{interaction.user.mention}')
		await owner.send(embed=embed)
		await interaction.response.send_message('Suggestion sent. Thank you :D',ephemeral=True)
	
	@app_commands.allowed_installs(guilds=True,users=True)
	@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
	@app_commands.checks.cooldown(2,12,key=lambda i: i.user.id)
	@app_commands.command(name='screenshot')
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
		ephemeral = not isinstance(interaction.user,discord.User) and interaction.user.resolved_permissions is not None and not interaction.user.resolved_permissions.embed_links
		await interaction.response.defer(ephemeral=ephemeral)
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

	@app_commands.allowed_installs(guilds=True,users=True)
	@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
	@app_commands.checks.cooldown(2,12,key=lambda i: i.user.id)
	@app_commands.command(name='cat')
	async def cat(self, interaction: discord.Interaction):
		"""Looks for a picture of a cat"""
		try:
			image_url = await animalapi.get_cat()
			embed = discord.Embed(
					title='Found cat!',
					color=discord.Color.random()
				)
			embed.set_image(url=image_url)
			await interaction.response.send_message(embed=embed)
		except animalapi.Error as e:
			await interaction.response.send_message(str(e),ephemeral=True)

	@app_commands.allowed_installs(guilds=True,users=True)
	@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
	@app_commands.checks.cooldown(2,12,key=lambda i: i.user.id)
	@app_commands.command(name='dog')
	async def dog(self, interaction: discord.Interaction):
		"""Looks for a picture of a dog"""
		try:
			image_url = await animalapi.get_dog()
			embed = discord.Embed(
					title='Found dog!',
					color=discord.Color.random()
				)
			embed.set_image(url=image_url)
			await interaction.response.send_message(embed=embed)
		except animalapi.Error as e:
			await interaction.response.send_message(str(e),ephemeral=True)

	async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
		if isinstance(error, discord.app_commands.errors.CommandOnCooldown):
			await interaction.response.send_message("Please don't spam this command :(",ephemeral=True)
		else: raise error

	@commands.command(name='mrl')
	async def reload_module(self, ctx: commands.Context):
		if ctx.author.id != 624277615951216643:
			return
		logger.info('Attempting to reload everything')
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
			logger.info(f'Attempting to reload extension: {ext}')
			try:
				await self.bot.reload_extension('cogs.'+ext)
				await ctx.send(f'Reloaded {ext}')
			except (commands.ExtensionNotFound,commands.ExtensionNotLoaded):
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
		
	@commands.command(name='source')
	@commands.is_owner()
	async def source_code(self, ctx:commands.Context):
		await ctx.reply('My source code is [here!](<https://github.com/UnaPepsi/UtilsBot>) :>',mention_author=False)
		
		
async def setup(bot: commands.Bot):
	await bot.add_cog(RandomCog(bot))