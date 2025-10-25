from PIL import Image, ImageDraw
import math

R = 1024
bg = Image.new('RGBA', (R, R), (0,0,0,0))
draw = ImageDraw.Draw(bg)

# Diagonal dark gradient background
grad = Image.new('RGBA', (R, R), (0,0,0,0))
gd = ImageDraw.Draw(grad)
for i in range(R):
    t = i/(R-1)
    # from #0B1020 to #111827
    c1 = (0x0B,0x10,0x20)
    c2 = (0x11,0x18,0x27)
    r = int(c1[0]*(1-t)+c2[0]*t)
    g = int(c1[1]*(1-t)+c2[1]*t)
    b = int(c1[2]*(1-t)+c2[2]*t)
    gd.line([(0,i),(R,i)], fill=(r,g,b,255))

# Squircle (rounded) mask
mask = Image.new('L', (R,R), 0)
md = ImageDraw.Draw(mask)
rad = int(R*0.18)
margin = int(R*0.08)
md.rounded_rectangle([margin, margin, R-margin, R-margin], radius=rad, fill=255)

canvas = Image.new('RGBA', (R,R), (0,0,0,0))
canvas.paste(grad, (0,0), mask)

# Glyph gradient layer (turquoise -> green)
glyph_grad = Image.new('RGBA', (R,R), (0,0,0,0))
lgd = ImageDraw.Draw(glyph_grad)
for y in range(R):
    t = y/(R-1)
    c1 = (0x06,0xB6,0xD4)  # #06b6d4
    c2 = (0x22,0xC5,0x5E)  # #22c55e
    r = int(c1[0]*(1-t)+c2[0]*t)
    g = int(c1[1]*(1-t)+c2[1]*t)
    b = int(c1[2]*(1-t)+c2[2]*t)
    lgd.line([(0,y),(R,y)], fill=(r,g,b,255))

# Glyph mask (arcs forming an abstract S)
glyph_mask = Image.new('L', (R,R), 0)
mdraw = ImageDraw.Draw(glyph_mask)

# Arc parameters
thick = int(R*0.09)
box1 = [int(R*0.20), int(R*0.10), int(R*0.86), int(R*0.76)]
box2 = [int(R*0.18), int(R*0.24), int(R*0.84), int(R*0.90)]

# Draw two opposing arcs
mdraw.arc(box1, start=210, end=20, fill=255, width=thick)
mdraw.arc(box2, start=200, end=10, fill=255, width=thick)

# Add a small vertical scribe bar on the right
bar_w = int(thick*0.28)
bar_h = int(R*0.18)
bar_x = int(R*0.72)
bar_y = int(R*0.50)
mdraw.rounded_rectangle([bar_x, bar_y, bar_x+bar_w, bar_y+bar_h], radius=bar_w//2, fill=255)

# Composite glyph gradient through mask onto canvas
glyph_colored = Image.new('RGBA', (R,R), (0,0,0,0))
glyph_colored.paste(glyph_grad, (0,0), glyph_mask)
canvas = Image.alpha_composite(canvas, glyph_colored)

# Subtle inner shadow
shadow = Image.new('RGBA', (R,R), (0,0,0,0))
sd = ImageDraw.Draw(shadow)
sd.rounded_rectangle([margin, margin, R-margin, R-margin], radius=rad, outline=(0,0,0,160), width=int(R*0.01))
canvas = Image.alpha_composite(canvas, shadow)

# Export sizes
out_big = 'raycast-extension/assets/icon_meetingscribe.png'
canvas.resize((512,512), Image.LANCZOS).save(out_big, 'PNG')

# Also update root icon.png
root_out = 'raycast-extension/icon.png'
canvas.resize((512,512), Image.LANCZOS).save(root_out, 'PNG')

print('WROTE', out_big, 'and', root_out)
