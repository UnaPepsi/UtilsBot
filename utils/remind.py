import time
import aiosqlite
import aiohttp
from os import environ

headers = {'Authorization':environ['TOPGG']}

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
			user INTEGER,
			timestamp INTEGER,
			reason TEXT,
			channel INTEGER,
			id INTEGER
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
	
	async def new_reminder(self, user: int, id: int, timestamp: int, channel_id: int,reason: str) -> None:
		await self.cursor.execute("""
		INSERT INTO usuarios VALUES
		(?, ?, ?, ?, ?)
		""",(user,timestamp,reason,channel_id,id))
		await self.connection.commit()

	async def delete_value(self, user: int, id: int) -> None:
		if await self.load_remind(user=user,id=id) is None:
			raise ValueError(f'No reminder of id **{id}** found')
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

	async def load_remind(self, user: int, id: int) -> tuple:
		await self.cursor.execute("""
		SELECT * FROM usuarios
		WHERE user = ? AND id = ?
		""",(user,id))
		return await self.cursor.fetchone()
	
	async def load_all_user_reminders(self, user: int) -> list[tuple[int]]:
		await self.cursor.execute("""
		SELECT id FROM usuarios
		WHERE user = ? ORDER BY timestamp
		""",(user,))
		return await self.cursor.fetchall()

	async def load_timestamp(self,actual_time: int) -> list[tuple]:
		await self.cursor.execute("""
		SELECT * FROM usuarios
		WHERE timestamp - ? < 12
		ORDER BY timestamp ASC
		""",(actual_time,))
		return await self.cursor.fetchall()
	
	async def load_everything(self) -> list[tuple]:
		await self.cursor.execute("""
		SELECT * FROM usuarios
		""")
		return await self.cursor.fetchall()

async def add_remind(user: int,channel_id: int | None,reason: str, days: int, hours: int, minutes: int) -> dict[str,int]:
	if channel_id is None:
		raise TypeError("You must provide a channel_id")
	timestamp = int(time.time())+(days*86400)+(hours*3600)+(minutes*60)
	if timestamp - time.time() > 31536000:
		raise ValueError("You can't have a reminder with a time longer than a year")
	async with aiohttp.ClientSession() as session:
		async with session.get(f"https://top.gg/api/bots/778785822828265514/check?userId={user}",headers=headers) as resp:
			data: dict = await resp.json()
	user_voted = data.get('voted',0)
	if len(reason) > 50 and user_voted != 1:
		raise ValueError("Your reminder's reason is way too big, to have a bigger limit please consider giving me a vote on <https://top.gg/bot/778785822828265514/vote> :D")
	if len(reason) > 500:
		raise ValueError("Your reminder's reason is way too big, to avoid excesive flood, the max length of your reason must not be larger than 500 characters")
	async with Reader() as f:
		reminders_amount = len(await f.load_all_user_reminders(user=user))
		if reminders_amount > 5 and user_voted != 1:
			raise ValueError("You can only have a maximum of 5 reminders at once, to be able to have more reminders consider giving me a vote on <https://top.gg/bot/778785822828265514/vote> :D")
		if reminders_amount > 50:
			raise ValueError("You can't have more than 50 reminders active")
		user_max_id = await f.max_id(user)
		print(user_max_id,user_voted,user)
		await f.new_reminder(user=user,id=user_max_id+1,timestamp=timestamp,channel_id=channel_id,reason=reason)
	
	return {'id':user_max_id+1,'timestamp':timestamp}

async def remove_remind(user: int, id: int):
	async with Reader() as f:
		await f.delete_value(user=user,id=id)

async def edit_remind(user: int, id: int, days: int = 0, hours: int = 0, minutes: int = 0, reason: str = '') -> tuple:
	if (days*86400)+(hours*3600)+(minutes*60) > 31536000:
		raise ValueError("You can't have a reminder with a time longer than a year")
	async with aiohttp.ClientSession() as session:
		async with session.get(f"https://top.gg/api/bots/778785822828265514/check?userId={user}",headers=headers) as resp:
			data = await resp.json()
	try:
		user_voted = data['voted']
	except KeyError:
		user_voted = 0
	if len(reason) > 50 and user_voted != 1:
		raise ValueError("Your reminder's reason is way too big, to have a bigger limit please consider giving me a vote on <https://top.gg/bot/778785822828265514/vote> :D")
	if len(reason) > 500:
		raise ValueError("Your reminder's reason is way too big, to avoid excesive flood, the max length of your reason must not be larger than 500 characters")
	async with Reader() as f:
		value = await f.load_remind(user=user,id=id)
		if value is None:
			raise ValueError(f'No reminder of id **{id}** found')
		reason = value[2] if reason == '' else reason
		timestamp = value[1] if (days == 0 and hours == 0 and minutes == 0) else int(time.time())+(days*86400)+(hours*3600)+(minutes*60)
		await f.update_value(user=user,id=id,timestamp=timestamp,reason=reason)
		return await f.load_remind(user=user,id=id)
	

async def check_remind(user: int, id: int) -> tuple[int,int,str,int,int]:
	async with Reader() as f:
		value = await f.load_remind(user=user,id=id)
		if value is None and await f.load_all_user_reminders(user=user) == []:
			raise ValueError(f'No reminder of id **{id}** found')
		elif value is None:
			raise TypeError(await f.load_all_user_reminders(user=user))
		return value

async def check_remind_fire() -> list[tuple[int,int,str,int,int]]:
	async with Reader() as f:
		value = await f.load_timestamp(actual_time=int(time.time()))
		if value is None:
			raise ValueError('No reminder to fire')
		return value

async def manual_add(user: int, channel_id: int, reason: str, timestamp: int, id: int):
	async with Reader() as f:
		await f.new_reminder(user=user,id=id,timestamp=timestamp,reason=reason,channel_id=channel_id)
