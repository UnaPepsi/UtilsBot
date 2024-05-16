import aiohttp
from os import environ
headers = {'Authorization':environ['TOPGG']}

async def has_user_voted(user_id: int) -> bool:
    """
    Returns True if user voted on top.gg
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://top.gg/api/bots/778785822828265514/check?userId={user_id}",headers=headers) as resp:
            data: dict = await resp.json()
    user_voted = data.get('voted',0)
    return user_voted == 1