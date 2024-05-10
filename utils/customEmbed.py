import aiosqlite
from typing import Any, Self

class TagInUse(Exception):
    ...
class BadTag(Exception):
    ...


class CustomEmbed:
	def __init__(self, path: str = 'users.db'):
		self.path = path
	
	async def __aenter__(self) -> Self:
		self.connection = await aiosqlite.connect(database=self.path)
		self.cursor = await self.connection.cursor()
		return self
	async def __aexit__(self, *args):
		await self.cursor.close()
		await self.connection.close()
	async def make_table(self) -> None:
		await self.cursor.execute("""
		CREATE TABLE IF NOT EXISTS ce (
			user INTEGER,
			tag TEXT,
			embed TEXT
		)
		""")
	async def new_embed(self,user: int, tag: str, embed: dict[Any,Any]) -> None:
		if await self.load_embed(user=user,tag=tag) is not None:
			raise TagInUse('Tag already in use')
		await self.cursor.execute("""
		INSERT INTO ce VALUES
		(?, ?, ?)
		""",(user,tag,str(embed)))
		await self.connection.commit()
	async def load_embed(self,user: int, tag: str) -> str | None:
		await self.cursor.execute("""
		SELECT embed FROM ce
		WHERE user = ? AND tag = ?
		""",(user,tag))
		result = await self.cursor.fetchone()
		return result[0] if result is not None else None
	async def delete_embed(self,user: int,tag: str) -> None:
		if await self.load_embed(user=user,tag=tag) is None:
			raise BadTag('No tag found')
		await self.cursor.execute("""
		DELETE FROM ce WHERE user = ? AND tag = ?
		""",(user,tag))
		await self.connection.commit()