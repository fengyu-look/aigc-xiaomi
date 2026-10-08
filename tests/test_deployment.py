import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

DEPLOY=Path(__file__).resolve().parent.parent/'tools/deploy_skill.py'

class DeploymentTests(unittest.TestCase):
    def test_copy_dry_run_refusal_and_backup(self):
        with tempfile.TemporaryDirectory(prefix='aigc-deploy-') as directory:
            root=Path(directory).resolve();project=root/'project';host=root/'host-skills'
            source=project/'skills/film-creation-library';source.mkdir(parents=True)
            (source/'SKILL.md').write_text('new skill',encoding='utf-8')
            def run(*args):
                return subprocess.run([sys.executable,'-X','utf8',str(DEPLOY),'--project-root',str(project),'--skills-dir',str(host),*args],capture_output=True,text=True,encoding='utf-8')
            preview=run('--mode','copy','--dry-run')
            self.assertEqual(preview.returncode,0,preview.stderr)
            self.assertFalse(host.exists())
            installed=run('--mode','copy')
            self.assertEqual(installed.returncode,0,installed.stderr)
            target=host/'film-creation-library'
            self.assertEqual((target/'SKILL.md').read_text(),'new skill')
            (source/'SKILL.md').write_text('updated skill',encoding='utf-8')
            refused=run('--mode','copy')
            self.assertEqual(refused.returncode,2)
            self.assertEqual((target/'SKILL.md').read_text(),'new skill')
            replaced=run('--mode','copy','--replace')
            self.assertEqual(replaced.returncode,0,replaced.stderr)
            receipt=json.loads(replaced.stdout)
            self.assertEqual((Path(receipt['Backup'])/'SKILL.md').read_text(),'new skill')
            self.assertEqual((target/'SKILL.md').read_text(),'updated skill')

    def test_link_uses_single_live_source(self):
        with tempfile.TemporaryDirectory(prefix='aigc-link-') as directory:
            root=Path(directory).resolve();source=root/'project/skills/film-creation-library'
            source.mkdir(parents=True)
            (source/'SKILL.md').write_text('version one',encoding='utf-8')
            target=root/'host/film-creation-library'
            command=[sys.executable,'-X','utf8',str(DEPLOY),'--project-root',str(root/'project'),'--skills-dir',str(root/'host'),'--mode','link']
            result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(target.resolve(),source.resolve())
            (source/'SKILL.md').write_text('version two',encoding='utf-8')
            self.assertEqual((target/'SKILL.md').read_text(),'version two')
            again=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(json.loads(again.stdout)['Status'],'already-linked')
            # Remove only the test junction/link, never recurse into its target.
            if os.name=='nt':os.rmdir(target)
            else:target.unlink()

if __name__=='__main__':unittest.main()
