# The Last Soviet Citizen — preview v3

23.000 s, 690 frames, 1920x1080, 30 fps. This is the preview, not the completed film. No voiceover. Hard cuts.

|Shot|Frames / time|Picture and camera|Edit text|Chronology / sound|
|---|---|---|---|---|
|1|0–119 / 0.000–4.000|Night Earth, actual spherical orthographic projection after approximate georeferencing of the retained July1991 CIA scan. Dim dissolved continent silhouettes and schematic city lights. One solid USSR outline until frame74. Frames75–77: white crack flash; 15 distinct republic regions begin a radially separated exploded-map illustration, reach34px displacement. A narrow screen-space seam and uniform small graphic shrink preserve negative space. Mir passes visibly above the limb. Slow camera push and sideways drift; brief crack shake.|He left Earth from one country.|Undated editorial foreshadowing of dissolution, not a claim it happened at launch. Quiet low-passed tonal atmosphere, fracture transient at2.500s. View explicitly stylized; displaced pieces are a visual metaphor.|
|2|120–239 / 4.000–8.000|Own canonical hero floats in a simplified cabin. Bent hips/knees; one hand holds wall rail with two bolted brackets. Free hand rests near chest. Face/gaze toward the left window with visible Earth. Slow push; gentle anchored drift.|He came back to another.|Undated editorial prologue. Low cabin atmosphere, not launch roar.|
|3|240–329 / 8.000–11.000|Soyuz suspended by four support arms. Two umbilical masts retract outward. Slow push-in; red countdown3,2,1 changes on seconds8,9,10. Flame trench and ground are visible.|May 1991. Sergei Krikalev flies / to the space station Mir.|DAY1;18MAY1991. Countdown beeps. Launch procedure is compressed for the preview, not a second-by-second engineering simulation.|
|4|330–404 / 11.000–13.500|Engine insert shows lower boosters, nozzles, launch table, open trench and ground. White-yellow-orange exhaust. Continuous layered billows issue from trench outlets and roll outward along the ground.|Same two caption lines continue.|DAY1/date stay visible. Engine roar ramps up.|
|5|405–479 / 13.500–16.000|Camera below rocket, ground in bottom quarter at shot entrance, upward taper. Four support arms swing outward as rocket rises; camera tilts up following it. No tall service tower beside it. Masts remain retracted. Smoke remains attached to trench at its source.|Same two caption lines continue.|DAY1/date stay visible. Support-release transient at13.500s; engine peak near liftoff, then clear cut out.|
|6|480–689 / 16.000–23.000|Hard cut across two days. A simplified Soyuz approaches Mir's fore docking port from the left. Solar arrays clear the approach path. Ease into contact near22.5s. Earth sits low behind the pair. This deliberately uses a different composition from the hook.|The plan: five months in orbit.|DAY3;20MAY1991 remains through final frame. Quiet orbital score/atmosphere. The exterior sound is editorial, not literal sound propagating through vacuum.|

## Source and fact discipline

- Historical republic shapes: CIA map801727(B01272)7-91, Library of Congress record2005626536: https://www.loc.gov/item/2005626536/ . The retained trace is used for all Soviet internal borders. Dim modern land polygons are dissolved into silhouettes only; they never supply the Soviet political overlay.
- Launch date18May1991 and docking two days later: ESA's dated mission history, https://www.esa.int/Science_Exploration/Space_Science/18_May . NASA Shuttle-Mir history documents Krikalev's return25March1992 and the October crew-change plan: https://www.nasa.gov/history/SP-4225/documentation/mission-summaries/sts60/biographies/biographies.htm . That biography contains a one-day launch-date discrepancy (19May); it is not silently treated as agreement with18May.
- Soyuz support mechanism reference: ESA photographs and description of the same Soyuz-family support principle: https://www.esa.int/ESA_Multimedia/Images/2009/06/Soyuz_launch_pad_primary_support_arms . These are later Kourou facilities; they support the arm mechanism, not an exact1991Baikonur set reconstruction.
- Five months is the rounded planned duration, not the eventual311-day stay. No invented quotation is presented as archival speech. Docking/spacecraft/module details are simplified animation, not engineering drawings.

## Delivery mix and review scope

Atmosphere approximately-20..-18LUFS short-term; launch-11..-9; integrated-14+/-0.5; LRA5..9; true peak<=-1.5dBTP. The preview has no intentional silence. No HRD/filler or bitrate-floor rule. Compare ten decoded RGB frames with their exact lossless input PNGs; SSIM>=0.98 is an encoding-fidelity check, not proof that no viewer can ever perceive banding.

`python render_preview_v3.py` produces the movie; `python qa_preview_v3.py` decodes it and creates reports, contact sheets and encoded mutation fixtures. The source and final movie must be kept together for independent review. Full film still awaits user approval of this preview.
