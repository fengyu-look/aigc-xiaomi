"""Document line links must resolve real files and reject invalid positions."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parent.parent/'tools/check_project.py'
spec=importlib.util.spec_from_file_location('project_document_check',SCRIPT)
check=importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

class DocumentLinkTests(unittest.TestCase):
    def test_line_link_positions_and_workspace_boundary(self):
        with tempfile.TemporaryDirectory(prefix='document-links-') as directory:
            root=Path(directory)
            doc=root/'report.md'
            target=root/'source.md'
            target.write_text('one\ntwo\nthree\n',encoding='utf-8')
            self.assertIsNone(check.document_link_error(doc,'source.md:3',root))
            self.assertIsNone(check.document_link_error(doc,target.as_posix()+':2',root))
            self.assertIsNone(check.document_link_error(doc,'source.md#heading',root))
            self.assertIn('行号无效',check.document_link_error(doc,'source.md:4',root))
            self.assertIn('行号无效',check.document_link_error(doc,'source.md:0',root))
            self.assertIn('缺失或越界',check.document_link_error(doc,'missing.md:1',root))
            self.assertIn('缺失或越界',check.document_link_error(doc,'../outside.md:1',root))
