# THE LAST SOVIET CITIZEN — current production

## Revision 3 — latest user requirements take precedence

- Active files: render_preview_v3.py, projection_v3.py, qa_preview_v3.py; delivery preview-v3.mp4 and preview-v3/qa/. Preserve v2 as superseded evidence.
- No HRD or filler. H.264 CRF16 / slow / animation / yuv420p. Delete the bitrate floor; decoded-to-lossless RGB SSIM >=0.98 at ten sampled frames including gradients.
- Audio: ambience approximately -20..-18 LUFS short-term; launch -11..-9 LUFS peaking near liftoff; integrated -14 +/-0.5; LRA5..9; TP<=-1.5; no1s window below-24 in preview. Quiet bed low-passed; no broadband hiss wall.
- After2.5s: 15 clearly tinted 1991 republics, 25..40px radial picture displacement, 3-frame white crack flash, non-overlap tested on decoded pixels. View is a stylized orthographic illustration from approximately georeferenced historical scan; no claim of exact cartography.
- Motion: >=3% changed pixels versus1s earlier, difference>3/255 at480x270 grayscale excluding edit graphics. No previous sample exists during first second; report null rather than an invented measurement.
- Keep DAY through frame689. LaunchDAY1/18MAY; dockingDAY3/20MAY. Cabin/hook are undated editorial prologue.
- Soyuz four support arms swing OUT, two umbilical masts retract OUT before liftoff. No tall adjacent tower. Trench-origin grounded billows; ground visible in engine insert. Low camera below rocket with upward taper and tilt.
- Shots16..23s show a simplified, time-compressed Soyuz approach/docking illustration, not a second hook. Cabin pose has a compact raised free arm, gaze toward Earth in window.
- Every automatic geometry rule must have decoded-output pixel evidence and an actual encoded negative fixture. Template conformance does not prove physical/historical correctness; retain honest limitations and visual inspection notes.

The older requirements below are historical context and are superseded wherever they conflict with Revision3 above.

- Current task: repair the 23-second preview and prove QA with deliberate mutations. Build the full 2:15–2:30 documentary ONLY after the user approves the corrected preview.
- Active renderer: render_preview_v2.py; shared Cairo primitives and canonical hero face/hair in render_preview.py; independent checks/mutation runner in qa_preview_v2.py. Preserve preview-v1-original/ as comparison evidence.
- 1920×1080, 30 fps, 16:9. Code-drawn flat 2D, near-black ground, thin grey strokes, same own hero in a flight suit. Fingerless rounded hands; no redesign of face/hair.
- Historical outline source: CIA July 1991 map 801727 (B01272) 7-91, LOC 2005626536. Vectorization and source scan retained in assets/. Do not replace it with modern country geometry or claim survey-level precision from the scan.
- No internal borders before 2.5 s. Then 15 tinted non-overlapping republic regions, displacement ≤12 px. Mir in hook must be ≥60 px and visibly travel. This overrides the older ≤40 px orbital-station requirement for the hook.
- Caption zone y0..200, x380..1540 contains plain background. Test picture pixels in every actual subtitle rectangle plus 8 px. Text is an edit layer.
- Neutral floating posture: hips about30°, knees40–50°, arms raised, relaxed fingerless hands. Fixed rail with two visible wall brackets; IK hand stays attached. No planted feet in cabin.
- Launch runs8..16 s, three shots: countdown, engine ignition, low-angle tower clearance; hard cut to orbit. Exhaust #fff3c4→#ffb347→transparent, smoke #8a8a90..#d0d0d4; no red flame.
- Audio priority explicitly resolved by user: integrated −14 LUFS, roughly −16..−12 LUFS per second, LRA≤10, true peak≤−1.5 dBTP; no1s window below−24 except the single registered full-film silence86..87 s. No planned silence in the preview.
- Encode x264 CRF16, preset slow, high profile, yuv420p, tune animation. Enforce measured video bitrate≥6 Mb/s with transparent reporting of HRD filler if needed. Bitrate padding is not added visual detail.
- QA must test actual rendered/decoded outputs and intentional corrupted copies, not merely claim success. Print all failures and keep evidence. Do not claim every frame was manually viewed from a sampled contact sheet.
