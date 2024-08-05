import discord
from discord import app_commands
from discord import ui
from datetime import datetime
from discord.ext import commands
from utils.todo import TodoDB, NoTodoFound, BadTodo
from time import time
import logging
from typing import Optional, List
logger = logging.getLogger(__name__)

async def autocomplete_todo(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[int]]:
	async with TodoDB() as todo:
		if current == '':
			tasks_ids = await todo.load_all_user_todos_id(user=interaction.user.id,limit=25)
			if tasks_ids is None:
				return []
			choices_list: List[app_commands.Choice[int]] = []
			for task_id in tasks_ids:
				task_info = await todo.load_todo(user=interaction.user.id,id=task_id)
				choices_list.append(app_commands.Choice(name=f"{task_id}. {task_info.reason if len(task_info.reason) <= 30 else task_info.reason[:27]+'...'}",value=task_id))
			return choices_list
		else:
			try:
				task_info = await todo.load_todo(user=interaction.user.id,id=int(current))
				return [app_commands.Choice(name=f"{current}. {task_info.reason if len(task_info.reason) <= 30 else task_info.reason[:27]+'...'}",value=int(current))]
			except NoTodoFound:
				return []
			except ValueError:
				tasks_todo = await todo.load_autocomplete(user=interaction.user.id,reason=current,limit=25)
				if tasks_todo is None: return []
				return [app_commands.Choice(name=f"{task.id}. {task.reason if len(task.reason) <= 30 else task.reason[:27]+'...'}",value=task.id) for task in tasks_todo]

class TodoPaginator(ui.View):
	index = 0
	message: Optional[discord.InteractionMessage] = None
	def __init__(self, pages: List[int], user_view: int,timeout: Optional[int] = 180):
		super().__init__(timeout=timeout)
		self.pages = pages
		self.user_view = user_view
		self.edit_children()

	async def on_timeout(self):
		if self.message is not None:
			try:
				await self.message.edit(view=None)
			except discord.NotFound: ...

	async def check_todo(self, *, interaction: discord.Interaction, user: int, id: int):
		if interaction.user.id != self.user_view:
			await interaction.followup.send(f'<@{self.user_view}> ran this command so only them can interact with it',ephemeral=True)
			return
		async with TodoDB() as todo:
			try:
				self.pages = await todo.load_all_user_todos_id(user=user) or [] #make type checker happy
				if not self.pages:
					raise NoTodoFound()
				t = await todo.load_todo(user=user,id=id)
			except NoTodoFound:
				await interaction.edit_original_response(content='Something wrong happened :(',embed=None,view=None)
				return
			embed = discord.Embed()
			embed.title = 'Task found'
			embed.description = f'**TODO {interaction.user.mention}:**\n ```\n{t.reason}\n```'
			embed.colour = discord.Colour.green()
			embed.set_thumbnail(url=interaction.user.display_avatar.url)
			embed.set_footer(text=f'ID of task: {t.id}')
			embed.timestamp = datetime.fromtimestamp(t.timestamp)
			self.edit_children()
			await interaction.edit_original_response(embed=embed,view=self)

	def edit_children(self):
		self.go_first.disabled = self.pages[0] == self.pages[self.index]
		self.go_back.disabled = self.pages[0] == self.pages[self.index]
		self.go_forward.disabled = self.pages[-1] == self.pages[self.index]
		self.go_last.disabled = self.pages[-1] == self.pages[self.index]

	@ui.button(label='<<',style=discord.ButtonStyle.primary)
	async def go_first(self, interaction: discord.Interaction, button: ui.Button):
		await interaction.response.defer()
		self.index = 0
		await self.check_todo(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])
	
	@ui.button(label='<',style=discord.ButtonStyle.secondary)
	async def go_back(self, interaction: discord.Interaction, button: ui.Button):
		await interaction.response.defer()
		self.index -= 1
		await self.check_todo(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])
	
	@ui.button(emoji='\N{WASTEBASKET}',style=discord.ButtonStyle.red)
	async def remove_todo(self, interaction: discord.Interaction, button: ui.Button):
		if interaction.user.id != self.user_view:
			await interaction.response.send_message(f'<@{self.user_view}> ran this command so only them can interact with it',ephemeral=True)
			return
		await interaction.response.defer()
		async with TodoDB() as todo:
			try:
				await todo.delete_todo(user=interaction.user.id,id=self.pages.pop(self.index))
				self.index -= 1 if self.index != 0 else 0
			except NoTodoFound:
				await interaction.edit_original_response(content='Something wrong happened :(',embed=None,view=None)
				return
		if len(self.pages) != 0:
			await self.check_todo(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])
			return
		embed = discord.Embed(
			title='No more tasks',colour=discord.Colour.red(),description='You have no more tasks saved'
		)
		await interaction.edit_original_response(embed=embed,view=None)

	@ui.button(label='>',style=discord.ButtonStyle.secondary)
	async def go_forward(self, interaction: discord.Interaction, button: ui.Button):
		await interaction.response.defer()
		self.index += 1
		await self.check_todo(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])
	
	@ui.button(label='>>',style=discord.ButtonStyle.primary)
	async def go_last(self, interaction: discord.Interaction, button: ui.Button):
		await interaction.response.defer()
		self.index = len(self.pages)-1
		await self.check_todo(interaction=interaction,user=interaction.user.id,id=self.pages[self.index])

class TodoRemoveView(ui.View):
	message: Optional[discord.InteractionMessage] = None
	def __init__(self, timeout: int, user_view: int, todo_id: int):
		super().__init__(timeout=timeout)
		self.user_view = user_view
		self.todo_id = todo_id

	@ui.button(label='Remove TODO task',emoji='\N{WASTEBASKET}',style=discord.ButtonStyle.red)
	async def remove_todo(self, interaction: discord.Interaction, button: ui.Button):
		if interaction.user.id != self.user_view:
			await interaction.response.send_message(f'<@{self.user_view}> ran this command so only them can interact with it',ephemeral=True)
			return
		await interaction.response.defer()
		embed = discord.Embed()
		async with TodoDB() as todo:
			try:
				await todo.delete_todo(user=self.user_view,id=self.todo_id)
				embed.title = 'Task marked as solved!'
				embed.description = f'TODO task of ID `{self.todo_id}` removed'
				embed.colour = discord.Colour.green()
			except NoTodoFound as e:
				embed.title = 'Task removal failed'
				embed.description = str(e)
				embed.colour = discord.Colour.red()
		await interaction.edit_original_response(embed=embed,view=None)

	async def on_timeout(self):
		if self.message is not None:
			try: await self.message.edit(view=None)
			except discord.NotFound: ...

#Never have I ever known you could add decorators to classes... lol
@app_commands.allowed_installs(guilds=True,users=True)
@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
class TODOCog(commands.GroupCog,name='task'):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	async def cog_load(self):
		async with TodoDB() as todo:
			await todo.make_table()
		logger.info('TODO table created')

	@app_commands.checks.cooldown(2,7,key=lambda i: i.user.id)
	@app_commands.command(name='add')
	async def todo_create(self, interaction: discord.Interaction, reason: str):
		"""Creates a TODO task

		Args:
			reason (str): The reason of your task
		"""
		ephemeral = not isinstance(interaction.user,discord.User) and interaction.user.resolved_permissions is not None and not interaction.user.resolved_permissions.embed_links
		await interaction.response.defer(ephemeral=ephemeral)
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
		await interaction.followup.send(embed=embed)
	@todo_create.error
	async def todo_create_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
		if isinstance(error, app_commands.errors.CommandOnCooldown):
			await interaction.response.send_message("Please don't spam this command :(",ephemeral=True)
		else: raise error

	@app_commands.command(name='solve')
	@app_commands.autocomplete(id=autocomplete_todo)
	async def todo_solve(self, interaction: discord.Interaction, id: int):
		"""Marks as solved a TODO task (removes a task)

		Args:
			id (int): The ID of your task to remove
		"""
		ephemeral = not isinstance(interaction.user,discord.User) and interaction.user.resolved_permissions is not None and not interaction.user.resolved_permissions.embed_links
		await interaction.response.defer(ephemeral=ephemeral)
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
		await interaction.followup.send(embed=embed)

	@app_commands.command(name='check')
	@app_commands.autocomplete(id=autocomplete_todo)
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
				view = TodoRemoveView(timeout=360,user_view=interaction.user.id,todo_id=id)
			except NoTodoFound as e:
				embed.title = 'No task found'
				embed.description = str(e)
				embed.colour = discord.Colour.red()
				view = discord.utils.MISSING
		await interaction.response.send_message(embed=embed,view=view)
		if isinstance(view,TodoRemoveView):
			try: view.message = await interaction.original_response()
			except discord.DiscordException: logger.warning('Could not set message to view')

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
		if isinstance(view,TodoPaginator):
			try:
				view.message = await interaction.original_response()
			except discord.DiscordException:
				view.message = None
				logger.warning('Could not set message to view')

async def setup(bot: commands.Bot):
	await bot.add_cog(TODOCog(bot))