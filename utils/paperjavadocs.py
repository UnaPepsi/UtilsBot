from aiohttp import ClientSession
from bs4 import BeautifulSoup
from os import environ
from urllib.parse import unquote

_items = []
def items(): return _items

async def reload_paper_docs():
    _items.clear()
    async with ClientSession() as sess:
        async with sess.get(f'https://jd.papermc.io/paper/{environ['VERSION']}/index-all.html') as resp:
            if not resp.ok:
                raise RuntimeError("Response was not ok")            
            soup = BeautifulSoup(await resp.content.read(),'html.parser')
            dts = soup.find_all('dt')
            for dt in dts:
                a = dt.find('a')
                if a and a.has_attr('href'):
                    _items.append(unquote(a.get('href').replace('.html','')))