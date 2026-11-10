"""Business smoke tests using synthetic audio and draft only."""
import contextlib,csv,hashlib,json,pathlib,uuid,wave,sys
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import audio_worker as w
root=w.ROOT
work=root/"build/ofx-audio-v0.1"/("smoke-"+uuid.uuid4().hex[:8]);work.mkdir(parents=True)
media=work/"audio";media.mkdir()
for name in ["DX","MX"]:
    with wave.open(str(media/(name+".wav")),"wb") as f:
        f.setparams((1,2,48000,0,"NONE","not compressed"));f.writeframes(b"\0\0"*48000)
source=work/"draft";source.mkdir();content=source/"draft_content.json"
content.write_text(json.dumps({"id":"TEST-DRAFT","duration":4000000,"tracks":[],"materials":{}}),encoding="utf-8")
before=hashlib.sha256(content.read_bytes()).hexdigest()
manifest=work/"clips.csv"
with manifest.open("w",newline="",encoding="utf-8-sig") as f:
    out=csv.DictWriter(f,fieldnames=["source","track_no","track_name","start_ms","duration_ms"]);out.writeheader()
    for file,track,start in [("DX",1,0),("DX",1,2000),("MX",2,1000)]:
        out.writerow(dict(source=str(media/(file+".wav")),track_no=track,track_name=file,start_ms=start,duration_ms=1000))
job=work/"job";job.mkdir()
with (work/"worker-smoke.log").open("w",encoding="utf-8") as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
    imported=w.import_copy(source,manifest,work/"draft-copy",job)
    original_config=w.read_config
    try:
        w.read_config=lambda:dict(audio_format="wav",name_template="{原始名}",name_templates_active=["{原始名}"],dedupe=False)
        exported=w.export_audio(media,work/"exports","clips",job)
    finally:w.read_config=original_config
    # Actual failure should be counted rather than raising an unbound exception variable.
    main,_=w.core();old_extract=main.extract_audio
    try:
        def broken(*a,**kw):raise RuntimeError("synthetic converter failure")
        main.extract_audio=broken
        stats=dict(success=0,failed=0,skipped=0)
        main.process_direct_file(media/"DX.wav",dict(audio_format="wav",output_dir=str(work/"failed"),name_templates_active=["{原始名}"]),job,{},stats)
        assert stats==dict(success=0,failed=1,skipped=0)
    finally:main.extract_audio=old_extract
assert hashlib.sha256(content.read_bytes()).hexdigest()==before
copy=json.loads((work/"draft-copy/draft_content.json").read_text(encoding="utf-8"))
tracks=[t for t in copy["tracks"] if t.get("type")=="audio"];assert len(tracks)==2
segments=[s for t in tracks for s in t["segments"]];assert len(segments)==3
assert sorted(s["target_timerange"].get("start",0) for s in segments)==[0,1000000,2000000]
assert all(s["target_timerange"]["duration"]==1000000 for s in segments)
outs=list((work/"exports").rglob("*.wav"));assert len(outs)==2
for p in outs:
    with wave.open(str(p),"rb") as f:assert (f.getframerate(),f.getnchannels(),f.getnframes())==(44100,2,44100)
for dest in [source,source/"nested",source.parent]:
    try:w.import_copy(source,manifest,dest,job);raise AssertionError("invalid destination accepted")
    except ValueError:pass
result=dict(import_two_tracks_three_clips="pass",clip_positions_and_durations="pass",original_unchanged="pass",
 invalid_destinations_rejected="pass",export_two_wavs_via_existing_core="pass",export_existing_44100_stereo_one_second="pass",
 export_error_counted="pass",real_jianying_ui=False,test_root=str(work))
(work.parent/"worker-smoke-results.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))

