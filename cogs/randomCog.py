import discord
from discord import app_commands
from discord.ext import commands
from utils.bypassUrl import bypass
from utils.websiteSS import get_ss, BadURL, BadResponse

class RandomCog(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
	
	@app_commands.command(name='bypassurl',description='Tries to unshorten a URL')
	@app_commands.describe(url='The URL to unshorten')
	async def bypassurl(self, interaction: discord.Interaction, url: str):
		try:
			await interaction.response.send_message(await bypass(url=url))
		except KeyError:
			await interaction.response.send_message('Could not unshorten that link')
		except ValueError:
			await interaction.response.send_message('Invalid URL')

	@app_commands.describe(user='The user to check')
	@app_commands.command(name='pfp',description="Shows someone's profile picture")
	async def pfp(self, interaction: discord.Interaction, user: discord.User):
		embed = discord.Embed(
			title = f"{user.display_name}'s profile picture",
			colour=discord.Colour.random())
		embed.set_image(url=user.display_avatar.url)
		await interaction.response.send_message(embed=embed)

	@app_commands.command(name='suggestion',description="Gives a suggestion to the bot's author :)")
	@app_commands.describe(suggestion='The suggestion to give')
	async def suggest(self, interaction: discord.Interaction, suggestion: str):
		if len(suggestion) > 4000:
			await interaction.response.send_message("A suggestion can't be larger than 4000 characters :<")
			return
		owner = await self.bot.fetch_user(624277615951216643)
		dm_channel = await owner.create_dm()
		embed = discord.Embed(
			title = f'New suggestion!',
			description=suggestion,color=discord.Colour.green())
		embed.add_field(name='Author:',value=f'{interaction.user.mention}')
		await dm_channel.send(embed=embed)
		await interaction.response.send_message('Suggestion sent. Thank you :D',ephemeral=True)
	
	@app_commands.command(name='screenshot',description='Takes a screenshot of a given website')
	@app_commands.describe(link='The URL of the desired website screenshot')
	async def screenshot(self, interaction: discord.Interaction, link: str):
		if not interaction.channel.is_nsfw():
			await interaction.response.send_message('This command is only available for channels with NSFW enabled')
			return
		await interaction.response.defer()
		try:
			fbytes = await get_ss(link=link)
		except BadURL:
			await interaction.followup.send('Must be a valid link')
		except BadResponse:
			await interaction.followup.send('An error happened :(')
		else:
			embed = discord.Embed(
				title = f'Screenshot taken from {link}',
				colour = discord.Colour.green(),
			)
			embed.set_image(url='attachment://image.png')
			await interaction.followup.send(file=discord.File(fbytes,filename='image.png'),embed=embed)