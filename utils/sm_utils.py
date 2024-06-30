from typing import Any, Callable, Union, List, Dict
import asyncio
from io import BytesIO

def format_miss_perms(missing_perms: List[str]) -> str:
	perms = [perm.replace('_',' ') for perm in missing_perms]
	formatted_perms = ', '.join(perms).title()
	return formatted_perms[:-1] if formatted_perms[-1] == ',' else formatted_perms

cache: Dict[str,Dict[Any,Any]] = {}

def caching(func: Callable):
	async def wrapper(*args):
		if len(args) == 0:
			raise ValueError('Missing parameters')
		if args in cache.get(func.__name__,{}):
			result = cache[func.__name__][args]
			if isinstance(result,BytesIO):
				result.seek(0)
			return result
		else:
			cache[func.__name__] = cache.get(func.__name__,{})
			cache[func.__name__][args] = await func(*args)
			asyncio.create_task(wait_and_remove(600,func.__name__,args))
			return cache[func.__name__][args]
	return wrapper

async def wait_and_remove(seconds: Union[int,float], func_name: str, value) -> None:
	await asyncio.sleep(seconds)
	if cache.get(func_name,None) is not None:
		cache[func_name].pop(value)

def rgb_to_hex(r: Union[str,int], g: Union[str,int], b: Union[str,int]) -> int:
    r,g,b = int(r),int(g),int(b)
    sum = (r << 16) + (g << 8) + b
    if sum not in range(16777215+1):
        raise TypeError('Invalid RGB')
    return sum

hex_colors = {
    "black": 0x000000,
    "white": 0xFFFFFF,
    "red": 0xFF0000,
    "green": 0x00FF00,
    "blue": 0x0000FF,
    "yellow": 0xFFFF00,
    "cyan": 0x00FFFF,
    "magenta": 0xFF00FF,
    "orange": 0xFFA500,
    "pink": 0xFFC0CB,
    "purple": 0x800080,
    "brown": 0xA52A2A,
    "gray": 0x808080,
}