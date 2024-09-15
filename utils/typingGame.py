from json import load
from random import choice
import aiosqlite
from typing import Self

def wagner_fischer(str1: str, str2: str) -> int:
    if not str2: #if user inputs nothing
        return len(str1)
    if str1 == str2:
        return 0
    len1, len2 = len(str1), len(str2)
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j
    
    for i in range(1,len1+1):
        for j in range(1,len2+1):
            t = int(str1[i-1] != str2[j-1]) #True == 1 && False == 0    
            dp[i][j] = min(
                dp[i-1][j]+1,
                dp[i-1][j-1]+t,
                dp[i][j-1]+1
            )
    return dp[i][j]

def random_paragraph() -> str:
	with open('paragraphs.json','r',encoding='utf-8') as f:
		data = load(f)
		return choice(data['data'])
	
class TypeRace:
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
		CREATE TABLE IF NOT EXISTS typerace (
			user INTEGER,
			paragraph TEXT,
			time REAL
		)
		""")
	