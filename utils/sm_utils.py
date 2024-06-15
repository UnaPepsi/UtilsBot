from typing import Any, Callable, Union
import asyncio
from io import BytesIO

def format_miss_perms(missing_perms: list[str]) -> str:
	perms = [perm.replace('_',' ') for perm in missing_perms]
	formatted_perms = ', '.join(perms).title()
	return formatted_perms[:-1] if formatted_perms[-1] == ',' else formatted_perms

cache: dict[str,dict[Any,Any]] = {}

def caching(func: Callable):
	async def wrapper(*args, **kwargs):
		# print(args,kwargs,cache)
		if kwargs:
			arg = next(iter(kwargs.values()))
		else:
			arg = args[0] if args else None
		if arg in cache.get(func.__name__,{}):
			result = cache[func.__name__][arg]
			if isinstance(result,BytesIO):
				result.seek(0)
			return result
		else:
			cache[func.__name__] = cache.get(func.__name__,{})
			cache[func.__name__][arg] = await func(arg)
			asyncio.create_task(wait_and_remove(600,func.__name__,arg))
			return cache[func.__name__][arg]
	return wrapper

async def wait_and_remove(seconds: Union[int,float], func_name: str, value) -> None:
	await asyncio.sleep(seconds)
	if cache.get(func_name,None) is not None:
		cache[func_name].pop(value)