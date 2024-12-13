from aiohttp import ClientSession
from typing import List
from utils.sm_utils import deprecated, caching

class TranslationFailed(Exception): ...

@caching
async def translate_google(*, target: str, q: str) -> str:
    url = f'https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&dt=t&dj=1&source=input'
    async with ClientSession() as sess:
        async with sess.get(url,params={'tl':target,'q':q}) as resp: #params kwarg here so characters like '&' don't mess with the actual translation
            if not resp.ok:
                raise TranslationFailed()
            data = await resp.json()
            translation = ''
            for sentence in data['sentences']:
                translation += sentence['trans']
            return translation