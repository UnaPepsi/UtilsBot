import aiohttp
from os import environ
from base64 import b64decode
import re
import io
from utils.sm_utils import caching
from playwright.async_api import async_playwright
from playwright._impl._errors import TimeoutError,Error
import logging
logger = logging.getLogger(__name__)

class BadResponse(Exception):
	...
class BadURL(Exception):
	...

key = environ['GOOGLE']
ip = environ['IP']

@caching
async def get_ss(link: str, width: int=1920, height: int=1080) -> io.BytesIO:
	valid_url = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
	if not valid_url.match(link):
		raise BadURL()

	async with async_playwright() as playwright:
		try:
			browser = await playwright.chromium.launch()
			page = await browser.new_page()
			await page.goto(link)
			await page.set_viewport_size({"width": width, "height": height})
			# await page.evaluate('document.body.style.zoom = "1000%"')
			await page.evaluate('''(ip) => {
    		document.body.innerHTML = document.body.innerHTML.replace(new RegExp(ip, 'g'), '----------');
			}''', ip)
			screenshot_bytes = await page.screenshot() #full_page=True
			await browser.close()
			return io.BytesIO(screenshot_bytes)
		except (TimeoutError,Error) as e:
			await browser.close()
			logger.warning(f"Couldn't take screenshot using playwright. Using google instead. Traceback: {e}")

	params = {'key':key,'strategy':'desktop','url':link}

	async with aiohttp.ClientSession() as sess:
		async with sess.get(url='https://www.googleapis.com/pagespeedonline/v5/runPagespeed',params=params) as resp:
			if resp.status != 200:
				logger.error(f'Error at using google. Most likely rate limited. JSON response: {await resp.json()}. URL: {resp.real_url}')
				raise BadResponse(resp.status)
			data = await resp.json()
			ss_encoded = data['lighthouseResult']['audits']['final-screenshot']['details']['data'].replace("data:image/jpeg;base64,", "")
			ss_decoded = b64decode(ss_encoded)
			return io.BytesIO(ss_decoded)
