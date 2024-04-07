import discord,remind
from discord.ext import commands,tasks


def run_discord_bot():
	client = commands.Bot(command_prefix="xd",intents=discord.Intents.all())
		
	@client.event
	async def on_ready():
		print(f"Bot is running. Currently in {len(client.guilds)} servers:")
		for guild in client.guilds:
			print(f"{guild.name} ({guild.member_count} members)")
		async with remind.Reader() as f:
			await f.make_table()
			print('table')
		loop_check.start()

	
	@tasks.loop(seconds=10)
	async def loop_check():
		try:
			items = await remind.check_remind_fire()
		except ValueError:
			return
		embed = discord.Embed(
			title = 'You have been reminded!',
			description= f'Reason of your reminder: **{items[2]}**',
			colour=discord.Colour.green()
		)
		try:
			channel = await client.fetch_channel(items[3])
			await channel.send(f'<@{items[0]}>',embed=embed)
			await remind.remove_remind(items[0],items[4])
		except (discord.Forbidden,discord.HTTPException):
			try:
				user = await client.fetch_user(items[0])
				dm_channel = await user.create_dm()
				await dm_channel.send(f'<@{items[0]}>',embed=embed)
				await dm_channel.send('_Sending the reminder in your desired channel failed. So I instead reminded you here_')
				await remind.remove_remind(items[0],items[4])
			except (discord.HTTPException,discord.NotFound,discord.Forbidden):
				await remind.remove_remind(items[0],items[4])
				return


	@client.command()
	async def botsync(ctx: commands.Context):
		if ctx.author.id != 624277615951216643:
			return
		await client.tree.sync()

	@client.command()
	async def add(ctx: commands.Context,user: int, timestamp: int, channel_id: int, id: int, *reason: str):
		if ctx.author.id != 624277615951216643:
			return
		reason_str = ' '.join(reason)
		await remind.manual_add(user=user,channel_id=channel_id,reason=reason_str,timestamp=timestamp,id=id)
		check = await remind.check_remind(user=user,id=id)
		await ctx.send(f'{check}')

	@client.command()
	async def seeallreminders(ctx: commands.Context):
		async with remind.Reader() as f:
			await ctx.send(f'{await f.load_everything()}')


	@client.tree.command(description="Adds a reminder")
	async def addreminder(interaction: discord.Interaction,reason: str,days: int = 0,hours: int = 0, minutes: int = 0):
		embed = discord.Embed()
		try:
			values = await remind.add_remind(user=interaction.user.id,channel_id=interaction.channel_id,reason=reason,days=days,hours=hours,minutes=minutes)
			embed.title = "Reminder created!"
			embed.description = f"Reminder for <t:{values['timestamp']}> of id **{values['id']}**\nwith reason **\"{reason}\"** added successfully"
			embed.colour = discord.Colour.green()
		except ValueError as e:
			embed.title = "Reminder failed"
			embed.description = str(e)
			embed.colour = discord.Colour.red()
		await interaction.response.send_message(embed=embed)
		
	@client.tree.command(description="Removes your current reminder")
	async def removereminder(interaction: discord.Interaction,id: int):
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

	@client.tree.command(description="Checks a specific reminder given the ID (if any)")
	async def checkreminder(interaction: discord.Interaction,id: int):
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

	with open("jaja.txt","r") as f:
		client.run(f.readlines()[0])
