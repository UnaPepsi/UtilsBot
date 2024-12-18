import aiosqlite
from typing import Self, List
from utils.userVoted import has_user_voted
from dataclasses import dataclass

class NoTodoFound(Exception): ...
class BadTodo(Exception): ...

@dataclass
class Todo:
	user: int
	id: int
	timestamp: int
	reason: str
	def __init__(self,user: int, id: int, timestamp: int, reason: str):
		self.user = user
		self.id = id
		self.timestamp = timestamp
		self.reason = reason

class TodoDB:

	def __init__(self, path: str = "users.db") -> None:
		self.path = path
	
	async def __aenter__(self) -> Self:
		self.connection = await aiosqlite.connect(database=self.path)
		self.cursor = await self.connection.cursor()
		return self

	async def __aexit__(self, *args) -> None:
		await self.cursor.close()
		await self.connection.close()

	async def make_table(self) -> None:
		"""
		Creates the Todo table if it doesn't exist
		"""
		
		await self.cursor.execute("""
		CREATE TABLE IF NOT EXISTS todos (
			user INTEGER NOT NULL,
			id INTEGER NOT NULL,
			timestamp INTEGER,
			reason TEXT NOT NULL
		)
		""")
	
	async def new_todo(self, *, user: int,timestamp: int, reason: str) -> Todo:
		"""
		Creates a new Todo.

		user `int`: The user ID
		timestamp `int`: The creation time of the Todo
		reason `str`: The reason of the Todo creation
		"""
		if len(reason) > 50 and not await has_user_voted(user_id=user):
			raise BadTodo("Your task's reason is way too big, to have a bigger limit please consider giving me a [vote](<https://top.gg/bot/778785822828265514/vote>) :D")
		elif (task_amounts:=await self.load_todo_amounts(user=user)) >= 10 and not await has_user_voted(user_id=user):
			raise BadTodo("You can't have more than 10 active tasks at once. Consider giving me a [vote](<https://top.gg/bot/778785822828265514/vote>) to increase the limit :D")
		elif len(reason) > 250:
			raise BadTodo("Your task's reason can't be larger than 250 characters")
		elif task_amounts > 50:
			raise BadTodo("You can't have more than 50 tasks active at once")
		await self.cursor.execute("""
		INSERT INTO todos VALUES (?, (SELECT IFNULL(MAX(id)+1,0) FROM todos WHERE user=?), ?, ?)
		""",(user,user,timestamp,reason))
		await self.connection.commit()
		return Todo(user,await self.load_todo_amounts(user=user),timestamp=timestamp,reason=reason)

	async def delete_todo(self, *, user: int, id: int) -> None:
		"""
		Deletes a saved Todo.
		
		user `int`: The user ID
		id `int`: The ID of the saved Todo
		"""

		if await self.load_todo(user=user,id=id) is None:
			raise NoTodoFound(f'No task of ID **{id}** found')
		await self.cursor.execute("""
		DELETE from todos WHERE user = ? AND id = ?
		""",(user,id))
		await self.connection.commit()

	async def edit_todo(self, *, user: int, id: int, reason: str) -> None:
		"""
		Edits a saved Todo

		user `int`: The user ID
		id `int`: The ID of the saved Todo
		reason `str`: The reason of the Todo creation
		"""

		try:
			await self.load_todo(user=user,id=id)
		except NoTodoFound:
			raise NoTodoFound(f'No task of ID {id} found') #lol
		await self.cursor.execute("""
		UPDATE todos
		SET reason = ?
		WHERE user = ? AND id = ?
		""",(reason,user,id))
		await self.connection.commit()

	async def load_todo(self, *, user: int, id: int | None) -> Todo:
		"""
		Returns a saved Todo

		user `int`: The user ID
		id `int`: The ID of the saved Todo
		"""
		await self.cursor.execute("""
		SELECT * FROM todos
		WHERE user = ? AND id = ?
		""",(user,id))
		results = await self.cursor.fetchone()
		if results is None:
			if not (user_todo_ids := await self.load_all_user_todos_id(user=user)):
				raise NoTodoFound(f'No task of ID **{id}** found.\n<@{user}> tasks: {" ".join(map(lambda x: f"{x}",user_todo_ids))}')
			else:
				raise NoTodoFound('You have no tasks saved')
		return Todo(*results)
	
	async def load_all_user_todos_id(self, *, user: int, limit: int = -1) -> List[int]:
		"""
		Returns all the IDs

		user `int`: The user ID
		limit `int`: The lookup limit
		"""
		await self.cursor.execute("""
		SELECT id FROM todos
		WHERE user = ? LIMIT ?
		""",(user,limit))
		results = await self.cursor.fetchall()
		return [result[0] for result in results]

	async def load_autocomplete(self,*, user: int, reason: str, limit: int = -1) -> List[Todo]:
		"""
		Returns a list of the TODOs that have a reason LIKE the given reason

		user `int`: The user ID
		reason `str`: The reason of the TODO creation
		limit `int`: The lookup limit
		"""
		await self.cursor.execute("""
		SELECT * FROM todos
		WHERE user = ? AND reason LIKE ? LIMIT ?
		""",(user,'%'+reason+'%',limit))
		results = await self.cursor.fetchall()
		return [Todo(*result) for result in results]

	async def load_todo_amounts(self,*, user: int) -> int:
		"""
		Returns the amount of Todos a user has
		"""
		await self.cursor.execute("""
		SELECT COUNT(user) FROM todos
		WHERE user = ?
		""",(user,))
		result = await self.cursor.fetchone()
		return result[0] if result is not None else 0