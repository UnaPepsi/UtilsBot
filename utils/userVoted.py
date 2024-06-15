import aiohttp
import asyncio
from os import environ
from typing import Optional
import logging
headers = {'Authorization':environ['TOPGG']}

logger = logging.getLogger(__name__)
rate_limited: Optional[tuple[asyncio.Task[None],int]] = None
async def has_user_voted(user_id: int) -> bool:
	"""
	Returns True if user voted on top.gg. If ratelimited, returns False
	"""
	global rate_limited
	if rate_limited is not None:
		return False
	async with aiohttp.ClientSession() as session:
		async with session.get(f"https://top.gg/api/bots/778785822828265514/check?userId={user_id}",headers=headers) as resp:
			data: dict = await resp.json()
	if data.get('retry-after',-1) != -1:
		rate_limited = (asyncio.create_task(wait_for_rate_limit(data.get('retry-after',-1))),data.get('retry-after',-1))
	user_voted = data.get('voted',0)
	return user_voted == 1

async def wait_for_rate_limit(time: int):
	logger.warning(f"TopGG rate limited for {time} seconds")
	global rate_limited
	await asyncio.sleep(time)
	rate_limited = None