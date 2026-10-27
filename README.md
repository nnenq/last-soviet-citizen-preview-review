# The Last Soviet Citizen — preview v2 review package

**Review target: the corrected 23-second animation preview. The full documentary is not complete.**

- [Download / view original preview MP4](preview-v2.mp4)
- [Latest downloadable package](https://github.com/nnenq/last-soviet-citizen-preview-review/releases/tag/preview-v2-review)
- [Script / shot list](preview-v2-script.md)
- [Review report and honest limits](preview-v2/qa/REVIEW.md)
- [Complete measured QA output](preview-v2/qa/QA-COMPLETE-OUTPUT.txt)
- [Contact sheet, 2 fps](preview-v2/qa/contact-sheet-2fps.jpg)
- [Native 1920x1080 sample frames](preview-v2/qa/frames/)
- [Deliberately corrupted mutation evidence](preview-v2/qa/mutations/)
- [Historical-map source and trace](assets/)
- [Credits and font/data licenses](credits-preview-v2.txt)

## Instructions for Claude / another independent reviewer

Do not trust the reported "QA issues: 0" without checking it. Download the repository or the release archive. Inspect the actual MP4 and code. Review the 1991 map, hidden/revealed borders, 15-piece fracture, readable station, zero-g pose, rail mounting/contact, launch continuity, captions, audio and test coverage. Report each issue with a timestamp, evidence and a concrete repair. Clearly separate measured failures, visual judgments, and things you could not execute or perceive. Do not claim the full film was reviewed.

A GitHub page link alone does **not** give a text-only assistant video perception. If your Claude environment cannot download files, run Python/FFmpeg, or view video, say so; a link does not add those capabilities.

## Fast access without downloading the full repository

The MP4 is 23 s, 1920x1080, 30 fps. Download it using the raw-file link or the release asset.
The release contains a ZIP with the complete project, supporting assets and QA evidence.
Frames requested by the user are linked below:

| Time | PNG |
|---|---|
|0.0 s|[frame 0](preview-v2/qa/frames/frame-0000-000.00s.png)|
|2.5 s|[frame 75](preview-v2/qa/frames/frame-0075-002.50s.png)|
|3.0 s|[frame 90](preview-v2/qa/frames/frame-0090-003.00s.png)|
|5.0 s|[frame 150](preview-v2/qa/frames/frame-0150-005.00s.png)|
|9.0 s|[frame 270](preview-v2/qa/frames/frame-0270-009.00s.png)|
|12.0 s|[frame 360](preview-v2/qa/frames/frame-0360-012.00s.png)|
|22.0 s|[frame 660](preview-v2/qa/frames/frame-0660-022.00s.png)|
|last frame|[frame 689](preview-v2/qa/frames/frame-0689-022.97s.png)|

## Run

Requirements: Python 3.11+ compatible package builds, FFmpeg and ffprobe on PATH.
The pinned versions reflect the original Windows Python 3.14 environment; choose compatible builds if using another Python version.

    python -m pip install -r requirements-preview.txt
    python render_preview_v2.py
    python audit_preview_v2.py
    python sample_loudness_qa.py

Run from the repository root. The renderer writes generated QA/media outputs in preview-v2/.
The historical tracing step is optional because its resulting vector asset is included:

    python trace_1991_map.py

The shared render_preview.py supplies drawing primitives and the own hero face/hair. Its old main entrypoint is not the active renderer.
The original v1 movie is retained only as a deliberate excessive-loudness-range test input.

## Important evidence/provenance limits

- Original MP4 bytes are unchanged. Recorded QA results belong to the original local run, not a new GitHub/cloud run.
- Local personal paths have been replaced with portable relative paths. The public code has a small portability change for event-template lookup and the FFmpeg null sink. Those changes are documented; the original source SHA256 values are retained as provenance.
- Tests, logs and source-checksum records are not cryptographic proof that every visual bug is absent.
- The high video bitrate contains HRD filler. Padding is not visual detail.
- The map is a simplified trace of a July 1991 CIA printed map. Fine scan-resolution features are not survey-certified.
- No model perceptual audition on a physical phone is claimed.
- The full film begins only after user approval of this preview.

## Rights

The film and own character/source drawings are shared here for review. No blanket open-source or reuse license is granted for the own film/character. Third-party fonts retain their SIL OFL licenses, and reference-map rights/attribution are recorded in credits. Do not assume public GitHub visibility grants unrestricted redistribution rights.
