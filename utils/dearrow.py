import aiohttp
from typing import Dict, Any, Optional
from dataclasses import dataclass

class VideoNotFound(Exception): ...

@dataclass
class DeArrow:
	title: Optional[str]
	thumbnail: Optional[bytes]
	
async def dearrow(video: str) -> DeArrow:
	async with aiohttp.ClientSession() as sess:
		async with sess.get(f'https://dearrow.minibomba.pro/sbserver/api/branding?videoID={video}') as resp:
			if resp.status != 200:
				raise VideoNotFound("[DeArrow's API](<https://dearrow.ajay.app/>) could not find that video. _Most likely no one sumbitted this video to their API_")
			data: Dict[str, Any] = await resp.json()
			title: Optional[str] = data['titles'][0]['title'] if len(data['titles']) != 0 else None
			timestamp: Optional[float] = data['thumbnails'][0]['timestamp'] if len(data['thumbnails']) != 0 else None
			if title is None and timestamp is None:
				raise VideoNotFound('No changes sumbitted of this video were found')
		params: Dict[str,Any] = { #make type-checker happy
			'videoID':video
		}
		if timestamp: #https://wiki.sponsor.ajay.app/w/API_Docs/DeArrow#:~:text=but%20without%20providing%20a%20value%20in%20the%20time%20field
			params['time'] = timestamp
		async with sess.get('https://dearrow-thumb.ajay.app/api/v1/getThumbnail',params=params) as resp:
			thumbnail_bytes = await resp.content.read() if resp.status == 200 else None
	return DeArrow(title,thumbnail_bytes)

