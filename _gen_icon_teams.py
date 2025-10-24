from PIL import Image, ImageDraw, ImageFilter

R = 1024
TEAMS_A = (0x5B,0x5F,0xC7)  # #5B5FC7
TEAMS_B = (0x46,0x4E,0xB8)  # #464EB8
DARK_OUTLINE = (16, 18, 32, 180)

# Background gradient (vertical)
bg_grad = Image.new('RGBA', (R, R), (0,0,0,0))
draw = ImageDraw.Draw(bg_grad)
for y in range(R):
    t = y/(R-1)
    r = int(TEAMS_A[0]*(1-t) + TEAMS_B[0]*t)
    g = int(TEAMS_A[1]*(1-t) + TEAMS_B[1]*t)
    b = int(TEAMS_A[2]*(1-t) + TEAMS_B[2]*t)
    draw.line([(0,y),(R,y)], fill=(r,g,b,255))

# Squircle mask
mask = Image.new('L', (R,R), 0)
md = ImageDraw.Draw(mask)
margin = int(R*0.08)
rad = int(R*0.22)
md.rounded_rectangle([margin, margin, R-margin, R-margin], radius=rad, fill=255)

canvas = Image.new('RGBA', (R,R), (0,0,0,0))
canvas.paste(bg_grad, (0,0), mask)

# Inner stroke
inner = Image.new('RGBA', (R,R), (0,0,0,0))
idraw = ImageDraw.Draw(inner)
idraw.rounded_rectangle([margin, margin, R-margin, R-margin], radius=rad, outline=DARK_OUTLINE, width=int(R*0.012))
canvas = Image.alpha_composite(canvas, inner)

# Waveform bars
bars = 7
gap = int(R*0.035)
bar_w = int(R*0.045)
center_x = R//2
center_y = R//2 + int(R*0.03)
heights = [0.28, 0.48, 0.72, 0.88, 0.72, 0.48, 0.28]

# Shadow layer
shadow = Image.new('RGBA', (R,R), (0,0,0,0))
sd = ImageDraw.Draw(shadow)
for i in range(bars):
    dx = (i - bars//2) * (bar_w + gap)
    h = int(R*0.45*heights[i])
    x0 = center_x + dx - bar_w//2
    y0 = center_y - h//2
    x1 = x0 + bar_w
    y1 = y0 + h
    off = int(R*0.012)
    sd.rounded_rectangle([x0+off, y0+off, x1+off, y1+off], radius=bar_w//2, fill=(0,0,0,90))

shadow = shadow.filter(ImageFilter.GaussianBlur(radius=int(R*0.008)))
canvas = Image.alpha_composite(canvas, shadow)

# Foreground bars
fg = Image.new('RGBA', (R,R), (0,0,0,0))
fd = ImageDraw.Draw(fg)
for i in range(bars):
    dx = (i - bars//2) * (bar_w + gap)
    h = int(R*0.45*heights[i])
    x0 = center_x + dx - bar_w//2
    y0 = center_y - h//2
    x1 = x0 + bar_w
    y1 = y0 + h
    fd.rounded_rectangle([x0, y0, x1, y1], radius=bar_w//2, fill=(255,255,255,255))

canvas = Image.alpha_composite(canvas, fg)

# Export
out1 = 'raycast-extension/icon.png'
out2 = 'raycast-extension/assets/icon_meetingscribe.png'
canvas.resize((512,512), Image.LANCZOS).save(out1, 'PNG')
canvas.resize((512,512), Image.LANCZOS).save(out2, 'PNG')
print('WROTE', out1, 'and', out2)
