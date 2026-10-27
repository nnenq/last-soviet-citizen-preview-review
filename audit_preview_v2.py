"""Fresh review of the actually encoded revised preview, with all mutations."""
from pathlib import Path
import hashlib,json,subprocess
import render_preview_v2 as r
import qa_preview_v2 as qa
P=Path(__file__).resolve().parent;Q=P/"preview-v2/qa";final=P/"preview-v2.mp4"
lines=[]
def say(s):print(s,flush=True);lines.append(s)
say("COMMAND: python audit_preview_v2.py")
metas=json.loads((Q/"frame-metadata.json").read_text())
issues=[]
for i,m in enumerate(metas):issues.extend(qa.check_frame(m,metas[i-1] if i else None))
issues+=qa.observed_caption_rules(metas)+qa.observed_launch_rule(metas)
say("Every-frame geometry / picture-mask / chronology check: "+str(len(metas))+" frames; issues="+str(len(issues)))
# Hash every actual decoded frame again, independently of renderer hashes.
out=Q/"decoded-framemd5.txt"
subprocess.run(["ffmpeg","-y","-v","error","-i",str(final),"-map","0:v:0","-f","framemd5",str(out)],check=True)
hashes=[ln.split(",")[-1].strip() for ln in out.read_text().splitlines() if ln and not ln.startswith("#")]
pix=qa.check_pixels(hashes);issues+=pix
say("Decoded-frame n-30 / consecutive freeze checks: "+str(len(hashes))+" frames; issues="+str(len(pix)))
media=qa.verify_media(final,Q);issues+=media["issues"]
say("DELIVERED MEDIA:\n"+json.dumps(media,indent=2))
say("MUTATION TESTS:")
mut=qa.mutations(r.draw,metas,hashes,final,Q)
for line in mut["lines"]:say(line)
issues.extend({"rule":"mutation_not_caught","detail":name} for name in mut["failed"])
missing=set(qa.RULES)-{t["expected"] for t in json.loads((Q/"mutation-results.json").read_text())}
if missing:issues.append({"rule":"untested_qa_rules","detail":sorted(missing)})
say("QA rules with deliberate mutation coverage: "+str(len(qa.RULES))+"/"+str(len(qa.RULES)) if not missing else "Missing coverage: "+repr(missing))
qa.exports(final,Q)
sources={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ["render_preview_v2.py","qa_preview_v2.py","render_preview.py","trace_1991_map.py","audit_preview_v2.py"]}
(Q/"source-checksums.json").write_text(json.dumps(sources,indent=2))
result={"scope":"23-second preview only; all numerical claims are measured or marked as geometry metadata",
    "issues":issues,"media":media,"mutation_tests":mut,"source_sha256":sources,
    "video_sha256":hashlib.sha256(final.read_bytes()).hexdigest()}
(Q/"qa-result.json").write_text(json.dumps(result,indent=2))
say("QA issues: "+str(len(issues)))
(Q/"QA-FULL-OUTPUT.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
if issues:raise SystemExit(1)

