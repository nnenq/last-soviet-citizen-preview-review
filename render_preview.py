import os
"""Real 23-second Cairo/NumPy animation preview. Not the complete documentary.
Run: python render_preview.py
Optional: python render_preview.py --stills
Every frame is drawn here; no generated-image or slideshow renderer.
"""
from pathlib import Path
import argparse, io, json, math, re, subprocess, wave, hashlib
import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUT = ROOT / "preview"
QA = OUT / "qa"
W, H, FPS, SECONDS = 1920, 1080, 30, 23
N = FPS * SECONDS
BG, LINE, INK = "#0d0d10", "#5b5b64", "#17191d"
SKIN, SUIT, FAR, RED = "#E4E0CF", "#c9c6bd", "#797d7d", "#ff4646"
WHITE, BLUE = "#f2efe6", "#13223a"
FONTS = {"caption": ASSETS/"Andika-Bold.ttf", "mono": ASSETS/"JetBrainsMono.ttf"}
OUT.mkdir(exist_ok=True)
QA.mkdir(exist_ok=True)
TEXT_CACHE = {}
BOUNDS = []
SCALES = []
C = None

def rgba(color, alpha=1):
    if isinstance(color, (tuple, list)):
        return tuple(color[:3]) + (color[3] if len(color)>3 else alpha,)
    return tuple(int(color[i:i+2],16)/255 for i in (1,3,5))+(alpha,)

def src(color, alpha=1): C.set_source_rgba(*rgba(color, alpha))
def fillstroke(fill=None, stroke=None, width=3, alpha=1):
    if fill:
        src(fill, alpha)
        if stroke: C.fill_preserve()
        else: C.fill()
    if stroke:
        src(stroke, alpha); C.set_line_width(width); C.stroke()
    elif not fill: C.new_path()

def line(pts, color=LINE, width=3, alpha=1):
    if len(pts)<2: return
    C.new_path(); C.move_to(*pts[0])
    for p in pts[1:]: C.line_to(*p)
    fillstroke(None,color,width,alpha)

def rect(x,y,w,h,fill=None,stroke=None,width=3,r=0,alpha=1):
    C.new_path()
    if r:
        r=min(r,w/2,h/2)
        C.move_to(x+r,y); C.line_to(x+w-r,y)
        C.arc(x+w-r,y+r,r,-math.pi/2,0); C.line_to(x+w,y+h-r)
        C.arc(x+w-r,y+h-r,r,0,math.pi/2); C.line_to(x+r,y+h)
        C.arc(x+r,y+h-r,r,math.pi/2,math.pi); C.line_to(x,y+r)
        C.arc(x+r,y+r,r,math.pi,3*math.pi/2); C.close_path()
    else: C.rectangle(x,y,w,h)
    fillstroke(fill,stroke,width,alpha)

def ellipse(x,y,rx,ry,fill=None,stroke=None,width=3,alpha=1):
    C.save(); C.translate(x,y); C.scale(rx,ry)
    C.new_path(); C.arc(0,0,1,0,2*math.pi)
    if fill:
        src(fill,alpha)
        if stroke: C.fill_preserve()
        else: C.fill()
    if stroke:
        src(stroke,alpha); C.set_line_width(width/max(rx,ry)); C.stroke()
    C.restore()

def svg(d,fill=None,stroke=None,width=3,alpha=1):
    tok=re.findall(r"[A-Za-z]|[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?",d)
    i=0; cmd=None; start=(0,0)
    C.new_path()
    while i<len(tok):
        if tok[i].isalpha(): cmd=tok[i]; i+=1
        if cmd=="Z":
            C.close_path(); cmd=None; continue
        n={"M":2,"L":2,"C":6,"Q":4,"H":1,"V":1}[cmd]
        a=list(map(float,tok[i:i+n])); i+=n
        if cmd=="M": C.move_to(*a); start=tuple(a); cmd="L"
        elif cmd=="L": C.line_to(*a)
        elif cmd=="C": C.curve_to(*a)
        elif cmd=="Q":
            x,y=C.get_current_point(); qx,qy,ex,ey=a
            C.curve_to(x+2*(qx-x)/3,y+2*(qy-y)/3,ex+2*(qx-ex)/3,ey+2*(qy-ey)/3,ex,ey)
        elif cmd=="H": C.line_to(a[0],C.get_current_point()[1])
        elif cmd=="V": C.line_to(C.get_current_point()[0],a[0])
    fillstroke(fill,stroke,width,alpha)

def ease(x): x=max(0,min(1,x)); return x*x*(3-2*x)
def fade(t,start,end,ramp=.2): return min(ease((t-start)/ramp),ease((end-t)/ramp))

def box(role,name,x0,y0,x1,y1,**extra):
    m=C.get_matrix()
    pts=[m.transform_point(x,y) for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]]
    BOUNDS.append(dict(role=role,name=name,box=[min(p[0] for p in pts),min(p[1] for p in pts),
        max(p[0] for p in pts),max(p[1] for p in pts)],**extra))

def text(s,x,baseline,size=56,color=WHITE,font="caption",center=True,alpha=1,role="caption"):
    if alpha<=0: return
    key=(s,size,color,font)
    if key not in TEXT_CACHE:
        f=ImageFont.truetype(str(FONTS[font]),size)
        b=f.getbbox(s,anchor="ls")
        im=Image.new("RGBA",(b[2]-b[0]+16,b[3]-b[1]+16))
        dr=ImageDraw.Draw(im)
        dr.text((8-b[0]+2,8-b[1]+3),s,font=f,anchor="ls",fill=(0,0,0,230),stroke_width=1)
        dr.text((8-b[0],8-b[1]),s,font=f,anchor="ls",fill=color)
        stream=io.BytesIO(); im.save(stream,format="PNG"); stream.seek(0)
        sf=cairo.ImageSurface.create_from_png(stream)
        TEXT_CACHE[key]=(sf,b)
    sf,b=TEXT_CACHE[key]; width=b[2]-b[0]
    left=x-width/2 if center else x
    C.set_source_surface(sf,left-8,baseline+b[1]-8); C.paint_with_alpha(alpha)
    box("text",s,left,baseline+b[1],left+width,baseline+b[3],text_role=role,opacity=round(alpha,4),font_size=size)

def caption(lines,t,start,end):
    a=fade(t,start,end)
    if isinstance(lines,str): lines=[lines]
    for j,s in enumerate(lines):
        baseline=152 if len(lines)==1 else 86+66*j
        text(s,960,baseline,alpha=a)

def stars(t,count=90):
    for i in range(count):
        x=49+(i*379.13)%1830; y=220+(i*163.77)%760
        a=.18+.10*math.sin(i*1.31+t*.23)
        ellipse(x-t*.35,y,.65+(i%3)*.24,.65+(i%3)*.24,"#bcc6cf",alpha=a)

GEO=json.loads((ASSETS/"countries.geojson").read_text(encoding="utf-8"))["features"]
FORMER={"RUS","UKR","BLR","MDA","EST","LVA","LTU","GEO","ARM","AZE","KAZ","UZB","TKM","TJK","KGZ"}

def project(lon,lat):
    lon,lat=math.radians(lon-90),math.radians(lat)
    lat0=math.radians(-6)
    visible=math.sin(lat0)*math.sin(lat)+math.cos(lat0)*math.cos(lat)*math.cos(lon)
    return (805+1600*math.cos(lat)*math.sin(lon),
            1950-1600*(math.cos(lat0)*math.sin(lat)-math.sin(lat0)*math.cos(lat)*math.cos(lon)),visible)

def geo_paths(feature):
    geom=feature["geometry"]
    polys=geom["coordinates"] if geom["type"]=="MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        outer=poly[0]
        pts=[project(*v[:2]) for v in outer]
        # All Soviet northern polygons are on this hemisphere. Far-side polygons
        # are skipped rather than drawing erroneous lines across the globe.
        if len(pts)<3 or sum(p[2]>0 for p in pts)<len(pts)*.93: continue
        C.new_path(); C.move_to(pts[0][0],pts[0][1])
        for x,y,z in pts[1:]: C.line_to(x,y)
        C.close_path()
        yield pts

def planet():
    C.save()
    ellipse(805,1950,1608,1608,None,"#456576",width=2,alpha=.45)
    ellipse(805,1950,1603,1603,None,"#84aabd",width=2,alpha=.5)
    C.new_path(); C.arc(805,1950,1600,0,2*math.pi); C.clip()
    grad=cairo.RadialGradient(620,580,0,805,1950,1750)
    grad.add_color_stop_rgb(0,.075,.13,.21); grad.add_color_stop_rgb(1,.018,.031,.055)
    C.set_source(grad); C.paint()
    for f in GEO:
        code=f["properties"].get("ADM0_A3")
        for _ in geo_paths(f):
            fillstroke("#17283b", "#253447", .8, .8)
    for f in GEO:
        code=f["properties"].get("ADM0_A3")
        if code not in FORMER: continue
        for pts in geo_paths(f):
            # Deliberately editorial map overlay; no historical territorial claim.
            C.save(); C.clip()
            rr=np.random.default_rng(sum(map(ord,code)))
            xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
            for x,y in zip(rr.uniform(min(xs),max(xs),45),rr.uniform(min(ys),max(ys),45)):
                ellipse(x,y,.8,.8,"#c1a574",alpha=.38)
            C.restore()
            C.new_path(); C.move_to(*pts[0][:2])
            for p in pts[1:]: C.line_to(*p[:2])
            C.close_path()
            src(RED,.08); C.fill_preserve()
            src(RED,.08); C.set_line_width(11); C.stroke_preserve()
            src(RED,.8); C.set_line_width(2.5); C.stroke()
    # Subtle edge shading, not grain or fluctuating opacity.
    shade=cairo.LinearGradient(0,350,0,1080)
    shade.add_color_stop_rgba(0,0,0,0,.08); shade.add_color_stop_rgba(1,0,0,0,.5)
    C.set_source(shade); C.paint()
    C.restore()

def mir(x,y,t):
    C.save(); C.translate(x,y); C.rotate(-.14+.005*t)
    # Entire station incl. panels fits 38 x 20 base pixels.
    rect(-6,-3,12,6,"#58636d","#a4adb4",.8)
    rect(-3,-8,6,16,"#45515d","#9ba8b3",.65)
    for side in [-1,1]:
        rect(side*12-5,-7,10,14,"#263b51","#8a9ba8",.7)
        for j in range(1,4): line([(side*12-5,-7+j*3.5),(side*12+5,-7+j*3.5)],"#6c7c8b",.4)
        line([(side*6,0),(side*7,0)],"#b7b6a8",1)
    SCALES.append({"name":"Mir","base_extent_px":38,"maximum_px":40,"scale":"O"})
    C.restore()

def limb(points,far=False,width=18):
    if not far: line(points,INK,width+4)
    line(points,FAR if far else SUIT,width)

def ik(a,b,l1=55,l2=55,bend=1):
    dx,dy=b[0]-a[0],b[1]-a[1]
    d=max(.001,math.hypot(dx,dy))
    if d>l1+l2: raise RuntimeError("Unreachable hand target")
    u,v=dx/d,dy/d; along=(l1*l1-l2*l2+d*d)/(2*d)
    h=math.sqrt(max(0,l1*l1-along*along))
    return a[0]+u*along-v*h*bend,a[1]+v*along+u*h*bend

def hero(t):
    root=(930+3*t,812-2*t)
    angle=math.radians(-2+t*.45)
    co,si=math.cos(angle),math.sin(angle)
    contact=(1020,585)
    dx,dy=contact[0]-root[0],contact[1]-root[1]
    hand=(co*dx+si*dy,-si*dx+co*dy)
    C.save(); C.translate(*root); C.rotate(angle)
    # A single actor owns all joints; hand is solved from a fixed world rail.
    limb([(-18,-126),(-38,-69),(-16,-12)],True)
    limb([(-25,-236),(-69,-193),(-57,-145)],True)
    svg("M-29 -255 Q-43 -188 -30 -119 Q0 -108 31 -120 Q40 -180 29 -255 Z",SUIT,INK,3)
    limb([(18,-126),(49,-74),(32,-6)],False)
    line([(-20,-229),(20,-229)],"#a4a59e",2)
    line([(1,-222),(1,-134)],"#9a9d98",1.5)
    rect(-25,-217,19,11,RED,None,r=2)
    # Patch remains on the same physical shoulder; lettering is meaningful only
    # in a later close-up, not invented microscopic text here.
    C.save(); C.translate(2,-301); C.scale(.95,.98)
    svg("M-45 -34 Q-37 -56 -10 -53 Q23 -58 42 -34 Q56 -1 40 26 Q25 48 -5 47 Q-42 44 -49 17 Q-58 -14 -45 -34 Z",SKIN,INK,3)
    svg("M-46 -24 C-58 -51 -31 -70 -8 -61 C1 -72 19 -68 24 -57 C34 -57 43 -48 41 -39 C23 -45 12 -43 2 -34 C-2 -47 -12 -45 -21 -37 C-27 -30 -35 -28 -46 -24 Z","#30343a")
    svg("M-32 -47 Q-19 -60 -5 -54 M8 -55 Q18 -59 27 -49",None,"#454950",2.5)
    blink=abs(t-1.65)<.075
    ey=.7 if blink else 4.5
    gaze=-3-1.4*ease(t/2)
    ellipse(-11+gaze,-1,4.3,ey,INK)
    ellipse(16+gaze,-2,4.3,ey,INK)
    svg("M-23 -17 Q-15 -20 -7 -18 M9 -19 Q18 -20 26 -16",None,INK,3.4)
    svg("M-5 19 Q5 17 16 19",None,INK,3)
    box("head","hero head",-53,-71,51,49)
    C.restore()
    shoulder=(28,-233); elbow=ik(shoulder,hand,55,55,1)
    limb([shoulder,elbow,hand],False)
    C.restore()
    SCALES.extend([
        {"name":"hero","base_extent_px":370,"scale":"H","camera_independent":True},
        {"name":"head face","base_size_px":[94,100],"scale":"H"},
    ])
    return contact, root

def cabin(t):
    # Same world-space camera for room, body, window and rail.
    zoom=1.25+.10*ease(t/4)
    C.save(); C.translate(960,570); C.scale(zoom,zoom); C.translate(-960,-570)
    rect(517,212,886,886,"#111115",LINE,3,r=156)
    rect(544,240,832,832,None,"#303239",2,r=139)
    for x in [590,742,1135,1286]:
        line([(x,264),(x,990)],"#2e3037",1.5)
    for y in [365,730,950]:
        line([(546,y),(1374,y)],"#292c32",1.5)
    for x,y in [(595,380),(1165,390),(1165,760)]:
        rect(x,y,140,105,"#17191f","#464952",2,r=9)
        for j in range(4):
            line([(x+15,y+25+j*17),(x+105,y+25+j*17)],"#3c414a",2)
        ellipse(x+118,y+24,2.5,2.5,"#81939a",alpha=.55+.13*math.sin(t*.7))
    # Window is always 63 px in base geometry, never enlarged independently.
    wx,wy=825,493
    ellipse(wx,wy,40,40,"#181b21","#60636b",3)
    C.save(); C.new_path(); C.arc(wx,wy,31.5,0,2*math.pi); C.clip()
    rect(wx-32,wy-32,64,64,"#090e16")
    ellipse(wx-10+t*.7,wy+34,54,54,BLUE)
    ellipse(wx-10+t*.7,wy+34,55,55,None,"#78a1b2",1)
    C.restore()
    ellipse(wx,wy,31.5,31.5,None,"#a2a7a8",2)
    for a in range(0,360,60):
        rad=math.radians(a)
        ellipse(wx+36*math.cos(rad),wy+36*math.sin(rad),1.5,1.5,"#8c9094")
    contact,root=hero(t)
    # Foreground handrail; palm covers its near contact point without fingers.
    line([(1020,559),(1020,707)],"#22252b",13)
    line([(1020,559),(1020,707)],"#90979d",8)
    line([(1006,559),(1034,559)],"#6d747d",5)
    line([(1006,707),(1034,707)],"#6d747d",5)
    ellipse(*contact,8.7,8.7,SUIT,INK,2)
    box("prop","round window",wx-31.5,wy-31.5,wx+31.5,wy+31.5,scale="H",base_px=63)
    SCALES.extend([
        {"name":"module","base_extent_px":886,"scale":"H"},
        {"name":"window","base_extent_px":63,"scale":"H"},
        {"name":"handrail","base_extent_px":8,"scale":"H"},
    ])
    C.restore()
    return {"root":list(root),"hand_world":list(contact),"rail_contact_world":list(contact),
        "root_speed_px_s":math.hypot(3,2),"rotation_deg_s":.45}

def rocket(t):
    # Scale R = 10 px/m. Rocket 50 m = 500 px; no humans in this shot.
    ignition=5.0; release=5.8; tau=max(0,t-release)
    dy=-7.2*tau*tau
    camera_y=-dy*.82
    shake=(1 if ignition<t<release+1 else 0)
    sx=shake*2.2*math.sin(t*43)
    sy=shake*2.0*math.sin(t*57)
    C.save(); C.translate(sx-.8*t,camera_y+sy)
    line([(0,906),(1920,906)],"#65666c",2)
    # Gantry behind rocket, fixed to the ground.
    rect(816,375,28,525,"#191b20","#565963",2)
    for j in range(7):
        y=385+j*72
        line([(818,y),(841,y+62),(818,y+62),(841,y)],"#444852",1.5)
    line([(830,375),(830,333),(858,333)],"#50565f",2)
    rect(785,900,98,14,"#272a30","#575a62",2)
    for pivot_y,sign in [(498,-1),(681,1)]:
        a=math.radians(68*ease((t-5.35)/1.2))*sign
        end=(844+104*math.cos(a),pivot_y+104*math.sin(a))
        line([(844,pivot_y),end],"#666b74",6)
        ellipse(*end,3,3,"#adb1b1")
    rect(895,901,134,9,"#32343b","#696b72",2)
    if t>=ignition:
        strength=ease((t-ignition)/.65)
        # Flames originate at the three nozzle exits and share rocket transform.
        for off in [-47,0,47]:
            x,y=960+off,900+dy
            L=(90+65*strength)*(1+.08*math.sin(t*39+off))
            grad=cairo.LinearGradient(x,y,x,y+L)
            grad.add_color_stop_rgba(0,1,.3,.22,.85)
            grad.add_color_stop_rgba(.55,1,.15,.12,.55)
            grad.add_color_stop_rgba(1,1,.15,.12,0)
            C.new_path(); C.move_to(x-12,y)
            C.curve_to(x-21,y+30,x-5,y+L*.8,x,y+L)
            C.curve_to(x+9,y+L*.7,x+20,y+30,x+12,y); C.close_path()
            C.set_source(grad); C.fill()
            svg(f"M{x-4} {y} Q{x-6} {y+40} {x} {y+L*.62} Q{x+7} {y+24} {x+4} {y} Z",WHITE,alpha=.8)
        # Ground smoke expands away from the pad, not from detached mid-air points.
        if t<9:
            for i in range(12):
                age=t-ignition; side=-1 if i%2 else 1
                x=960+side*(55+age*(55+i*4))
                y=918+(i%3)*10
                ellipse(x,y,30+age*15,7+age*4,"#555459",alpha=.14*strength)
    C.save(); C.translate(0,dy)
    # Four side boosters: rear silhouettes first, then near pair, central core.
    svg("M941 592 L952 653 L951 861 L945 894 L925 894 L932 851 L934 659 Z","#656973",LINE,2)
    svg("M979 592 L990 659 L994 851 L1001 894 L981 894 L975 861 L974 653 Z","#656973",LINE,2)
    svg("M920 591 L934 651 L938 860 L931 900 L895 900 L903 860 L907 659 Z","#aaaeb1",LINE,2)
    svg("M1000 591 L1013 659 L1017 860 L1025 900 L989 900 L982 860 L986 651 Z","#aaaeb1",LINE,2)
    svg("M960 400 L978 445 L978 480 L972 496 L972 791 L984 900 L936 900 L948 791 L948 496 L942 480 L942 445 Z","#d1d0c8",LINE,2)
    for y in [480,507,605,786]:
        line([(949,y),(971,y)],"#747a80",2)
    line([(960,444),(960,772)],"#ece9d9",1,alpha=.35)
    for x in [913,960,1007]:
        svg(f"M{x-10} 896 L{x-12} 908 L{x+12} 908 L{x+10} 896 Z","#25282e",LINE,1.5)
    box("prop","rocket",895,400,1025,900,scale="R",base_height_px=500)
    C.restore()
    C.restore()
    # Screen graphics stay fixed while the world camera rises.
    if 2<=t<5:
        digit=3-int(t-2)
        text(str(digit),1210,602,96,RED,font="mono",role="countdown")
    SCALES.append({"name":"rocket","base_extent_px":500,"meters":50,"px_per_meter":10,"scale":"R"})
    return {"ignition_frame":390,"liftoff_frame":414,"rocket_dy":dy,"world_camera_y":camera_y}

def render_frame(n):
    global C,BOUNDS,SCALES
    BOUNDS=[]; SCALES=[]
    sf=cairo.ImageSurface(cairo.FORMAT_RGB24,W,H)
    C=cairo.Context(sf); C.set_line_cap(cairo.LINE_CAP_ROUND); C.set_line_join(cairo.LINE_JOIN_ROUND)
    src(BG); C.paint()
    t=n/FPS
    info={}
    if t<4:
        scene=1
        stars(t)
        C.save(); C.translate(-t*2.5,t*.6); planet()
        mir(1290+t*5,320+t*.5,t)
        C.restore()
        SCALES.append({"name":"Earth","base_extent_px":3200,"minimum_px":2688,"scale":"O"})
        caption("He left Earth from one country.",t,0,4)
    elif t<8:
        scene=2; info=cabin(t-4)
        caption("He came back to another.",t,4,8)
    else:
        scene=3; info=rocket(t-8)
        text("DAY",64,104,40,"#878991",font="mono",center=False,role="counter")
        text("1",153,104,60,WHITE,font="mono",center=False,role="counter")
        text("18 MAY 1991",64,164,40,"#9b9da4",font="mono",center=False,role="date")
        caption(["May 1991. Sergei Krikalev flies","to the space station Mir."],t,8.2,15.5)
    sf.flush()
    return sf,{"frame":n,"time":round(t,6),"scene":scene,"bounds":list(BOUNDS),"scales":list(SCALES),"motion":info}

def overlaps(a,b): return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])

def qa(meta):
    found=[]
    heads=[o for o in meta["bounds"] if o["role"]=="head"]
    texts=[o for o in meta["bounds"] if o["role"]=="text" and o.get("opacity",1)>.03]
    def issue(rule,msg): found.append({"frame":meta["frame"],"scene":meta["scene"],"rule":rule,"detail":msg})
    for h in heads:
        b=h["box"]
        if b[0]<8 or b[1]<8 or b[2]>W-8 or b[3]>H-8: issue("head_crop",h["name"])
    for i,a in enumerate(texts):
        b=a["box"]
        if b[0]<32 or b[1]<8 or b[2]>W-32 or b[3]>H-16: issue("text_margin",a["name"])
        if a["text_role"]=="caption":
            if b[0]<380 or b[2]>1540 or b[1]<0 or b[3]>200: issue("subtitle_zone",a["name"])
        for h in heads:
            if overlaps(b,h["box"]): issue("text_head_overlap",a["name"])
        for c in texts[i+1:]:
            if overlaps(b,c["box"]): issue("text_text_overlap",a["name"]+" / "+c["name"])
    if meta["scene"]==2:
        m=meta["motion"]
        if math.dist(m["hand_world"],m["rail_contact_world"])>.01: issue("rail_contact","hand detached")
        if m["root_speed_px_s"]>15: issue("zero_g_speed","root")
        if abs(m["rotation_deg_s"])>6: issue("zero_g_rotation","root")
    expected={"hero":370,"module":886,"window":63,"handrail":8,"rocket":500}
    for v in meta["scales"]:
        name=v["name"]
        if name in expected and abs(v["base_extent_px"]/expected[name]-1)>.05:
            issue("scale",name)
    if meta["scene"] in [1,3] and heads: issue("wrong_scale_human","human in exterior")
    return found

def sound():
    sr=48000; length=SECONDS*sr; t=np.arange(length,dtype=np.float64)/sr
    rng=np.random.default_rng(19910518)
    def band_noise(low,high):
        white=rng.normal(size=length)
        spec=np.fft.rfft(white); f=np.fft.rfftfreq(length,1/sr)
        smooth=(1/(1+(np.maximum(f,1)/high)**4))*(1/(1+(low/np.maximum(f,1))**4))
        s=np.fft.irfft(spec*smooth,n=length)
        return s/(np.std(s)+1e-9)
    # Editorial low texture in exterior, quiet ventilation only in interior.
    hum=.011*np.sin(2*np.pi*57*t)+.006*np.sin(2*np.pi*87*t)
    vent=band_noise(200,1400)*.005
    interior=((t>=4)&(t<8)).astype(float)
    amb=hum*.65+vent*(.25+.8*interior)
    signal=amb
    cues=[]
    def cue(time,duration,name,kind):
        nonlocal signal
        start=round(time*sr); length0=round(duration*sr); tt=np.arange(length0)/sr
        if kind=="beep":
            env=np.minimum(1,tt/.006)*np.exp(-tt*15)
            s=.05*(np.sin(2*np.pi*740*tt)+.25*np.sin(2*np.pi*1480*tt))*env
        else:
            env=np.minimum(1,tt/.004)*np.exp(-tt*19)
            s=.06*rng.normal(size=length0)*env+.045*np.sin(2*np.pi*140*tt)*env
        signal[start:start+length0]+=s[:max(0,min(length0,len(signal)-start))]
        cues.append({"time":time,"frame":round(time*FPS),"cue":name,"visual_frame":round(time*FPS),"offset_frames":0})
    for second,digit in [(10,3),(11,2),(12,1)]: cue(second,.18,f"countdown {digit}","beep")
    cue(13.8,.42,"service arms released / liftoff","clunk")
    roar=band_noise(24,450)
    hiss=band_noise(600,4500)
    a=np.maximum(0,t-13)
    env=np.where(t>=13,np.minimum(1,a/.8)*(1-.24*np.minimum(a/10,1)),0)
    modulation=1+.07*np.sin(2*np.pi*3.1*t)+.035*np.sin(2*np.pi*7.7*t)
    signal+=env*modulation*(.1*roar+.012*hiss)
    cues.append({"time":13,"frame":390,"cue":"ignition / nozzle flames","visual_frame":390,"offset_frames":0})
    signal*=np.minimum(1,(SECONDS-t)/.08)
    # Stereo remains mostly centered and mono-compatible.
    stereo=np.column_stack([signal,signal*.985])
    with wave.open(str(OUT/"preview-original-mix.wav"),"wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(sr)
        f.writeframes((np.clip(stereo,-1,1)*32767).astype("<i2").tobytes())
    (OUT/"audio-cues.json").write_text(json.dumps(cues,indent=2),encoding="utf-8")

def build_sheet(paths,name,cols=4,thumb_w=480):
    cell_h=270+30
    sheet=Image.new("RGB",(cols*thumb_w,math.ceil(len(paths)/cols)*cell_h),(16,17,21))
    dr=ImageDraw.Draw(sheet); font=ImageFont.truetype(str(FONTS["mono"]),18)
    for i,p in enumerate(paths):
        im=Image.open(p).convert("RGB").resize((thumb_w,270),Image.Resampling.LANCZOS)
        x=(i%cols)*thumb_w; y=(i//cols)*cell_h
        sheet.paste(im,(x,y)); dr.text((x+9,y+274),p.stem,font=font,fill="#e4e0cf")
    sheet.save(QA/name,quality=94)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--stills",action="store_true")
    args=parser.parse_args()
    if args.stills:
        for n in [60,180,315,405,570]:
            sf,m=render_frame(n); sf.write_to_png(str(QA/f"design-{n:04}.png"))
            print(json.dumps({"frame":n,"qa":qa(m),"heads":[b for b in m["bounds"] if b["role"]=="head"]}))
        build_sheet([QA/f"design-{n:04}.png" for n in [60,180,315,405,570]],"design-sheet.jpg",cols=3)
        return
    command=["ffmpeg","-y","-hide_banner","-loglevel","warning","-f","rawvideo","-pixel_format","bgr0",
        "-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","pipe:0","-an","-c:v","libx264",
        "-preset","fast","-crf","18","-pix_fmt","yuv420p",str(OUT/"picture.mp4")]
    print("PICTURE COMMAND:",subprocess.list2cmdline(command),flush=True)
    proc=subprocess.Popen(command,stdin=subprocess.PIPE)
    issues=[]; metadata=[]; repeats=[]; past={}
    # Every 1 s plus cut-boundary frames, scene midpoints and caption onsets.
    exports=set(range(0,N,30))|{0,N-1,119,120,239,240,60,180,465,246,390,414}
    pngs=[]
    for n in range(N):
        sf,m=render_frame(n); issues.extend(qa(m)); metadata.append(m)
        data=sf.get_data()
        digest=hashlib.sha256(data).digest()
        if n>=30 and past[n-30]==digest: repeats.append(n)
        past[n]=digest
        if n in exports:
            p=QA/f"frame-{n:04d}-{n/FPS:06.2f}s.png"; sf.write_to_png(str(p)); pngs.append(p)
        proc.stdin.write(data)
        if n%90==0: print(f"RENDER {n}/{N}",flush=True)
    proc.stdin.close()
    if proc.wait()!=0: raise RuntimeError("FFmpeg picture encode failed")
    for n in repeats: issues.append({"frame":n,"rule":"identical_n_minus_30"})
    (QA/"frame-metadata.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    (QA/"geometry-issues.json").write_text(json.dumps(issues,indent=2),encoding="utf-8")
    print("PREVIEW GEOMETRY/PIXEL ISSUES:",len(issues),flush=True)
    sound()
    # Real two-pass EBU measurement/normalization, then encoded-output verification.
    measurement=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(OUT/"preview-original-mix.wav"),
        "-af","loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json","-f","null",os.devnull],capture_output=True,text=True)
    (QA/"loudness-input.txt").write_text(measurement.stderr,encoding="utf-8")
    if measurement.returncode: raise RuntimeError(measurement.stderr)
    block=json.JSONDecoder().raw_decode(measurement.stderr[measurement.stderr.rfind("{"):])[0]
    filt=("loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I="+block["input_i"]+
        ":measured_TP="+block["input_tp"]+":measured_LRA="+block["input_lra"]+
        ":measured_thresh="+block["input_thresh"]+":offset="+block["target_offset"])
    mux=["ffmpeg","-y","-hide_banner","-loglevel","warning","-i",str(OUT/"picture.mp4"),
        "-i",str(OUT/"preview-original-mix.wav"),"-af",filt,"-map","0:v:0","-map","1:a:0",
        "-c:v","copy","-c:a","aac","-b:a","192k","-ar","48000","-t",str(SECONDS),
        "-movflags","+faststart",str(ROOT/"preview.mp4")]
    subprocess.run(mux,check=True)
    build_sheet(pngs,"contact-sheet.jpg")
    probe=subprocess.run(["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(ROOT/"preview.mp4")],capture_output=True,text=True,check=True)
    (QA/"ffprobe.json").write_text(probe.stdout,encoding="utf-8")
    # Read logs as observations, not a fake full-documentary QA certificate.
    checks={
        "freezedetect":["-vf","freezedetect=n=0:d=1","-an"],
        "blackdetect":["-vf","blackdetect=d=0.1:pix_th=0.10:pic_th=0.98","-an"],
        "silencedetect":["-af","silencedetect=noise=-45dB:d=1.5","-vn"],
        "loudness-final":["-af","loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json","-vn"],
    }
    for name,flt in checks.items():
        cmd=["ffmpeg","-hide_banner","-nostats","-i",str(ROOT/"preview.mp4")]+flt+["-f","null",os.devnull]
        res=subprocess.run(cmd,capture_output=True,text=True)
        (QA/(name+".txt")).write_text(subprocess.list2cmdline(cmd)+"\n"+res.stderr,encoding="utf-8")
        if res.returncode: raise RuntimeError(f"{name} failed")
    report={"scope":"23-second preview only; not final documentary","frames":N,"seconds":SECONDS,
        "geometry_pixel_issue_count":len(issues),"mutation_tests":"not run",
        "all_frame_visual_inspection":"not claimed","rendered_sample_count":len(pngs)}
    (QA/"preview-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2),flush=True)
    print("OUTPUT:",str(ROOT/"preview.mp4"),flush=True)

if __name__=="__main__": main()

