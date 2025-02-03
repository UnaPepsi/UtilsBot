from datetime import datetime
from typing import List
from aiohttp import ClientSession
from utils.sm_utils import caching

class NotFound(Exception): ...

def day_suffix(day: int) -> str:
	return {1: 'st', 2: 'nd', 3: 'rd'}.get(day%20,'th')

class TinEyeResult:
	def __init__(self, query_hash: str, url: str, backlink: str, crawl_date: str):
		self.query_hash = query_hash
		self.url = url
		self.backlink = backlink
		_date = datetime.strptime(crawl_date,'%Y-%m-%d')
		self.date = _date.strftime(f'%b {str(_date.day)+day_suffix(_date.day)}, %Y') #Sep 28th, 2007 for example

@caching
async def tin_eye(url: str) -> List[TinEyeResult]:
	async with ClientSession() as sess:
		async with sess.post('https://tineye.com/api/v1/result_json/',data={'url':url}) as resp:
			if not resp.ok:
				raise NotFound()
			data = await resp.json()
			result = []
			for match in data.get('matches'):
				for backlink in match.get('backlinks'):
					result.append(TinEyeResult(data.get('query_hash'),backlink.get('url'),backlink.get('backlink'),backlink.get('crawl_date')))
			return result