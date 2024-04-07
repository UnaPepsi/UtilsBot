import discord,remind
from discord.ext import commands,tasks


def run_discord_bot():
	client = commands.Bot(command_prefix="xd",intents=discord.Intents.all())

	# class Roles(discord.ui.View):
	# 	def __init__(self):
	# 		super().__init__(timeout=None)
	# 	@discord.ui.button(label="English",style=discord.ButtonStyle.green,emoji="<:us:1204578320898072668>")
	# 	async def english(self, interaction: discord.Interaction, button: discord.ui.Button):
	# 		# role = discord.utils.get(interaction.user.get_role(1116808264915624057))
	# 		role = interaction.guild.get_role(1204562912115429486)
	# 		member = interaction.user
	# 		if role in member.roles:
	# 			await member.remove_roles(role,reason="Unchecked role button")
	# 			await interaction.response.send_message("English role removed successfully",ephemeral=True)
	# 			return
	# 		# discord.utils.get
	# 		await member.add_roles(role,reason="Checked role button")
	# 		await interaction.response.send_message("English role added successfully",ephemeral=True)

	# 	@discord.ui.button(label="Spanish",style=discord.ButtonStyle.green,emoji="<:spain:1204578612154728538>")
	# 	async def spanish(self, interaction: discord.Interaction, button: discord.ui.Button):
	# 		# role = discord.utils.get(interaction.user.get_role(1116808264915624057))
	# 		role = interaction.guild.get_role(1200962062067707945)
	# 		member = interaction.user
	# 		if role in member.roles:
	# 			await member.remove_roles(role,reason="Unchecked role button")
	# 			await interaction.response.send_message("Rol Español removido satisfactoriamente",ephemeral=True)
	# 			return
	# 		# discord.utils.get
	# 		await member.add_roles(role)
	# 		await interaction.response.send_message("Se te agregó el rol Español correctamente",ephemeral=True)
		
	@client.event
	async def on_ready():
		await client.tree.sync()
		loop_check.start()
		print(f"Bot is running. Currently in {len(client.guilds)} servers:")
		for guild in client.guilds:
			# owner = guild.owner
			# try:
			# 	dm_channel = await owner.create_dm()
			# 	await dm_channel.send("ReminderBot changed hosting, if you had any reminders please make sure they have not been deleted. -holyhosting (aka Pepsi)")
			# except:
			# 	print(f"Couldn't DM {owner}")
			print(f"{guild.name} ({guild.member_count} members)")
		# channel = client.get_guild(813927669908766791).get_channel(1204580190538436618)
		# # messages = channel.history(limit=5)
		# # print(messages)
		# # async for message in messages:
		# # 	print(message.content)
		# message = await channel.fetch_message(1204589317641601034)
		# embed = discord.Embed(
		# 	title="NamePlease's Discord",
		# 	description="・To enhance your experience, please choose a language\n ・Para mejorar tu experiencia, selecciona un idioma",
		# 	color=discord.Colour.green()
		# )
		# await message.edit(embed=embed,view=Roles())


	
	# @client.event
	# async def on_message(message: discord.Message):
	# 	pass
		# if message.author.id != 624277615951216643:
		# 	return
		# channel = client.get_channel(1200961883994333274)
		# embed = discord.Embed(
		# 	title="Discord Rules",
		# 	description=message.content,
		# 	colour=discord.Colour.red()
		# )
		# await channel.send(embed=embed)

	@tasks.loop(seconds=10)
	async def loop_check():
		items = remind.check_remind()
		if items:
			# print(items)
			remind.remove_reminder(items[0],items[3])
			if items[4]:
				user = client.get_user(items[0])
				dm_channel = await user.create_dm()
				await dm_channel.send(f"You have been reminded!\nReason: {items[2]}")
			else:
				channel = client.get_channel(items[1])
				await channel.send(f"<@{items[0]}>, you have been reminded!\nReason: {items[2]}")

	@client.command()
	async def jaja(ctx,user: int,*msg: str):
		if ctx.author.id != 624277615951216643:
			return
		usuario = client.get_user(user)
		dm_channel = await usuario.create_dm()
		mensaje = ""
		for word in msg:
			mensaje += word+" "
		await dm_channel.send(f"{mensaje}")
		await ctx.send("done")

	@client.tree.command(description="Adds a reminder")
	async def addreminder(interaction: discord.Interaction,reason: str,days: int,hours: int, minutes: int):
		is_dm = ""
		if interaction.channel.type is discord.ChannelType.private:
			is_dm = "yes"
		await interaction.response.send_message(remind.add_remind(interaction.user.id,interaction.channel_id,reason,days,hours,minutes,is_dm))
	
	@client.tree.command(description="Removes your current reminder")
	async def removereminder(interaction: discord.Interaction,id: int):
		await interaction.response.send_message(remind.remove_reminder(interaction.user.id,id=id))

	@client.tree.command(description="Checks a specific reminder given the ID (if any)")
	async def checkreminder(interaction: discord.Interaction,id: int):
		items = remind.user_check_remind(interaction.user.id,id)
		if type(items) == str:
			await interaction.response.send_message(items)
		else:
			await interaction.response.send_message(f"That reminder id could no be found. Your reminder IDs:\n `{items[1]}`")
	# @client.command()
	# async def reaction(ctx):
	# 	if ctx.author.id not in [624277615951216643,1155209588254195854,347939231265718272,800432216147755049]:
	# 		return
	# 	# view = discord.ui.View()
	# 	# button = discord.ui.Button(label="jajaja")
	# 	# view.add_item(button)
	# 	view = Roles()
	# 	# button = discord.ui.Button(label="el pepe")
	# 	# view.add_item(button)
	# 	embed = discord.Embed(
	# 		title="NamePlease's Discord",
	# 		description="・To enhance your experience, please choose a language\n ・Para mejorar tu experiencia, selecciona un idioma",
	# 		color=discord.Colour.green()
	# 	)
	# 	await ctx.send(embed=embed,view=view)



















	with open("jaja.txt","r") as f:
		client.run(f.readline())