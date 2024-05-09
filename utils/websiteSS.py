import aiohttp
#import urllib.parse as ul
from os import environ
from base64 import b64decode
import re
import io

class BadResponse(Exception):
	...
class BadURL(Exception):
	...

key = environ['GOOGLE']
async def get_ss(link: str):
	valid_url = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
	if not valid_url.match(link):
		raise BadURL()
	# urle = ul.quote_plus(link)
	params = {'key':key,'strategy':'desktop','url':link}

	async with aiohttp.ClientSession() as sess:
		async with sess.get(url='https://www.googleapis.com/pagespeedonline/v5/runPagespeed',params=params) as resp:
			if resp.status != 200:
				print(await resp.json(),resp.real_url)
				raise BadResponse(resp.status)
			data = await resp.json()
			ss_encoded = data['lighthouseResult']['audits']['final-screenshot']['details']['data'].replace("data:image/jpeg;base64,", "")
			ss_decoded = b64decode(ss_encoded)
			return io.BytesIO(ss_decoded)
