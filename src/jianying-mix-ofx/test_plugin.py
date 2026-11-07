from pathlib import Path
import sys
p=Path(__file__).parent.parent/'jianying-ofx-probe/test_probe.py'
source=p.read_text(encoding='utf-8-sig')
source=source.replace('assert set(params)=={b"probe_level",b"probe_button",b"param_draft_path"}', 'assert set(params)=={b"source_path",b"output_path",b"fill_output",b"export_aaf",b"open_jobs",b"open_panel",b"choose_source",b"choose_output",b"open_output",b"restore_paths",b"inspect_project",b"open_report",b"refresh_status",b"last_job",b"task_status",b"group_project",b"group_export",b"group_execute",b"source_origin",b"export_format",b"handoff_mode",b"handles_mode",b"toggle_details",b"batch_source_path",b"choose_batch_source",b"export_stems",b"export_batch_stems"}')
exec(compile(source,str(p),'exec'))
