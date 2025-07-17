from pilmoji import Pilmoji
import requests
from enum import Enum 
from io import BytesIO
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageOps
from discord import Asset, Member, Message

from utils.sm_utils import caching

class Bubble(Enum):
    RECTANGLE = BytesIO(open('bubbles/rectangle.png','rb').read())
    THOUGHT = BytesIO(open('bubbles/thought.png','rb').read())
    ROUND = BytesIO(open('bubbles/round.png','rb').read())
    TRANSPARENT = BytesIO(open('bubbles/transparent.png','rb').read())
class Background(Enum):
    LIGHT = (251, 251, 251)
    ASH = (50, 51, 57)
    DARK = (26, 26, 30)
    ONYX = (7, 7, 9)
    LEGACY = (46, 51, 54)
    OLD = (55, 57, 61) #lol
    MOBILE_DARK = (28, 29, 34)

text_font = ImageFont.truetype('bubbles/gg sans Medium.ttf',20)
nick_font = ImageFont.truetype('bubbles/gg sans Bold.ttf',20)
time_font = ImageFont.truetype('bubbles/gg sans Regular.ttf',15)

@caching
async def generate_speech_bubble(background: Background, message: Message, bubble: Bubble = Bubble.ROUND) -> BytesIO:
    assert message.content
    pfp_size = 50
    lines = textwrap.wrap(text=message.content,width=60)
    nick = message.author.nick or message.author.display_name if isinstance(message.author,Member) else message.author.display_name

    #profile picture
    pfp_pad = 10
    pfp_size = 50,50
    mask = Image.new('L',pfp_size,0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0,0)+pfp_size,fill=255)
    pfp = Image.open(get_profile_picture(message.author.display_avatar))
    pfp_out = ImageOps.fit(pfp,mask.size,centering=(0.5,0.5))

    #background
    w, h = pfp_size[0] + pfp_pad + 510, pfp_size[0] + pfp_pad
    bg = Image.new('RGB',(w,h),color=background.value)

    #text
    global text_font
    global nick_font
    global time_font 
    
    offset = 5
    for line in lines:
        bbox = dict(zip(('left', 'top', 'right', 'bottom'),text_font.getbbox(line)))
        new_h = int(bbox['bottom']-bbox['top']) + offset
        w = max(w,80+bbox['right']-bbox['left']+10)
        bg = bg.resize((w,bg.height+new_h))
    with Pilmoji(bg) as draw:
        #message content
        draw.text((80,40),'\n'.join(lines),fill=(255,255,255) if background != Background.LIGHT else (77, 78, 83),font=text_font,embedded_color=True,emoji_scale_factor=1.3)
        #nick
        draw.text((80,12),nick,fill=(255,255,255) if background != Background.LIGHT else (77, 78, 83),font=nick_font,embedded_color=True,emoji_scale_factor=1.3)
        #time
        draw.text((90+nick_font.getlength(nick),16),message.created_at.strftime('%H:%M %p'),fill=(130, 131, 139),font=time_font) #eg. 01:40 PM
    
    #add pfp
    bg.paste(pfp_out,(pfp_pad,20),mask)

    #bubble speech
    bubble_im = Image.open(bubble.value)
    bubble_im = bubble_im.resize((bg.width,bubble_im.height))
    bg.paste(bubble_im,(0,0),bubble_im.convert('RGBA'))
    buffer = BytesIO()
    bg.save(buffer,format='GIF')
    buffer.seek(0)
    return buffer

def get_profile_picture(avatar: Asset) -> BytesIO:
    return BytesIO(requests.get(avatar.url).content)