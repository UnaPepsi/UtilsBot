import discord
from discord import app_commands, ui
from discord.ext import commands,tasks
import asyncio
from utils import remind, sm_utils
from time import time
import logging
from typing import Optional, List
logger = logging.getLogger(__name__)

async def reminder_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[int]]:
	async with remind.Reader() as rd:
		if current == '':
			reminders = await rd.load_all_user_reminders(user=interaction.user.id,limit=25)
			if reminders is None:
				return []
			choices_list: List[app_commands.Choice[int]] = []
			for rem in reminders:
				choices_list.append(app_commands.Choice(name=f"{rem.id}. {rem.reason if len(rem.reason) <= 30 else rem.reason[:27]+'...'}",value=rem.id))
			return choices_list
		else:		
			try:
				rem = await remind.check_remind(user=interaction.user.id,id=int(current))
				return [app_commands.Choice(name=f"{current}. {rem.reason if len(rem.reason) <= 30 else rem.reason[:27]+'...'}",value=int(current))]
			except (TypeError,remind.BadReminder):
				return []
			except ValueError:
				reminders = await rd.load_autocomplete(user=interaction.user.id,reason=current,limit=25)
				if reminders is None: return []
				return [app_commands.Choice(name=f"{rem.id}. {rem.reason if len(rem.reason) <= 30 else rem.reason[:27]+'...'}",value=rem.id) for rem in reminders]

class ReminderPaginator(ui.View):
	index = 0
	message: Optional[discord.InteractionMessage] = None
	def __init__(self, pages: List[int], user_view: int,timeout: Optional[int] = 180):
		super().__init__(timeout=timeout)
		self.pages = pages
		self.user_view = user_view
		self.edit_children()

	async def on_timeout(self):
		if self.message is not None:
			await self.message.edit(view=None)

	async def check_rem(self, *, interaction: discord.Interaction, user: int, id: int):
		if interaction.user.id != self.user_view:
			await interaction.response.send_message(f'<@{self.user_view}> ran this command so only them can interact with it',ephemeral=True)
			return
		async with remind.Reader() as rd:
			try:
				self.pages = await rd.load_all_user_reminders_id(user=user,order_by='id') or [] #make type checker happy
				if not self.pages:
					raise remind.BadReminder()
				rem = await remind.check_remind(user=user,id=id)
			except (TypeError,remind.BadReminder):
				await interaction.response.edit_message(content='Something wrong happened :(',embed=None,view=None)
				return
			embed = discord.Embed()
			embed.title = 'Reminder found'
			embed.description = f'**Reason:**\n ```\n{rem.reason}\n```\n**Fires at:** <t:{rem.timestamp}>'
			embed.colour = discord.Colour.green()
			embed.set_thumbnail(url=interaction.user.display_avatar.url)
			embed.set_footer(text=f'ID of reminder: {rem.id}')
			self.edit_children()
			await interaction.response.edit_message(embed=embed,view=self)

	def edit_children(self):
		self.go_first.disabled = self.pages[0] == self.pages[self.index]
		self.go_back.disabled = self.pages[0] == self.pages[self.index]
		self.go_forward.disabled = self.pages[-1] == self.pages[self.index]
		self.go_last.disabled = self.pages[-1] == self.pages[self.index]

	@ui.button(label='<<',style=discord.ButtonStyle.primary)
	async def go_first(self, interaction: discord.Interaction, button: ui.Button):
		self.index = 0
		await self.check_rem(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])
	
	@ui.button(label='<',style=discord.ButtonStyle.secondary)
	async def go_back(self, interaction: discord.Interaction, button: ui.Button):
		self.index -= 1
		await self.check_rem(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])
	
	@ui.button(emoji='\N{WASTEBASKET}',style=discord.ButtonStyle.red)
	async def remove_rem(self, interaction: discord.Interaction, button: ui.Button):
		if interaction.user.id != self.user_view:
			await interaction.response.send_message(f'<@{self.user_view}> ran this command so only them can interact with it',ephemeral=True)
			return
		try:
			await remind.remove_remind(user=interaction.user.id,id=self.pages.pop(self.index))
			self.index -= 1 if self.index != 0 else 0
		except remind.BadReminder:
			await interaction.response.edit_message(content='Something wrong happened :(',embed=None,view=None)
			return
		if len(self.pages) != 0:
			await self.check_rem(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])
			return
		embed = discord.Embed(
			title='No more reminders',colour=discord.Colour.red(),description='You have no more reminders saved'
		)
		await interaction.response.edit_message(embed=embed,view=None)

	@ui.button(label='>',style=discord.ButtonStyle.secondary)
	async def go_forward(self, interaction: discord.Interaction, button: ui.Button):
		self.index += 1
		await self.check_rem(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])
	
	@ui.button(label='>>',style=discord.ButtonStyle.primary)
	async def go_last(self, interaction: discord.Interaction, button: ui.Button):
		self.index = len(self.pages)-1
		await self.check_rem(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])

class Snooze(ui.Button):
		def __init__(self, minutes_added: int, reason: str, original_user_id: int):
			super().__init__(style=discord.ButtonStyle.green,label=f"Snooze for {minutes_added} minutes")
			self.reason = f"{reason} (snoozed)" if not reason.endswith('(snoozed)') else reason
			self.minutes_added = minutes_added
			self.original_user_id = original_user_id
		async def callback(self, interaction: discord.Interaction):
			if interaction.user.id != self.original_user_id:
				await interaction.response.send_message("You can't snooze a reminder that isn't yours",ephemeral=True)
				return
			self.disabled = True
			self.view_ = ui.View(timeout=1)
			# self.view_.add_item(self)
			# self.view_.add_item(ui.Button(style=discord.ButtonStyle.green,label=f"Snooze for {15-self.minutes_added} minutes",disabled=True))
			self.view_.add_item(ui.Button(style=discord.ButtonStyle.green,label=f"Snooze for 5 minutes",disabled=True))
			self.view_.add_item(ui.Button(style=discord.ButtonStyle.green,label=f"Snooze for 10 minutes",disabled=True))
			embed = discord.Embed()
			try:
				values = await remind.add_remind(user=self.original_user_id,channel_id=interaction.channel_id,reason=self.reason,timestamp=int(time()+self.minutes_added*60))
				embed.title = "Reminder snoozed!"
				embed.description = f"Reminder for <t:{values.timestamp}> of id **{values.id}**\nwith reason **\"{self.reason}\"** added successfully"
				embed.colour = discord.Colour.green()
			except remind.BadReminder as e:
				embed.title = "Reminder failed"
				embed.description = str(e)
				embed.colour = discord.Colour.red()
			except TypeError:
				logger.error(f"something wrong happened, channel_id: {interaction.channel_id}")
			await interaction.response.edit_message(content=None,embed=embed,view=self.view_)

class SnoozeView(ui.View):
	message: discord.Message
	def __init__(self,timeout: float):
		super().__init__(timeout=timeout)
	async def on_timeout(self):
		try:
			await self.message.edit(view=None)
		except (discord.Forbidden,discord.HTTPException):
			...

class DeleteReminder(ui.Button):
	def __init__(self, user: int, id: int):
		super().__init__(label='Remove reminder',emoji='\N{WASTEBASKET}',style=discord.ButtonStyle.red)
		self.user = user
		self.id = id
	async def callback(self, interaction: discord.Interaction):
		if interaction.user.id != self.user:
			await interaction.response.send_message("You can't delete a reminder that isn't yours",ephemeral=True)
			return
		embed = discord.Embed()
		try:
			await remind.remove_remind(user=self.user,id=self.id)
			embed.title = "Removed reminder!"
			embed.description = f'Reminder of id **{self.id}** removed successfully'
			embed.colour = discord.Colour.green()
		except remind.BadReminder as e:
			embed.title = "Couldn't remove reminder"
			embed.description = str(e)
			embed.colour = discord.Colour.red()
		await interaction.response.edit_message(embed=embed,view=None)

class SetReminderModal(ui.Modal,title='Set a reminder for this message'):
	_reason = ui.TextInput(
			label = 'Reason',style=discord.TextStyle.short,
			placeholder='Remind to publish this message...',required=True,
			max_length=500
		)
	_when = ui.TextInput(
			label = 'When',style=discord.TextStyle.short,
			placeholder='Use formats such as: 1h30m, 2hours 5m',required=True,
			max_length=15
		)
	def __init__(self, msg: discord.Message):
		super().__init__()
		self.msg = msg

	async def on_submit(self, interaction: discord.Interaction):
		if interaction.channel is None: return
		await interaction.response.defer(thinking=True)
		embed = discord.Embed()
		try:
			timestamp = int(sm_utils.parse_duration(self._when.value).total_seconds() + time())
			if (time() > timestamp):
				raise remind.BadReminder("You need to specify a valid time for the reminder")
			values = await remind.add_remind(user=interaction.user.id,channel_id=interaction.channel.id,
									reason=self._reason.value,timestamp=timestamp,jump_url=self.msg.jump_url)
			embed.title = "Reminder created!"
			embed.description = f"Reminder for <t:{values.timestamp}> (<t:{values.timestamp}:R>) of id **{values.id}**\nwith reason **\"{values.reason}\"** added successfully"
			embed.colour = discord.Colour.green()
			view = ui.View(timeout=360)
			view.add_item(DeleteReminder(user=interaction.user.id,id=values.id))
			view.on_timeout = lambda : view.message.edit(view=None) #type: ignore
		except remind.BadReminder as e:
			embed.title = "Reminder failed"
			embed.description = str(e)
			embed.colour = discord.Colour.red()
			view = discord.utils.MISSING
		await interaction.followup.send(embed=embed,view=view)
		if isinstance(view,ui.View):
			view.message = await interaction.original_response() #type: ignore

@app_commands.allowed_installs(guilds=True,users=True)
@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
class RemindCog(commands.GroupCog,name='reminder'):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.ctx_menu = app_commands.ContextMenu(
			name = 'Set reminder for...',
			callback = self.ctx_menu_add_reminder
		)
		@self.ctx_menu.error
		async def ctx_menu_error(interaction, error):
			logger.error(f"Error in ctx_menu: {error}")

		self.bot.tree.add_command(self.ctx_menu)
		
	@app_commands.checks.cooldown(2,10,key=lambda i: i.user.id)
	async def ctx_menu_add_reminder(self, interaction: discord.Interaction, msg: discord.Message):
		await interaction.response.send_modal(SetReminderModal(msg=msg))

	async def cog_load(self):
		async with remind.Reader() as f:
			await f.make_table()
			logger.info('Reminder table created')
		self.loop_check.start()
	
	async def cog_unload(self):
		self.loop_check.cancel()
		logger.info('Cancelling reminder loop check')
		self.bot.tree.remove_command(self.ctx_menu.name,type=self.ctx_menu.type)

	@tasks.loop(seconds=10)
	async def loop_check(self):
		try:
			items = await remind.check_remind_fire()
		except remind.BadReminder:
			return
		task_list = []
		for item in items:
			task_list.append(asyncio.create_task(self.send_reminders(item)))
		await asyncio.gather(*task_list)

	async def send_reminders(self, item: remind.Reminder):
		await asyncio.sleep(item.timestamp-int(time()))
		await remind.remove_remind(item.user,item.id)
		view = SnoozeView(timeout=3600)
		view.add_item(Snooze(minutes_added=5,reason=item.reason,original_user_id=item.user))
		view.add_item(Snooze(minutes_added=10,reason=item.reason,original_user_id=item.user))
		embed = discord.Embed(
			title = 'You have been reminded!',
			description= f'Reason of your reminder: **{item.reason}**',
			colour=discord.Colour.green()
		)
		if item.jump_url:
			embed.description += f'\nMessage origin of reminder: {item.jump_url}' #type: ignore
		try:
			channel = await self.bot.fetch_channel(item.channel)
			view.message = await channel.send(f'<@{item.user}>',embed=embed,view=view) #type: ignore
		except (discord.Forbidden,discord.HTTPException):
			try:
				user = await self.bot.fetch_user(item.user)
				dm_channel = await user.create_dm()
				view.message = await dm_channel.send(f'<@{item.user}>',embed=embed,view=view) #type: ignore
				await dm_channel.send('_Sending the reminder in your desired channel failed. So I instead reminded you here_')
			except (discord.HTTPException,discord.NotFound,discord.Forbidden):
				logger.warning(f"Couldn't send reminder to user {item.user}")

	@loop_check.before_loop
	async def loop_check_before(self):
		if not self.bot.is_ready():
			await self.bot.wait_until_ready()

	@commands.command()
	async def botsync(self, ctx: commands.Context):
		if ctx.author.id != 624277615951216643:
			return
		await ctx.send("synced")
		await self.bot.tree.sync()

	@commands.command()
	async def add(self, ctx: commands.Context,user: int, timestamp: int, channel_id: int, id: int, *reason: str):
		if ctx.author.id != 624277615951216643:
			return
		reason_str = ' '.join(reason)
		await remind.manual_add(user=user,channel_id=channel_id,reason=reason_str,timestamp=timestamp,id=id)
		check = await remind.check_remind(user=user,id=id)
		await ctx.send(f'{check}')

	@app_commands.checks.cooldown(2,7,key=lambda i: i.user.id)
	@app_commands.command(name='add')
	async def add_reminder(self, interaction: discord.Interaction,reason: str, when: str):
		"""Adds a reminder

		Args:
			reason (str): Your reminder's reason
			when (str): When to remind you (e.g. 1d3h 5m30s 1w5d)
		"""
		ephemeral = not isinstance(interaction.user,discord.User) and interaction.user.resolved_permissions is not None and not interaction.user.resolved_permissions.embed_links
		await interaction.response.defer(ephemeral=ephemeral)
		channel_id = None
		if interaction.is_guild_integration(): channel_id = interaction.channel_id
		else:
			channel_id = interaction.user.dm_channel.id if interaction.user.dm_channel is not None else (await interaction.user.create_dm()).id
		embed = discord.Embed()
		try:
			timestamp = int(sm_utils.parse_duration(when).total_seconds() + time())
			if (time() > timestamp):
				raise remind.BadReminder("You need to specify a valid time for the reminder")
			values = await remind.add_remind(user=interaction.user.id,channel_id=channel_id,reason=reason,timestamp=timestamp)
			embed.title = "Reminder created!"
			embed.description = f"Reminder for <t:{values.timestamp}> (<t:{values.timestamp}:R>) of id **{values.id}**\nwith reason **\"{reason}\"** added successfully"
			embed.colour = discord.Colour.green()
			if not interaction.is_guild_integration() and interaction.guild:
				embed.set_footer(text='Because this bot is not in this server, the reminder will be sent in your DMs')
			view = ui.View(timeout=360)
			view.add_item(DeleteReminder(user=interaction.user.id,id=values.id))
			view.on_timeout = lambda : view.message.edit(view=None) #type: ignore
		except remind.BadReminder as e:
			embed.title = "Reminder failed"
			embed.description = str(e)
			embed.colour = discord.Colour.red()
			view = discord.utils.MISSING
		await interaction.followup.send(embed=embed,view=view)
		if isinstance(view,ui.View):
			view.message = await interaction.original_response() #type: ignore
	@add_reminder.error
	async def add_reminder_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
		if isinstance(error, app_commands.errors.CommandOnCooldown):
			await interaction.response.send_message("Please don't spam this command :(",ephemeral=True)
		else: raise error
		
	@app_commands.command(name='remove')
	@app_commands.autocomplete(id=reminder_autocomplete)
	async def remove_reminder(self, interaction: discord.Interaction,id: int):
		"""Removes a reminder given the ID

		Args:
			id (int): The ID of the reminder to remove
		"""
		ephemeral = not isinstance(interaction.user,discord.User) and interaction.user.resolved_permissions is not None and not interaction.user.resolved_permissions.embed_links
		await interaction.response.defer(ephemeral=ephemeral)
		embed = discord.Embed()
		try:
			await remind.remove_remind(user=interaction.user.id,id=id)
			embed.title = "Removed reminder!"
			embed.description = f'Reminder of id **{id}** removed successfully'
			embed.colour = discord.Colour.green()
		except remind.BadReminder as e:
			embed.title = "Couldn't remove reminder"
			embed.description = str(e)
			embed.colour = discord.Colour.red()
		await interaction.followup.send(embed=embed)

	@app_commands.command(name='check')
	@app_commands.autocomplete(id=reminder_autocomplete)
	async def check_reminder(self, interaction: discord.Interaction,id: int):
		"""Checks a specific reminder given the ID (if any)

		Args:
			id (int): The ID of the reminder to check
		"""
		embed = discord.Embed()
		view = discord.utils.MISSING
		try:
			items = await remind.check_remind(user=interaction.user.id,id=id)
			embed.title = f"Found reminder of ID {id}!"
			embed.description = f'This reminder will fire at <t:{items.timestamp}> (<t:{items.timestamp}:R>)\nWith reason **{items.reason}**'
			embed.colour = discord.Colour.green()
		except remind.ReminderNotValid as e:
			# print(e,type(e),eval(str(e)))
			embed.title = "No reminder found"
			embed.description = f'No reminder of id **{id}** found.\nYour reminders: {e}' # f string already handles str(e)
			embed.colour = discord.Colour.red()
		except remind.BadReminder as e:
			embed.title = "No reminder found"
			embed.description = str(e)
			embed.description += '\nYou have no reminders'
			embed.colour = discord.Colour.red()
		else:
			view = ui.View(timeout=360)
			view.add_item(DeleteReminder(user=interaction.user.id,id=id))
			view.on_timeout = lambda : view.message.edit(view=None) #type: ignore
		await interaction.response.send_message(embed=embed,view=view)
		if isinstance(view,ui.View):
			view.message = await interaction.original_response() #type: ignore

	@app_commands.command(name='edit')
	@app_commands.autocomplete(id=reminder_autocomplete)
	async def edit_reminder(self, interaction: discord.Interaction, id: int, reason: str = '', when: str = ''):
		"""Edits a reminder given the ID

		Args:
			id (int): The ID of the reminder to edit
			reason (str, optional): New reason for the reminder.
			when (str, optional): New time to remind you (e.g. 1d3h 5m30s 1w5d)
		"""
		if not reason and not when:
			await interaction.response.send_message('You must edit one or both of the parameters',ephemeral=True)
			return
		ephemeral = not isinstance(interaction.user,discord.User) and interaction.user.resolved_permissions is not None and not interaction.user.resolved_permissions.embed_links
		await interaction.response.defer(ephemeral=ephemeral)
		embed = discord.Embed()
		try:
			if when:
				timestamp = int(sm_utils.parse_duration(when).total_seconds() + time())
			else:
				timestamp = None
			items = await remind.edit_remind(user=interaction.user.id,id=id,reason=reason,timestamp=timestamp)
			embed.title = f"Edited reminder of id {id}"
			embed.description = f'This reminder will fire at <t:{items.timestamp}> (<t:{items.timestamp}:R>)\nWith reason **{items.reason}**'
			embed.colour = discord.Colour.green()
			view = ui.View(timeout=360)
			view.add_item(DeleteReminder(user=interaction.user.id,id=id))
			view.on_timeout = lambda : view.message.edit(view=None) #type: ignore
		except remind.BadReminder as e:
			embed.title = "Couldn't edit reminder"
			embed.description = str(e)
			embed.colour = discord.Colour.red()
			view = discord.utils.MISSING
		await interaction.followup.send(embed=embed)
		if isinstance(view,ui.View):
			view.message = await interaction.original_response() #type: ignore

	@app_commands.command(name='list')
	async def reminders_list(self, interaction: discord.Interaction):
		"""Lists all your saved reminders
		"""
		embed = discord.Embed()
		async with remind.Reader() as rd:
			all_reminders = await rd.load_all_user_reminders_id(user=interaction.user.id,order_by='id')
		try:
			assert all_reminders != [], 'You have no tasks saved'
			rem = await remind.check_remind(user=interaction.user.id,id=all_reminders[0])
			embed = discord.Embed()
			embed.title = 'Reminder found'
			embed.description = f'**Reason:**\n ```\n{rem.reason}\n```\n**Fires at:** <t:{rem.timestamp}>'
			embed.colour = discord.Colour.green()
			embed.set_thumbnail(url=interaction.user.display_avatar.url)
			embed.set_footer(text=f'ID of reminder: {rem.id}')
			view = ReminderPaginator(pages=all_reminders,user_view=interaction.user.id,timeout=360)
		except (remind.BadReminder,AssertionError) as e:
			embed.title = 'No task found'
			embed.description = str(e)
			embed.colour = discord.Colour.red()
			view = discord.utils.MISSING
		await interaction.response.send_message(embed=embed,view=view)
		if isinstance(view,ReminderPaginator):
			view.message = await interaction.original_response()

async def setup(bot: commands.Bot):
	await bot.add_cog(RemindCog(bot))