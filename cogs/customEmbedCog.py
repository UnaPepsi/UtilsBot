import discord
from discord import app_commands, ui
from discord.ext import commands
import re
from datetime import datetime
from typing import Union, Optional, Any, List, TYPE_CHECKING
from utils.customEmbed import CustomEmbed, BadTag, TagInUse, TooManyEmbeds
from utils import sm_utils
import time
import json
import logging
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
	from bot import UtilsBot

default_embed = discord.Embed(
	title='This is the title',
	description='This is the description, every field supports markdown, such as `this`, **this**, ~~this~~ ```python\n print("And many others")```'+
	'\nDescription can have a maximum of 4000 characters (technically 4096)',
	colour=discord.Colour.green(),
	url='https://discord.com/vanityurl/dotcom/steakpants/flour/flower/index11.html',
	timestamp=datetime.now(),
	)
default_embed.set_author(name="I'm the author",icon_url='https://i.imgur.com/UMQCyXX.gif',url='https://discord.com/vanityurl/dotcom/steakpants/flour/flower/index11.html')
default_embed.set_image(url='https://i.imgur.com/hrDkWqw.gif')
default_embed.set_thumbnail(url='https://i.imgur.com/HKG9dl8.gif')
default_embed.set_footer(text="I'm the footer! Next to me is the timestamp",icon_url='https://i.imgur.com/bxaPyZD.jpeg')
default_embed.add_field(name='Image',value='The big `GIF` is the `Image` field')
default_embed.add_field(name='Thumbnail',value='The small `GIF` is the `Thumbnail`')
default_embed.add_field(name='Inline',value='You can have up to `3 fields` in the `same line`!')
default_embed.add_field(name='Fields',value='You can have up to `25 fields` in total!')
default_embed.add_field(name='Size',value='Embeds can have up to `6000 total characters`')

async def embed_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
	async with CustomEmbed() as ce:
		tags_found = await ce.load_autocomplete(user=interaction.user.id,tag=current)
	if tags_found is None:
		return []
	return [
		app_commands.Choice(name=tag, value=tag)
		for tag in tags_found
	]

async def size_check(embed: discord.Embed, *args) -> bool:
	embed_size = len(embed.title or '')+len(embed.description or '')+len(embed.author.name or '')+len(embed.footer.text or '')
	for field in embed.fields:
		if field.name is not None and field.value is not None:
			embed_size += len(field.name) + len(field.value)
	for arg in args:
		embed_size += len(arg)
	return embed_size > 6000

class EmbedMakerDropdown(ui.DynamicItem[ui.Select], template=r'ce:dp:mid:(?P<msg_id>[0-9]+):uid:(?P<user_id>[0-9]+)'):
	def __init__(self, msg_id: int, user_id: int):
		super().__init__(ui.Select(
			placeholder='Edit the embed',custom_id=f'ce:dp:mid:{msg_id}:uid:{user_id}',options=[
				discord.SelectOption(label='General Embed',emoji='\N{PAGE FACING UP}',description='Edits general values of the embed',value='general'),
				discord.SelectOption(label='Images',emoji='\N{FRAME WITH PICTURE}',description="Edits the embed's shown images",value='img'),
				discord.SelectOption(label='Author',emoji='\N{MEMO}',description='Edits author values',value='author'),
				discord.SelectOption(label='Add field',emoji='<:plus_sign:1232874335107285063>',description='Adds a field to the embed',value='add'),
				discord.SelectOption(label='Remove field',emoji='<:minus:1232879295001526292>',description='Removes a field to the embed',value='remove'),
				discord.SelectOption(label='Edit field',emoji='\N{PENCIL}',description='Edits a field of the embed',value='edit'),
				discord.SelectOption(label='Footer',emoji='\N{FOOT}',description='Edits the footer',value='footer')
			]
		))
		self.msg_id = msg_id
		self.user_id = user_id
	
	@classmethod
	async def from_custom_id(cls, interaction: discord.Interaction, item: ui.Select, match: re.Match[str], /):
		msg_id = int(match['msg_id'])
		user_id = int(match['user_id'])
		return cls(msg_id,user_id)

	async def interaction_check(self, interaction: discord.Interaction):
		if interaction.user.id != self.user_id:
			await interaction.response.send_message('Only whoever ran this command can interact with it',ephemeral=True)
			return False
		return True
	
	async def callback(self, interaction: discord.Interaction):
		try: embed = interaction.message.embeds[0] if interaction.message is not None else [][0]
		except IndexError:
			await interaction.response.send_message("Something wrong happened",ephemeral=True)
			return
		place_holders: dict[str,dict[str,Optional[Union[str,int]]]] = {
			'general':{
				'title':embed.title,
				'description':embed.description,
				'url':embed.url,
			},
			'img':{
				'url':embed.image.url,
				'thumbnail':embed.thumbnail.url
			},
			'author':{
				'name':embed.author.name,
				'url':embed.author.url,
				'icon_url':embed.author.icon_url
			},
			'footer':{
				'text':embed.footer.text,
				'icon_url':embed.footer.icon_url,
				'timestamp':int(embed.timestamp.timestamp()) if embed.timestamp is not None else ''
			}
		}
		place_holders['general']['color'] = sm_utils.rgb_to_hex(embed.color.r,embed.color.g,embed.color.b) if embed.color is not None else None
		options: dict[str,ui.Modal] = {
			'general':EmbedPrompt(place_holders=place_holders["general"]),
			'img':EmbedURL(place_holders=place_holders["img"]),
			'author':EmbedAuthor(place_holders=place_holders["author"]),
			'add':EmbedFields.AddField(),
			'remove':EmbedFields.RemoveField(),
			'edit':EmbedFields.EditField(),
			'footer':EmbedFooter(place_holders=place_holders["footer"])
		}
		self.item.placeholder = 'Edit the embed'
		if interaction.message is None:
			await interaction.response.send_message('Something went wrong :(',ephemeral=True)
			return
		if interaction.is_guild_integration():
			await interaction.message.edit(view=self.view)
		await interaction.response.send_modal(options[self.item.values[0]])

class EmbedMakerSaveButton(ui.DynamicItem[ui.Button],template=r'ce:sbtn:mid:(?P<msg_id>[0-9]+):uid:(?P<user_id>[0-9]+)'):
	def __init__(self, msg_id: int, user_id: int):
		super().__init__(ui.Button(label='Save',style=discord.ButtonStyle.green,custom_id=f'ce:sbtn:mid:{msg_id}:uid:{user_id}'))
		self.msg_id = msg_id
		self.user_id = user_id

	@classmethod
	async def from_custom_id(cls, interaction: discord.Interaction, item: ui.Button, match: re.Match[str], /):
		msg_id = int(match['msg_id'])
		user_id = int(match['user_id'])
		return cls(msg_id,user_id)

	async def interaction_check(self, interaction: discord.Interaction):
		if interaction.user.id != self.user_id:
			await interaction.response.send_message('Only whoever ran this command can interact with it',ephemeral=True)
			return False
		return True
	
	async def callback(self, interaction: discord.Interaction):
		await interaction.response.send_modal(SaveEmbed())

class EmbedMakerClearButton(ui.DynamicItem[ui.Button],template=r'ce:cbtn:mid:(?P<msg_id>[0-9]+):uid:(?P<user_id>[0-9]+)'):
	def __init__(self, msg_id: int, user_id: int):
		super().__init__(ui.Button(label='Clear',style=discord.ButtonStyle.danger,custom_id=f'ce:cbtn:mid:{msg_id}:uid:{user_id}'))
		self.msg_id = msg_id
		self.user_id = user_id

	@classmethod
	async def from_custom_id(cls, interaction: discord.Interaction, item: ui.Button, match: re.Match[str], /):
		msg_id = int(match['msg_id'])
		user_id = int(match['user_id'])
		return cls(msg_id,user_id)

	async def interaction_check(self, interaction: discord.Interaction):
		if interaction.user.id != self.user_id:
			await interaction.response.send_message('Only whoever ran this command can interact with it',ephemeral=True)
			return False
		return True

	async def callback(self, interaction: discord.Interaction):
		await interaction.response.edit_message(embed=discord.Embed(description='Empty embed'))

class EmbedMaker(ui.View):
	def __init__(self, msg_id: int, user_id: int):
		super().__init__(timeout=None)
		self.user_id = user_id
		self.add_item(EmbedMakerDropdown(msg_id,user_id))
		self.add_item(EmbedMakerSaveButton(msg_id,user_id))
		self.add_item(EmbedMakerClearButton(msg_id,user_id))
	
	async def interaction_check(self, interaction: discord.Interaction):
		print(interaction.user.id,self.user_id)
		if interaction.user.id != self.user_id:
			await interaction.response.send_message('Only whoever ran this command can interact with it')
			return False
		return True

class EmbedFields:
	class AddField(ui.Modal,title='Add a field!'):
		name_ = ui.TextInput(
			label = 'Name',style=discord.TextStyle.short,
			required=False,max_length=256,placeholder='The name/title of the field. Up to 256 characters'
		)
		value_ = ui.TextInput(
			label = 'Value',style=discord.TextStyle.long,
			required=False,max_length=1024,placeholder='The field text value. Up to 1024 characters'
		)
		inline_ = ui.TextInput(
			label='Inline',style=discord.TextStyle.short,
			required=False,placeholder='Type whatever to disable'
		)
		async def on_submit(self, interaction: discord.Interaction):
			try: embed = interaction.message.embeds[0] if interaction.message is not None else [][0]
			except IndexError:
				await interaction.response.send_message("Something wrong happened",ephemeral=True)
			if len(embed.fields) > 24:
				await interaction.response.send_message('Discord limits up to 25 fields maximum',ephemeral=True)
				return
			embed.add_field(name=self.name_.value,value=self.value_.value,inline=self.inline_.value=='')
			if await size_check(embed):
				await interaction.response.send_message("Discord limits embeds not to be larger than 6000 characters in total",ephemeral=True)
				return
			await interaction.response.edit_message(embed=embed)
	class RemoveField(ui.Modal,title='Removes a field'):
		index_ = ui.TextInput(
			label = 'Index', style=discord.TextStyle.short,
			required=True,placeholder='The index number of the field to remove (starts at 1)'
		)
		async def on_submit(self, interaction: discord.Interaction):
			try:
				if interaction.message is None: raise IndexError
				await interaction.response.edit_message(embed=interaction.message.embeds[0].remove_field(int(self.index_.value)-1))
			except IndexError:
				await interaction.response.send_message("Something wrong happened",ephemeral=True)
			except ValueError:
				await interaction.response.send_message("Must be a valid number",ephemeral=True)
	class EditField(ui.Modal,title='Edits a specific field'):
		index_ = ui.TextInput(
			label = 'Index',style = discord.TextStyle.short,
			required=True,placeholder='The index number of the field to edit (starts at 1)'
		)
		name_ = ui.TextInput(
			label = 'Name',style=discord.TextStyle.short,
			required=False,placeholder='The name/title of the field. Up to 256 characters',
			max_length=256
		)
		value_ = ui.TextInput(
			label = 'Value',style = discord.TextStyle.long,
			required=False,placeholder='The field text value. Up to 1024 characters',
			max_length=1024
		)
		inline_ = ui.TextInput(
			label = 'Inline',style=discord.TextStyle.short,
			required=False,placeholder='Type whatever to disable'
		)
		#can't autocomplete :(
		async def on_submit(self, interaction: discord.Interaction):
			try:
				if interaction.message is None: raise IndexError
				await interaction.response.edit_message(embed=interaction.message.embeds[0].set_field_at(index=int(self.index_.value)-1,
														name=self.name_.value,value=self.value_.value,
														inline=self.inline_.value==''))
			except IndexError: await interaction.response.send_message("Something wrong happened :(",ephemeral=True)
		
class EmbedAuthor(ui.Modal,title='Edit the author!'):
	name_ = ui.TextInput(
		label = 'Name',style=discord.TextStyle.short,
		required=False,max_length=256,placeholder='The name of the author. Up to 256 characters'
	)
	url_ = ui.TextInput(
		label = 'URL',style=discord.TextStyle.short,
		required = False,placeholder='Must be HTTP(S) format'
	)
	icon_url_ = ui.TextInput(
		label = 'Icon URL', style= discord.TextStyle.short,
		required=False,placeholder='Must be HTTP(S) format'
	)
	def __init__(self, place_holders: dict[str, Any]):
		super().__init__()
		self.name_.default = place_holders['name']
		self.url_.default = place_holders['url']
		self.icon_url_.default = place_holders['icon_url']
	async def on_submit(self, interaction: discord.Interaction):
		valid_url = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
		url,icon_url = None,None
		if valid_url.match(self.icon_url_.value):
			icon_url = self.icon_url_.value
		if valid_url.match(self.url_.value):
			url = self.url_.value
		try:
			embed = interaction.message.embeds[0] if interaction.message is not None else [][0]
		except IndexError:
			await interaction.response.send_message("Something wrong happened",ephemeral=True)
		embed.set_author(name=self.name_.value,url=url,icon_url=icon_url) if self.name_.value != '' else embed.remove_author()
		if await size_check(embed):
			await interaction.response.send_message("Discord limits embeds not to be larger than 6000 characters in total",ephemeral=True)
			return
		await interaction.response.edit_message(embed=embed)
class EmbedFooter(ui.Modal,title='Edit the footer!'):
	text_ = ui.TextInput(
		label = 'Text',style=discord.TextStyle.short,
		required=False,placeholder="Footer's text. Up to 2048 characters",max_length=2048
	)
	icon_url_ = ui.TextInput(
		label = 'Icon URL',style=discord.TextStyle.short,
		required=False,placeholder='Must be HTTP(S) format (Text label is required for this)'
	)
	timestamp_ = ui.TextInput(
		label = 'Timestamp',style=discord.TextStyle.short,
		required=False,placeholder=f'Must be in timestamp format (E.g. {int(time.time())})'
	)
	def __init__(self, place_holders: dict[str,Any]):
		super().__init__()
		self.text_.default = place_holders['text']
		self.icon_url_.default = place_holders['icon_url']
		self.timestamp_.default = place_holders['timestamp']
	async def on_submit(self, interaction: discord.Interaction):
		valid_url = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
		icon_url = None
		if valid_url.match(self.icon_url_.value):
			icon_url = self.icon_url_.value
		try:
			embed = interaction.message.embeds[0] if interaction.message is not None else [][0]
		except IndexError:
			await interaction.response.send_message("Something wrong happened",ephemeral=True)
		embed.set_footer(text=self.text_.value,icon_url=icon_url)
		if await size_check(embed):
			await interaction.response.send_message("Discord limits embeds not to be larger than 6000 characters in total",ephemeral=True)
			return
		try: embed.timestamp = datetime.fromtimestamp(int(self.timestamp_.value))
		except (ValueError,OSError): embed.timestamp = None
		await interaction.response.edit_message(embed=embed)
class EmbedURL(ui.Modal,title='Edit the images!'):
	url_ = ui.TextInput(
		label = 'Image URL',style=discord.TextStyle.short,
		required = False,placeholder = 'Must be HTTP(S) format')
	thumbnail_ = ui.TextInput(
		label = 'Thumbnail URL',style=discord.TextStyle.short,
		required = False,placeholder = 'Must be HTTP(S) format')
	def __init__(self, place_holders: dict[str,Any]):
		super().__init__()
		self.url_.default = place_holders['url']
		self.thumbnail_.default = place_holders['thumbnail']
	async def on_submit(self, interaction: discord.Interaction):
		valid_url = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
		try:
			embed = interaction.message.embeds[0] if interaction.message is not None else [][0]
		except IndexError:
			await interaction.response.send_message("Something wrong happened",ephemeral=True)
		if valid_url.match(self.url_.value):
			embed.set_image(url=self.url_.value)
		else:
			embed.set_image(url=None)
		if valid_url.match(self.thumbnail_.value):
			embed.set_thumbnail(url=self.thumbnail_.value)
		else:
			embed.set_thumbnail(url=None)
		await interaction.response.edit_message(embed=embed)
class EmbedPrompt(ui.Modal,title='Edit the embed!'):
	title_ = ui.TextInput(
		label = 'Title',style=discord.TextStyle.short,max_length=256,
		required = False,placeholder = 'Your title here')
	description_ = ui.TextInput(
		label = 'Description',style=discord.TextStyle.long,
		required = False,placeholder = 'Your description here. Up to 4000 characters',max_length=4000)
	url_ = ui.TextInput(
		label = 'Title URL',style=discord.TextStyle.short,
		required = False,placeholder = 'Must be HTTP(S) format')
	color_ = ui.TextInput(
		label= 'Color',style=discord.TextStyle.long,
		required=False,placeholder='Must be Hex (#FFFFFF) or RGB (255,255,255). Some common colors such as "red" or "white" are fine'
	)
	def __init__(self, place_holders: dict[str,Any]):
		super().__init__()
		self.title_.default = place_holders['title']
		self.description_.default = place_holders['description']
		self.url_.default = place_holders['url']
		self.color_.default = place_holders['color']
	async def on_submit(self, interaction: discord.Interaction):
		if not (self.title_.value or self.description_.value or self.url_.value):
			await interaction.response.send_message("Invalid embed!",ephemeral=True)
			return
		valid_url = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
		if not self.color_.value.isdigit():
			try:  color_sel = sm_utils.hex_colors[self.color_.value] if self.color_.value in list(sm_utils.hex_colors) else int(self.color_.value[1:],16)
			except ValueError: color_sel = None
			try: color_sel = sm_utils.rgb_to_hex(*self.color_.value.split(',',3))
			except (TypeError,ValueError): ...
		else: color_sel = int(self.color_.value)
		try: embed = interaction.message.embeds[0] if interaction.message is not None else [][0]
		except IndexError: await interaction.response.send_message("Somthing wrong happened",ephemeral=True);return
		embed.title = self.title_.value
		embed.description = self.description_.value
		embed.colour = color_sel
		if valid_url.match(self.url_.value):
			embed.url = self.url_.value
		else:
			embed.url = None
		if await size_check(embed):
			await interaction.response.send_message("Discord limits embeds not to be larger than 6000 characters in total",ephemeral=True)
			return
		await interaction.response.edit_message(embed=embed)
class SaveEmbed(ui.Modal,title='Saves the embed!'):
	tag = ui.TextInput(
		label = 'Tag',style=discord.TextStyle.short,
		required=True,max_length=20,placeholder='The UNIQUE tag name of your embed'
	)
	async def on_submit(self, interaction: discord.Interaction):
		try:
			if interaction.message is None: raise IndexError
			async with CustomEmbed() as ce:
				await ce.new_embed(user=interaction.user.id,tag=self.tag.value,embed=json.dumps(interaction.message.embeds[0].to_dict()))
			await interaction.response.send_message(f"Embed saved with tag {self.tag.value}",ephemeral=True)
		except IndexError:
			await interaction.response.send_message("Something wrong happened",ephemeral=True)
		except TagInUse:
			await interaction.response.send_message("You already have a saved embed with that tag",ephemeral=True)
		except TooManyEmbeds:
			await interaction.response.send_message("You have reached the limit of embeds you can have",ephemeral=True)

@app_commands.allowed_installs(guilds=True,users=True)
@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
class CECog(commands.GroupCog,name='embed'):
	def __init__(self, bot: 'UtilsBot'):
		self.bot = bot

	async def cog_load(self):
		async with CustomEmbed() as ce:
			await ce.make_table()
		logger.info('CustomEmbed table created')

	@app_commands.command(name='create',description='Creates a custom embed!')
	async def create_embed(self, interaction: discord.Interaction):
		if isinstance(interaction.user,discord.Member) and not interaction.permissions.manage_messages:
			raise app_commands.MissingPermissions(['manage_messages'])
		ephemeral = not isinstance(interaction.user,discord.User) and not interaction.permissions.embed_links
		await interaction.response.defer(ephemeral=ephemeral) #this is to get the message id
		await interaction.followup.send(embed=default_embed,
				view=EmbedMaker(
						user_id=interaction.user.id,
						msg_id=(await interaction.original_response()).id)
					)
	
	@app_commands.autocomplete(tag=embed_autocomplete)
	@app_commands.command(name='remove')
	async def delete_embed(self, interaction: discord.Interaction, tag: str):
		"""Removes a previously saved embed
		
		Args:
			tag (int): The saved tag of your saved embed to remove
		"""
		async with CustomEmbed() as ce:
			try:
				await ce.delete_embed(user=interaction.user.id,tag=tag)
				await interaction.response.send_message(f'Embed with tag {tag} deleted!',ephemeral=True)
			except BadTag:
				await interaction.response.send_message(f'No embed with tag {tag} found',ephemeral=True)
	
	@app_commands.autocomplete(tag=embed_autocomplete)
	@app_commands.command(name='send')
	async def send_embed(self, interaction: discord.Interaction, tag: str, public: bool):
		"""Sends a saved embed!

		Args:
			tag (str): The tag of your saved embed
			public (bool): Wheter the embed should stick to your command interaction
		"""
		if not public and not interaction.is_guild_integration():
			await interaction.response.send_message('For `public` to be false, you must run this command in a server where I am',ephemeral=True)
			return
		if isinstance(interaction.user,discord.Member) and not interaction.permissions.manage_messages:
			raise app_commands.MissingPermissions(['manage_messages'])
			
		if interaction.channel is None or isinstance(interaction.channel,(discord.ForumChannel,discord.CategoryChannel)):
			await interaction.response.send_message('Something wrong happened',ephemeral=True)
			return
		async with CustomEmbed() as ce:
			plain_embed = await ce.load_embed(user=interaction.user.id,tag=tag)
			if plain_embed is None:
				await interaction.response.send_message(f'No embed with tag {tag} found',ephemeral=True)
				return
		embed = discord.Embed.from_dict(json.loads(plain_embed))
		if public:
			await interaction.response.send_message(embed=embed)
		else:
			try:
				await interaction.channel.send(embed=embed)
				await interaction.response.send_message('Embed sent',ephemeral=True)
			except discord.Forbidden:
				await interaction.response.send_message("Couldn't send embed, check my permissions",ephemeral=True)

	async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
		if isinstance(error,discord.app_commands.MissingPermissions):
			missing_perms = sm_utils.format_miss_perms(error.missing_permissions)
			await interaction.response.send_message(f"You need `{missing_perms}` to do this",ephemeral=True)
		else:
			raise error

async def setup(bot: 'UtilsBot'):
	await bot.add_cog(CECog(bot))