import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
from datetime import datetime
import re
from utils.giveaway import GiveawayDB, Giveaway
from utils import sm_utils
from time import time
import asyncio
from random import randint
from utils.userVoted import has_user_voted
from typing import List, Optional, Union, TYPE_CHECKING
import logging
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
	from bot import UtilsBot

class GiveawayEndedOverviewView(ui.View):
	def __init__(self, *, hoster_id: int, participants: List[int], winners: List[int], timeout: Optional[Union[int,float]] = None):
		self.hoster_id = hoster_id
		self.participants = participants
		self.winners = winners
		super().__init__(timeout=timeout)
	
	@ui.button(label='Winners',style=discord.ButtonStyle.green,emoji='\N{CROWN}')
	async def winners_overview(self, interaction: discord.Interaction, button: ui.Button):
		embed = discord.Embed(
			title = 'Page 1' if len(self.winners) > 8 else None,
			description = '\n'.join(f'- <@{winner_id}>' for winner_id in (self.winners[:8] if len(self.winners) > 8 else self.winners)),
			color = discord.Color.green()
		)
		view = GiveawayPaginator(itr=self.winners,timeout=300) if len(self.winners) > 8 else discord.utils.MISSING
		await interaction.response.send_message(embed=embed,view=view,ephemeral=True)
	
	@ui.button(label='Reroll',style=discord.ButtonStyle.danger,emoji='\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}') #lmao
	async def reroll_giveaway(self, interaction: discord.Interaction, button: ui.Button):
		if interaction.user.id != self.hoster_id and not interaction.permissions.manage_messages:
			await interaction.response.send_message('Only the hoster and people with `Manage Messages` can reroll this giveaway',ephemeral=True)
			return
		participants_who_didnt_win = list(filter(lambda x: x not in self.winners, self.participants))
		if len(participants_who_didnt_win) < len(self.winners):
			await interaction.response.send_message('Not enough participants to reroll the giveaway :(',ephemeral=True)
			return
		new_winners = [participants_who_didnt_win.pop(randint(0,len(participants_who_didnt_win)-1)) for _ in range(len(self.winners))]
		await interaction.response.edit_message(content=f'Giveaway has been rerolled! <t:{int(time())}:R>',
			view=GiveawayEndedOverviewView(hoster_id=self.hoster_id,participants=self.participants,winners=new_winners))
		self.stop()

	@ui.button(label='Participants',style=discord.ButtonStyle.green,emoji='\N{HAPPY PERSON RAISING ONE HAND}')
	async def participants_overview(self, interaction: discord.Interaction, button: ui.Button):
		embed = discord.Embed(
			title = 'Page 1' if len(self.participants) > 8 else None,
			description = '\n'.join(f'- <@{participant_id}>' for participant_id in (self.participants[:8] if len(self.participants) > 8 else self.participants)),
			color = discord.Color.green()
		)
		view = GiveawayPaginator(itr=self.participants,timeout=300) if len(self.participants) > 8 else discord.utils.MISSING
		await interaction.response.send_message(embed=embed,view=view,ephemeral=True)

class GiveawayPaginator(ui.View):
	index = 0
	def __init__(self, itr: List[int], timeout: Optional[Union[int,float]] = None):
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
			description = '\n'.join(f'- <@{user_id}>' for user_id in self.chunked[self.index]),
			color = discord.Color.green()
		)
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

class GiveawayJoinDynamicButton(ui.DynamicItem[ui.Button],template=r'giveaway_join:channel_id:(?P<id>[0-9]+)'):
	def __init__(self, channel_id: int):
		super().__init__(ui.Button(label='Join Giveaway!',style=discord.ButtonStyle.green,custom_id=f'giveaway_join:channel_id:{channel_id}',emoji='\N{PARTY POPPER}'))
		self.channel_id = channel_id

	@classmethod
	async def from_custom_id(cls, interaction: discord.Interaction, item: ui.Button, match: re.Match[str], /):
		channel_id = int(match['id'])
		return cls(channel_id)

	async def callback(self, interaction: discord.Interaction):
		if interaction.message is None or interaction.message is None:
			await interaction.response.send_message('Something went wrong :(',ephemeral=True)
			return
		async with GiveawayDB() as gw:
			try:
				assert await gw.giveaway_exists(giveaway_id=interaction.message.id) == True, 'Giveaway does not exists'
				if not await gw.user_already_in(user=interaction.user.id,giveaway_id=interaction.message.id):
					await gw.insert_user(user=interaction.user.id,giveaway_id=interaction.message.id)
				else:
					view = ui.View(timeout=60)
					view.add_item(GiveawayLeaveButton(giveaway_id=interaction.message.id))
					await interaction.response.send_message('You are already participating!',view=view,ephemeral=True)
					return
			except AssertionError as e:
				await interaction.response.send_message('Something wrong happened :(',ephemeral=True)
				logger.warning(e)
				return
			async with GiveawayDB() as gw:
				participants = len(await gw.fetch_participants(giveaway_id=interaction.message.id))
				# giveaway_info: dict[str,int | str] = await gw.fetch_giveaway(giveaway_id=interaction.message.id)
				try:
					embed = interaction.message.embeds[0]
				except IndexError:
					await gw.delete_giveaway(giveaway_id=interaction.message.id)
					await interaction.response.send_message('Seems like the message embed is missing, giveaway deleted')
					return
				if embed.description is None:
					await interaction.response.send_message('Something wrong happened',ephemeral=True)
					return
				else:
					pattern = r"Entries: \*\*.*?\*\*"
					matches = list(re.finditer(pattern, embed.description))
					if matches:
						last_match = matches[-1]
						start_index = last_match.start()
						end_index = last_match.end()
						embed.description = embed.description[:start_index] + re.sub(pattern, f"Entries: **{participants}**", embed.description[start_index:end_index]) + embed.description[end_index:]
				await interaction.message.edit(embed=embed)
			await interaction.response.send_message('You have joined the giveaway!',ephemeral=True)

class GiveawayLeaveButton(ui.Button):
	def __init__(self, giveaway_id: int):
		super().__init__(emoji='\N{NO ENTRY}',label='Leave giveaway',style=discord.ButtonStyle.red)
		self.giveaway_id = giveaway_id
	async def callback(self, interaction: discord.Interaction):
		if interaction.channel is None or interaction.message is None:
			return
		async with GiveawayDB() as gw:
			try:
				await gw.remove_user(user=interaction.user.id,giveaway_id=self.giveaway_id)
			except AssertionError as e:
				await interaction.response.send_message('Hmm... something went wrong...',ephemeral=True)
				logger.debug(e)
				return
			try: participants = len(await gw.fetch_participants(giveaway_id=self.giveaway_id))
			except AssertionError: participants = 0
			# giveaway_info: dict[str,int | str] = await gw.fetch_giveaway(giveaway_id=self.giveaway_id)
			try:
				if isinstance(interaction.channel,(discord.ForumChannel,discord.CategoryChannel)):
					await interaction.response.send_message('Something wrong happened',ephemeral=True)
					return
				msg = await interaction.channel.fetch_message(self.giveaway_id)
				embed = msg.embeds[0]
			except IndexError:
				await gw.delete_giveaway(giveaway_id=self.giveaway_id)
				await interaction.response.send_message('Seems like the message embed is missing, giveaway deleted')
				return
			if embed.description is None:
				await interaction.response.send_message('Something wrong happened',ephemeral=True)
				return
			else:
				pattern = r"Entries: \*\*.*?\*\*"
				matches = list(re.finditer(pattern, embed.description))
				if matches:
					last_match = matches[-1]
					start_index = last_match.start()
					end_index = last_match.end()
					embed.description = embed.description[:start_index] + re.sub(pattern, f"Entries: **{participants}**", embed.description[start_index:end_index]) + embed.description[end_index:]
			await msg.edit(embed=embed)
			await interaction.response.send_message('You are no longer participating in the giveaway!',ephemeral=True)

class GiveawayModal(ui.Modal,title='Creates a giveaway!'):
		_prize = ui.TextInput(
			label = 'What will the winner receive?',style=discord.TextStyle.short,
			placeholder='Free Pizza!',required=True,max_length=30
		)
		_description = ui.TextInput(
			label = 'Description',style=discord.TextStyle.long,
			placeholder='The winner of this giveaway will receive free pizza',required=False,
			max_length=100
		)
		_duration = ui.TextInput(
			label = 'Duration',style=discord.TextStyle.short,
			placeholder='Use formats such as: 1h30m, 2hours, 5m',required=True,
			max_length=15
		)
		_winners = ui.TextInput(
			label = 'Winners',style=discord.TextStyle.short,
			placeholder='How many winners? (max of 20)',required=True,
			max_length=2
		)
		async def on_submit(self, interaction: discord.Interaction):
			if interaction.channel is None:
				return
			async with GiveawayDB() as gw:
				amount_of_giveaways = await gw.fetch_hosted_giveaways(user_id=interaction.user.id)
				user_voted = await has_user_voted(user_id=interaction.user.id)
			if amount_of_giveaways > 4 and not user_voted:
				await interaction.response.send_message("You can't have more than 5 giveaways active at once. Consider giving me a [vote](<https://top.gg/bot/778785822828265514/vote>) to increase the limit :D")
				return
			elif amount_of_giveaways > 50:
				await interaction.response.send_message("You can't have more than 50 giveaways active at once")
				return
			c_time = int(time())
			if self._duration.value.isdecimal():
				when = int(self._duration.value)
			else:
				try: when = int(sm_utils.parse_duration(self._duration.value).total_seconds())
				except ValueError:
					await interaction.response.send_message('Duration invalid, if it keeps failing you could try with a timestamp',ephemeral=True)
					return
			if when/86400 > 150:
				await interaction.response.send_message("A maximum of 150 days (around 5 months) only",ephemeral=True)
				return
			elif when < 15:
				await interaction.response.send_message('Duration cannot be less than 15 seconds',ephemeral=True)
				return
			embed = discord.Embed(
				title = self._prize.value,
				description = f"{self._description.value}\n\n" +
				f"Ends: <t:{when+c_time}:R> (<t:{when+c_time}:T>)\n" +
				f"Hosted by: {interaction.user.mention}\n"+
				f"Entries: **0**\n"+
				"Winners: **",
				timestamp = datetime.fromtimestamp(when+c_time),
				color=discord.Color.blue()
			)
			try: winners = int(self._winners.value)
			except ValueError: winners = 0
			if winners < 1:
				await interaction.response.send_message('At least 1 person has to win something :<',ephemeral=True)
				return
			if winners > 20:
				await interaction.response.send_message('You can only have a max of 20 participants per giveaway',ephemeral=True)
				return
			if embed.description is None:
				await interaction.response.send_message('Something went wrong :(',ephemeral=True)
				return
			embed.description += f'{winners}**'
			view = ui.View(timeout=None)
			view.add_item(GiveawayJoinDynamicButton(interaction.channel.id))
			await interaction.response.send_message(embed=embed,view=view)
			msg_itr = await interaction.original_response()
			async with GiveawayDB() as gw:
				await gw.create_giveaway(id=msg_itr.id,channel_id=msg_itr.channel.id,time=when+c_time,prize=self._prize.value,winners=winners,user_id=interaction.user.id)


class GiveawayCog(commands.GroupCog,name='giveaway'):
	def __init__(self, bot: 'UtilsBot'):
		self.bot = bot
	
	@tasks.loop(seconds=10)
	async def loop_check(self):
		try:
			async with GiveawayDB() as gw:
				items = await gw.check_timestamp_fire(time=int(time()))
		except AssertionError:
			return
		task_list = []
		for item in items:
			task_list.append(asyncio.create_task(self.send_giveaway(item)))
		await asyncio.gather(*task_list)
	
	@loop_check.before_loop
	async def loop_check_before(self):
		if not self.bot.is_ready():
			await self.bot.wait_until_ready()
			return

	async def cog_unload(self):
		self.loop_check.cancel()
		logger.info('Cancelling giveaway loop check')

	async def cog_load(self):
		async with GiveawayDB() as gw:
			await gw.make_table()
			logger.info('Giveaway table created')
		self.loop_check.start()

	@commands.Cog.listener()
	async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
		async with GiveawayDB() as gw:
			try:
				await gw.delete_giveaway(giveaway_id=payload.message_id)
			except AssertionError:
				return
			logger.debug(f'giveaway {payload.message_id} deleted')

	async def send_giveaway(self, item: Giveaway):
		async def delgiveaway():
			try:
				async with GiveawayDB() as gw:
					await gw.delete_giveaway(giveaway_id=item.id)
			except AssertionError:
				return
		await asyncio.sleep(item.timestamp-time())
		try:
			logger.debug(f'Checking giveaway {item.id}')
			channel = await self.bot.fetch_channel(item.channel_id)
			msg: discord.Message = await channel.fetch_message(item.id) #type: ignore
			embed = msg.embeds[0]
			assert embed and embed.description
			parts = embed.description.rsplit('Ends',)
			embed.description = 'Ended'.join(parts)
		except (discord.HTTPException,discord.Forbidden,discord.NotFound,discord.InvalidData,AssertionError):
			await delgiveaway()
			return
		try:
			async with GiveawayDB() as gw:
				participants: List[int] = await gw.fetch_participants(giveaway_id=item.id)
				assert len(participants) >= item.winners, 'Not enough participants'
		except AssertionError:
			try:
				await msg.reply("Not enough participants to choose a winner :(")
				await msg.edit(embed=embed,view=None)
				await delgiveaway()
				return
			except (discord.Forbidden,discord.HTTPException):
				await delgiveaway()
				return
		else:
			try:
				participants_copy = participants.copy()					
				winners = [participants.pop(randint(0,len(participants)-1)) for _ in range(item.winners)]
				view = GiveawayEndedOverviewView(hoster_id=item.hoster_id,participants=participants_copy,winners=winners,timeout=3600*24*7) #7 days
				await msg.reply(content=f':tada: Giveaway for `{item.prize}` has ended! :tada: Click below for more information',view=view)
				await msg.edit(embed=embed,view=None)
				await delgiveaway()
			except (discord.Forbidden,discord.HTTPException):
				await delgiveaway()
				return

		
	@app_commands.command(name='create',description='Creates a giveaway!')
	@app_commands.guild_only()
	@app_commands.checks.has_permissions(manage_messages=True)
	async def create_giveaway(self, interaction: discord.Interaction):
		await interaction.response.send_modal(GiveawayModal())
		
	@create_giveaway.error
	async def create_giveaway_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
		if isinstance(error,app_commands.MissingPermissions):
			missing_perms = sm_utils.format_miss_perms(error.missing_permissions)
			await interaction.response.send_message(f"You need `{missing_perms}` to do this",ephemeral=True)
		else:
			raise error

	@app_commands.command(name='remove')
	@app_commands.guild_only()
	async def remove_giveaway(self, interaction: discord.Interaction, id: str):
		"""Removes a giveaway. You can also remove a giveaway by deleting the message itself

		Args:
			id (str): The message ID of the giveaway
		"""
		if not isinstance(interaction.user,discord.Member) or interaction.guild is None: #make type checker happy
			await interaction.response.send_message("Server only command")
			return
		try: int(id)
		except ValueError: await interaction.response.send_message('Must be a valid Discord Message ID');return
		async with GiveawayDB() as gw:
			try:
				giveaway = await gw.fetch_giveaway(giveaway_id=int(id))
			except AssertionError:
				await interaction.response.send_message('Hmm... giveaway not found, remember the `id` is the `id` of the giveaway message',ephemeral=True)
				return
			if giveaway.hoster_id != interaction.user.id and not interaction.permissions.manage_messages:
				await interaction.response.send_message("Only people with `Manage Messages` or the Giveaway hoster can remove this giveaway",ephemeral=True)
				return
			message = None
			try:
				for channel in interaction.guild.channels:
					if giveaway.channel_id != channel.id or isinstance(channel,(discord.ForumChannel,discord.CategoryChannel)):
						continue
					message = await channel.fetch_message(int(id))
					break
			except discord.NotFound:
				await interaction.response.send_message("This giveaway exists, though the message could not be fetched. This shouldn't have happened. Please try again or contact the developer",ephemeral=True)
				return
			except discord.Forbidden:
				await interaction.response.send_message('I have no permission to fetch messages from this channel :(',ephemeral=True)
				return
			try:
				if message is None:
					raise TypeError
				await message.delete()
			except (discord.Forbidden,discord.NotFound):
				await interaction.response.send_message('Either I have no permissions to delete messages or the giveaway message has already been deleted',ephemeral=True)
				return
			except TypeError:
				await interaction.response.send_message('This giveaway exists, but was not created in the same **Server** where you ran this command. Please run the command in the **Server** the giveaway was created',ephemeral=True)
				return
			# await gw.delete_giveaway(giveaway_id=id) on message delete already handles this
			await interaction.response.send_message('Giveaway deleted! You can also delete giveaways by deleting the message itself',ephemeral=True)

	@commands.is_owner()
	@commands.command(name='check')
	async def checkgiveaway(self, ctx: commands.Context):
		if not await self.bot.is_owner(ctx.author): #useless but just in case
			return
		async with GiveawayDB() as gw:
			a = await gw.select_all()
			await ctx.send(content=f'{a}')

async def setup(bot: 'UtilsBot'):
	await bot.add_cog(GiveawayCog(bot))