"""Run the synthetic OFX host against the audio plug-in without dispatching jobs."""
from pathlib import Path
import sys
source=Path(__file__).with_name("test_probe.py").read_text(encoding="utf-8-sig")
old='assert set(params)=={b"probe_level",b"probe_button",b"param_draft_path"}'
new='assert set(params)=={b"source_path",b"output_path",b"manifest_path",b"copy_path",b"export_mode",b"export_audio",b"import_copy",b"open_toolkit",b"open_jobs"}'
assert old in source
exec(compile(source.replace(old,new),str(Path(__file__).with_name("test_probe.py")),"exec"))

