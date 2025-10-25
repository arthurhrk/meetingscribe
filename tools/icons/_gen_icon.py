from PIL import Image, ImageDraw
SIZE = 512
R = SIZE
img = Image.new('RGBA', (R, R), (0,0,0,0))
draw = ImageDraw.Draw(img)
# Background gradient vertical
for y in range(R):
    t = y / (R-1)
    c1 = (0x7F,0x56,0xD9)
    c2 = (0x4C,0x6F,0xFF)
    r = int(c1[0]*(1-t) + c2[0]*t)
    g = int(c1[1]*(1-t) + c2[1]*t)
    b = int(c1[2]*(1-t) + c2[2]*t)
    draw.line([(0,y),(R,y)], fill=(r,g,b,255))
# rounded square mask
mask = Image.new('L', (R, R), 0)
md = ImageDraw.Draw(mask)
rad = int(R*0.2)
md.rounded_rectangle([int(R*0.08), int(R*0.08), int(R*0.92), int(R*0.92)], radius=rad, fill=255)
bg = Image.new('RGBA', (R,R), (0,0,0,0))
bg.paste(img, (0,0), mask)
img = bg

draw = ImageDraw.Draw(img)
# Mic
center = (R//2 - 30, R//2)
mic_w = int(R*0.18)
mic_h = int(R*0.28)
mic_x0 = center[0] - mic_w//2
mic_y0 = center[1] - mic_h//2
mic_x1 = mic_x0 + mic_w
mic_y1 = mic_y0 + mic_h
# capsule
draw.rounded_rectangle([mic_x0, mic_y0, mic_x1, mic_y1], radius=int(mic_w*0.5), fill=(255,255,255,255))
# stem
stem_w = int(mic_w*0.18)
stem_h = int(R*0.08)
stem_x0 = center[0] - stem_w//2
stem_y0 = mic_y1
stem_x1 = stem_x0 + stem_w
stem_y1 = stem_y0 + stem_h
draw.rounded_rectangle([stem_x0, stem_y0, stem_x1, stem_y1], radius=stem_w//2, fill=(255,255,255,255))
# base
base_w = int(mic_w*1.4)
base_h = int(R*0.02)
base_x0 = center[0] - base_w//2
base_y0 = stem_y1 + int(R*0.02)
base_x1 = base_x0 + base_w
base_y1 = base_y0 + base_h
draw.rounded_rectangle([base_x0, base_y0, base_x1, base_y1], radius=base_h//2, fill=(255,255,255,255))
# lines
line_x = center[0] + mic_w//2 + int(R*0.06)
for i, lw in enumerate([0.22, 0.18, 0.14]):
    ly = mic_y0 + int((i+0.7)* (mic_h/3))
    l = int(R*lw)
    draw.rounded_rectangle([line_x, ly, line_x + l, ly + int(R*0.018)], radius=8, fill=(255,255,255,230))
# dot
d = int(R*0.04)
draw.ellipse([int(R*0.18), int(R*0.2), int(R*0.18)+d, int(R*0.2)+d], fill=(255,255,255,210))

out = 'raycast-extension/assets/icon_meetingscribe.png'
img.save(out, 'PNG')
print('WROTE', out)
