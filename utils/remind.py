import time
import aiosqlite
from utils.userVoted import has_user_voted
from typing import List, Self, Optional
from dataclasses import dataclass

#This was made a long while ago so even though this works, it may not be the best code out there

@dataclass
class Reminder:
	user: int
	timestamp: int
	reason: str
	channel: int
	id: int
	jump_url: Optional[str] = None

class BadReminder(Exception): ...
class ReminderNotValid(BadReminder):
	"""
	When a reminder is not found but there are reminders saved for that user
	"""
	def __init__(self, data: List[int]) -> None:
		self.data = data
		self.index = 0
	
	def __iter__(self) -> Self:
		return self
	
	def __next__(self) -> int:
		if self.index < len(self.data):
			self.index += 1
			return self.data[self.index-1]
		else:
			self.index = 0
			raise StopIteration
			
	def __getitem__(self, value: int) -> int:
		return self.data[value]

	def __str__(self) -> str:
		return ' '.join(map(lambda x: f'**{x}**',self.data))

class Reader:

	def __init__(self, path: str = "users.db") -> None:
		self.path = path
	
	async def __aenter__(self):
		self.connection = await aiosqlite.connect(database=self.path)
		self.cursor = await self.connection.cursor()
		return self

	async def __aexit__(self, *args):
		await self.cursor.close()
		await self.connection.close()

	async def make_table(self) -> None:
		await self.cursor.execute("""
		CREATE TABLE IF NOT EXISTS usuarios (
			user INTEGER NOT NULL,
			timestamp INTEGER NOT NULL,
			reason TEXT NOT NULL,
			channel INTEGER NOT NULL,
			id INTEGER NOT NULL,
			jump_url TEXT
		)
		""")
	
	async def max_id(self, user: int) -> int:
		await self.cursor.execute("""
		SELECT id FROM usuarios
		WHERE user = ?
		ORDER BY id DESC LIMIT 1
		""",(user,))
		value = await self.cursor.fetchone()
		return value[0] if value is not None else 0
	
	async def new_reminder(self, user: int, id: int, timestamp: int, channel_id: int,reason: str, jump_url: Optional[str] = None) -> None:
		await self.cursor.execute("""
		INSERT INTO usuarios VALUES
		(?, ?, ?, ?, ?, ?)
		""",(user,timestamp,reason,channel_id,id,jump_url))
		await self.connection.commit()

	async def delete_value(self, user: int, id: int) -> None:
		if await self.load_remind(user=user,id=id) is None:
			raise BadReminder(f'No reminder of id **{id}** found')
		await self.cursor.execute("""
		DELETE from usuarios WHERE user = ? AND id = ?
		""",(user,id))
		await self.connection.commit()

	async def update_value(self, user: int, id: int, timestamp: int, reason: str) -> None:
		await self.cursor.execute("""
		UPDATE usuarios
		SET timestamp = ?, reason = ?
		WHERE user = ? AND id = ?
		""",(timestamp,reason,user,id))
		await self.connection.commit()

	async def load_remind(self, user: int, id: int) -> Optional[Reminder]:
		await self.cursor.execute("""
		SELECT * FROM usuarios
		WHERE user = ? AND id = ?
		""",(user,id))
		result = await self.cursor.fetchone()
		return Reminder(*result) if result is not None else None
	
	async def load_all_user_reminders_id(self, user: int, order_by: str = 'timestamp') -> List[int]:
		await self.cursor.execute("""
		SELECT id FROM usuarios
		WHERE user = ? ORDER BY ?
		""",(user,order_by))
		results = await self.cursor.fetchall()
		return [result[0] for result in results]

	async def load_timestamp(self,actual_time: int) -> List[Reminder]:
		await self.cursor.execute("""
		SELECT * FROM usuarios
		WHERE timestamp - ? < 12
		ORDER BY timestamp ASC
		""",(actual_time,))
		results = await self.cursor.fetchall()
		return [Reminder(*result) for result in results]
	
	async def load_everything(self) -> List[Reminder]:
		await self.cursor.execute("""
		SELECT * FROM usuarios
		""")
		results = await self.cursor.fetchall()
		return [Reminder(*result) for result in results]

	async def load_all_user_reminders(self, user: int, limit: int = -1) -> List[Reminder]:
		await self.cursor.execute("""
		SELECT * FROM usuarios
		WHERE user = ? ORDER BY id LIMIT ?
		""",(user,limit))
		results = await self.cursor.fetchall()
		return [Reminder(*result) for result in results]
	
	async def load_autocomplete(self, user: int, reason: str, limit: int  =-1) -> List[Reminder]:
		await self.cursor.execute("""
		SELECT * FROM usuarios
		WHERE user = ? AND reason LIKE ? LIMIT ?
		""",(user,'%'+reason+'%',limit))
		results = await self.cursor.fetchall()
		return [Reminder(*result) for result in results]

async def add_remind(user: int,channel_id: Optional[int],reason: str, timestamp: int, jump_url: Optional[str] = None) -> Reminder:
	if channel_id is None:
		raise TypeError("You must provide a channel_id")
	if timestamp - time.time() > 31536000:
		raise BadReminder("You can't have a reminder with a time longer than a year")
	if len(reason) > 500:
		raise BadReminder("Your reminder's reason is way too big, to avoid excesive flood, the max length of your reason must not be larger than 500 characters (or 50 without a vote)")
	if len(reason) > 80 and not await has_user_voted(user_id=user):
		raise BadReminder("Your reminder's reason is way too big, to have a bigger limit please consider giving me a [vote](<https://top.gg/bot/778785822828265514/vote>) :D")
	async with Reader() as f:
		reminders_amount = len(await f.load_all_user_reminders_id(user=user))
		if reminders_amount > 50:
			raise BadReminder("You can't have more than 50 reminders active (or 5 without a vote)")
		if reminders_amount > 5 and not await has_user_voted(user_id=user):
			raise BadReminder("You can only have a maximum of 5 reminders at once, to be able to have more reminders consider giving me a [vote](<https://top.gg/bot/778785822828265514/vote>) :D")
		user_max_id = await f.max_id(user)
		await f.new_reminder(user=user,id=user_max_id+1,timestamp=timestamp,channel_id=channel_id,reason=reason,jump_url=jump_url)
	
	return Reminder(user,timestamp,reason,channel_id,user_max_id+1)

async def remove_remind(user: int, id: int):
	async with Reader() as f:
		await f.delete_value(user=user,id=id)

async def edit_remind(user: int, id: int, timestamp: Optional[int] = None, reason: str = '') -> Reminder:
	timestamp = timestamp or int(time.time())
	if timestamp - time.time() > 31536000:
		raise BadReminder("You can't have a reminder with a time longer than a year")
	user_voted = await has_user_voted(user_id=user)
	if len(reason) > 80 and not user_voted:
		raise BadReminder("Your reminder's reason is way too big, to have a bigger limit please consider giving me a [vote](<https://top.gg/bot/778785822828265514/vote>) :D")
	if len(reason) > 500:
		raise BadReminder("Your reminder's reason is way too big, to avoid excesive flood, the max length of your reason must not be larger than 500 characters")
	async with Reader() as f:
		value = await f.load_remind(user=user,id=id)
		if value is None:
			raise BadReminder(f'No reminder of id **{id}** found')
		reason = value.reason if reason == '' else reason
		if time.time() >= timestamp:
			timestamp = value.timestamp
		await f.update_value(user=user,id=id,timestamp=timestamp,reason=reason)
		new_reminder = await f.load_remind(user=user,id=id)
		if new_reminder is None:
			raise BadReminder(f"No reminder of id **{id}** found. But this shouldn't have happened, please contact the developer.")
		return new_reminder
	

async def check_remind(user: int, id: int) -> Reminder:
	async with Reader() as f:
		value = await f.load_remind(user=user,id=id)
		if value is None and await f.load_all_user_reminders_id(user=user) == []:
			raise BadReminder(f'No reminder of id **{id}** found')
		elif value is None:
			raise ReminderNotValid(await f.load_all_user_reminders_id(user=user))
		return value

async def check_remind_fire() -> List[Reminder]:
	async with Reader() as f:
		values = await f.load_timestamp(actual_time=int(time.time()))
		if values is None:
			raise BadReminder('No reminder to fire')
		return [value for value in values]

async def manual_add(user: int, channel_id: int, reason: str, timestamp: int, id: int, jump_url: Optional[str] = None):
	async with Reader() as f:
		await f.new_reminder(user=user,id=id,timestamp=timestamp,reason=reason,channel_id=channel_id,jump_url=jump_url)
