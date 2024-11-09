from typing import Any, Callable, Union, List, Dict
import asyncio
from io import BytesIO
import re
from datetime import timedelta
from warnings import warn

def format_miss_perms(missing_perms: List[str]) -> str:
	perms = [perm.replace('_',' ') for perm in missing_perms]
	formatted_perms = ', '.join(perms).title()
	return formatted_perms[:-1] if formatted_perms[-1] == ',' else formatted_perms

cache: Dict[str,Dict[Any,Any]] = {}

def caching(func: Callable):
	async def wrapper(*args, **kwargs):
		combined_args = args+tuple(kwargs.values())
		if len(combined_args) == 0:
			raise ValueError('Missing parameters')
		if combined_args in cache.get(func.__name__,{}):
			result = cache[func.__name__][combined_args]
			if isinstance(result,BytesIO):
				result.seek(0)
			return result
		else:
			cache[func.__name__] = cache.get(func.__name__,{})
			cache[func.__name__][combined_args] = await func(*args,**kwargs)
			asyncio.create_task(wait_and_remove(600,func.__name__,combined_args))
			return cache[func.__name__][combined_args]
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

def parse_duration(duration_str: str):
	pattern = r"""
		(?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?                 # e.g. 10w
		(?:(?P<days>[0-9]{1,5})(?:days?|d))?                   # e.g. 14d
		(?:(?P<hours>[0-9]{1,5})(?:hours?|hr?s?))?             # e.g. 12h
		(?:(?P<minutes>[0-9]{1,5})(?:minutes?|m(?:ins?)?))?    # e.g. 10m
		(?:(?P<seconds>[0-9]{1,5})(?:seconds?|s(?:ecs?)?))?    # e.g. 15s
	"""

	match = re.match(pattern, duration_str, re.VERBOSE | re.IGNORECASE)

	if match:
		weeks = int(match.group('weeks')) if match.group('weeks') else 0
		days = int(match.group('days')) if match.group('days') else 0
		hours = int(match.group('hours')) if match.group('hours') else 0
		minutes = int(match.group('minutes')) if match.group('minutes') else 0
		seconds = int(match.group('seconds')) if match.group('seconds') else 0

		duration = timedelta(
			days=days + weeks * 7,
			hours=hours,
			minutes=minutes,
			seconds=seconds
		)
		return duration
	else:
		raise ValueError("Invalid duration format")

def deprecated(reason: str):
	def dec(func: Callable):
		async def wrapper(*args,**kwargs):
			warn(message=reason,category=DeprecationWarning,stacklevel=2)
			return await func(*args,**kwargs)
		return wrapper
	return dec


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