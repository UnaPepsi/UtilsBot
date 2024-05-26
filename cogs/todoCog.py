import discord
from discord import app_commands
from discord import ui
from datetime import datetime
from discord.ext import commands
from utils.todo import TodoDB, NoTodoFound, BadTodo
from time import time

class TodoPaginator(ui.View):
	index = 0
	def __init__(self, pages: list[int], user_view: int,timeout: int | None = 180):
		super().__init__(timeout=timeout)
		self.pages = pages
		self.user_view = user_view
		self.edit_children()

	async def on_timeout(self):
		await self.message.edit(view=None)

	async def check_todo(self, *, interaction: discord.Interaction, user: int, id: int):
		if interaction.user.id != self.user_view:
			await interaction.response.send_message(f'<@{self.user_view}> ran this command so only them can interact with it',ephemeral=True)
			return
		async with TodoDB() as todo:
			try:
				self.pages = await todo.load_all_user_todos_id(user=user)
				t = await todo.load_todo(user=user,id=id)
			except NoTodoFound:
				await interaction.response.edit_message(content='Something wrong happened :(',embed=None,view=None)
				return
			embed = discord.Embed()
			embed.title = 'Task found'
			embed.description = f'**TODO {interaction.user.mention}:**\n ```\n{t.reason}\n```'
			embed.colour = discord.Colour.green()
			embed.set_thumbnail(url=interaction.user.display_avatar.url)
			embed.set_footer(text=f'ID of task: {t.id}')
			embed.timestamp = datetime.fromtimestamp(t.timestamp)
			self.edit_children()
			await interaction.response.edit_message(embed=embed,view=self)

	def edit_children(self):
		self.go_first.disabled = self.pages[0] == self.pages[self.index]
		self.go_back.disabled = self.pages[0] == self.pages[self.index]
		self.go_forward.disabled = self.pages[-1] == self.pages[self.index]
		self.go_last.disabled = self.pages[-1] == self.pages[self.index]

	@ui.button(label='<<',style=discord.ButtonStyle.primary)
	async def go_first(self, interaction: discord.Interaction, button: discord.Button):
		self.index = 0
		await self.check_todo(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])
	
	@ui.button(label='<',style=discord.ButtonStyle.secondary)
	async def go_back(self, interaction: discord.Interaction, button: discord.Button):
		self.index -= 1
		await self.check_todo(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])
	
	@ui.button(emoji='\N{WASTEBASKET}',style=discord.ButtonStyle.red)
	async def remove_todo(self, interaction: discord.Interaction, button: discord.Button):
		if interaction.user.id != self.user_view:
			await interaction.response.send_message(f'<@{self.user_view}> ran this command so only them can interact with it',ephemeral=True)
			return
		async with TodoDB() as todo:
			try:
				await todo.delete_todo(user=interaction.user.id,id=self.pages.pop(self.index))
				self.index -= 1 if self.index != 0 else 0
			except NoTodoFound:
				await interaction.response.edit_message(content='Something wrong happened :(',embed=None,view=None)
				return
		if len(self.pages) != 0:
			await self.check_todo(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])
			return
		embed = discord.Embed(
			title='No more tasks',colour=discord.Colour.red(),description='You have no more tasks saved'
		)
		await interaction.response.edit_message(embed=embed,view=None)

	@ui.button(label='>',style=discord.ButtonStyle.secondary)
	async def go_forward(self, interaction: discord.Interaction, button: discord.Button):
		self.index += 1
		await self.check_todo(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])
	
	@ui.button(label='>>',style=discord.ButtonStyle.primary)
	async def go_last(self, interaction: discord.Interaction, button: discord.Button):
		self.index = len(self.pages)-1
		await self.check_todo(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])
	
class TodoRemoveButton(ui.Button):
	def __init__(self, id: int, user_button: int):
		super().__init__(label='Remove TODO task',emoji='\N{WASTEBASKET}',style=discord.ButtonStyle.red)
		self.id = id
		self.user_button = user_button
	async def callback(self, interaction: discord.Interaction):
		if interaction.user.id != self.user_button:
			await interaction.response.send_message(f'<@{self.user_view}> ran this command so only them can interact with it',ephemeral=True)
			return
		embed = discord.Embed()
		async with TodoDB() as todo:
			try:
				await todo.delete_todo(user=self.user_button,id=self.id)
				embed.title = 'Task marked as solved!'
				embed.description = f'TODO task of ID `{self.id}` removed'
				embed.colour = discord.Colour.green()
			except NoTodoFound as e:
				embed.title = 'Task removal failed'
				embed.description = str(e)
				embed.colour = discord.Colour.red()
		await interaction.response.edit_message(embed=embed,view=None)

class TODOCog(commands.GroupCog,name='task'):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_ready(self):
		async with TodoDB() as todo:
			await todo.make_table()
		print('table3')

	@app_commands.checks.cooldown(2,7,key=lambda i: i.user.id)
	@app_commands.command(name='add')
	async def todo_create(self, interaction: discord.Interaction, reason: str):
		"""Creates a TODO task

		Args:
			reason (str): The reason of your task
		"""
		embed = discord.Embed()
		async with TodoDB() as todo:
			try:
				created_todo = await todo.new_todo(user=interaction.user.id,timestamp=int(time()),reason=reason)
				embed.title = 'Task created!'
				embed.description = f'**TODO {interaction.user.mention}:**\n ```\n{reason}\n```'
				embed.colour = discord.Colour.green()
				embed.set_thumbnail(url=interaction.user.display_avatar.url)
				embed.set_footer(text=f'ID of task: {created_todo.id}')
				embed.timestamp = datetime.fromtimestamp(created_todo.timestamp)
			except BadTodo as e:
				embed.title = 'Task failed'
				embed.description = str(e)
				embed.colour = discord.Colour.red()
		await interaction.response.send_message(embed=embed)
	@todo_create.error
	async def todo_create_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
		if isinstance(error, app_commands.errors.CommandOnCooldown):
			await interaction.response.send_message("Please don't spam this command :(",ephemeral=True)
		else: raise error

	@app_commands.command(name='solve')
	async def todo_solve(self, interaction: discord.Interaction, id: int):
		"""Marks as solved a TODO task (removes a task)

		Args:
			id (int): The ID of your task to remove
		"""
		embed = discord.Embed()
		async with TodoDB() as todo:
			try:
				await todo.delete_todo(user=interaction.user.id,id=id)
				embed.title = 'Task marked as solved!'
				embed.description = f'TODO task of ID `{id}` removed'
				embed.colour = discord.Colour.green()
			except NoTodoFound as e:
				embed.title = 'Task removal failed'
				embed.description = str(e)
				embed.colour = discord.Colour.red()
		await interaction.response.send_message(embed=embed)

	@app_commands.command(name='check')
	async def todo_check(self, interaction: discord.Interaction, id: int):
		"""Checks a saved TODO task

		Args:
			id (int): The ID of the task to check
		"""
		embed = discord.Embed()
		async with TodoDB() as todo:
			try:
				t = await todo.load_todo(user=interaction.user.id,id=id)
				embed.title = 'Task found'
				embed.description = f'**TODO {interaction.user.mention}:**\n ```\n{t.reason}\n```'
				embed.colour = discord.Colour.green()
				embed.set_thumbnail(url=interaction.user.display_avatar.url)
				embed.set_footer(text=f'ID of task: {t.id}')
				embed.timestamp = datetime.fromtimestamp(t.timestamp)
				view = ui.View(timeout=360)
				view.add_item(TodoRemoveButton(id,interaction.user.id))
				view.on_timeout = lambda : view.message.edit(view=None)
			except NoTodoFound as e:
				embed.title = 'No task found'
				embed.description = str(e)
				embed.colour = discord.Colour.red()
				view = discord.utils.MISSING
		await interaction.response.send_message(embed=embed,view=view)
		view.message = await interaction.original_response()

	@app_commands.command(name='list')
	async def todo_list(self, interaction: discord.Interaction):
		"""Lists all your saved tasks
		"""
		embed = discord.Embed()
		async with TodoDB() as todo:
			try:
				all_todos = await todo.load_all_user_todos_id(user=interaction.user.id)
				assert all_todos is not None, 'You have no tasks saved'
				t = await todo.load_todo(user=interaction.user.id,id=all_todos[0])
				embed.title = 'Task found'
				embed.description = f'**TODO {interaction.user.mention}:**\n ```\n{t.reason}\n```'
				embed.colour = discord.Colour.green()
				embed.set_thumbnail(url=interaction.user.display_avatar.url)
				embed.set_footer(text=f'ID of task: {t.id}')
				embed.timestamp = datetime.fromtimestamp(t.timestamp)
				view = TodoPaginator(pages=all_todos,user_view=interaction.user.id,timeout=360)
			except (NoTodoFound,AssertionError) as e:
				embed.title = 'No task found'
				embed.description = str(e)
				embed.colour = discord.Colour.red()
				view = discord.utils.MISSING
		await interaction.response.send_message(embed=embed,view=view)
		view.message = await interaction.original_response()

async def setup(bot: commands.Bot):
	await bot.add_cog(TODOCog(bot))