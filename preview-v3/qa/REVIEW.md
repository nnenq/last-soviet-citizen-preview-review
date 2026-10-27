# Preview v3 — independent-review delivery

This report describes the corrected23-second preview only. The full film is not complete. Original v2 artifacts are preserved; v3 supersedes them.

## Reproduction commands

```powershell
python '.\render_preview_v3.py'
python '.\qa_preview_v3.py'
```

Full actual QA stdout: [QA-FULL-OUTPUT.txt](QA-FULL-OUTPUT.txt). Render command/output: [RENDER-FINAL.txt](RENDER-FINAL.txt). Final audio-only rerun: [AUDIO-FINAL.txt](AUDIO-FINAL.txt). Prior failed/intermediate passes remain in QA-FIRST-PASS.txt, QA-SECOND-PASS.txt and QA-THIRD-PASS.txt.

## Repairs against the review

|Item / time|Problem|Final change and evidence|
|---|---|---|
|1 / entire mix|Cabin and launch had the same loudness/noise character.|Low-passed quiet air, restrained tonal atmosphere, musical countdown crescendo, distinct low-mid engine roar. All pure-atmosphere3-second windows are checked literally against-20..-18LUFS. Loud launch and integrated targets measured on delivered AAC.|
|2 / encoding|HRD filler inflated the bitrate.|CRF16, slow, animation, yuv420p; no minrate/maxrate/HRD/filler. Parse delivered Annex-B NALs and SPS; compare10 lossless RGB inputs against actual decoded output.|
|3 / 1.2–2.5 and9–11s|Pixel-identical-only checks missed nearly static shots.|Camera drift/push, real support/mast movement; one-second-lag diff>3/255 at480x270, excluding exact font rectangles and edit graphics. Test all660 comparable frames.|
|4 /16–23s|DAY disappeared.|DAY3/20MAY1991 remains in every frame through689. DAY1 is retained through launch. Dates differ because the docking cut skips two days, supported by ESA mission chronology.|
|5 /2.5–4s|Fracture unreadable and offsets too small.|Three-frame white crack flash, red/rose lightness bands in9-point steps, 34px designed radial translation. Actual decoded colour centroids, not reported offsets, are measured below. Paint-order reversal is separately encoded and compared.|
|6 /hook|Flat map pasted over disc.|Approximate inverse conic georeferencing of historical scan then true spherical orthographic projection; dim dissolved continental silhouettes, night-light illustration and limb shading. Explicitly stylized in script.|
|7 /16–23s|Hook composition repeated.|New simplified Soyuz approach, fore-port alignment and contact near22.5s. Arrays clear the docking path; different composition and camera move.|
|8 /11–16s|Two detached blurry smoke ovals.|Sequential layered billows issue from the trench outlets and roll outward with fresh puffs maintaining the connection. Engine insert includes table, open trench and ground. Split table rims remove an erroneous crossbar over the exhaust opening.|
|9 /13.5–16s|Side view labelled low angle.|Low camera, horizon in bottom quarter at entrance, converging ground rays, upward rocket taper and tracking tilt. This is a flat2D perspective illustration, not a3D engineering render.|
|10 /8–16s|American-style tower/pad.|Four counterweighted support members and two outward-retracting umbilical masts; support arms open outward at liftoff; no tall service tower alongside. Mechanism referenced to ESA Soyuz material; exact1991pad detail not claimed.|
|11 /4–8s|Sideways free arm and camera-facing gaze.|Compact bent free arm near chest, same canonical head/hair with gaze shifted to Earth window, softly anchored drift, bent legs, two wall brackets.|

During repair, the first perspective implementation produced strip seams and a clipped rocket nose; it was replaced by a cached continuous raster warp and a tracking camera. The first map fit had an inverted image-y convention; corrected before delivery. A geometry-only no-overlap check missed antialias colour mixing; the real-pixel reverse-order comparison exposed it and a visible sub-pixel safety gap fixed it. The broad-band release-sound matcher locked to engine energy; matching the release attack at2.2–9kHz recovers the true frame405 onset. A static-mutation test showed that exact-zero freezedetect misses codec noise; its sensitivity was changed to-60dB and the negative test repeated. These are retained as findings, not hidden by a summary.

## Delivered media and measurements

Duration23.000s;690frames;1920x1080;30/1fps;H.264High,yuv420p;AACstereo48kHz192k target. Integrated-13.93LUFS;LRA8.9LU;true peak-2.68dBTP.
Cabin3s readings: [-18.36726841151181, -18.453466180967084]. Launch peak3s:-9.422LUFS. Pure-atmosphere3s span:-18.511..-18.145LUFS.
All-sample one-second-floor result:1,056,001windows;minimum-19.129LUFS;below-24 count:0. This is ungated K-weighted one-second power; gated fixed/0.1s-step readings are separately retained, not relabelled as the same measurement.
Actual video payload excluding filler NALs:1,018,062bits/s. Filler NALs:0;filler bytes:0;HRD present:False. The file is small because the pictures are simple; no bitrate floor is enforced.
RGB SSIM at10 actual decoded frames:minimum0.986104. Per-frame non-text motion minimum:4.3181%. No failed comparable frame. No preceding1s frame exists at time0;the first entry below is null rather than an invented zero or duplicate.

One-second loudness values,seconds0..22:
```json
[-18.206, -18.319, -18.42, -18.246, -18.169, -18.368, -18.432, -18.219, -12.862, -11.356, -9.664, -10.071, -9.683, -9.556, -9.325, -9.508, -18.176, -18.366, -18.426, -18.233, -18.155, -18.344, -18.382]
```

Changed non-text pixels versus1s earlier,at seconds0..22(%):
```json
[null, 9.3463, 9.4636, 14.5714, 47.7171, 8.069, 8.9062, 8.6456, 52.6188, 7.8595, 8.2415, 32.801, 21.1195, 28.1028, 46.6189, 18.4777, 26.3214, 4.6148, 5.0738, 5.5466, 5.7479, 5.8205, 5.6306]
```

## Pixel geometry evidence

15 decoded region masks found. Measured translations:33.804..37.952picture pixels, within25..40. Reversing the republic paint order changes0decoded pixels above3RGB levels. Evidence: map-decoded-pixel-measurements.json and map-order-pixel-evidence.json.
26registered geometry ROI checks compare decoded H.264 against the retained lossless picture-space layout. No geometry pass relies solely on renderer metadata. The map centroid/count/order tests add direct image measurements. A reference-layout check proves encoded fidelity to that layout; it does not independently prove that the layout is realistic or historically exact.

|Republic|Decoded interior pixels|Measured radial shift(px)|
|---|---:|---:|
|Russian SFSR|72654|33.809|
|Ukrainian SSR|2442|33.804|
|Byelorussian SSR|764|34.201|
|Moldavian SSR|34|34.166|
|Estonian SSR|67|34.018|
|Latvian SSR|8|37.952|
|Lithuanian SSR|178|33.812|
|Georgian SSR|231|34.146|
|Armenian SSR|73|33.860|
|Azerbaijan SSR|317|34.079|
|Kazakh SSR|17228|33.829|
|Uzbek SSR|2270|34.219|
|Turkmen SSR|2639|33.921|
|Kirghiz SSR|869|33.978|
|Tajik SSR|611|34.144|

## Mutation tests

47checks,all passed,including original-video checksum preservation. Encoded mutations remain in mutations/. Actual quiet/noisy/flat-loudness/high-peak WAVs are measured after writing. Actual wrong-format/filler/banding/near-static/black/frozen/silent clips are decoded and checked. The near-static fixture contains a real moving dot, so the new motion rule is exercised beyond exact equality.

|Mutation|Expected rule|Caught|
|---|---|---|
|map_reveal|map_reveal|PASS|
|map_count|map_count|PASS|
|map_displacement|map_displacement|PASS|
|map_tints|map_tints|PASS|
|map_overlap|map_overlap|PASS|
|map_sphere_projection|map_sphere_projection|PASS|
|crack_flash|crack_flash|PASS|
|mir_size|mir_size|PASS|
|hero_scale|hero_scale|PASS|
|neutral_pose|neutral_pose|PASS|
|free_arm|free_arm|PASS|
|gaze_window|gaze_window|PASS|
|rail_contact|rail_contact|PASS|
|rail_brackets|rail_brackets|PASS|
|window_earth|window_earth|PASS|
|head_visibility|head_visibility|PASS|
|smoke_ground_connection|smoke_ground_connection|PASS|
|pad_in_closeup|pad_in_closeup|PASS|
|flame_palette|flame_palette|PASS|
|four_support_arms|four_support_arms|PASS|
|umbilical_retraction|umbilical_retraction|PASS|
|low_angle_perspective|low_angle_perspective|PASS|
|no_liftoff_tower|no_liftoff_tower|PASS|
|docking_replaces_hook|docking_replaces_hook|PASS|
|docking_contact|docking_contact|PASS|
|day_visible_after_16s|day_visible_after_16s|PASS|
|stroke_in_caption|subtitle_art|PASS|
|near_static_motion|near_static_motion|PASS|
|banded_gradients|ssim_fidelity|PASS|
|filler_payload|no_filler_hrd|PASS|
|integrated_loudness|integrated_loudness|PASS|
|true_peak|true_peak|PASS|
|loudness_range|loudness_range|PASS|
|audio_window_floor|audio_window_floor|PASS|
|ambience_level|ambience_level|PASS|
|launch_level|launch_level|PASS|
|ambience_spectrum|ambience_spectrum|PASS|
|wrong-resolution|resolution|PASS|
|wrong-fps|frame_rate|PASS|
|missing-audio|audio_present|PASS|
|duration-mismatch|duration_match|PASS|
|freezedetect|freezedetect|PASS|
|blackdetect|blackdetect|PASS|
|silencedetect|silencedetect|PASS|
|caption_read_time|subtitle_read_time|PASS|
|late_crack|sfx_sync|PASS|
|original_unchanged|original checksum unchanged|PASS|

## Requested review images

[2fps contact sheet](contact-sheet-2fps.jpg) —46samples; visual review also used the three contact pages and the six requested native PNGs. This is not a claim that every one of690frames was manually inspected.

- [2.5s](frames/frame-0075-002.50s.png)
- [2.6s](frames/frame-0078-002.60s.png)
- [11.5s](frames/frame-0345-011.50s.png)
- [13.8s](frames/frame-0414-013.80s.png)
- [16.5s](frames/frame-0495-016.50s.png)
- [22.0s](frames/frame-0660-022.00s.png)

First/last frames, both sides of every cut, scene middles and2fps samples are exported. Actual files are listed in frames/; an exhaustive native-frame visual audit is not claimed.

## Detector evidence and honest limits

freezedetect(-60dB,d1),blackdetect and silencedetect logs are retained in full. No unexpected interval was reported in the delivery. Mutated clips produce detections. Five waveform-matched cues are0frames from their visual events;see sfx-measured.json. Engine tone is editorial and is not a recording of this historical launch.

The sphere georeferencing uses hand-read printed city control points with approximately10source-pixel RMS fit error;no independent far-east survey accuracy is certified. The explosion uses a small uniform graphic shrink and thin cuts in addition to translation;it is an exploded illustration,not literal territorial motion. Latvia has only a few encoded interior pixels at this globe scale; all15regions are measured,but no promise is made that a phone viewer can name/count every small republic without pausing.

Pad,rocket,Mir and Soyuz are simplified2D drawings and the eight-second launch/seven-second docking are heavily time-compressed. Pixel-template checks and mutation coverage do not establish physical/historical correctness. No physical-phone listening audition or full-speed perceptual audio review is claimed. SSIM>=0.98 is not a mathematical guarantee of imperceptible banding. The full2:15–2:30film is still awaiting preview approval.

Registered final result: **QA issues:0**. Read raw reports rather than treating this line as proof of every possible visual property.
