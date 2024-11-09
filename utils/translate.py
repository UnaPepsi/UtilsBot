from aiohttp import ClientSession
from typing import List
from utils.sm_utils import deprecated, caching

@deprecated('Use translate_google instead')
async def translate_text(*, source = 'auto', target: str, q: str) -> List[str]:
    async with ClientSession() as sess:
        body = {
            'source':source,
            'target':target,
            'q':q,
            'alternatives': 5,
        }
        async with sess.post('https://translate.guimx.me/translate',json=body) as resp:
            if resp.ok:
                data = await resp.json()
                # translations = data.get('alternatives').insert(0,data.get('translatedText')) #this returns None for some reason???
                translations = [data.get('translatedText')]
                translations += data.get('alternatives')
                return translations
            else:
                return []

@caching
async def translate_google(*, target: str, q: str) -> str:
    url = f'https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target}&dt=t&dj=1&source=input&q={q}'
    async with ClientSession() as sess:
        async with sess.get(url) as resp:
            data = await resp.json()
            translation = ''
            for sentence in data['sentences']:
                translation += sentence['trans']
            return translation