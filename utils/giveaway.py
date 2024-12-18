import aiosqlite
from typing import Self, List, Union, Dict
from dataclasses import dataclass

@dataclass
class Giveaway:
	id: int
	channel_id: int
	timestamp: int
	prize: str
	winners: int
	hoster_id: int

@dataclass
class Participant:
	participant_id: int
	giveaway_id: int

class GiveawayDB:

	def __init__(self, path: str = 'users.db') -> None:
		self.path = path

	async def __aenter__(self) -> Self:
		self.connection = await aiosqlite.connect(self.path)
		self.cursor = await self.connection.cursor()
		await self.cursor.execute("PRAGMA foreign_keys = ON")
		return self
	
	async def __aexit__(self, *args) -> None:
		await self.cursor.close()
		await self.connection.close()

	async def make_table(self):
		await self.cursor.execute("""
		CREATE TABLE IF NOT EXISTS giveaways (
			id INTEGER NOT NULL PRIMARY KEY,
			channel_id INTEGER NOT NULL,
			timestamp INTEGER NOT NULL,
			prize TEXT NOT NULL,
			winners INTEGER NOT NULL,
			hoster_id INTEGER NOT NULL
		)
		""")
		await self.cursor.execute("""
		CREATE TABLE IF NOT EXISTS participants (
			participant_id INTEGER NOT NULL,
			giveaway_id INTEGER NOT NULL,
			FOREIGN KEY(giveaway_id) REFERENCES giveaways(id) ON DELETE CASCADE
		)
		""")

	async def fetch_participants(self,*,giveaway_id: int) -> List[int]:
		await self.cursor.execute("""
		SELECT DISTINCT participant_id FROM participants
		WHERE giveaway_id = ?
		""",(giveaway_id,))
		results = await self.cursor.fetchall()
		assert results, 'No participants'
		return [result[0] for result in results]
	
	async def fetch_giveaway(self,*,giveaway_id: int) -> Giveaway:
		await self.cursor.execute("""
		SELECT * FROM giveaways WHERE id = ?
		""",(giveaway_id,))
		result = await self.cursor.fetchone()
		assert result is not None, 'No giveaway found'
		return Giveaway(*result)

	async def giveaway_exists(self,*,giveaway_id: int) -> bool:
		"""
		Returns True if a giveaway with the given id exists
		"""
		await self.cursor.execute("""
		SELECT id FROM giveaways WHERE id = ?
		""",(giveaway_id,))
		results = await self.cursor.fetchone()
		return results != None

	async def check_timestamp_fire(self,*, time: int) -> List[Giveaway]:
		await self.cursor.execute("""
		SELECT * from giveaways
		WHERE timestamp - ? < 12
		ORDER BY timestamp ASC
		""",(time,))
		results = await self.cursor.fetchall()
		assert results != [], 'No giveaway to fire'
		return [Giveaway(*result) for result in results]
	
	async def create_giveaway(self, *,id: int, channel_id:int, time: int, prize: str, winners: int, user_id: int) -> None:
		await self.cursor.execute("""
		INSERT INTO giveaways VALUES (?, ?, ?, ?, ?, ?)
		""",(id,channel_id,time,prize,winners,user_id))
		await self.connection.commit()

	async def delete_giveaway(self, giveaway_id: int) -> None:
		assert await self.giveaway_exists(giveaway_id=giveaway_id), 'No giveaway found'
		await self.cursor.execute("""
		DELETE FROM giveaways WHERE id = ?
		""",(giveaway_id,))
		await self.connection.commit()

	async def insert_user(self,*, user: int, giveaway_id: int) -> None:
		assert await self.giveaway_exists(giveaway_id=giveaway_id), 'No giveaway found'
		await self.cursor.execute("""
		INSERT INTO participants VALUES (?, ?)
		""",(user,giveaway_id))
		await self.connection.commit()

	async def remove_user(self,*,user:int, giveaway_id: int) -> None:
		assert await self.user_already_in(user=user,giveaway_id=giveaway_id), 'User not in that giveaway'
		await self.cursor.execute("""
		DELETE FROM participants WHERE participant_id = ? AND giveaway_id = ?
		""",(user,giveaway_id))
		await self.connection.commit()

	async def user_already_in(self,*,user:int,giveaway_id: int) -> bool:
		assert await self.giveaway_exists(giveaway_id=giveaway_id), 'No giveaway found'
		await self.cursor.execute("""
		SELECT participant_id FROM participants WHERE participant_id = ? AND giveaway_id = ?
		""",(user,giveaway_id))
		result = await self.cursor.fetchone()
		return result is not None
	
	async def select_all(self) -> Dict[str,List[Union[Giveaway,Participant]]]:
		await self.cursor.execute("""
		SELECT * FROM giveaways
		""")
		giv = await self.cursor.fetchall()
		await self.cursor.execute("""
		SELECT * FROM participants
		""")
		part = await self.cursor.fetchall()
		results = {
			'giveaway': [Giveaway(*g) for g in giv],
			'participants': [Participant(*p) for p in part]
		}
		return results

	async def fetch_hosted_giveaways(self, user_id: int) -> int:
		await self.cursor.execute("""
		SELECT COUNT(hoster_id) FROM giveaways
		WHERE hoster_id = ?
		""",(user_id,))
		result = await self.cursor.fetchone()
		return result[0] if result != None else 0
