from contextlib import redirect_stdout
from io import StringIO
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import SimpleTestCase
from scripts import cap_nhat_du_an as updater


class SourceUpdaterTests(SimpleTestCase):
    def manifest(self, files):
        return {'ref':'a'*40,'files':[{'path':name,'sha256':hashlib.sha256(data).hexdigest()} for name,data in files.items()]}

    def test_paths_cannot_escape_or_replace_private_configuration(self):
        for name in ('../secrets', '/absolute', 'templates/../../.env', '.env', 'salon/../manage.py', 'C:/file', 'salon/.env', 'salon\\file.py'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                updater.validate_manifest(self.manifest({name:b'bad'}))

    def test_complete_update_backups_missing_templates_and_keeps_private_files(self):
        files={'manage.py':b'# current\n','templates/features/page.html':b'<h1>Ready</h1>'}
        manifest=self.manifest(files)
        def fetch(url):
            if url.endswith('update_manifest.json'): return json.dumps(manifest).encode()
            return files[url.split('/'+'a'*40+'/')[1]]
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'manage.py').write_bytes(b'# old\n');(root/'.env').write_bytes(b'private sentinel')
            with patch.object(updater,'fetch',side_effect=fetch), patch('sys.argv',['updater','--project',tmp]), redirect_stdout(StringIO()):
                self.assertEqual(updater.main(),0)
                self.assertEqual(updater.main(),0)
            self.assertEqual((root/'templates/features/page.html').read_bytes(),files['templates/features/page.html'])
            self.assertEqual((root/'.env').read_bytes(),b'private sentinel')
            backups=list((root/'.local').glob('*/sao-luu/manage.py'))
            self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_bytes(),b'# old\n')

    def test_hash_error_stops_before_replacing_any_source(self):
        files={'manage.py':b'new','templates/features/page.html':b'valid'}
        manifest=self.manifest(files)
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'manage.py').write_bytes(b'old')
            def fetch(url):
                return json.dumps(manifest).encode() if url.endswith('update_manifest.json') else b'corrupted'
            with patch.object(updater,'fetch',side_effect=fetch), patch('sys.argv',['updater','--project',tmp]), redirect_stdout(StringIO()), self.assertRaises(ValueError):
                updater.main()
            self.assertEqual((root/'manage.py').read_bytes(),b'old')
            self.assertFalse((root/'templates/features/page.html').exists())

    def test_write_failure_restores_prior_sources(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/'project';root.mkdir();stage=Path(tmp)/'stage';stage.mkdir();backup=Path(tmp)/'backup'
            (root/'manage.py').write_bytes(b'old');(stage/'manage.py').write_bytes(b'new');(stage/'other.py').write_bytes(b'new file')
            real_replace=updater.os.replace
            def replace(source,target):
                if str(target).endswith('other.py'): raise OSError('simulated disk error')
                return real_replace(source,target)
            with patch.object(updater.os,'replace',side_effect=replace), self.assertRaises(OSError):
                updater.apply_files(root,stage,['manage.py','other.py'],backup)
            self.assertEqual((root/'manage.py').read_bytes(),b'old');self.assertFalse((root/'other.py').exists())
