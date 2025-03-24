import importlib
import discord
from discord import app_commands, ui
from discord.ext import commands
from utils.bypassUrl import bypass
from utils.websiteSS import get_ss, BadURL, BadResponse
from utils.dearrow import dearrow, VideoNotFound
from utils import animalapi, translate, reverseImage
from typing import Literal, Optional, List, TYPE_CHECKING, Union
import os
import logging
from time import perf_counter
from asyncio import TimeoutError
import re
from io import BytesIO
from shazamio import Shazam, Serialize #reverse engineered shazam library. awesome
from shazamio.schemas.models import TrackInfo
from utils.sm_utils import caching
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
	from bot import UtilsBot

class ChunkedPaginator(ui.View):
	index = 0
	def __init__(self, itr: List[reverseImage.TinEyeResult], timeout: Optional[Union[int,float]] = None):
		self.chunked = list(discord.utils.as_chunks(itr,8))
		logger.debug(self.chunked)
		super().__init__(timeout=timeout)
		self.edit_children()

	def edit_children(self):
		self.go_first.disabled = self.index == 0
		self.go_back.disabled = self.index == 0
		self.go_foward.disabled = self.index == len(self.chunked)-1
		self.go_last.disabled = self.index == len(self.chunked)-1

	async def edit_embed(self, interaction: discord.Interaction):
		embed = discord.Embed(
			title = f'Page {self.index+1}',
			description = '\n'.join(f'- [URL]({result.url}) - [Backlink]({result.backlink}) - {result.date}' for result in self.chunked[self.index]),
			color = discord.Color.green()
		)
		embed.set_author(name='Using TinEye, click to see results on your browser',icon_url='https://i.imgur.com/O1LYRWf.png',url='https://tineye.com/search/'+self.chunked[0][0].query_hash)
		self.edit_children()
		await interaction.response.edit_message(embed=embed,view=self)

	@ui.button(label='<<',style=discord.ButtonStyle.primary)
	async def go_first(self, interaction: discord.Interaction, button: ui.Button):
		self.index = 0
		await self.edit_embed(interaction)

	@ui.button(label='<',style=discord.ButtonStyle.secondary)
	async def go_back(self, interaction: discord.Interaction, button: ui.Button):
		self.index -= 1
		await self.edit_embed(interaction)

	@ui.button(label='>',style=discord.ButtonStyle.secondary)
	async def go_foward(self, interaction: discord.Interaction, button: ui.Button):
		self.index += 1
		await self.edit_embed(interaction)

	@ui.button(label='>>',style=discord.ButtonStyle.primary)
	async def go_last(self, interaction: discord.Interaction, button: ui.Button):
		self.index = len(self.chunked)-1
		await self.edit_embed(interaction)

class RandomCog(commands.Cog):
	def __init__(self, bot: 'UtilsBot'):
		self.bot = bot
		self.shazam = Shazam()
		self.clickbait_ctx_menu = app_commands.ContextMenu(
			name = 'Remove clickbait',
			callback = self.remove_clickbait
		)
		self.translate_ctx_menu = app_commands.ContextMenu(
			name = 'Translate',
			callback = self.translate_text
		)
		self.shazam_ctx_menu = app_commands.ContextMenu(
			name = 'Shazam!',
			callback = self.shazam_song
		)
		self.reverse_image_ctx_menu = app_commands.ContextMenu(
			name = 'Reverse Image Search',
			callback = self.reverse_image_search
		)
		@self.clickbait_ctx_menu.error
		async def clickbait_ctx_menu_error(interaction, error):
			await self.cog_app_command_error(interaction,error)
		@self.translate_ctx_menu.error
		async def translate_ctx_menu_error(interaction, error):
			await self.cog_app_command_error(interaction,error)
		@self.shazam_ctx_menu.error
		async def shazam_ctx_menu_error(interaction, error):
			await self.cog_app_command_error(interaction,error)
		@self.reverse_image_ctx_menu.error
		async def reverse_image_ctx_menu_error(interaction, error):
			await self.cog_app_command_error(interaction,error)

		self.bot.tree.add_command(self.clickbait_ctx_menu)
		self.bot.tree.add_command(self.translate_ctx_menu)
		self.bot.tree.add_command(self.shazam_ctx_menu)
		self.bot.tree.add_command(self.reverse_image_ctx_menu)
	
	async def cog_unload(self):
		self.bot.tree.remove_command(self.clickbait_ctx_menu.name,type=self.clickbait_ctx_menu.type)
		self.bot.tree.remove_command(self.translate_ctx_menu.name,type=self.translate_ctx_menu.type)
		self.bot.tree.remove_command(self.shazam_ctx_menu.name,type=self.shazam_ctx_menu.type)
		self.bot.tree.remove_command(self.reverse_image_ctx_menu.name,type=self.reverse_image_ctx_menu.type)

	@app_commands.allowed_installs(guilds=True,users=True)
	@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
	@app_commands.checks.cooldown(rate=1,per=10,key=lambda i: i.user.id)
	async def reverse_image_search(self, interaction: discord.Interaction, msg: discord.Message):
		attachments = msg.attachments
		if not attachments:
			return await interaction.response.send_message('Message must contain at least 1 image',ephemeral=True)
		if len(attachments) > 10:
			logger.warning('It seems like Discord now supports more than 10 attachments in a single message')

		await interaction.response.defer(ephemeral=True)

		results = []
		for attachment in attachments:
			if attachment.content_type and attachment.content_type.startswith('image/'):
				try:
					results += await reverseImage.tin_eye(attachment.proxy_url)
				except reverseImage.NotFound: ...
		if not results:
			return await interaction.followup.send('Nothing found :(')
		view = ChunkedPaginator(results,300)
		embed = discord.Embed(
			title = f'Page 1',
			description = '\n'.join(f'- [URL]({result.url}) - [Backlink]({result.backlink}) - {result.date}' for result in results[:8]),
			color = discord.Color.green()
		)
		embed.set_author(name='Using TinEye, click to see results on your browser',icon_url='https://i.imgur.com/O1LYRWf.png',url='https://tineye.com/search/'+results[0].query_hash)
		await interaction.followup.send(view=view,embed=embed)

	@app_commands.allowed_installs(guilds=True,users=True)	
	@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
	@app_commands.checks.cooldown(rate=1,per=10,key=lambda i: i.user.id)
	async def shazam_song(self, interaction: discord.Interaction, msg: discord.Message):
		if not msg.attachments:
			await interaction.response.send_message('Message must contain at least 1 attachment',ephemeral=True)
			return
		if len(msg.attachments) > 10:
			logger.warning('It seems like Discord now supports more than 10 attachments in a single message')

		await interaction.response.defer(ephemeral=True)

		@caching
		async def get_shazam_song(o: bytes) -> Optional[TrackInfo]:
			data = await self.shazam.recognize(await attachment.read())
			if data.get('matches',[]):
				return Serialize.track(await self.shazam.track_about(data['matches'][0]['id']))

		results: List[TrackInfo] = []
		for attachment in msg.attachments:
			if not attachment.content_type or not re.search('(audio|video)',attachment.content_type):
				continue
			data = await get_shazam_song(await attachment.read())
			if data: results.append(data)
		if not results:
			await interaction.followup.send('No matches found :(')
			return
		embed = discord.Embed(
			description = '',
			color=discord.Color.blue()
		)
		embed.set_author(icon_url='https://fun.guimx.me/r/PFTT4RB5Bx.png?compress=false',name='Songs found')
		for result in results:
			info = ''
			#these links are sometimes wrong or just broken
			if result.youtube_link: info += f'{self.bot.custom_emojis.youtube} [YouTube]({result.youtube_link}) '
			if result.spotify_url: info += f'{self.bot.custom_emojis.spotify} [Ppotify]({result.spotify_url}) '
			if result.apple_music_url and result.apple_music_url != 'https://music.apple.com/subscribe':
				info += f'{self.bot.custom_emojis.apple_music} [Apple Music]({result.apple_music_url}) '
			if result.ringtone: info += f'{self.bot.custom_emojis.apple_music} [Ringtone]({result.ringtone}) '
			info += f'{self.bot.custom_emojis.shazam} [Shazam](https://shazam.com/track/{result.key}) '
			# if result.shazam_url: info += f'{self.bot.custom_emojis.shazam} [Shazam]({result.shazam_url}) ' #just returns /42
			embed.add_field(name=f'{results.index(result)+1}. {result.title}',value=info,inline=False)			
		await interaction.followup.send(embed=embed)

	@app_commands.allowed_installs(guilds=True,users=True)
	@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
	@app_commands.checks.cooldown(2,10,key=lambda i: i.user.id)
	async def remove_clickbait(self, interaction: discord.Interaction, msg: discord.Message):
		if (vid_re := re.search(r'(?P<url>http(s)?:\/\/(w{3}\.)?(youtu.be\/|youtube.com\/watch\?v=))(?P<video_id>[\w-]+)',msg.content)) is None:
			await interaction.response.send_message(
			'Message must contain a valid YouTube video link. Example links:\n'
			'`https://www.youtube.com/watch?v=6NQHtVrP3gE\n'+
			'https://youtu.be/6NQHtVrP3gE`',ephemeral=True)
			return
		await interaction.response.defer(ephemeral=True)
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

	@app_commands.allowed_installs(guilds=True,users=True)
	@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
	@app_commands.checks.cooldown(rate=1,per=5,key=lambda i: i.user.id)
	async def translate_text(self, interaction: discord.Interaction, msg: discord.Message):
		content = msg.content
		if not msg.content and len(msg.embeds) > 0 and msg.embeds[0].description:
			content = msg.embeds[0].description
		elif msg.reference and isinstance(msg.reference.resolved,discord.Message) and msg.reference.resolved.content: # msg.reference.resolved is always None. Probably something to do with my intents
			content = msg.reference.resolved.content
		if not content or not content.split():
			await interaction.response.send_message("Couldn't translate that message. Is there content there?",ephemeral=True)
			return
		await interaction.response.defer(ephemeral=True)
		try:
			translation = await translate.translate_google(target=interaction.locale.value,q=content)
		except translate.TranslationFailed:
			await interaction.followup.send("Something went wrong :(")
			return
		embed = discord.Embed(
			description=f'```{translation}```',
			color=discord.Color.green()
		)
		embed.set_thumbnail(url='https://fun.guimx.me/r/3797961.png?compress=false')
		embed.set_footer(text='Translated to your Discord language')
		await interaction.followup.send(embed=embed)

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
		owner = await self.bot.fetch_user(int(os.environ['OWNER_ID']))
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
		ephemeral = not isinstance(interaction.user,discord.User) and not interaction.permissions.embed_links
		await interaction.response.defer(ephemeral=ephemeral)
		height = int(resolution[:-1])
		width = int(height*(16/9))
		try:
			fbytes = await get_ss(link,width,height)
		except BadURL:
			await interaction.followup.send('Must be a valid link. Example links:\n`https://example.com`\n`http://example.com`')
		except BadResponse:
			await interaction.followup.send('An error happened :(')
		else:
			embed = discord.Embed(
				title = 'Screenshot of website',
				colour = discord.Colour.green()
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

	@app_commands.allowed_installs(guilds=True,users=True)
	@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
	@app_commands.command(name='about')
	async def about_bot(self, interaction: discord.Interaction):
		"""Information about UtilsBot"""
		e = discord.Embed(title='About UtilsBot!',
						description='UtilsBot is an open-source bot that serves quality of life features.\n This bot is and will always be free to use.',
						color=0xff0000) #red
		e.add_field(name=':bar_chart: Server Count',value=f'{len(self.bot.guilds)}',inline=False)
		e.add_field(name=':man_raising_hand: Approx. Individual User Count',value=f'{(await self.bot.application_info()).approximate_user_install_count or 0}',inline=False)
		e.add_field(name=':scroll: Author',value='[.guimx](https://guimx.me)',inline=False)
		e.add_field(name=':globe_with_meridians: Add App URL',value='[URL](https://discord.com/oauth2/authorize?client_id=778785822828265514)',inline=False)
		e.add_field(name=f'{self.bot.custom_emojis.github} Source Code',value='[GitHub](https://github.com/UnaPepsi/UtilsBot)',inline=False)
		e.add_field(name=':man_police_officer: ToS',value='https://guimx.me/rbot/tos',inline=False)
		e.add_field(name=':detective: Privacy Policy',value='https://guimx.me/rbot/privacypolicy',inline=False)
		await interaction.response.send_message(embed=e)

	@commands.command(name='mrl')
	async def reload_module(self, ctx: commands.Context):
		if not await self.bot.is_owner(ctx.author): #useless but just incase
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
		if not await self.bot.is_owner(ctx.author): #useless but just incase
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

	@commands.command(name='botsync')
	@commands.is_owner()
	async def sync_slash_commands(self, ctx: commands.Context):
		if not await self.bot.is_owner(ctx.author): #useless but just in case
			return
		await self.bot.tree.sync()
		await ctx.send("synced")
		
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
		
		
async def setup(bot: 'UtilsBot'):
	await bot.add_cog(RandomCog(bot))