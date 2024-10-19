import discord
from discord import app_commands, ui
from discord.ext import commands
from time import time
from utils import typingGame
from typing import Optional

class RaceModal(ui.Modal,title='Typing Race!'):
	_text = ui.TextInput(label='Type!',style=discord.TextStyle.short,
			placeholder='Start typing here!',max_length=4000)
	_text_preview = ui.TextInput(label="Type what's shown below!",style=discord.TextStyle.long,
			placeholder='N/A',max_length=1,required=False)
	def __init__(self, answer: str):
		super().__init__()
		self.start_time = time()
		self.answer = answer
		self._text_preview.placeholder = answer
	async def on_submit(self, interaction: discord.Interaction):
		speed = time()-self.start_time
		await interaction.response.defer()
		mistakes = typingGame.wagner_fischer(self.answer,self._text.value)
		acc = 100-(100/len(self.answer)*mistakes)
		if acc < 0: acc = 0
		raw_wpm = int(len(self._text.value.split())/(speed/60))
		if raw_wpm >= 310:
			await interaction.followup.send('https://www.indeed.com/career-advice/finding-a-job/fast-typing-jobs')
			return
		if raw_wpm >= 120:
			color = discord.Color.green()
		elif raw_wpm >= 70:
			color = discord.Color.yellow()
		else:
			color = discord.Color.red()
		embed = discord.Embed(
			title = 'Test complete!',
			description=f'You took `{speed:.2f}` seconds.\n'+
			f'You made `{mistakes}` mistakes ({acc:.2f}% accuracy)\n'+
			f'Your raw wpm (wpm ignoring mistakes) is `{raw_wpm}`',
			color=color
		)
		embed.set_author(name=interaction.user.display_name,icon_url=interaction.user.display_avatar)
		embed.set_footer(text='This is in beta so expect more features soon :)')
		await interaction.followup.send(embed=embed)

class RaceView(ui.View):
	message: Optional[discord.InteractionMessage] = None
	def __init__(self, answer: str):
		super().__init__()
		self.answer = answer
	
	async def on_timeout(self):
		if self.message is not None:
			await self.message.edit(view=None)

	@ui.button(label='Start Race!',style=discord.ButtonStyle.green)
	async def start_race_button(self, interaction: discord.Interaction, button: ui.Button):
		await interaction.response.send_modal(RaceModal(self.answer))
		
@app_commands.allowed_installs(guilds=True,users=True)
@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
class TypingGame(commands.GroupCog,name='type-race'):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	@app_commands.command(name='race')
	async def start_race(self, interaction: discord.Interaction):
		"""Starts a speed type test!
		"""
		paragraph = typingGame.random_paragraph() #spelling paragraph is freaking st**pid
		embed = discord.Embed(
			title='Typing Race!',description='Race starts when you click the button.',
			color=discord.Color.random()
		)
		view = RaceView(paragraph)
		await interaction.response.send_message(embed=embed,view=view)
		view.message = await interaction.original_response()

async def setup(bot: commands.Bot):
	await bot.add_cog(TypingGame(bot))