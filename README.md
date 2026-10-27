# The Last Soviet Citizen — corrected preview v3

**Latest review target: preview-v3.mp4, 23 seconds. The full film is not complete.**

- [Download complete v3 package](https://github.com/nnenq/last-soviet-citizen-preview-review/releases/download/preview-v3-review/review-preview-v3.zip)
- [Download MP4](https://github.com/nnenq/last-soviet-citizen-preview-review/releases/download/preview-v3-review/preview-v3.mp4)
- [Script and source notes](preview-v3-script.md)
- [Review report and measured limits](preview-v3/qa/REVIEW.md)
- [Complete QA stdout](preview-v3/qa/QA-FULL-OUTPUT.txt)
- [Machine-readable results](preview-v3/qa/qa-result.json)
- [2 fps contact sheet](preview-v3/qa/contact-sheet-2fps.jpg)
- [Full-resolution frames](preview-v3/qa/frames/)
- [Every mutation and result](preview-v3/qa/mutation-results.json)
- [Lossless source frames used for SSIM](preview-v3/qa/source/)
- [Credits, fact references and caveats](credits-preview-v3.txt)

## Independent reviewer instructions

Download the release ZIP and inspect the actual MP4, source, source PNGs and encoded mutation fixtures. Do not accept QA claims without checking. Report bugs with timestamps and evidence. Geometry template conformance does not prove physical realism, historical accuracy or artistic quality. If your environment cannot download, view video, hear audio or execute Python/FFmpeg, state that explicitly. A URL alone does not add those abilities.

## Reproduce

Python with requirements-preview.txt, FFmpeg and ffprobe must be available. From the extracted project directory:

    python -m pip install -r requirements-preview.txt
    python render_preview_v3.py
    python qa_preview_v3.py

render_preview.py supplies drawing primitives; render_preview_v2.py supplies the canonical hero rig. Only render_preview_v3.py is the active renderer. The v2 artifacts retained in Git history and in this repository are superseded. The v3 release ZIP contains the necessary shared code and assets, without the older v2 QA archive.

## Scope and evidence

No voiceover. No filler/HRD or bitrate floor. Ten decoded RGB SSIM comparisons; all-frame 480x270 non-text motion test; sample-by-sample one-second audio floor; real encoded geometry/media/audio mutations. See REVIEW.md for measured values and limits. The orthographic globe uses approximately georeferenced July1991 scan geometry, not modern Soviet-republic substitutes. Detailed spacecraft/pad drawings and docking are simplified, time-compressed illustrations.

Video bytes are identical to the final local artifact. Personal local paths are removed from published reports. Saved results are local execution evidence, not a new GitHub-hosted test run. Prior failed QA logs are retained. Public viewing does not grant a blanket reuse license for the own film/character; font licenses and map attribution are retained.
