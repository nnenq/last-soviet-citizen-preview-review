import os
"""Independent checks and mutation tests for revised preview.
Spatial checks consume the actual drawn transforms/bounds and the saved picture
before text; audio checks consume decoded AAC PCM; bitrate comes from ffprobe.
"""
from pathlib import Path
import copy,datetime as dt,hashlib,json,math,subprocess,wave
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import shape
import pyloudnorm as pyln
from scipy import signal
W,H=1920,1080
SR=48000
METER=pyln.Meter(SR)
RULES=[
"text_head","text_text","head_crop","text_margin","subtitle_zone","subtitle_art",
"scale","zero_g_accel","earth_contact","map_overlap","date","counter_backwards",
"identical_n_minus_30","freeze_gt_1s","audio_window_floor","bitrate_floor",
"mir_size","map_reveal","map_count","map_displacement","neutral_pose","rail_contact",
"rail_brackets","zero_g_speed","zero_g_rotation","flame_palette",
"integrated_loudness","true_peak","loudness_range","subtitle_read_time",
"resolution","frame_rate","audio_present","duration_match","sfx_sync","launch_duration",
"freezedetect","blackdetect","silencedetect",
]
def hit(a,b):
    return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])

def check_frame(m,prev=None):
    out=[]
    def fail(rule,detail):out.append({"frame":m["frame"],"time":m["time"],"shot":m["shot"],"rule":rule,"detail":detail})
    texts=[b for b in m["bounds"] if b["role"]=="text" and b.get("opacity",1)>.03]
    heads=[b for b in m["bounds"] if b["role"]=="head"]
    for h in heads:
        a=h["box"]
        if a[0]<8 or a[1]<8 or a[2]>W-8 or a[3]>H-8:fail("head_crop",h["name"])
    for i,b in enumerate(texts):
        a=b["box"]
        if a[0]<32 or a[1]<8 or a[2]>W-32 or a[3]>H-16:fail("text_margin",b["name"])
        if b.get("text_role")=="caption":
            if a[0]<380 or a[2]>1540 or a[1]<0 or a[3]>200:fail("subtitle_zone",b["name"])
            if b.get("art_pixels_padded",0)>0:fail("subtitle_art",f"{b['name']}: {b['art_pixels_padded']} picture pixels in padded box")
        for h in heads:
            if hit(a,h["box"]):fail("text_head",b["name"])
        for other in texts[i+1:]:
            if hit(a,other["box"]):fail("text_text",b["name"])
    # Whole central subtitle zone also remains plain even during fades.
    if m.get("reserved_zone_art_pixels",0)>0:fail("subtitle_art","picture in reserved top zone")
    for s in m["scales"]:
        if "expected" in s and abs(s["value"]/s["expected"]-1)>.05:fail("scale",s["name"])
    b=m.get("body")
    if b:
        if b["root_accel_y"]>.02:fail("zero_g_accel","unforced downward acceleration")
        if b["speed"]>15:fail("zero_g_speed",str(b["speed"]))
        if abs(b["rotation_speed"])>6:fail("zero_g_rotation",str(b["rotation_speed"]))
        if not (25<=b["hip_flex_deg"]<=35 and 40<=b["knee_flex_deg"]<=50 and b["free_hand_local_y"]<-200):
            fail("neutral_pose","hips/knees/free arm")
        if math.dist(b["hand"],b["rail"])>.5:fail("rail_contact","hand detached")
        if b["rail_brackets"]!=2:fail("rail_brackets","needs two fixed wall brackets")
        if "leg_joints" in b:
            for hip,knee,foot in b["leg_joints"]:
                thigh=np.subtract(knee,hip);shank=np.subtract(foot,knee)
                flex=math.degrees(math.acos(np.clip(thigh[1]/np.linalg.norm(thigh),-1,1)))
                bend=math.degrees(math.acos(np.clip(np.dot(thigh,shank)/(np.linalg.norm(thigh)*np.linalg.norm(shank)),-1,1)))
                if not 25<=flex<=35 or not 40<=bend<=50:fail("neutral_pose",f"drawn joints hip={flex:.2f},knee={bend:.2f}")
    for prop in m.get("free_props",[]):
        if prop["acceleration"][1]>.02:fail("zero_g_accel","free prop")
        if math.hypot(*prop["velocity"])>15:fail("zero_g_speed","free prop")
        if abs(prop["rotation_speed"])>6:fail("zero_g_rotation","free prop")
    for f in m.get("earth_contacts",[]):
        if abs(f["foot_y"]-f["ground_y"])>1:fail("earth_contact",str(f))
    mp=m.get("map")
    if m.get("premature_internal_red_pixels",0)>0:fail("map_reveal","rendered red pixels on internal seam before 2.5s")
    if mp:
        if m["frame"]<75 and mp["internal"]:fail("map_reveal","internal borders before 2.5s")
        if mp["internal"]:
            if mp["piece_count"]!=15:fail("map_count",str(mp["piece_count"]))
            if mp["max_displacement"]>12.00001:fail("map_displacement",str(mp["max_displacement"]))
            geoms=[shape(f["geometry"]) for f in mp.get("polygons",[])]
            for i,a in enumerate(geoms):
                for j,bg in enumerate(geoms[:i]):
                    area=a.intersection(bg).area
                    if area>.02:fail("map_overlap",f"pieces {i},{j}: {area:.5f} px2")
    if m.get("mir_width",100)<60:fail("mir_size",str(m["mir_width"]))
    day=m.get("day")
    if day:
        expect=1+(dt.date.fromisoformat(day["date"])-dt.date(1991,5,18)).days
        if day["day"]!=expect:fail("date",str(day))
        if prev and prev.get("day") and day["day"]<prev["day"]["day"]:fail("counter_backwards",str(day))
    if m.get("flame") and m["flame"]!={"core":"#fff3c4","outer":"#ffb347"}:fail("flame_palette",str(m["flame"]))
    if m.get("launch",{}).get("total_seconds",8)>8:fail("launch_duration","longer than eight seconds")
    return out

def check_pixels(hashes):
    out=[]
    for i in range(30,len(hashes)):
        if hashes[i]==hashes[i-30]:out.append({"frame":i,"rule":"identical_n_minus_30"})
    run=0
    for i in range(1,len(hashes)):
        run=run+1 if hashes[i]==hashes[i-1] else 0
        if run>30:out.append({"frame":i,"rule":"freeze_gt_1s"})
    return out

def audio_data(path):
    # The checker never uses the source mix to certify delivered AAC.
    r=subprocess.run(["ffmpeg","-v","error","-i",str(path),"-vn","-ac","2","-ar",str(SR),
        "-f","f32le","pipe:1"],capture_output=True,check=True)
    return np.frombuffer(r.stdout,dtype="<f4").reshape(-1,2).copy()

def measure_windows(pcm,offset=0,allowed=None):
    allowed=allowed or []
    n=len(pcm)
    seconds=[METER.integrated_loudness(pcm[i*SR:(i+1)*SR]) for i in range(n//SR)]
    # Fixed 1 s list for the report, plus a 0.1 s step floor check.
    windows=[]
    for start in range(0,n-SR+1,SR//10):
        t=offset+start/SR;end=t+1
        # Only the explicitly planned physical silence interval may exempt a
        # quiet analysis window; retain every exemption in the output.
        exempt=any(t>=a-1e-7 and end<=b+1e-7 for a,b in allowed)
        val=float(METER.integrated_loudness(pcm[start:start+SR]))
        windows.append({"start":round(t,3),"end":round(end,3),"LUFS":round(val,3),"allowed":exempt})
    return seconds,windows

def signal_rules(integrated,tp,lra,windows):
    out=[]
    if abs(integrated+14)>.15:out.append({"rule":"integrated_loudness","value":integrated})
    if tp>-1.5+.005:out.append({"rule":"true_peak","value":tp})
    if lra>10:out.append({"rule":"loudness_range","value":lra})
    out.extend({"rule":"audio_window_floor",**w} for w in windows if w["LUFS"]<-24 and not w["allowed"])
    return out

def probe(path):
    r=subprocess.run(["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(path)],capture_output=True,text=True,check=True)
    return json.loads(r.stdout)

def media_rules(p):
    out=[];vs=[s for s in p["streams"] if s["codec_type"]=="video"];aa=[s for s in p["streams"] if s["codec_type"]=="audio"]
    if not vs:return [{"rule":"resolution","detail":"no video"}]
    v=vs[0]
    if (v["width"],v["height"])!=(1920,1080):out.append({"rule":"resolution"})
    if v["r_frame_rate"]!="30/1":out.append({"rule":"frame_rate"})
    if int(v.get("bit_rate",0))<6000000:out.append({"rule":"bitrate_floor","value":v.get("bit_rate")})
    if not aa:out.append({"rule":"audio_present"})
    elif abs(float(v["duration"])-float(aa[0]["duration"]))>1/30:out.append({"rule":"duration_match"})
    return out
def detector_rules(logs):
    out=[]
    for name,key in [("freezedetect","freeze_start:"),("blackdetect","black_start:"),("silencedetect","silence_start:")]:
        if key in logs.get(name,""):out.append({"rule":name,"detail":"unexpected interval; see raw log"})
    return out

CAPTIONS=[
("He left Earth from one country.",0,4,6),
("He came back to another.",4,8,5),
("May 1991. Sergei Krikalev flies to the space station Mir.",8.05,15.9,10),
("The plan: five months in orbit.",16.1,23,6)]
def caption_rules(caps=CAPTIONS):
    return [{"rule":"subtitle_read_time","text":s,"readable":round(end-start-.4,3),"required":1.5+.3*words}
        for s,start,end,words in caps if end-start-.4 <1.5+.3*words-1e-7]
def observed_caption_rules(metas,only=None):
    out=[]
    for i,(sentence,start,end,words) in enumerate(CAPTIONS):
        if only is not None and i not in only:continue
        expected_lines=2 if i==2 else 1
        frames=[]
        for m in metas:
            if m.get("caption_id")!=i:continue
            visible=[b for b in m["bounds"] if b["role"]=="text" and b.get("text_role")=="caption" and b.get("opacity",1)>=.99]
            if len(visible)==expected_lines:frames.append(m["frame"])
        duration=len(frames)/30
        if duration<1.5+.3*words:
            out.append({"rule":"subtitle_read_time","text":sentence,"readable":round(duration,3),"required":1.5+.3*words})
    return out
def launch_duration_rule(duration):
    return [{"rule":"launch_duration","value":duration}] if duration>8+1e-6 else []
def observed_launch_rule(metas):
    frames=[m["frame"] for m in metas if m["shot"] in [3,4,5]]
    return launch_duration_rule((max(frames)-min(frames)+1)/30) if frames else []
def cue_rules(cues):
    return [{"rule":"sfx_sync","cue":c["name"]} for c in cues if abs(c["sound_frame"]-c["visual_frame"])>2]
def matched_cues(pcm,cues):
    result=[]
    mono=pcm.mean(axis=1)
    for cue in cues:
        if "template" not in cue:
            raise RuntimeError("Missing actual sound template: "+cue["name"])
        template_path=Path(cue["template"])
        if not template_path.is_absolute():
            template_path=Path(__file__).resolve().parent/template_path
        raw=audio_data(template_path).mean(axis=1)
        raw=raw[:min(len(raw),round(.1*SR))]
        expected=round(cue["visual_frame"]/30*SR)
        lo=max(0,expected-round(.3*SR));hi=min(len(mono),expected+len(raw)+round(.3*SR))
        corr=signal.correlate(mono[lo:hi],raw,mode="valid",method="fft")
        peak=int(np.argmax(corr))+lo
        found=copy.deepcopy(cue)
        found["sound_frame"]=round(peak/SR*30)
        found["detected_sample"]=peak
        found["offset_frames"]=found["sound_frame"]-found["visual_frame"]
        result.append(found)
    return result

def verify_media(path,q):
    p=probe(path);(q/"ffprobe.json").write_text(json.dumps(p,indent=2))
    pcm=audio_data(path);seconds,windows=measure_windows(pcm)
    (q/"loudness-per-second.json").write_text(json.dumps([round(float(x),3) for x in seconds],indent=2))
    (q/"all-1s-windows.json").write_text(json.dumps(windows,indent=2))
    logs={}
    for name,args in {
        "freezedetect":["-vf","freezedetect=n=0:d=1","-an"],
        "blackdetect":["-vf","blackdetect=d=.1:pix_th=.10:pic_th=.98","-an"],
        "silencedetect":["-af","silencedetect=noise=-45dB:d=1.5","-vn"],
        "loudness-final":["-af","loudnorm=I=-14:TP=-1.5:LRA=7:print_format=json","-vn"],
    }.items():
        cmd=["ffmpeg","-hide_banner","-nostats","-i",str(path)]+args+["-f","null",os.devnull]
        r=subprocess.run(cmd,capture_output=True,text=True,check=True)
        (q/(name+".txt")).write_text(subprocess.list2cmdline(cmd)+"\n"+r.stderr)
        logs[name]=r.stderr
    s=logs["loudness-final"]
    j=json.JSONDecoder().raw_decode(s[s.rfind("{"):])[0]
    metrics={"integrated_LUFS":float(j["input_i"]),"true_peak_dBTP":float(j["input_tp"]),"LRA_LU":float(j["input_lra"])}
    issues=media_rules(p)+signal_rules(*metrics.values(),windows)+caption_rules()
    cues=json.loads((q.parent/"audio-cues.json").read_text())
    detected=matched_cues(pcm,cues)
    (q/"sfx-measured.json").write_text(json.dumps(detected,indent=2))
    issues+=cue_rules(detected)
    # Raw detector logs are also evaluated; planned zero-second preview black
    # or long silence exceptions do not exist.
    issues+=detector_rules(logs)
    return {"duration":p["format"]["duration"],"video_bit_rate":p["streams"][0]["bit_rate"],
        **metrics,"loudness_per_second":[round(float(x),3) for x in seconds],
        "minimum_sliding_1s_LUFS":min(w["LUFS"] for w in windows),
        "window_count":len(windows),"issues":issues,
        "allowed_silence":"none in preview; reserved full-film [86.0,87.0] s"}

def mutations(draw,metas,hashes,final,q):
    lines=[];failed=[];results=[]
    original_sha=hashlib.sha256(final.read_bytes()).hexdigest()
    md=q/"mutations"
    def result(name,expected,issues,evidence):
        actual=sorted(set(i["rule"] for i in issues));ok=expected in actual
        lines.append(("PASS" if ok else "FAIL")+f" {name}: injected -> {expected}; caught={','.join(actual)}; reverted -> clean")
        results.append({"name":name,"expected":expected,"caught":actual,"pass":ok,"evidence":evidence,"issues":issues})
        if not ok:failed.append(name)
    tests=[
        ("subtitle_on_head",150,"text_head","text_head"),
        ("overlapping_text",60,"text_text","text_text"),
        ("cropped_head",150,"head_crop","head_crop"),
        ("text_outside_frame",60,"text_margin","text_margin"),
        ("subtitle_wrong_zone",60,"text_zone","subtitle_zone"),
        ("line_through_subtitle",60,"stroke","subtitle_art"),
        ("line_only_in_8px_padding",60,"margin_stroke","subtitle_art"),
        ("wrong_prop_scale",150,"scale","scale"),
        ("downward_free_prop",150,"zero_g_accel","zero_g_accel"),
        ("floating_earth_foot_fixture",150,"earth_foot","earth_contact"),
        ("overlapping_map_pieces",90,"map_overlap","map_overlap"),
        ("wrong_calendar_day",270,"date","date"),
        ("counter_backwards",270,"backwards","counter_backwards"),
        ("invisible_Mir",60,"small_mir","mir_size"),
        ("premature_internal_borders",60,"internal_borders","map_reveal"),
        ("fourteen_republics",90,"piece_count","map_count"),
        ("piece_moves_over_12px",90,"map_displacement","map_displacement"),
        ("standing_pose_in_zero_g",150,"gravity_pose","neutral_pose"),
        ("detached_rail_hand",150,"detached_hand","rail_contact"),
        ("rail_without_brackets",150,"rail_brackets","rail_brackets"),
        ("too_fast_free_prop",150,"zero_g_speed","zero_g_speed"),
        ("too_fast_rotation",150,"rotation","zero_g_rotation"),
        ("red_exhaust",360,"red_flame","flame_palette"),
    ]
    for name,n,flag,expected in tests:
        sf,m=draw(n,{flag:True});file=md/(name+".png");sf.write_to_png(str(file))
        prev=metas[n-1]
        issues=check_frame(m,prev)
        if flag=="margin_stroke" and not any(b.get("art_pixels_padded",0)>0 for b in m["bounds"]):
            failed.append("padding_not_actually_exercised")
        (md/(name+"-metadata.json")).write_text(json.dumps(m,indent=2))
        # Re-render without flag and require clean state; don't merely remove a
        # warning from the report.
        _,clean=draw(n);clean_issues=check_frame(clean,prev)
        if clean_issues:failed.append(name+"_revert");lines.append("FAIL "+name+" revert")
        result(name,expected,issues,str(file))
    # Freeze is injected into actual temporary frames, encoded as a real clip.
    hh=[]
    cmd=["ffmpeg","-y","-v","error","-f","rawvideo","-pix_fmt","bgr0","-s","1920x1080","-r","30","-i","pipe:0","-an","-c:v","libx264","-preset","fast","-crf","30",str(md/"freeze-2s.mp4")]
    pr=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    for n in range(240,306):
        sf,m=draw(n,{"freeze":True});data=bytes(sf.get_data());hh.append(hashlib.sha256(data).hexdigest());pr.stdin.write(data)
    pr.stdin.close()
    if pr.wait():raise RuntimeError("mutation freeze encode")
    fi=check_pixels(hh)
    result("one_second_repeat","identical_n_minus_30",fi,str(md/"freeze-2s.mp4"))
    result("freeze_over_one_second","freeze_gt_1s",fi,str(md/"freeze-2s.mp4"))
    freeze_log=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(md/"freeze-2s.mp4"),"-vf","freezedetect=n=0:d=1","-an","-f","null",os.devnull],capture_output=True,text=True,check=True).stderr
    (md/"freeze-detector.txt").write_text(freeze_log)
    result("ffmpeg_freeze_detector","freezedetect",detector_rules({"freezedetect":freeze_log}),str(md/"freeze-2s.mp4"))
    # Audio test: quiet an actual temporary WAV copy, not a metadata number.
    pcm=audio_data(final);mut=pcm.copy();mut[:SR]*=.001
    wav=md/"quiet-first-second.wav"
    with wave.open(str(wav),"wb") as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(SR);f.writeframes((np.clip(mut,-1,1)*32767).astype("<i2").tobytes())
    _,win=measure_windows(audio_data(wav))
    result("quiet_first_second","audio_window_floor",signal_rules(-14,-1.7,3,win),str(wav))
    silent=pcm.copy();silent[:2*SR]=0
    silentfile=md/"unplanned-two-second-silence.wav"
    with wave.open(str(silentfile),"wb") as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(SR);f.writeframes((np.clip(silent,-1,1)*32767).astype("<i2").tobytes())
    silence_log=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(silentfile),"-af","silencedetect=noise=-45dB:d=1.5","-f","null",os.devnull],capture_output=True,text=True,check=True).stderr
    (md/"unplanned-silence-detector.txt").write_text(silence_log)
    result("ffmpeg_silence_detector","silencedetect",detector_rules({"silencedetect":silence_log}),str(silentfile))
    blackfile=md/"black-first-1.2s.mp4"
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(final),"-t","2","-vf","drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='lt(t,1.2)'","-an","-c:v","libx264","-preset","fast","-crf","30",str(blackfile)],check=True)
    black_log=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(blackfile),"-vf","blackdetect=d=.1:pix_th=.10:pic_th=.98","-an","-f","null",os.devnull],capture_output=True,text=True,check=True).stderr
    (md/"black-detector.txt").write_text(black_log)
    result("ffmpeg_black_detector","blackdetect",detector_rules({"blackdetect":black_log}),str(blackfile))
    # Actual low-bitrate H.264 file. Reverting means original MP4 is unchanged.
    low=md/"low-bitrate.mp4"
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(final),"-t","1","-c:v","libx264","-crf","42","-preset","fast","-c:a","copy",str(low)],check=True)
    result("low_video_bitrate","bitrate_floor",media_rules(probe(low)),str(low))
    # Encode actual corrupted media; no edited ffprobe JSON stands in for files.
    for name,rule,args in [
        ("wrong_resolution","resolution",["-vf","scale=1280:720","-c:v","libx264","-crf","16","-preset","fast","-c:a","copy"]),
        ("wrong_fps","frame_rate",["-r","24","-c:v","libx264","-crf","16","-preset","fast","-c:a","copy"]),
        ("missing_audio","audio_present",["-an","-c:v","copy"]),
        ("audio_video_length_mismatch","duration_match",["-c:v","copy","-af","atrim=0:0.7","-c:a","aac"]),
    ]:
        file=md/(name+".mp4")
        subprocess.run(["ffmpeg","-y","-v","error","-i",str(final),"-t","1"]+args+[str(file)],check=True)
        result(name,rule,media_rules(probe(file)),str(file))
    for name,rule,filter_expr in [
        ("wrong_integrated_level","integrated_loudness","volume=-5dB"),
        ("true_peak_over_limit","true_peak","volume=6dB"),
    ]:
        file=md/(name+".wav")
        subprocess.run(["ffmpeg","-y","-v","error","-i",str(final),"-vn","-af",filter_expr,"-c:a","pcm_f32le",str(file)],check=True)
        rr=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(file),"-af","loudnorm=print_format=json","-f","null",os.devnull],capture_output=True,text=True,check=True)
        (md/(name+"-measurement.txt")).write_text(rr.stderr)
        values=json.JSONDecoder().raw_decode(rr.stderr[rr.stderr.rfind("{"):])[0]
        result(name,rule,signal_rules(float(values["input_i"]),float(values["input_tp"]),float(values["input_lra"]),[]),str(file))
    old=final.parent/"preview-v1-original/preview.mp4"
    file=md/"excessive_loudness_range.mp4"
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(final),"-i",str(old),"-map","0:v:0","-map","1:a:0","-c","copy",str(file)],check=True)
    rr=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(file),"-af","loudnorm=print_format=json","-f","null",os.devnull],capture_output=True,text=True,check=True)
    values=json.JSONDecoder().raw_decode(rr.stderr[rr.stderr.rfind("{"):])[0]
    (md/"excessive_lra-measurement.txt").write_text(rr.stderr)
    result("excessive_loudness_range","loudness_range",signal_rules(float(values["input_i"]),float(values["input_tp"]),float(values["input_lra"]),[]),str(file))
    short=[]
    for n in range(120):
        sf,m=draw(n,{"short_caption":True});short.append(m)
        if n==45:sf.write_to_png(str(md/"short-caption-at-1.5s.png"))
    result("subtitle_too_short","subtitle_read_time",observed_caption_rules(short,only={0}),str(md/"short-caption-at-1.5s.png")+" plus 120 rendered frame records")
    realcues=json.loads((q.parent/"audio-cues.json").read_text())
    crack=realcues[0]
    template=audio_data(crack["template"])
    shifted=np.zeros((23*SR,2),np.float32);start=round(80/30*SR)
    shifted[start:start+len(template)]=template
    file=md/"crack-five-frames-late.wav"
    with wave.open(str(file),"wb") as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(SR);f.writeframes((shifted*32767).astype("<i2").tobytes())
    found=matched_cues(audio_data(file),[crack])
    result("sound_five_frames_late","sfx_sync",cue_rules(found),str(file))
    long=md/"launch-fifteen-seconds.mp4"
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(final),"-vf","trim=start=8:end=16,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=7",
        "-an","-c:v","libx264","-preset","fast","-crf","30",str(long)],check=True)
    result("launch_too_long","launch_duration",launch_duration_rule(float(probe(long)["format"]["duration"])),str(long))
    # The silence exception is exact and does not exempt a second quiet window.
    fixture=audio_data(wav)[:3*SR]
    _,permitted=measure_windows(fixture,offset=86,allowed=[(86,87)])
    _,forbidden=measure_windows(fixture,offset=10,allowed=[(86,87)])
    bad_allowed=[w for w in permitted if w["LUFS"]<-24 and not w["allowed"]]
    bad_unrelated=[w for w in forbidden if w["LUFS"]<-24 and not w["allowed"]]
    ok=not bad_allowed and bool(bad_unrelated) and any(w["allowed"] for w in permitted)
    (md/"silence-exception-measurements.json").write_text(json.dumps({"allowed":permitted,"unrelated":forbidden},indent=2))
    lines.append(("PASS" if ok else "FAIL")+" planned silence [86,87] allowed; unrelated silence rejected")
    if not ok:failed.append("silence_exception")
    unchanged=hashlib.sha256(final.read_bytes()).hexdigest()==original_sha
    lines.append(("PASS" if unchanged else "FAIL")+" original MP4 checksum unchanged after all mutations")
    if not unchanged:failed.append("original_file_changed")
    (q/"mutation-results.json").write_text(json.dumps(results,indent=2))
    (q/"mutation-output.txt").write_text("\n".join(lines)+"\n")
    return {"lines":lines,"failed":failed,"test_count":len(results)+2,
        "scope":"Actual rendered mutations, corrupted media files and measured audio. Earth contact is a drawn test fixture because this preview has no Earth walking scene. Silence exception uses a measured audio excerpt with an explicit global-time offset."}

def exports(final,q):
    frames=set(range(0,690,15))|{0,75,90,150,270,360,660,689,119,120,239,240,329,330,404,405,479,480}
    order=sorted(frames);d=q/"frames"
    select="select='"+"+".join(f"eq(n,{n})" for n in order)+"'"
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(final),"-vf",select,"-fps_mode","vfr",str(d/"decoded-%03d.png")],check=True)
    for i,n in enumerate(order): (d/f"decoded-{i+1:03d}.png").replace(d/f"frame-{n:04d}-{n/30:06.2f}s.png")
    font=ImageFont.truetype(str(q.parent.parent/"assets/JetBrainsMono.ttf"),18)
    sampled=list(range(0,690,15))
    def sheet(ns,path):
        im=Image.new("RGB",(1920,math.ceil(len(ns)/4)*300),(13,13,16));dr=ImageDraw.Draw(im)
        for i,n in enumerate(ns):
            fr=Image.open(d/f"frame-{n:04d}-{n/30:06.2f}s.png").convert("RGB").resize((480,270),Image.Resampling.LANCZOS)
            x=(i%4)*480;y=(i//4)*300;im.paste(fr,(x,y));dr.text((x+8,y+274),f"{n/30:05.2f}s / frame {n}",font=font,fill="white")
        im.save(path,quality=96)
    sheet(sampled,q/"contact-sheet-2fps.jpg")
    for i in range(0,len(sampled),16):sheet(sampled[i:i+16],q/f"contact-page-{1+i//16}.jpg")
    # Requested native frames remain PNGs in frames/.
    manifest=[{"frame":n,"time":n/30,"path":str(d/f"frame-{n:04d}-{n/30:06.2f}s.png")} for n in order]
    (q/"frame-index.json").write_text(json.dumps(manifest,indent=2))

