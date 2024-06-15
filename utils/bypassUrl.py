from aiohttp import ClientSession
import re
from utils.sm_utils import caching

@caching
async def bypass(url: str) -> str:
	valid_url = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
	if not valid_url.match(url):
		raise ValueError
	params = {
		'url':url
	}
	async with ClientSession() as session:
		async with session.get(f"https://bypass.pm/bypass2",params=params) as data:
			if data.status != 200:
				raise KeyError
			data = await data.json()
			return data['destination']