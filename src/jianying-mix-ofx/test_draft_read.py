import pathlib,json,sys,tempfile,hashlib,types,unittest
from unittest.mock import patch
import aaf_worker as w
if str(w.CODE) not in sys.path:sys.path.insert(0,str(w.CODE))
import import_audio as imp
class DraftReadTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='ofx-read-');self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name);self.source=self.root/'draft';self.source.mkdir();self.file=self.source/'draft_content.json';self.file.write_bytes(b'ciphertext-fixture');self.before=self.file.read_bytes();self.job=self.root/'job';self.job.mkdir();self.install=self.root/'11.7.0.14614';self.install.mkdir();(self.install/'videoeditor.dll').write_bytes(b'test');self.converter=self.root/'converter.exe';self.converter.write_bytes(b'test')
  runtime_patch=patch.object(w,'configured_runtime',return_value=None);runtime_patch.start();self.addCleanup(runtime_patch.stop)
  for name,value in [('DEFAULT_DRAFTC',self.converter),('_jianying_install_dir',lambda:self.install)]:
   p=patch.object(imp,name,value);p.start();self.addCleanup(p.stop)
 def test_empty_response_reports_stage_and_preserves_source(self):
  with patch.object(w.subprocess,'run',return_value=types.SimpleNamespace(returncode=20,stdout='output_len=0',stderr='')):
   with self.assertRaises(w.DraftReadError) as caught:w.load_draft(self.source,self.job)
  d=json.loads(pathlib.Path(caught.exception.diagnostic).read_text(encoding='utf-8'));self.assertEqual(d['phase'],'读取加密草稿');self.assertTrue(d['source_matches_snapshot']);self.assertFalse(d['decoded_json_valid']);self.assertEqual(self.file.read_bytes(),self.before)
 def test_exit_zero_with_ciphertext_is_not_success(self):
  def run(*args,**kw):
   (self.job/'草稿副本/draft_content.json.dec.json').write_bytes(b'ciphertext-fixture');return types.SimpleNamespace(returncode=0,stdout='copied',stderr='')
  with patch.object(w.subprocess,'run',side_effect=run),self.assertRaises(w.DraftReadError):w.load_draft(self.source,self.job)
 def test_converter_valid_json_and_original_filename(self):
  def run(args,**kw):
   self.assertEqual(pathlib.Path(args[-1]).name,'draft_content.json');self.assertEqual(kw['cwd'],self.job/'converter');self.assertTrue(str(args[-1]).startswith(str(self.job)))
   (self.job/'草稿副本/draft_content.json.dec.json').write_text('{"tracks":[],"materials":{}}',encoding='utf-8');return types.SimpleNamespace(returncode=0,stdout='ok',stderr='')
  with patch.object(w.subprocess,'run',side_effect=run):data,_,_=w.load_draft(self.source,self.job)
  self.assertEqual(data['tracks'],[]);self.assertEqual(self.file.read_bytes(),self.before)
 def test_broken_plain_json_does_not_call_converter(self):
  self.file.write_bytes(b'{broken')
  with patch.object(w.subprocess,'run') as call,self.assertRaisesRegex(ValueError,'JSON结构损坏'):w.load_draft(self.source,self.job)
  call.assert_not_called()
 def test_media_relocated_inside_original_directory(self):
  original=self.root/'Video/22.mp4';archived=original.parent/'归档/22.mp4';archived.parent.mkdir(parents=True);archived.write_bytes(b'fixture')
  self.assertEqual(w.source_file(str(original),self.source),archived.resolve())
 def test_ambiguous_relocated_media_is_rejected(self):
  original=self.root/'Video/22.mp4'
  for name in ('归档A','归档B'):
   p=original.parent/name/'22.mp4';p.parent.mkdir(parents=True);p.write_bytes(b'fixture')
  with self.assertRaisesRegex(ValueError,'多个同名'):w.source_file(str(original),self.source)
class RuntimeConfigTests(unittest.TestCase):
 def test_pinned_runtime_hash_and_tamper_detection(self):
  with tempfile.TemporaryDirectory(prefix='ofx-runtime-') as tmp:
   root=pathlib.Path(tmp);runtime=root/'11.6.0.14552';runtime.mkdir()
   engine=runtime/'videoeditor.dll';engine.write_bytes(b'engine-fixture');converter=runtime/'jy-draftc.exe';converter.write_bytes(b'converter-fixture')
   config=root/'runtime.json';config.write_text(json.dumps(dict(runtime_dir=str(runtime),engine_sha256=hashlib.sha256(engine.read_bytes()).hexdigest(),converter_sha256=hashlib.sha256(converter.read_bytes()).hexdigest())),encoding='utf-8')
   self.assertEqual(w.configured_runtime(config),runtime)
   engine.write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'发生变化'):w.configured_runtime(config)
 def test_no_config_keeps_existing_plain_or_runtime_flow(self):
  with tempfile.TemporaryDirectory(prefix='ofx-runtime-') as tmp:self.assertIsNone(w.configured_runtime(pathlib.Path(tmp)/'absent.json'))
if __name__=='__main__':unittest.main(verbosity=2)
