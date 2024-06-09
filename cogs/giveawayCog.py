import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
from datetime import timedelta
import re
from utils.giveaway import GiveawayDB
from utils import perms
from time import time
from datetime import datetime
import asyncio
from random import randint
from utils.userVoted import has_user_voted
import logging
logger = logging.getLogger(__name__)

def parse_duration(duration_str: str):
	pattern = r"""
		(?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?                 # e.g. 10w
		(?:(?P<days>[0-9]{1,5})(?:days?|d))?                   # e.g. 14d
		(?:(?P<hours>[0-9]{1,5})(?:hours?|hr?s?))?             # e.g. 12h
		(?:(?P<minutes>[0-9]{1,5})(?:minutes?|m(?:ins?)?))?    # e.g. 10m
		(?:(?P<seconds>[0-9]{1,5})(?:seconds?|s(?:ecs?)?))?    # e.g. 15s
	"""

	match = re.match(pattern, duration_str, re.VERBOSE | re.IGNORECASE)

	if match:
		weeks = int(match.group('weeks')) if match.group('weeks') else 0
		days = int(match.group('days')) if match.group('days') else 0
		hours = int(match.group('hours')) if match.group('hours') else 0
		minutes = int(match.group('minutes')) if match.group('minutes') else 0
		seconds = int(match.group('seconds')) if match.group('seconds') else 0

		duration = timedelta(
			days=days + weeks * 7,
			hours=hours,
			minutes=minutes,
			seconds=seconds
		)
		return duration
	else:
		raise ValueError("Invalid duration format")

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
			placeholder='Use formats such as: 1h30m, 2hours 5m',required=True,
			max_length=15
		)
		_winners = ui.TextInput(
			label = 'Winners',style=discord.TextStyle.short,
			placeholder='How many winners? (max of 99)',required=True,
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
				try: when = int(parse_duration(self._duration.value).total_seconds())
				except ValueError:
					await interaction.response.send_message('Duration invalid, if keeps failing you could try with a timestamp',ephemeral=True)
					return
			if (when-int(time()))/86400 > 180:
				await interaction.response.send_message("A maximum of 6 months only",ephemeral=True)
				return
			elif when < 30:
				await interaction.response.send_message('Duration cannot be less than 30 seconds',ephemeral=True)
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
			if embed.description is None:
				await interaction.response.send_message('Something went wrong :(',ephemeral=True)
				return
			embed.description += f'{winners}**'
			view = ui.View(timeout=None)
			view.add_item(GiveawayJoinDynamicButton(interaction.channel.id))
			await interaction.response.send_message(embed=embed,view=view)
			msg_id = await interaction.original_response()
			async with GiveawayDB() as gw:
				await gw.create_giveaway(id=msg_id.id,channel_id=msg_id.channel.id,time=when+c_time,prize=self._prize.value,winners=winners,user_id=interaction.user.id)


class GiveawayCog(commands.GroupCog,name='giveaway'):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
	
	@tasks.loop(seconds=10)
	async def loop_check(self):
		if not self.bot.is_ready():
			await self.bot.wait_until_ready()
			return
		try:
			async with GiveawayDB() as gw:
				items: list[tuple[int,int,int,str,int,int]] = await gw.check_timestamp_fire(time=int(time()))
		except AssertionError:
			return
		task_list = []
		for item in items:
			task_list.append(asyncio.create_task(self.send_giveaways(item)))
		await asyncio.gather(*task_list)

	async def cog_load(self):
		async with GiveawayDB() as gw:
			await gw.make_table()
			logger.info('Giveaway table created')
		self.loop_check.start()

	@commands.Cog.listener()
	async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
		async with GiveawayDB() as gw:
			try:
				_ = await gw.fetch_giveaway(giveaway_id=payload.message_id)
			except AssertionError:
				return
			await gw.delete_giveaway(giveaway_id=payload.message_id)
			logger.debug(f'giveaway {payload.message_id} deleted')

	async def send_giveaways(self, item: tuple[int,int,int,str,int,int]):
		async def delgiveaway():
			try:
				async with GiveawayDB() as gw:
					await gw.delete_giveaway(giveaway_id=item[0])
			except AssertionError as e:
				return
		await asyncio.sleep(item[2]-int(time()))
		try:
			logger.debug(f'Checking giveaway {item[0]}')
			channel = await self.bot.fetch_channel(item[1])
			msg: discord.Message = await channel.fetch_message(item[0]) #type: ignore
			embed = msg.embeds[0]
			if embed is None or embed.description is None:
				raise TypeError()
			parts = embed.description.rsplit('Ends',)
			embed.description = 'Ended'.join(parts)
		except (discord.HTTPException,discord.Forbidden,discord.NotFound,discord.InvalidData,TypeError):
			await delgiveaway()
			return
		try:
			async with GiveawayDB() as gw:
				winners_id: list[tuple[int,str]] = await gw.fetch_participants(giveaway_id=item[0])
				if len(winners_id) < item[4]:
					raise AssertionError('Not enough participants')
		except AssertionError as e:
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
				winners = ''
				prize = winners_id[0][1]
				for i in range(item[4]):
					if len(winners_id) != 0:
						rand = randint(0,len(winners_id)-1)
						winners += f'<@{winners_id.pop(rand)[0]}> '
					else:
						logger.debug("No more winners")
						winners += f'<@{winners_id.pop(0)[0]}> '
				await msg.reply(f"The giveaway for `{prize}` has ended! Winners: {winners}")
				await msg.edit(embed=embed,view=None)
				await delgiveaway()
			except (discord.Forbidden,discord.HTTPException):
				await delgiveaway()
				return

		
	@app_commands.command(name='create',description='Creates a giveaway!')
	@app_commands.checks.has_permissions(manage_messages=True)
	async def create_giveaway(self, interaction: discord.Interaction):
		await interaction.response.send_modal(GiveawayModal())
		
	@create_giveaway.error
	async def create_giveaway_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
		if isinstance(error,app_commands.MissingPermissions):
			missing_perms = perms.format_miss_perms(error.missing_permissions)
			await interaction.response.send_message(f"You need `{missing_perms}` to do this",ephemeral=True)
		else:
			raise error

	@app_commands.command(name='remove')
	async def remove_giveaway(self, interaction: discord.Interaction, id: str):
		"""Removed an owned giveaway

		Args:
			id (str): The message ID of the giveaway
		"""
		try: int(id)
		except ValueError: await interaction.response.send_message('Must be a valid Discord ID');return
		async with GiveawayDB() as gw:
			try:
				giveaway = await gw.fetch_giveaway(giveaway_id=int(id))
			except AssertionError:
				await interaction.response.send_message('Hmm... giveaway not found, remember the id is the id of the giveaway message',ephemeral=True)
				return
			if giveaway['hoster_id'] != interaction.user.id:
				await interaction.response.send_message("You have not created this giveaway!\n_If you're an admin you can remove a giveaway just by deleting the message_",ephemeral=True)
				return
			try:
				message = await interaction.channel.fetch_message(int(id)) #type: ignore
			except discord.NotFound:
				await interaction.response.send_message('This giveaway exists, though the message id was not found. If this giveaway was made in another **channel** please use the command there',ephemeral=True)
				return
			except discord.Forbidden:
				await interaction.response.send_message('I have no permission to fetch messages from this channel :(',ephemeral=True)
				return
			try:
				await message.delete()
			except (discord.Forbidden,discord.NotFound):
				await interaction.response.send_message('Either I have no permissions or the giveaway message has already been deleted',ephemeral=True)
				return
			# await gw.delete_giveaway(giveaway_id=id) on message delete already handles this
			await interaction.response.send_message('Giveaway deleted!',ephemeral=True)


	@commands.command(name='check')
	async def checkgiveaway(self, ctx: commands.Context):
		if ctx.author.id != 624277615951216643:
			return
		async with GiveawayDB() as gw:
			a = await gw.select_all()
			await ctx.send(content=f'{a}')

async def setup(bot: commands.Bot):
	await bot.add_cog(GiveawayCog(bot))