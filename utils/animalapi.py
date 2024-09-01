import aiohttp

class Error(Exception): ...

async def get_cat() -> str:
	try:
		async with aiohttp.ClientSession() as session:
			async with session.get("https://api.thecatapi.com/v1/images/search") as data:
				if data.status == 200:
					data = await data.json()
					return data[0]['url']
				raise Error('Something wrong happened')
	except (IndexError, KeyError):
		raise Error('Something wrong happened')
	
async def get_dog() -> str:
	try:
		async with aiohttp.ClientSession() as session:
			async with session.get("https://api.thedogapi.com/v1/images/search") as data:
				if data.status == 200:
					data = await data.json()
					return data[0]['url']
				raise Error('Something wrong happened')
	except (IndexError, KeyError):
		raise Error('Something wrong happened')