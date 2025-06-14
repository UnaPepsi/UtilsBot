import requests
from bs4 import BeautifulSoup
from os import environ
from urllib.parse import unquote
import re

_items = []
_deprecated = set()
def items(): return _items
def deprecated(): return _deprecated

#beauifulsoup blocks so eh why not use requests
def reload_paper_docs():
	_items.clear()
	resp = requests.get(f'https://jd.papermc.io/paper/{environ['VERSION']}/index-all.html')
	if not resp.ok:
		raise RuntimeError(f"Response was not ok {resp.reason}")
	soup = BeautifulSoup(resp.content,'html.parser')
	dts = soup.find_all('dt')
	for dt in dts:
		a = dt.find('a')
		if a and a.has_attr('href'):
			_items.append(unquote(a.get('href').replace('.html','' if a.get('href').endswith('.html') else '.html')))
	resp = requests.get(f'https://jd.papermc.io/paper/{environ['VERSION']}/deprecated-list.html')
	if not resp.ok:
		raise RuntimeError(f"Deprecated response was not ok {resp.reason}")
	soup = BeautifulSoup(resp.content,'html.parser')
	divs = soup.find_all('div',class_='col-summary-item-name')
	for div in divs:
		a = div.find('a')
		if a and a.has_attr('href'):
			_deprecated.add(unquote(a.get('href').replace('.html','' if a.get('href').endswith('.html') else '.html')))

def format_string(key: str):
	a = '`'+re.sub(r'\b[a-z]\w*\.', '',key.replace('/','.'))[-65:]+'`'
	if key in _deprecated:
		a = f'~~{a}~~'
	return a