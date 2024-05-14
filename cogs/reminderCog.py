import discord
from discord import app_commands
from discord.ext import commands,tasks
import asyncio
from utils import remind
from time import time

class RemindCog(commands.GroupCog,name='reminder'):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	class Snooze(discord.ui.Button):
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
			self.view_ = discord.ui.View(timeout=1)
			# self.view_.add_item(self)
			# self.view_.add_item(discord.ui.Button(style=discord.ButtonStyle.green,label=f"Snooze for {15-self.minutes_added} minutes",disabled=True))
			self.view_.add_item(discord.ui.Button(style=discord.ButtonStyle.green,label=f"Snooze for 5 minutes",disabled=True))
			self.view_.add_item(discord.ui.Button(style=discord.ButtonStyle.green,label=f"Snooze for 10 minutes",disabled=True))
			embed = discord.Embed()
			try:
				values = await remind.add_remind(user=self.original_user_id,channel_id=interaction.channel_id,reason=self.reason,days=0,hours=0,minutes=self.minutes_added)
				embed.title = "Reminder snoozed!"
				embed.description = f"Reminder for <t:{values['timestamp']}> of id **{values['id']}**\nwith reason **\"{self.reason}\"** added successfully"
				embed.colour = discord.Colour.green()
			except ValueError as e:
				embed.title = "Reminder failed"
				embed.description = str(e)
				embed.colour = discord.Colour.red()
			except TypeError:
				print(f"something wrong happened, channel_id: {interaction.channel_id}")
			await interaction.response.edit_message(content=None,embed=embed,view=self.view_)
	class SnoozeView(discord.ui.View):
		def __init__(self,timeout: float):
			super().__init__(timeout=timeout)
		async def on_timeout(self):
			try:
				await self.message.edit(view=None)
			except (discord.Forbidden,discord.HTTPException):
				...

	@commands.Cog.listener()
	async def on_ready(self):
		print(f"{self.bot.user} currently in {len(self.bot.guilds)} servers:")
		for guild in self.bot.guilds:
			print(f"{guild.name} ({guild.member_count:,} members)")
		async with remind.Reader() as f:
			await f.make_table()
			print('table')
		try:
			self.loop_check.start()
		except RuntimeError:
			print('task already running. most likely because on_ready got called again')

	
	@tasks.loop(seconds=10)
	async def loop_check(self):
		try:
			items = await remind.check_remind_fire()
		except ValueError:
			return
		task_list = []
		for item in items:
			task_list.append(asyncio.create_task(self.send_reminders(item)))
		await asyncio.gather(*task_list)

	async def send_reminders(self, item: tuple[int,int,str,int,int]):
		await asyncio.sleep(item[1]-int(time()))
		await remind.remove_remind(item[0],item[4])
		view = self.SnoozeView(timeout=3600)
		view.add_item(self.Snooze(minutes_added=5,reason=item[2],original_user_id=item[0]))
		view.add_item(self.Snooze(minutes_added=10,reason=item[2],original_user_id=item[0]))
		embed = discord.Embed(
			title = 'You have been reminded!',
			description= f'Reason of your reminder: **{item[2]}**',
			colour=discord.Colour.green()
		)
		try:
			channel = await self.bot.fetch_channel(item[3])
			view.message = await channel.send(f'<@{item[0]}>',embed=embed,view=view)
		except (discord.Forbidden,discord.HTTPException):
			try:
				user = await self.bot.fetch_user(item[0])
				dm_channel = await user.create_dm()
				view.message = await dm_channel.send(f'<@{item[0]}>',embed=embed,view=view)
				await dm_channel.send('_Sending the reminder in your desired channel failed. So I instead reminded you here_')
			except (discord.HTTPException,discord.NotFound,discord.Forbidden):
				print(f"Couldn't send reminder to user {item[0]}")

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

	@commands.command()
	async def seeallreminders(self, ctx: commands.Context):
		if ctx.author.id != 624277615951216643:
			return
		content = ''
		async with remind.Reader() as f:
			for item in await f.load_everything():
				content += f'**User**: {item[0]}\n'
				content += f'**Timestamp**: <t:{item[1]}>\n'
				content += f'**Reason**: {item[2]}\n'
				content += f'**Channel**: {item[3]}\n'
				content += f'**ID**: {item[4]}\n'
			await ctx.send(content=content)


	@app_commands.command(description="Adds a reminder",name='add')
	@app_commands.describe(reason="Your reminder's reason",days="Days to wait",hours="Hours to wait",minutes="Minutes to wait")
	async def addreminder(self, interaction: discord.Interaction,reason: str,days: int = 0,hours: int = 0, minutes: int = 0):
		embed = discord.Embed()
		try:
			if ((days*86400) + (hours*3600) + (minutes*60)) <= 0:
				raise ValueError("You need to specify a valid time for the reminder")
			values = await remind.add_remind(user=interaction.user.id,channel_id=interaction.channel_id,reason=reason,days=days,hours=hours,minutes=minutes)
			embed.title = "Reminder created!"
			embed.description = f"Reminder for <t:{values['timestamp']}> of id **{values['id']}**\nwith reason **\"{reason}\"** added successfully"
			embed.colour = discord.Colour.green()
		except ValueError as e:
			embed.title = "Reminder failed"
			embed.description = str(e)
			embed.colour = discord.Colour.red()
		await interaction.response.send_message(embed=embed)
		
	@app_commands.command(description="Removes your current reminder",name='remove')
	@app_commands.describe(id="ID of the reminder to remove")
	async def removereminder(self, interaction: discord.Interaction,id: int):
		embed = discord.Embed()
		try:
			await remind.remove_remind(user=interaction.user.id,id=id)
			embed.title = "Removed reminder!"
			embed.description = f'Reminder of id **{id}** removed successfully'
			embed.colour = discord.Colour.green()
		except ValueError as e:
			embed.title = "Couldn't remove reminder"
			embed.description = str(e)
			embed.colour = discord.Colour.red()
		await interaction.response.send_message(embed=embed)

	@app_commands.command(description="Checks a specific reminder given the ID (if any)",name='check')
	@app_commands.describe(id="ID of the reminder to check")
	async def checkreminder(self, interaction: discord.Interaction,id: int):
		embed = discord.Embed()
		try:
			items = await remind.check_remind(user=interaction.user.id,id=id)
			embed.title = f"Found reminder of id {id}!"
			embed.description = f'This reminder will fire at <t:{items[1]}>\nWith reason **{items[2]}**'
			embed.colour = discord.Colour.green()
		except ValueError as e:
			embed.title = "No reminder found"
			embed.description = str(e)
			embed.description += '\nYou have no reminders'
			embed.colour = discord.Colour.red()
		except TypeError as e:
			# print(e,type(e),eval(str(e)))
			embed.title = "No reminder found"
			embed.description = f'No reminder of id **{id}** found.\nYour reminders: '
			for item in eval(str(e)):
				embed.description += f'**{item[0]}** '
			embed.colour = discord.Colour.red()
		await interaction.response.send_message(embed=embed)

	@app_commands.command(description="Edits a reminder",name='edit')
	@app_commands.describe(id="ID of the reminder to edit",reason="New reason for the reminder",days="New days to wait",hours="New hours to wait",minutes="New minutes to wait")
	async def editreminder(self, interaction: discord.Interaction, id: int, reason: str = '', days: int = 0, hours: int = 0, minutes: int = 0):
		embed = discord.Embed()
		try:
			items = await remind.edit_remind(user=interaction.user.id,id=id,reason=reason,days=days,hours=hours,minutes=minutes)
			embed.title = f"Edited reminder of id {id}"
			embed.description = f'This reminder will fire at <t:{items[1]}>\nWith reason **{items[2]}**'
			embed.colour = discord.Colour.green()
		except ValueError as e:
			embed.title = "Couldn't edit reminder"
			embed.description = str(e)
			embed.colour = discord.Colour.red()
		await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
	await bot.add_cog(RemindCog(bot))