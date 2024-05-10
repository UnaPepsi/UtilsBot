def rgb_to_hex(r: str, g: str, b: str) -> int:
    r,g,b = int(r),int(g),int(b)

    print(type(r))
    sum = (r << 16) + (g << 8) + b
    if sum not in range(16777215+1):
        raise TypeError('Invalid RGB')
    return sum

def def_colors():
    return {
        "black": 0x000000,
        "white": 0xFFFFFF,
        "red": 0xFF0000,
        "green": 0x00FF00,
        "blue": 0x0000FF,
        "yellow": 0xFFFF00,
        "cyan": 0x00FFFF,
        "magenta": 0xFF00FF,
        "orange": 0xFFA500,
        "pink": 0xFFC0CB,
        "purple": 0x800080,
        "brown": 0xA52A2A,
        "gray": 0x808080,
    }