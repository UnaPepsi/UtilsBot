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

class GiveawayView(discord.ui.View):
	def __init__(self,timeout: float | None = None):
		super().__init__(timeout=timeout)

	@ui.button(label='Join Giveaway!',style=discord.ButtonStyle.green)
	async def join_giveaway(self, interaction: discord.Interaction, button: ui.Button):
		if interaction.message is None:
			await interaction.response.send_message('Something went wrong :(',ephemeral=True)
			return
		async with GiveawayDB() as gw:
			try:
				assert await gw.giveaway_exists(giveaway_id=interaction.message.id) == True, 'Giveaway does not exists'
				if not await gw.user_already_in(user=interaction.user.id,giveaway_id=interaction.message.id):
					await gw.insert_user(user=interaction.user.id,giveaway_id=interaction.message.id)
				else:
					await interaction.response.send_message('You are already participating!',ephemeral=True)
					return
			except AssertionError as e:
				await interaction.response.send_message('Something wrong happened :(',ephemeral=True)
				print(e)
				return
			async with GiveawayDB() as gw:
				participants = len(await gw.fetch_participants(giveaway_id=interaction.message.id))
				giveaway_info: dict[str,int | str] = await gw.fetch_giveaway(giveaway_id=interaction.message.id)
				try:
					embed = interaction.message.embeds[0]
				except IndexError:
					await gw.delete_giveaway(giveaway_id=interaction.message.id)
					await interaction.response.send_message('Seems like the message embed is missing, giveaway deleted')
					return
				if embed.description is None:
					embed.description = f"Ends: <t:{giveaway_info['time']}:R> (<t:{giveaway_info['time']}:T>)\n" + \
					f"Hosted by: {interaction.user.mention}\n" + \
					f"Entries: **{participants}**\n" + \
					f"Winners: **{giveaway_info['winners']}**"
				else:
					embed.description = re.sub(r"Entries: \*\*.*?\*\*", f"Entries: **{participants}**", embed.description)
				await interaction.message.edit(embed=embed)
			await interaction.response.send_message('You have joined the giveaway!',ephemeral=True)

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
				f"Ends: <t:{when+c_time}:R> (<t:{when}:T>)\n" +
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
			view = GiveawayView(timeout=None)
			await interaction.response.send_message(embed=embed,view=view)
			msg_id = await interaction.original_response()
			async with GiveawayDB() as gw:
				await gw.create_giveaway(id=msg_id.id,channel_id=msg_id.channel.id,time=when+c_time,prize=self._prize.value,winners=winners)


class GiveawayCog(commands.GroupCog,name='giveaway'):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
	
	@tasks.loop(seconds=10)
	async def loop_check(self):
		try:
			async with GiveawayDB() as gw:
				items: tuple[int,int,int,str,int] = await gw.check_timestamp_fire(time=int(time()))
		except AssertionError:
			return
		task_list = []
		for item in items:
			task_list.append(asyncio.create_task(self.send_giveaways(item)))
		await asyncio.gather(*task_list)

	@commands.Cog.listener()
	async def on_ready(self):
		async with GiveawayDB() as gw:
			await gw.make_table()
			print('table2')
		self.loop_check.start()

	async def send_giveaways(self, item: tuple[int,int,int,str,int]):
		async def delgiveaway():
			try:
				async with GiveawayDB() as gw:
					await gw.delete_giveaway(giveaway_id=item[0])
			except AssertionError as e:
				return
		await asyncio.sleep(item[2]-int(time()))
		try:
			print("embed")
			channel = await self.bot.fetch_channel(item[1])
			msg = await channel.fetch_message(item[0])
			view = discord.ui.View.from_message(msg)
			view.stop()
			embed = msg.embeds[0]
			embed.description = embed.description.replace('Ends','Ended')
		except (discord.HTTPException,discord.Forbidden,discord.NotFound,discord.InvalidData):
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
						print("empty")
						winners += f'<@{winners_id.pop(0)[0]}> '
				await msg.reply(f"The giveaway for {prize} has ended! Winners: {winners}")
				await msg.edit(embed=embed,view=None)
				await delgiveaway()
			except (discord.Forbidden,discord.HTTPException):
				await delgiveaway()
				return

		
	@app_commands.command(name='create',description='Creates a giveaway!')
	@app_commands.checks.has_permissions(manage_messages=True)
	async def creategiveaway(self, interaction: discord.Interaction):
		await interaction.response.send_modal(GiveawayModal())
		
	@creategiveaway.error
	async def create_giveaway_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
		if isinstance(error,app_commands.MissingPermissions):
			missing_perms = await perms.format_miss_perms(error.missing_permissions)
			await interaction.response.send_message(f"You need `{missing_perms}` to do this",ephemeral=True)
		else:
			raise error

	@commands.command(name='check')
	async def checkgiveaway(self, ctx: commands.Context):
		if ctx.author.id != 624277615951216643:
			return
		async with GiveawayDB() as gw:
			a = await gw.select_all()
			await ctx.send(content=f'{a}')

async def setup(bot: commands.Bot):
	await bot.add_cog(GiveawayCog(bot))