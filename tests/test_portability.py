import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT=Path(__file__).resolve().parent.parent
SOURCE=PROJECT/'skills/film-creation-library'

class PortabilityTests(unittest.TestCase):
    def test_independent_skill_copy_and_unrelated_working_directory(self):
        with tempfile.TemporaryDirectory(prefix='aigc-relocation-') as directory:
            root=Path(directory).resolve();skill=root/'另一个位置 独立Skill/film-creation-library'
            shutil.copytree(SOURCE,skill,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            cwd=root/'unrelated';cwd.mkdir()
            def run(*args):
                return subprocess.run([sys.executable,'-X','utf8',str(skill/'scripts/library_lookup.py'),*args],cwd=cwd,capture_output=True,text=True,encoding='utf-8')
            validated=run('validate')
            self.assertEqual(validated.returncode,0,validated.stderr)
            report=json.loads(validated.stdout)
            self.assertEqual(report['CheckedOriginalBlocks'],112)
            self.assertEqual(report['HistoricalPrompts'],38)
            self.assertEqual(report['Warnings'],[])
            result=run('term','--library','43','--ordinal','2')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('和声',result.stdout)
            result=run('deep','--task','L01-T0012')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('0.4秒',result.stdout)
            self.assertIn('完整例子',result.stdout)
            self.assertNotIn('### L01-T0013',result.stdout)
            result=run('search','--scope','history','--query','Suno','--limit','2')
            self.assertEqual(result.returncode,0,result.stderr)
            matches=json.loads(result.stdout)['Results']
            self.assertTrue(matches)
            self.assertTrue(all(x['HistoryId'] for x in matches))

    @unittest.skipUnless(shutil.which('git'),'Git unavailable')
    def test_git_does_not_normalize_literal_source_newlines(self):
        with tempfile.TemporaryDirectory(prefix='aigc-git-newlines-') as directory:
            root=Path(directory).resolve()
            subprocess.run(['git','init','-q',str(root)],check=True,capture_output=True)
            shutil.copy2(PROJECT/'.gitattributes',root/'.gitattributes')
            for name in ('source.md','source.txt','source.TXT'):
                path=root/name;path.write_bytes('原文\r\n第二行\n'.encode('utf-8'))
                filtered=subprocess.check_output(['git','-c','core.autocrlf=true','hash-object','--path',name,name],cwd=root)
                literal=subprocess.check_output(['git','hash-object','--no-filters',name],cwd=root)
                self.assertEqual(filtered,literal)

    def test_refresh_preserves_baseline_and_rejects_source_tampering(self):
        with tempfile.TemporaryDirectory(prefix='aigc-reindex-') as directory:
            root=Path(directory).resolve()
            shutil.copytree(SOURCE,root/'skills/film-creation-library',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            (root/'tools').mkdir()
            shutil.copy2(PROJECT/'tools/refresh_index.py',root/'tools/refresh_index.py')
            knowledge=root/'skills/film-creation-library/references/knowledge_base'
            index_path=knowledge/'91_创作小秘工作库/00_全量检索索引.json'
            index=json.loads(index_path.read_text(encoding='utf-8'))
            item=next(x for x in index['Libraries'] if x['Id']==43)
            path=knowledge/item['ExpandedRelativePath']
            with path.open(encoding='utf-8',newline='') as f:body=f.read()
            path.write_text(body+'\n新增应用设计示例。\n',encoding='utf-8',newline='')
            command=[sys.executable,'-X','utf8',str(root/'tools/refresh_index.py')]
            result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(len(json.loads(result.stdout)['ChangedDocuments']),1)
            updated=json.loads(index_path.read_text(encoding='utf-8'))
            after=next(x for x in updated['Libraries'] if x['Id']==43)
            self.assertEqual(item['OriginalTextSHA256'],after['OriginalTextSHA256'])
            baseline=index_path.read_bytes()
            start=after['OriginalBlockOffset']
            tampered=body[:start]+'改'+body[start+1:]
            path.write_text(tampered,encoding='utf-8',newline='')
            result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,2)
            self.assertEqual(index_path.read_bytes(),baseline)

if __name__=='__main__':unittest.main()
