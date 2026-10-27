"""Delivered-pixel/audio checks and actual encoded mutation fixtures.
No metadata-only geometry result is counted as a decoded-pixel pass.
Template conformance is NOT proof of photorealism, historical accuracy or good acting.
"""
from pathlib import Path
import argparse,hashlib,json,math,os,re,subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageOps
from scipy import ndimage,signal
from skimage.metrics import structural_similarity
import pyloudnorm as pyln
P=Path(__file__).resolve().parent;O=P/'preview-v3';Q=O/'qa';F=P/'preview-v3.mp4'
SR=48000;METER=pyln.Meter(SR);W,H=1920,1080
SAMPLES=[0,75,78,150,270,345,414,495,600,660]
CUTS=[120,240,330,405,480]
def run(args,**kw):return subprocess.run(args,capture_output=True,check=True,**kw)
def ff(*args,**kw):return run(['ffmpeg','-hide_banner','-nostats',*map(str,args)],**kw)
def probe(file):return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(file)],text=True).stdout)
def pcm(file):return np.frombuffer(ff('-v','error','-i',file,'-vn','-ar',SR,'-ac',2,'-f','f32le','pipe:1').stdout,'<f4').reshape(-1,2).copy()
def loudness(file):
    raw=ff('-i',file,'-af','loudnorm=I=-14:TP=-1.5:LRA=7:print_format=json','-f','null',os.devnull).stderr.decode()
    j=json.JSONDecoder().raw_decode(raw[raw.rfind('{'):])[0]
    return {'integrated_LUFS':float(j['input_i']),'true_peak_dBTP':float(j['input_tp']),'LRA_LU':float(j['input_lra'])},raw
def audio_rules(x,metrics):
    issues=[];seconds=[float(METER.integrated_loudness(x[i*SR:(i+1)*SR])) for i in range(23)]
    short=[{'end_s':i,'LUFS':float(METER.integrated_loudness(x[(i-3)*SR:i*SR]))} for i in range(3,24)]
    floor=[float(METER.integrated_loudness(x[k:k+SR])) for k in range(0,len(x)-SR+1,SR//10)]
    if abs(metrics['integrated_LUFS']+14)>.5:issues.append('integrated_loudness')
    if metrics['true_peak_dBTP']>-1.5:issues.append('true_peak')
    if not 5<=metrics['LRA_LU']<=9:issues.append('loudness_range')
    if min(floor)<-24:issues.append('audio_window_floor')
    # Pure cabin windows, excluding transitions/cues: 4..7 and 5..8.
    cabin=[s['LUFS'] for s in short if s['end_s'] in [7,8]]
    pure_atmosphere=[s['LUFS'] for s in short if s['end_s'] in [3,4,5,6,7,8,19,20,21,22,23]]
    if not all(-20<=v<=-18 for v in pure_atmosphere):issues.append('ambience_level')
    peak=max(s['LUFS'] for s in short if 14<=s['end_s']<=16)
    if not -11<=peak<=-9:issues.append('launch_level')
    # Soft low-passed bed: encoded cabin energy above 3 kHz must be negligible.
    f,power=signal.welch(x[4*SR:8*SR].mean(axis=1),SR,nperseg=8192)
    high=float(power[f>3000].sum()/power.sum())
    if high>.025:issues.append('ambience_spectrum')
    weighted=x.astype('float64').copy()
    for stage in METER._filters.values():
        for channel in range(2):weighted[:,channel]=stage.apply_filter(weighted[:,channel])
    cumulative=np.r_[0.,np.cumsum(np.sum(weighted*weighted,axis=1))]
    means=(cumulative[SR:]-cumulative[:-SR])/SR
    sample_windows=-.691+10*np.log10(np.maximum(means,1e-30))
    sample_floor={'method':'BS.1770 K-weighted ungated one-second power; every sample start',
        'window_count':len(sample_windows),'minimum_LUFS':float(sample_windows.min()),
        'minimum_start_s':int(sample_windows.argmin())/SR,'below_minus24_count':int(np.count_nonzero(sample_windows<-24))}
    if sample_floor['below_minus24_count']:issues.append('audio_window_floor')
    return sorted(set(issues)),{'loudness_per_second':[round(v,3) for v in seconds],
        'short_term_3s':short,'minimum_sliding_1s_LUFS':min(floor),'window_count':len(floor),
        'cabin_short_term_LUFS':cabin,'all_pure_atmosphere_short_term_LUFS':pure_atmosphere,'launch_peak_short_term_LUFS':peak,'cabin_energy_above_3kHz_ratio':high,'every_sample_floor':sample_floor}
def filler_info(file):
    data=ff('-v','error','-i',file,'-map','0:v:0','-c:v','copy','-bsf:v','h264_mp4toannexb','-f','h264','pipe:1').stdout
    nals=[x for x in re.split(b'\x00\x00\x00?\x01',data) if x]
    filler=sum(len(x) for x in nals if x[0]&31==12)
    headers=ff('-v','verbose','-i',file,'-map','0:v:0','-c:v','copy','-bsf:v','trace_headers','-f','null',os.devnull).stderr.decode(errors='replace')
    hrd=[line for line in headers.splitlines() if 'nal_hrd_parameters_present_flag' in line]
    hrd_present=any(re.search(r'=\s*1\s*$',line) for line in hrd)
    duration=float(probe(file)['streams'][0]['duration'])
    return {'annex_b_bytes':len(data),'filler_NAL_bytes':filler,'filler_NAL_count':sum(1 for x in nals if x[0]&31==12),
        'real_video_payload_bps':round(sum(len(x) for x in nals if x[0]&31!=12)*8/duration),
        'HRD_present':hrd_present,'HRD_header_evidence':hrd},headers
def native_frame(file,n):
    b=ff('-v','error','-i',file,'-vf',f'select=eq(n\\,{n})','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1').stdout
    if len(b)!=W*H*3:raise RuntimeError('Native frame decode failed '+str(n))
    return np.frombuffer(b,np.uint8).reshape(H,W,3).copy()
def gray_video(file):
    b=ff('-v','error','-i',file,'-vf','scale=480:270:flags=area,format=gray','-f','rawvideo','-pix_fmt','gray','pipe:1').stdout
    return np.frombuffer(b,np.uint8).reshape(-1,270,480).copy()
def motion(gray):
    vals=[]
    font=ImageFont.truetype(str(P/'assets/Andika-Bold.ttf'),56)
    def text_mask(n):
        # Exact font metrics, including outline/shadow padding. Mask text
        # rectangles, NOT the entire blank caption band (which would inflate
        # the changed-pixel percentage by shrinking its denominator).
        mask=np.ones((270,480),bool)
        lines=['He left Earth from one country.'] if n<120 else ['He came back to another.'] if n<240 else ['May 1991. Sergei Krikalev flies','to the space station Mir.'] if n<480 else ['The plan: five months in orbit.']
        for i,s in enumerate(lines):
            b=font.getbbox(s,anchor='ls');width=b[2]-b[0];base=152 if len(lines)==1 else 86+66*i
            x0=int((960-width/2-8)/4);x1=math.ceil((960+width/2+8)/4)
            y0=int((base+b[1]-8)/4);y1=math.ceil((base+b[3]+8)/4)
            mask[max(0,y0):y1,max(0,x0):x1]=False
        if n>=240:mask[8:47,10:80]=False
        if 240<=n<330:mask[120:152,298:329]=False
        return mask
    masks=[text_mask(n) for n in range(len(gray))]
    for n in range(30,len(gray)):
        # Caption and day/counter/clock graphics cannot make a static picture pass.
        mask=masks[n]&masks[n-30]
        changed=(np.abs(gray[n].astype('int16')-gray[n-30].astype('int16'))>3)&mask
        vals.append({'frame':n,'time':round(n/30,4),'percent':float(100*changed.sum()/mask.sum())})
    # First second has no preceding one-second sample. Do not invent one.
    per_second=[None]+[round(next(v['percent'] for v in vals if v['frame']==s*30),4) for s in range(1,math.ceil(len(gray)/30))]
    bad=[v for v in vals if v['percent']<3]
    return {'per_second_percent':per_second,'first_entry':'not defined: no preceding frame at t=-1',
        'minimum_percent':min(v['percent'] for v in vals),'failures':bad,'all_windows':vals}

# Explicit picture-space regions. Every rule below sees decoded RGB pixels,
# compared with the lossless approved layout; metadata is not its evidence.
GEOMETRY=[
 ('map_reveal',60,(180,240,1740,1030)),('map_count',100,(130,240,1780,1050)),
 ('map_displacement',100,(130,240,1780,1050)),('map_tints',100,(130,240,1780,1050)),
 ('map_overlap',100,(130,240,1780,1050)),('map_sphere_projection',60,(130,215,1790,1050)),
 ('crack_flash',75,(130,240,1780,1050)),('mir_size',60,(1200,240,1440,370)),
 ('hero_scale',150,(700,340,1130,810)),('neutral_pose',150,(850,540,1100,830)),
 ('free_arm',150,(770,425,1010,640)),('gaze_window',150,(770,340,1020,540)),
 ('rail_contact',150,(950,400,1120,655)),('rail_brackets',150,(970,400,1150,760)),
 ('window_earth',150,(570,440,760,650)),('head_visibility',150,(740,320,1050,570)),
 ('smoke_ground_connection',345,(0,630,1920,1050)),('pad_in_closeup',345,(420,710,1500,1030)),
 ('flame_palette',345,(760,720,1170,1040)),('four_support_arms',300,(690,485,1260,1030)),
 ('umbilical_retraction',300,(590,400,1350,1050)),('low_angle_perspective',414,(650,210,1270,1050)),
 ('no_liftoff_tower',414,(380,215,1550,1050)),('docking_replaces_hook',600,(470,350,1540,880)),
 ('docking_contact',689,(470,350,1540,880)),('day_visible_after_16s',660,(40,35,315,185)),
]
def crop(a,box):x0,y0,x1,y1=box;return a[y0:y1,x0:x1]
def image_agreement(actual,reference,box):
    a=crop(actual,box).astype('int16');b=crop(reference,box).astype('int16')
    # Pixel evidence is sensitive to missing 3 px strokes, not dominated by black.
    support=np.max(np.abs(b-np.array([13,13,16])),axis=2)>12
    support=ndimage.binary_dilation(support,iterations=2)
    if not support.any():support[:]=True
    mismatch=np.max(np.abs(a-b),axis=2)>22
    return float((mismatch&support).sum()/support.sum())
def geometry_rule(actual,reference,rule,box):
    error=image_agreement(actual,reference,box)
    # Red small lettering has normal 4:2:0 edge differences; an absent counter
    # still disagrees across almost its entire measured foreground.
    fail=error>(.04 if rule=='day_visible_after_16s' else .025)
    if rule in ['map_count','map_overlap']:
        import render_preview_v3 as R
        a=crop(actual,box).astype('int16');b=crop(reference,box).astype('int16')
        for color in R.PALETTE:
            c=np.array([int(color[k:k+2],16) for k in (1,3,5)])
            expected=np.max(np.abs(b-c),axis=2)<9
            if expected.sum()<8:continue
            # A tiny region may be only a few chroma samples wide. Verify its
            # decoded red/rose foreground rather than demand exact pre-4:2:0
            # RGB at every antialiased edge. A missing/moved region is blue.
            visible=(a[:,:,0]-np.maximum(a[:,:,1],a[:,:,2])>15)&(a[:,:,0]>60)
            coverage=(visible&expected).sum()/expected.sum()
            if coverage<.75:fail=True
    if rule=='crack_flash':
        a=crop(actual,box);b=crop(reference,box)
        white_a=(a.min(axis=2)>175).sum();white_b=(b.min(axis=2)>175).sum()
        if white_a<white_b*.85:fail=True
    return ([rule] if fail else []),error
def encode_image(im,path):
    temp=path.with_suffix('.png');im.save(temp)
    ff('-y','-v','error','-i',temp,'-frames:v','1','-r','30','-c:v','libx264','-crf','16','-preset','slow','-tune','animation','-pix_fmt','yuv420p',path)
    return native_frame(path,0)
def text_zone_check(actual,reference):
    # Reference typography only; all picture content is prohibited here.
    a=actual[:200,380:1540].astype('int16');b=reference[:200,380:1540].astype('int16')
    glyph=np.max(np.abs(b-np.array([13,13,16])),axis=2)>12
    glyph=ndimage.binary_dilation(glyph,iterations=8)
    stray=(np.max(np.abs(a-np.array([13,13,16])),axis=2)>22)&~glyph
    return int(stray.sum())

def subtitle_reading(gray):
    result=[];issues=[]
    for start,end,words in [(0,min(120,len(gray)),6),(120,min(240,len(gray)),5),(240,min(480,len(gray)),10),(480,min(690,len(gray)),6)]:
        if start>=len(gray):continue
        counts=np.count_nonzero(gray[start:end,:50,95:385]>180,axis=(1,2))
        duration=float(np.count_nonzero(counts>=max(20,float(counts.max())*.90))/30)
        required=1.5+.3*words
        result.append({'start_s':start/30,'end_s':end/30,'words':words,'decoded_readable_duration_s':duration,'minimum_s':required,'pass':duration>=required})
        if duration<required:issues.append('subtitle_read_time')
    return issues,result

def cue_measurements(x,cues):
    mono=x.mean(axis=1);result=[]
    for cue in cues:
        template=pcm(P/cue['template']).mean(axis=1)[:4800]
        expected=round(cue['visual_frame']/30*SR);lo=max(0,expected-round(.3*SR));hi=min(len(mono),expected+len(template)+round(.3*SR))
        observed=mono[lo:hi]
        method='full-band matched waveform'
        if cue['name']=='support release':
            # The 120Hz metallic body is masked by the engine. Match the
            # cue's unique high-frequency attack, not that shared tone.
            sos=signal.butter(4,[2200,9000],fs=SR,btype='bandpass',output='sos')
            observed=signal.sosfilt(sos,observed);template=signal.sosfilt(sos,template)
            method='2.2..9kHz attack matched waveform; reject engine low-band correlation'
        corr=signal.correlate(observed,template,mode='valid',method='fft');found=int(np.argmax(corr))+lo
        result.append({'name':cue['name'],'visual_frame':cue['visual_frame'],'detected_sample':found,'sound_frame':round(found/SR*30),'offset_frames':round(found/SR*30)-cue['visual_frame'],'method':method})
    return result

def detector_failures(file,name):
    flag,expr,key={'freezedetect':('-vf','freezedetect=n=-60dB:d=1','freeze_start:'),
        'blackdetect':('-vf','blackdetect=d=.1:pix_th=.1:pic_th=.98','black_start:'),
        'silencedetect':('-af','silencedetect=noise=-45dB:d=1.5','silence_start:')}[name]
    raw=ff('-i',file,flag,expr,'-f','null',os.devnull).stderr.decode(errors='replace')
    return ([name] if key in raw else []),raw

def export():
    selected=set(range(0,690,15))|set(SAMPLES)|{689,78,414,495}|set(CUTS)|{n-1 for n in CUTS}|{60,100,300,367,442,1,121,242,484}
    ordered=sorted(selected);dest=Q/'frames'
    for d in [dest,Q/'mutations']:d.mkdir(exist_ok=True)
    expression='select='+ '+'.join(f'eq(n\\,{n})' for n in ordered)
    ff('-y','-v','error','-i',F,'-vf',expression,'-fps_mode','vfr',dest/'decoded-%03d.png')
    for i,n in enumerate(ordered):(dest/f'decoded-{i+1:03d}.png').replace(dest/f'frame-{n:04d}-{n/30:06.2f}s.png')
    font=ImageFont.truetype(str(P/'assets/JetBrainsMono.ttf'),18)
    def sheet(ns,file):
        im=Image.new('RGB',(1920,math.ceil(len(ns)/4)*300),(13,13,16));d=ImageDraw.Draw(im)
        for i,n in enumerate(ns):
            frame=Image.open(dest/f'frame-{n:04d}-{n/30:06.2f}s.png').convert('RGB').resize((480,270),Image.Resampling.LANCZOS)
            x=i%4*480;y=i//4*300;im.paste(frame,(x,y));d.text((x+8,y+274),f'{n/30:05.2f}s / {n}',font=font,fill='white')
        im.save(file,quality=95)
    frames=list(range(0,690,15));sheet(frames,Q/'contact-sheet-2fps.jpg')
    for k in range(0,len(frames),16):sheet(frames[k:k+16],Q/f'contact-page-{k//16+1}.jpg')
    return ordered
def load_frame(n):return np.array(Image.open(Q/'frames'/f'frame-{n:04d}-{n/30:06.2f}s.png').convert('RGB'))

def map_pixel_measurements(actual,n=100):
    """Measure the actual encoded colour centroids against isolated unshifted
    picture layers. Neither an offset field nor a claimed region count passes.
    """
    import cairo
    import render_preview_v3 as R
    from shapely import affinity
    rows=[];t=n/30;s=R.camera(t)[0]
    for i,(name,g,off) in enumerate(R.pieces_at(t)):
        sf=cairo.ImageSurface(cairo.FORMAT_RGB24,W,H);R.setup(sf)
        R.B.src(R.B.BG);R.C.paint();R.C.save();R.world_transform(t)
        R.path(affinity.translate(g,*(-off)));R.B.fillstroke(R.PALETTE[i],None);R.C.restore()
        baseline=R.rgb(sf)
        color=np.array([int(R.PALETTE[i][k:k+2],16) for k in (1,3,5)])
        bmask=np.max(np.abs(baseline.astype('int16')-color),axis=2)<8
        amask=np.max(np.abs(actual.astype('int16')-color),axis=2)<12
        # Restrict the colour search to the maximum physically permitted
        # neighbourhood of this isolated region. Red tints can share codec-
        # quantized RGB values elsewhere on the globe; global thresholding
        # would incorrectly merge distant republics.
        by0,bx0=np.nonzero(bmask)
        spatial=np.zeros((H,W),bool)
        if len(bx0):
            pad=math.ceil(45*s)
            spatial[max(0,by0.min()-pad):min(H,by0.max()+pad+1),max(0,bx0.min()-pad):min(W,bx0.max()+pad+1)]=True
        amask&=spatial
        by,bx=np.nonzero(bmask);ay,ax=np.nonzero(amask)
        shift=float(math.hypot(ax.mean()-bx.mean(),ay.mean()-by.mean())/s) if len(ax) and len(bx) else None
        mean=actual[amask].mean(axis=0).tolist() if len(ax) else None
        rows.append({'republic':name,'decoded_interior_pixels':len(ax),'unshifted_reference_pixels':len(bx),
          'measured_radial_shift_in_picture_px':shift,'decoded_mean_RGB':mean,
          'target_shift_range_px':[25,40],'pass':len(ax)>=8 and shift is not None and 25<=shift<=40})
    return rows

def mutations(references,clean_metrics,clean_pcm):
    import render_preview_v3 as R
    results=[];md=Q/'mutations';before=hashlib.sha256(F.read_bytes()).hexdigest()
    def record(name,caught,rule,evidence):
        ok=rule in caught;results.append({'name':name,'expected_rule':rule,'caught':caught,'pass':ok,'evidence':str(evidence.relative_to(P))})
        print(('PASS' if ok else 'FAIL')+f' MUTATION {name}: expected={rule}; caught={caught}',flush=True)
    # Every geometry rule gets an actual one-frame H.264 mutation. Diagnostic
    # omissions exercise the same decoded-pixel checker used above.
    flags={'map_reveal':'map_reveal','map_count':'map_count','map_tints':'map_tints','map_displacement':'map_displacement','map_overlap':'map_overlap',
        'crack_flash':'no_flash','mir_size':'small_mir','hero_scale':'hero_scale','neutral_pose':'gravity_pose','rail_contact':'detached_hand','rail_brackets':'rail_brackets','window_earth':'scale','day_visible_after_16s':'missing_day'}
    for rule,n,box in GEOMETRY:
        reference=references[n]
        if rule in flags:
            sf,m,pic=R.draw(n,{flags[rule]:True});im=Image.fromarray(R.rgb(sf))
        else:
            # A visible wrong/cropped geometry patch, not edited JSON.
            im=Image.fromarray(reference.copy());d=ImageDraw.Draw(im)
            x0,y0,x1,y1=box;d.rectangle((x0,y0,x1,y1),fill=(13,13,16))
        file=md/(rule+'.mp4');decoded=encode_image(im,file)
        caught,_=geometry_rule(decoded,reference,rule,box);record(rule,caught,rule,file)
    # New caption rule catches line art even though all typography is intact.
    n=60;im=Image.fromarray(references[n]);ImageDraw.Draw(im).line((600,128,1320,128),fill='#929ba3',width=3)
    file=md/'stroke-through-caption.mp4';a=encode_image(im,file)
    record('stroke_in_caption',['subtitle_art'] if text_zone_check(a,references[n])>0 else [],'subtitle_art',file)
    # New near-static mutation is NOT pixel-identical: a tiny cursor moves.
    file=md/'near-static-with-moving-cursor.mp4'
    png=md/'near-static-base.png';Image.fromarray(references[270]).save(png)
    ff('-y','-v','error','-loop','1','-i',png,'-t','2.1','-r','30','-vf',"drawbox=x=30:y=300:w=4:h=4:color=white:t=fill",'-an','-c:v','libx264','-crf','16',file)
    g=gray_video(file);g[:,100,8]=(np.arange(len(g))%9)*5 # retain a real, encoded moving dot below
    # Encode the moving-pixel sequence, then decode it again for the test.
    ff('-y','-v','error','-f','rawvideo','-s','480x270','-r','30','-pix_fmt','gray','-i','pipe:0','-an','-c:v','libx264','-crf','16',file,input=g.tobytes())
    mm=motion(gray_video(file));record('near_static_motion',['near_static_motion'] if mm['failures'] else [],'near_static_motion',file)
    # New SSIM fidelity mutation: severe posterization and geometry-preserving
    # blur on a genuine source frame, followed by H.264 encoding/decoding.
    im=ImageOps.posterize(Image.fromarray(references[0]),2).filter(ImageFilter.GaussianBlur(3))
    file=md/'gradient-banding.mp4';a=encode_image(im,file)
    s=float(structural_similarity(a,references[0],channel_axis=2,data_range=255))
    record('banded_gradients',['ssim_fidelity'] if s<.98 else [],'ssim_fidelity',file)
    # Explicit filler test. It must fail even when picture quality is high.
    file=md/'filler-inflated.mp4'
    ff('-y','-v','error','-i',F,'-t','1','-an','-c:v','libx264','-crf','16','-minrate','10000k','-maxrate','10000k','-bufsize','20000k','-x264-params','nal-hrd=vbr:filler=1',file)
    fi,_=filler_info(file);record('filler_payload',['no_filler_hrd'] if fi['filler_NAL_bytes'] or fi['HRD_present'] else [],'no_filler_hrd',file)
    # Audio mutations are actual WAVs measured after writing, never fabricated
    # loudness numbers. One corrupted example for every active audio rule.
    for rule in ['integrated_loudness','true_peak','loudness_range','audio_window_floor','ambience_level','launch_level','ambience_spectrum']:
        x=clean_pcm.copy()
        if rule=='integrated_loudness':x*=.45
        elif rule=='true_peak':x*=3
        elif rule=='audio_window_floor':x[:SR]*=.001
        elif rule=='ambience_level':x[4*SR:8*SR]*=2.8
        elif rule=='launch_level':x[11*SR:16*SR]*=.35
        elif rule=='ambience_spectrum':
            rng=np.random.default_rng(19);x[4*SR:8*SR]+=rng.normal(0,.10,(4*SR,2))
        else:
            # Replacing the full soundtrack by one loudness level destroys LRA.
            rng=np.random.default_rng(123);v=signal.sosfilt(signal.butter(2,1100,fs=SR,output='sos'),rng.normal(size=len(x)))
            x=np.column_stack([v,v]);x*=10**((-14-METER.integrated_loudness(x))/20)
        file=md/(rule+'.wav');R.writewav(file,x);metrics,_=loudness(file)
        caught,_=audio_rules(pcm(file),metrics);record(rule,caught,rule,file)
    # Real encoded mutations for format, missing audio and mismatched duration.
    for name,rule,args in [
        ('wrong-resolution','resolution',['-vf','scale=1280:720','-c:v','libx264','-crf','16','-c:a','copy']),
        ('wrong-fps','frame_rate',['-r','24','-c:v','libx264','-crf','16','-c:a','copy']),
        ('missing-audio','audio_present',['-an','-c:v','copy']),
        ('duration-mismatch','duration_match',['-c:v','copy','-af','atrim=0:0.5','-c:a','aac'])]:
        file=md/(name+'.mp4');ff('-y','-v','error','-i',F,'-t','1',*args,file)
        caught=media_rules(probe(file));record(name,caught,rule,file)
    # Existing detectors also have real corrupted-media negative controls.
    for name in ['freezedetect','blackdetect','silencedetect']:
        file=md/(name+'-negative.mp4')
        if name=='freezedetect':
            ff('-y','-v','error','-loop','1','-i',md/'near-static-base.png','-t','2.1','-r','30','-c:v','libx264','-crf','16',file)
        elif name=='blackdetect':
            ff('-y','-v','error','-i',F,'-t','2','-vf',"drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='lt(t,1.2)'",'-c:v','libx264','-crf','16','-c:a','copy',file)
        else:
            ff('-y','-v','error','-i',F,'-t','3','-af',"volume=0:enable='lt(t,2)'",'-c:v','copy','-c:a','aac',file)
        caught,raw=detector_failures(file,name);(md/(name+'-negative.txt')).write_text(raw)
        record(name,caught,name,file)
    file=md/'too-short-caption.mp4'
    ff('-y','-v','error','-i',F,'-t','4','-vf',"drawbox=x=380:y=0:w=1160:h=200:color=0x0d0d10:t=fill:enable='gte(t,1)'",'-an','-c:v','libx264','-crf','16',file)
    caught,_=subtitle_reading(gray_video(file));record('caption_read_time',caught,'subtitle_read_time',file)
    cues=json.loads((O/'audio-cues.json').read_text());late=clean_pcm.copy();crack=pcm(P/cues[0]['template'])
    late[:]=0;sample=round((cues[0]['time']+5/30)*SR);late[sample:sample+len(crack)]=crack
    file=md/'sfx-five-frames-late.wav';R.writewav(file,late)
    found=cue_measurements(pcm(file),[cues[0]])
    record('late_crack',['sfx_sync'] if abs(found[0]['offset_frames'])>2 else [],'sfx_sync',file)
    unchanged=hashlib.sha256(F.read_bytes()).hexdigest()==before
    results.append({'name':'original_unchanged','pass':unchanged})
    (Q/'mutation-results.json').write_text(json.dumps(results,indent=2))
    return results
def media_rules(p):
    issues=[];vs=[s for s in p['streams'] if s['codec_type']=='video'];aa=[s for s in p['streams'] if s['codec_type']=='audio']
    if not vs:return ['resolution']
    v=vs[0]
    if (v['width'],v['height'])!=(W,H):issues.append('resolution')
    if v['r_frame_rate']!='30/1':issues.append('frame_rate')
    if not aa:issues.append('audio_present')
    elif abs(float(v['duration'])-float(aa[0]['duration']))>1/30:issues.append('duration_match')
    return issues

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--skip-mutations',action='store_true');args=parser.parse_args()
    import render_preview_v3 as R
    issues=[];p=probe(F);issues+=media_rules(p)
    metrics,raw=loudness(F);(Q/'loudness-final.txt').write_text(raw)
    x=pcm(F);audio_issues,ar=audio_rules(x,metrics);issues+=audio_issues
    print('AUDIO',json.dumps({**metrics,**ar}),flush=True)
    filler,headers=filler_info(F);(Q/'h264-header-trace.txt').write_text(headers)
    if filler['filler_NAL_bytes'] or filler['HRD_present']:issues.append('no_filler_hrd')
    print('ENCODING',json.dumps(filler),flush=True)
    gray=gray_video(F);mr=motion(gray);(Q/'motion-per-frame.json').write_text(json.dumps(mr,indent=2))
    if mr['failures']:issues.append('near_static_motion')
    print('MOTION',json.dumps({k:v for k,v in mr.items() if k!='all_windows'}),flush=True)
    text_issues,reading=subtitle_reading(gray);issues+=text_issues
    (Q/'subtitle-reading.json').write_text(json.dumps(reading,indent=2))
    cues=cue_measurements(x,json.loads((O/'audio-cues.json').read_text()))
    if any(abs(c['offset_frames'])>2 for c in cues):issues.append('sfx_sync')
    (Q/'sfx-measured.json').write_text(json.dumps(cues,indent=2))
    print('SFX',json.dumps(cues),flush=True)
    order=export();references={};actuals={}
    frames=sorted(set(order)|{n for _,n,_ in GEOMETRY})
    for n in frames:
        sf,m,pic=R.draw(n);references[n]=R.rgb(sf);actuals[n]=load_frame(n)
    ssims=[]
    for n in SAMPLES:
        value=float(structural_similarity(actuals[n],references[n],channel_axis=2,data_range=255))
        ssims.append({'frame':n,'time':n/30,'SSIM_RGB':value})
        if value<.98:issues.append('ssim_fidelity')
    (Q/'ssim-samples.json').write_text(json.dumps(ssims,indent=2));print('SSIM',json.dumps(ssims),flush=True)
    geom=[]
    for rule,n,box in GEOMETRY:
        caught,error=geometry_rule(actuals[n],references[n],rule,box);issues+=caught
        geom.append({'rule':rule,'frame':n,'time':n/30,'ROI_px':box,'mismatched_foreground_fraction':error,'pass':not caught,'evidence':'decoded H.264 RGB versus retained lossless picture-space layout; no metadata-only pass'})
    # Native-pixel text/line-art clearance at every exported frame, including
    # both sides of cuts. Extra all-frame grayscale top check follows below.
    for n in frames:
        count=text_zone_check(actuals[n],references[n])
        if count:issues.append('subtitle_art');geom.append({'rule':'subtitle_art','frame':n,'stray_pixels':count,'pass':False})
    # DAY is checked in every delivered frame from 16 s until the last frame.
    for n in range(480,len(gray)):
        if np.count_nonzero(gray[n,9:44,12:76]>48)<30:issues.append('day_visible_after_16s');break
    detector_logs={}
    for name,flag,filterexpr in [('freezedetect','-vf','freezedetect=n=-60dB:d=1'),('blackdetect','-vf','blackdetect=d=.1:pix_th=.1:pic_th=.98'),('silencedetect','-af','silencedetect=noise=-45dB:d=1.5')]:
        log=ff('-i',F,flag,filterexpr,'-f','null',os.devnull).stderr.decode(errors='replace');detector_logs[name]=log
        (Q/(name+'.txt')).write_text(log)
        if any(k in log for k in ['freeze_start:','black_start:','silence_start:']):issues.append(name)
    (Q/'decoded-geometry-checks.json').write_text(json.dumps(geom,indent=2))
    map_measurements=map_pixel_measurements(actuals[100])
    (Q/'map-decoded-pixel-measurements.json').write_text(json.dumps(map_measurements,indent=2))
    if not all(row['pass'] for row in map_measurements):issues.append('map_displacement_or_count')
    print('MAP PIXEL MEASUREMENTS',json.dumps(map_measurements),flush=True)
    # A direct decoded-pixel test for hidden overpainted map intersections:
    # reversing the republic paint order must not change the image at all.
    # Both forward and reverse images are independently H.264 encoded first.
    sf,_,_=R.draw(100)
    forward=encode_image(Image.fromarray(R.rgb(sf)),Q/'mutations'/'map-order-forward.mp4')
    sf,_,_=R.draw(100,{'reverse_map':True})
    reverse=encode_image(Image.fromarray(R.rgb(sf)),Q/'mutations'/'map-order-reverse.mp4')
    order_delta=int(np.count_nonzero(np.max(np.abs(forward.astype('int16')-reverse.astype('int16')),axis=2)>3))
    order_evidence={'changed_decoded_pixels_when_paint_order_reversed':order_delta,'tolerance_RGB':3,'frame':100}
    (Q/'map-order-pixel-evidence.json').write_text(json.dumps(order_evidence,indent=2))
    if order_delta:issues.append('map_overlap')
    print('MAP ORDER PIXELS',json.dumps(order_evidence),flush=True)
    mut=[] if args.skip_mutations else mutations(references,metrics,x)
    issues+=['mutation_not_caught:'+v['name'] for v in mut if not v['pass']]
    result={'scope':'23-second corrected preview only','video':p,'audio':{**metrics,**ar},'encoding':filler,
        'motion':{k:v for k,v in mr.items() if k!='all_windows'},'ssim':ssims,'geometry':geom,
        'mutation_test_count':len(mut),'issues':sorted(set(issues)),
        'limits':['SSIM is a fidelity metric, not a guarantee that banding is imperceptible.',
          'Geometry pixel-template conformance and mutation sensitivity are measured; artistic quality and physical realism still require visual judgment.',
          'No physical-phone listening audition is claimed. Historical scan georeferencing is approximate.']}
    (Q/'qa-result.json').write_text(json.dumps(result,indent=2))
    print('QA issues:',len(set(issues)),flush=True)
    if issues:print('FAILURES',json.dumps(sorted(set(issues))),flush=True);raise SystemExit(1)
if __name__=='__main__':main()
