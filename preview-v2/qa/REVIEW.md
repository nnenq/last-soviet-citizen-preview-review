# Corrected preview V2

Actual movie: preview-v2.mp4.23.000000s,690 frames,1920x1080,30fps,H.264High/yuv420p,AAC192k stereo48kHz.
Full documentary is NOT built; waiting for user approval of this preview.

## The eight requested fixes
1. Opening audio rebuilt and launch balanced. Encoded AAC: -14.01LUFS, TP-3.29dBTP, LRA1.2LU.
2. One intact USSR outer outline before2.5s;15 tinted historical republic pieces from frame75. Narrow fixed fracture seam, maximum rigid displacement1.0px, no geometric overlap>0.02px². Small displacement preserves the irregular regions without collisions. The0.15s shake is sampled at30fps as a five-timestamp burst, frames75–79. Crack sound at frame75.
3. Mir approximately78px in hook, travelling352px over4s, panel subdivisions and a pale light.
4. Ceiling below caption area. Actual picture snapshot before text is tested: reserved zone plain, every caption box plus8px clear. Zero failures over690 frames.
5. Hips about30°, knees45°, arms raised, fixed IK hand, two wall brackets. Free hand/window separated after visual review. Fingerless rounded hands preserve the existing hero design.
6. Launch exactly8s:8–11 wide countdown;11–13.5 engines;13.5–16 tower clearance. Hard orbit cut at16s. Upper rocket intentionally outside the engine-detail insert.
7. Exhaust#fff3c4→#ffb347→transparent. Soft grey-white smoke#8a8a90..#d0d0d4, particle centre alpha0.6. No red exhaust.
8. libx264 CRF16/slow/High/yuv420p/tune animation. Video bitrate9913786b/s. HRD filler enforces the numerical floor for a minimal flat drawing. Padding is not newly added visual detail; CRF16 sets actual coding quality.

## Real verification
Two complete revised690-frame renders; second contains window/hand clearance.
Fresh command: python audit_preview_v2.py
All690 geometry/picture-mask/timeline records checked. All690 final encoded frames decoded and hashed.
39/39 named rules have deliberate negative coverage.40 actual mutation cases plus silence-policy and original-checksum tests =42 checks; all pass.
Spatial mutations are rendered. Freeze, black, low-bitrate, wrong-format and changed-audio mutations are real media files. Earth foot contact is a drawn fixture because this preview has no Earth walking shot.
SFX timing is measured by correlation with actual event templates in decoded AAC, within±2 frames; delayed-crack mutation uses a real shifted WAV.
Caption reading time is checked from actual frame visibility.
No silence exception in this preview. Full-film86.0–87.0s is reserved and labelled, not yet rendered or certified. Measured quiet-WAV excerpts are checked at allowed and forbidden global-time offsets.
No final freeze/black/long-silence detections. Corrupt copies demonstrate all three FFmpeg detectors.
Original MP4 checksum unchanged by mutations.

## Per-second gated loudness, seconds0–22
[-14.304, -14.244, -14.277, -14.315, -14.226, -14.321, -14.215, -14.283, -14.224, -14.222, -14.554, -12.91, -13.277, -13.272, -13.263, -12.882, -14.479, -14.237, -14.321, -14.292, -14.252, -14.251, -14.224]

Regular checker:221 windows at0.1s steps. Additional independent K-weighted ungated1s energy check: every sample start, 1056001 windows, minimum -14.740664LUFS, zero below−24.
The same all-sample check catches 5234 failing windows in the quiet-first-second copy.
Gated one-second readings and ungated continuous-window energy are explicitly distinct measurements.
QA-COMPLETE-OUTPUT.txt includes both complete tool outputs.

## Visual review actually performed
All46 final2fps tiles inspected at480x270 across three1920x1200 pages.
Native1920x1080 frames individually displayed at0.0,2.5,3.0,5.0,9.0,12.0,22.0,22.9667s.
No claim of manual full-resolution inspection of every690 frames.
Current authoritative images are decoded frames/ and contact sheets. Old design-* images are working drafts, excluded from the package.

## Honest limits
Historical map is traced from the actual July1991 CIA sheet, not modern-country polygons. Simplification/scan resolution limit fine enclaves/coastline precision; no survey-level border certification.
No perceptual audition on a physical phone. Loudness, peaks, floors and cue times are measured.
High bitrate partly contains HRD filler, which is not visual information.
Later docking, collapse silence, landing, future dates and full-film QA are not certified by this preview.

QA issues:0 for the declared preview checks.
