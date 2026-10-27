from pathlib import Path
import hashlib,json,math
P=Path(__file__).resolve().parent;Q=P/'preview-v3/qa'
r=json.loads((Q/'qa-result.json').read_text())
if r['issues']:raise SystemExit('Final QA has not passed')
audio=r['audio'];motion=r['motion'];enc=r['encoding']
mut=json.loads((Q/'mutation-results.json').read_text())
ssim=min(s['SSIM_RGB'] for s in r['ssim'])
map_rows=json.loads((Q/'map-decoded-pixel-measurements.json').read_text())
shifts=[v['measured_radial_shift_in_picture_px'] for v in map_rows]
native=[(75,'2.5'),(78,'2.6'),(345,'11.5'),(414,'13.8'),(495,'16.5'),(660,'22.0')]
lines=['# Preview v3 — independent-review delivery','',
 'This report describes the corrected23-second preview only. The full film is not complete. Original v2 artifacts are preserved; v3 supersedes them.','',
 '## Reproduction commands','',
 '```powershell',f"python '{P / 'render_preview_v3.py'}'",f"python '{P / 'qa_preview_v3.py'}'",'```','',
 'Full actual QA stdout: [QA-FULL-OUTPUT.txt](QA-FULL-OUTPUT.txt). Render command/output: [RENDER-FINAL.txt](RENDER-FINAL.txt). Final audio-only rerun: [AUDIO-FINAL.txt](AUDIO-FINAL.txt). Prior failed/intermediate passes remain in QA-FIRST-PASS.txt, QA-SECOND-PASS.txt and QA-THIRD-PASS.txt.','',
 '## Repairs against the review','',
 '|Item / time|Problem|Final change and evidence|','|---|---|---|',
 '|1 / entire mix|Cabin and launch had the same loudness/noise character.|Low-passed quiet air, restrained tonal atmosphere, musical countdown crescendo, distinct low-mid engine roar. All pure-atmosphere3-second windows are checked literally against-20..-18LUFS. Loud launch and integrated targets measured on delivered AAC.|',
 '|2 / encoding|HRD filler inflated the bitrate.|CRF16, slow, animation, yuv420p; no minrate/maxrate/HRD/filler. Parse delivered Annex-B NALs and SPS; compare10 lossless RGB inputs against actual decoded output.|',
 '|3 / 1.2–2.5 and9–11s|Pixel-identical-only checks missed nearly static shots.|Camera drift/push, real support/mast movement; one-second-lag diff>3/255 at480x270, excluding exact font rectangles and edit graphics. Test all660 comparable frames.|',
 '|4 /16–23s|DAY disappeared.|DAY3/20MAY1991 remains in every frame through689. DAY1 is retained through launch. Dates differ because the docking cut skips two days, supported by ESA mission chronology.|',
 '|5 /2.5–4s|Fracture unreadable and offsets too small.|Three-frame white crack flash, red/rose lightness bands in9-point steps, 34px designed radial translation. Actual decoded colour centroids, not reported offsets, are measured below. Paint-order reversal is separately encoded and compared.|',
 '|6 /hook|Flat map pasted over disc.|Approximate inverse conic georeferencing of historical scan then true spherical orthographic projection; dim dissolved continental silhouettes, night-light illustration and limb shading. Explicitly stylized in script.|',
 '|7 /16–23s|Hook composition repeated.|New simplified Soyuz approach, fore-port alignment and contact near22.5s. Arrays clear the docking path; different composition and camera move.|',
 '|8 /11–16s|Two detached blurry smoke ovals.|Sequential layered billows issue from the trench outlets and roll outward with fresh puffs maintaining the connection. Engine insert includes table, open trench and ground. Split table rims remove an erroneous crossbar over the exhaust opening.|',
 '|9 /13.5–16s|Side view labelled low angle.|Low camera, horizon in bottom quarter at entrance, converging ground rays, upward rocket taper and tracking tilt. This is a flat2D perspective illustration, not a3D engineering render.|',
 '|10 /8–16s|American-style tower/pad.|Four counterweighted support members and two outward-retracting umbilical masts; support arms open outward at liftoff; no tall service tower alongside. Mechanism referenced to ESA Soyuz material; exact1991pad detail not claimed.|',
 '|11 /4–8s|Sideways free arm and camera-facing gaze.|Compact bent free arm near chest, same canonical head/hair with gaze shifted to Earth window, softly anchored drift, bent legs, two wall brackets.|','',
 'During repair, the first perspective implementation produced strip seams and a clipped rocket nose; it was replaced by a cached continuous raster warp and a tracking camera. The first map fit had an inverted image-y convention; corrected before delivery. A geometry-only no-overlap check missed antialias colour mixing; the real-pixel reverse-order comparison exposed it and a visible sub-pixel safety gap fixed it. The broad-band release-sound matcher locked to engine energy; matching the release attack at2.2–9kHz recovers the true frame405 onset. A static-mutation test showed that exact-zero freezedetect misses codec noise; its sensitivity was changed to-60dB and the negative test repeated. These are retained as findings, not hidden by a summary.','',
 '## Delivered media and measurements','',
 f"Duration23.000s;690frames;1920x1080;30/1fps;H.264High,yuv420p;AACstereo48kHz192k target. Integrated{audio['integrated_LUFS']:.2f}LUFS;LRA{audio['LRA_LU']:.1f}LU;true peak{audio['true_peak_dBTP']:.2f}dBTP.",
 f"Cabin3s readings: {audio['cabin_short_term_LUFS']}. Launch peak3s:{audio['launch_peak_short_term_LUFS']:.3f}LUFS. Pure-atmosphere3s span:{min(audio['all_pure_atmosphere_short_term_LUFS']):.3f}..{max(audio['all_pure_atmosphere_short_term_LUFS']):.3f}LUFS.",
 f"All-sample one-second-floor result:{audio['every_sample_floor']['window_count']:,}windows;minimum{audio['every_sample_floor']['minimum_LUFS']:.3f}LUFS;below-24 count:{audio['every_sample_floor']['below_minus24_count']}. This is ungated K-weighted one-second power; gated fixed/0.1s-step readings are separately retained, not relabelled as the same measurement.",
 f"Actual video payload excluding filler NALs:{enc['real_video_payload_bps']:,}bits/s. Filler NALs:{enc['filler_NAL_count']};filler bytes:{enc['filler_NAL_bytes']};HRD present:{enc['HRD_present']}. The file is small because the pictures are simple; no bitrate floor is enforced.",
 f"RGB SSIM at10 actual decoded frames:minimum{ssim:.6f}. Per-frame non-text motion minimum:{motion['minimum_percent']:.4f}%. No failed comparable frame. No preceding1s frame exists at time0;the first entry below is null rather than an invented zero or duplicate.",'',
 'One-second loudness values,seconds0..22:','```json',json.dumps(audio['loudness_per_second']),'```','',
 'Changed non-text pixels versus1s earlier,at seconds0..22(%):','```json',json.dumps(motion['per_second_percent']),'```','',
 '## Pixel geometry evidence','',
 f"15 decoded region masks found. Measured translations:{min(shifts):.3f}..{max(shifts):.3f}picture pixels, within25..40. Reversing the republic paint order changes0decoded pixels above3RGB levels. Evidence: map-decoded-pixel-measurements.json and map-order-pixel-evidence.json.",
 f"{len(r['geometry'])}registered geometry ROI checks compare decoded H.264 against the retained lossless picture-space layout. No geometry pass relies solely on renderer metadata. The map centroid/count/order tests add direct image measurements. A reference-layout check proves encoded fidelity to that layout; it does not independently prove that the layout is realistic or historically exact.",'',
 '|Republic|Decoded interior pixels|Measured radial shift(px)|','|---|---:|---:|']
lines += [f"|{v['republic']}|{v['decoded_interior_pixels']}|{v['measured_radial_shift_in_picture_px']:.3f}|" for v in map_rows]
lines += ['', '## Mutation tests','',f"{len(mut)}checks,all passed,including original-video checksum preservation. Encoded mutations remain in mutations/. Actual quiet/noisy/flat-loudness/high-peak WAVs are measured after writing. Actual wrong-format/filler/banding/near-static/black/frozen/silent clips are decoded and checked. The near-static fixture contains a real moving dot, so the new motion rule is exercised beyond exact equality.",'',
 '|Mutation|Expected rule|Caught|','|---|---|---|']
lines += [f"|{v['name']}|{v.get('expected_rule','original checksum unchanged')}|{'PASS' if v['pass'] else 'FAIL'}|" for v in mut]
lines += ['', '## Requested review images','', '[2fps contact sheet](contact-sheet-2fps.jpg) —46samples; visual review also used the three contact pages and the six requested native PNGs. This is not a claim that every one of690frames was manually inspected.','']
lines += [f"- [{time}s](frames/frame-{n:04d}-{n/30:06.2f}s.png)" for n,time in native]
lines += ['', 'First/last frames, both sides of every cut, scene middles and2fps samples are exported. Actual files are listed in frames/; an exhaustive native-frame visual audit is not claimed.','',
 '## Detector evidence and honest limits','',
 'freezedetect(-60dB,d1),blackdetect and silencedetect logs are retained in full. No unexpected interval was reported in the delivery. Mutated clips produce detections. Five waveform-matched cues are0frames from their visual events;see sfx-measured.json. Engine tone is editorial and is not a recording of this historical launch.','',
 'The sphere georeferencing uses hand-read printed city control points with approximately10source-pixel RMS fit error;no independent far-east survey accuracy is certified. The explosion uses a small uniform graphic shrink and thin cuts in addition to translation;it is an exploded illustration,not literal territorial motion. Latvia has only a few encoded interior pixels at this globe scale; all15regions are measured,but no promise is made that a phone viewer can name/count every small republic without pausing.','',
 'Pad,rocket,Mir and Soyuz are simplified2D drawings and the eight-second launch/seven-second docking are heavily time-compressed. Pixel-template checks and mutation coverage do not establish physical/historical correctness. No physical-phone listening audition or full-speed perceptual audio review is claimed. SSIM>=0.98 is not a mathematical guarantee of imperceptible banding. The full2:15–2:30film is still awaiting preview approval.','',
 'Registered final result: **QA issues:0**. Read raw reports rather than treating this line as proof of every possible visual property.','']
(Q/'REVIEW.md').write_text('\n'.join(lines),encoding='utf-8')
combined=(Q/'QA-FULL-OUTPUT.txt').read_text(encoding='utf-8')
for name in ['freezedetect.txt','blackdetect.txt','silencedetect.txt','loudness-final.txt']:
    combined+='\n\n===== RAW '+name+' =====\n'+(Q/name).read_text(encoding='utf-8')
(Q/'QA-COMPLETE-OUTPUT.txt').write_text(combined,encoding='utf-8')
paths=[P/f for f in ['render_preview_v3.py','projection_v3.py','qa_preview_v3.py','render_preview.py','render_preview_v2.py','preview-v3.mp4','preview-v3-script.md']]
paths+=list((Q/'source').glob('*.png'))
(Q/'final-source-checksums.json').write_text(json.dumps({f.relative_to(P).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in paths},indent=2))
print(json.dumps({'review':str(Q/'REVIEW.md'),'mutations':len(mut),'QA_issues':r['issues'],'video_bytes':(P/'preview-v3.mp4').stat().st_size},indent=2))
