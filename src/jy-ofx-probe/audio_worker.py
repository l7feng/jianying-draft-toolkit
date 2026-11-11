"""OFX audio bridge. Reuses the existing toolkit; never edits the loaded draft."""
from __future__ import annotations
import argparse, contextlib, copy, hashlib, json, os, pathlib, shutil, sys, time, traceback, uuid
ROOT=pathlib.Path(__file__).resolve().parents[2]
CODE=ROOT/"src/jy-tools/code"
PREFS=pathlib.Path(r"D:/Ai-Files/Tools/Exe/02-JY Tools（剪映工程工具）/jy-tools-v4.3.1/jy.h-preferences.local.json")
def core():
    if str(CODE) not in sys.path: sys.path.insert(0,str(CODE))
    import main
    import import_audio
    return main, import_audio
def read_config():
    cfgpath=ROOT/"src/jy-tools/config.json"
    cfg=json.loads(cfgpath.read_text(encoding="utf-8-sig")) if cfgpath.is_file() else {}
    if PREFS.is_file():
        f=json.loads(PREFS.read_text(encoding="utf-8-sig")).get("form",{}).get("fields",{})
        for a,b in {"expFmt":"audio_format","expBitrate":"bitrate_kbps","expTrackTpl":"track_name_template",
                    "expSpec":"track_spec","expDedupe":"dedupe","expVideoTracks":"extract_video_tracks",
                    "expClipType":"clip_type_override","expRemarks":"remarks"}.items():
            if a in f: cfg[b]=f[a]
    return cfg
def export_audio(source,output,mode,job):
    main,_=core()
    if not source.exists():raise ValueError("输入路径不存在 / Input path does not exist")
    if source.resolve()==output.resolve():raise ValueError("输入输出不能相同 / Input and output must differ")
    cfg={**copy.deepcopy(main.DEFAULT_CONFIG),**read_config()}
    cfg.update(input_dir=str(source),output_dir=str(output),export_mode={"tracks":["tracks"],"clips":["clips"],"both":["tracks","clips"]}[mode],
               conflict="rename",skip_existing=False,export_aaf=False,export_subtitles=False,
               split_by_video=False,temp_dir=str(output/(".jy-ofx-"+job.name)),log_dir=str(job),data_dir=str(job/"data"))
    drafts,root,filemode=main.resolve_input_paths([source])
    media=[]
    if filemode:
        media=([source] if source.is_file() else [p for p in source.rglob("*") if p.is_file() and main.media_kind(p)])
        media=[p for p in media if main.media_kind(p)]
    if not drafts and not media:raise ValueError("未找到草稿或媒体 / No drafts or media found")
    stats=main.execute_export(cfg,(source if source.is_dir() else source.parent) if media and not drafts else (root or source),draft_dirs=drafts,media_files=media)
    if stats["failed"] or not stats["success"]:raise RuntimeError("导出未全部成功 / Export incomplete: "+str(stats))
    return {"stats":stats,"output":str(output),"effects":"Existing toolkit rendering only; not Jianying effect rendering"}
def import_copy(source,manifest,destination,job):
    _,imp=core()
    if not source.is_dir() or not manifest.is_file():raise ValueError("请选择有效草稿与清单 / Choose a draft and manifest")
    source=source.resolve();destination=destination.resolve()
    if destination.exists() or source==destination or source in destination.parents or destination in source.parents:
        raise ValueError("副本必须是独立且不存在的新目录 / Copy destination must be new and separate")
    for p in source.rglob("*"):
        if p.is_symlink() or (hasattr(p,"is_junction") and p.is_junction()):
            raise ValueError("草稿含链接目录，请先整理 / Linked draft paths are not supported")
    authority,_,_=imp.resolve_content_files(source)
    if authority is None:raise ValueError("没有draft_content.json / Missing draft content")
    original=hashlib.sha256(authority.read_bytes()).hexdigest()
    rows=imp.parse_pt_clips(manifest,tuple(imp.DEFAULT_EXCLUDE)) if manifest.suffix.lower()==".json" else imp.parse_manifest(manifest)
    if not rows:raise ValueError("清单没有可导入片段 / No importable clips")
    shutil.copytree(source,destination)
    if hashlib.sha256(authority.read_bytes()).hexdigest()!=original:
        raise RuntimeError("复制时源草稿发生变化，请重试 / Source draft changed during copy")
    target,targets,_=imp.resolve_content_files(destination)
    if hashlib.sha256(target.read_bytes()).hexdigest()!=original:
        raise RuntimeError("草稿副本与来源不一致 / Draft copy mismatch")
    encrypted=False
    try:data=json.loads(target.read_text(encoding="utf-8-sig"))
    except (UnicodeError,json.JSONDecodeError):
        encrypted=True
        if not imp.DEFAULT_DRAFTC.is_file():raise ValueError("缺少jy-draftc / Missing draft converter")
        dec=imp.decrypt_file(imp.DEFAULT_DRAFTC,target)
        data=json.loads(dec.read_text(encoding="utf-8-sig"))
    data,plan=imp.apply_import(data,rows,use_pt_tracks=manifest.suffix.lower()==".json")
    report,ok=imp.verify_written(data,plan)
    if not ok:raise RuntimeError("导入结构校验失败 / Import verification failed: "+"; ".join(report))
    encoded=json.dumps(data,ensure_ascii=False,indent=2).encode("utf-8")
    if encrypted:
        intermediate=job/"import-content.json";intermediate.write_bytes(encoded)
        encoded=imp.encrypt_file(imp.DEFAULT_DRAFTC,intermediate).read_bytes()
    # Synchronize the root and authoritative main timeline, preserving other timelines.
    for p in targets:
        if p==target or p.parent==destination:p.write_bytes(encoded)
    if hashlib.sha256(authority.read_bytes()).hexdigest()!=original:
        raise RuntimeError("来源有并发保存；副本已保留，请核对 / Source changed; inspect saved copy")
    return {"draft_copy":str(destination),"import_clips":len(rows),"verification":report,
            "registration":"Not registered in Jianying; open/import the copy manually",
            "original_authority_unchanged":True}
def run(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--action",choices=["export","import-copy"],required=True)
    ap.add_argument("--source",required=True);ap.add_argument("--output",default="")
    ap.add_argument("--manifest",default="");ap.add_argument("--copy",default="")
    ap.add_argument("--mode",choices=["tracks","clips","both"],default="tracks")
    args=ap.parse_args(argv)
    base=pathlib.Path(os.environ.get("LOCALAPPDATA",str(pathlib.Path.home())))/"JyOfxAudio"
    base.mkdir(parents=True,exist_ok=True)
    job=base/(time.strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:8]);job.mkdir()
    result={"ok":False,"action":args.action,"job":str(job)}
    with (job/"task.log").open("w",encoding="utf-8") as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        try:
            import msvcrt
            with (base/"worker.lock").open("a+b") as lock:
                lock.seek(0);lock.write(b"0");lock.flush();lock.seek(0)
                msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
                try:
                    if args.action=="export":
                        if not args.output.strip():raise ValueError("请填写导出目录 / Output folder is required")
                        result["result"]=export_audio(pathlib.Path(args.source),pathlib.Path(args.output),args.mode,job)
                    else:
                        if not args.copy.strip():raise ValueError("请填写新草稿副本目录 / New draft copy folder is required")
                        result["result"]=import_copy(pathlib.Path(args.source),pathlib.Path(args.manifest),pathlib.Path(args.copy),job)
                    result["ok"]=True
                finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
        except Exception as exc:
            result["error"]=str(exc);traceback.print_exc()
    (job/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    summary=("任务完成 / Completed\n"+json.dumps(result.get("result",{}),ensure_ascii=False,indent=2)) if result["ok"] else ("任务失败 / Failed\n"+result.get("error",""))
    (job/"结果说明.txt").write_text(summary,encoding="utf-8")
    return 0 if result["ok"] else 1
if __name__=="__main__":raise SystemExit(run())

