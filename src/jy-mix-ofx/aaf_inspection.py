"""Read-only handoff preflight; never renders or modifies a draft."""
from pathlib import Path
import datetime,json

def inspect(worker,data,source,authority,digest,job,handles_seconds=0):
    issues=[];risks=[];material_map={m['id']:(cat,m) for cat,items in data.get('materials',{}).items() if isinstance(items,list) for m in items if isinstance(m,dict) and 'id' in m}
    counts=[];missing=[]
    for ti,track in enumerate(data.get('tracks',[]),1):
        if track.get('type') not in ('audio','video'):continue
        name=track.get('name') or f'轨道{ti}';segments=track.get('segments',[]);counts.append({'name':name,'type':track.get('type'),'segments':len(segments)})
        if any(track.get(k) for k in ['is_muted','muted','is_solo','solo']):risks.append(name+'：静音或独奏状态未还原')
        for si,segment in enumerate(segments,1):
            label=f'{name} 第{si}段'
            material=material_map.get(segment.get('material_id'))
            if not material or not material[1].get('path'):missing.append(label+'：缺少素材路径')
            else:
                try:worker.source_file(material[1]['path'],source)
                except (ValueError,OSError) as exc:missing.append(label+'：'+str(exc))
            if any(segment.get(k) for k in ['common_keyframes','keyframes','keyframe_refs']):risks.append(label+'：发现关键帧数据，当前不还原其自动化')
            for ref in segment.get('extra_material_refs',[]):
                cat,_=material_map.get(ref,('',{}))
                if cat in ['audio_effects','audio_effect','sound_channel_mappings','vocal_separations']:
                    risks.append(label+'：发现未支持的声音处理引用 '+cat)
    tracks=[];total=0;warnings=[]
    try:tracks,total,warnings=worker.plan(data,source)
    except (ValueError,OSError,RuntimeError) as exc:issues.append(str(exc))
    issues=list(dict.fromkeys(missing+issues));risks=list(dict.fromkeys(risks))
    mapping=[]
    for track in tracks:
        channels=sorted({c['channels'] for c in track['clips']})
        mapping.append({'source_track':track['name'],'clips':len(track['clips']),'channels':channels})
    fps=data.get('fps');fps=fps if isinstance(fps,(int,float)) and fps>0 else None
    report=dict(project=source.name,source=str(source),authority=str(authority),source_sha256=digest,source_modified=datetime.datetime.fromtimestamp(authority.stat().st_mtime).isoformat(timespec='seconds'),duration_seconds=total/worker.SR if total else None,fps=fps,start_timecode='未知，当前不写入AAF时码轨',source_tracks=counts,aaf_track_mapping=mapping,issues=issues,risks=risks,warnings=warnings,can_export=not issues,handles_seconds=handles_seconds,effects_mode='原始素材剪辑交接；固定片段音量和线性淡化已烘焙')
    path=job/'工程检查报告.md'
    lines=['# AAF工程检查报告','',f'- 工程：{source.name}',f'- 草稿目录：{source}',f'- 文件更新时间：{report["source_modified"]}',f'- 工程总长：{report["duration_seconds"] if report["duration_seconds"] is not None else "检查未通过，无法确定"} 秒',f'- 帧率：{fps if fps else "未识别"}',f'- 起始时间码：{report["start_timecode"]}',f'- 可导出：{"是（仍需核对差异）" if not issues else "否，请处理下列问题"}','','## 阻止导出的问题','']
    lines+=['- '+x for x in issues] or ['- 未发现阻止导出的问题。']
    lines+=['','## 交接差异与待核对事项','']
    lines+=['- '+x for x in risks+warnings]
    lines+=[f'- 片段前后余量：各{handles_seconds}秒；受源素材边界限制，未知素材时长不添加后余量。','- 所有声道按单声道AAF轨交接；立体声拆左右，重叠片段可能增加轨道。','- 本报告仅检测已知字段；未检测到风险不代表剪映全部效果均可还原。','','## 原轨与声道映射','','| 原轨 | 片段数 | 素材声道数 |','| --- | --- | --- |']
    lines += [f'| {x["source_track"].replace("|","/")} | {x["clips"]} | {x["channels"]} |' for x in mapping]
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (job/'工程检查报告.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report,path,tracks,total,warnings
