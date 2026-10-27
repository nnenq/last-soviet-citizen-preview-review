"""Additional continuous-window loudness floor test at every audio sample.
Uses the installed BS.1770 K-weighting filters, then ungated mean-square energy
for every 1-second interval. It supplements (does not rename) gated 1s reports.
"""
from pathlib import Path
import json
import numpy as np
import pyloudnorm as pyln
from qa_preview_v2 import audio_data
P=Path(__file__).resolve().parent;Q=P/"preview-v2/qa"
def minimum(path):
    data=audio_data(path).astype(np.float64)
    meter=pyln.Meter(48000)
    for stage in meter._filters.values():
        for c in range(data.shape[1]):data[:,c]=stage.apply_filter(data[:,c])
    energy=np.sum(data*data,axis=1)
    total=np.r_[0.,np.cumsum(energy)]
    means=(total[48000:]-total[:-48000])/48000
    values=-.691+10*np.log10(np.maximum(means,1e-30))
    idx=int(values.argmin())
    return {"method":"BS.1770 K-weighted, ungated 1-second power, every sample start",
        "window_count":len(values),"minimum_LUFS":float(values[idx]),"minimum_start_seconds":idx/48000,
        "below_minus24_count":int(np.count_nonzero(values<-24))}
good=minimum(P/"preview-v2.mp4")
bad=minimum(Q/"mutations/quiet-first-second.wav")
passed=good["below_minus24_count"]==0 and bad["below_minus24_count"]>0
(Q/"every-sample-floor.json").write_text(json.dumps({"delivered":good,"quiet_mutation":bad,"pass":passed},indent=2))
output="COMMAND: python sample_loudness_qa.py\n"+json.dumps({"delivered":good,"quiet_mutation":bad},indent=2)+"\nEvery-sample floor mutation: "+("PASS" if passed else "FAIL")+"\nQA issues: "+("0" if passed else "1")+"\n"
(Q/"every-sample-floor-output.txt").write_text(output)
print(output)
if not passed:raise SystemExit(1)

