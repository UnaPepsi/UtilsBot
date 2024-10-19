from aiohttp import ClientSession
from typing import List

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