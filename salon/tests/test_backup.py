import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.conf import settings
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from salon.database_backup import backup, restore, digest


class BackupGuardsTests(SimpleTestCase):
    def test_restore_cannot_target_current_or_system_database(self):
        for name in [str(settings.DATABASES['default']['NAME']), 'postgres', 'template0', 'template1']:
            with self.subTest(name=name), self.assertRaises(CommandError): restore('missing.dump',name,name)

    def test_restore_rejects_missing_confirmation_and_sql_identifiers(self):
        for name, confirmation in [('new_copy','different'), ('db; DROP DATABASE test','db; DROP DATABASE test'), ('../file','../file')]:
            with self.assertRaises(CommandError): restore('missing.dump',name,confirmation)

    def test_backup_never_overwrites_an_existing_file(self):
        with TemporaryDirectory() as tmp:
            target=Path(tmp)/'existing.dump';target.write_bytes(b'original')
            with self.assertRaises(CommandError): backup(target)
            self.assertEqual(target.read_bytes(),b'original')

    def test_modified_dump_is_rejected_before_database_connection(self):
        with TemporaryDirectory() as tmp:
            source=Path(tmp)/'bad.dump';source.write_bytes(b'original')
            meta={'format':1,'sha256':digest(source),'counts':{}}
            source.with_suffix('.dump.json').write_text(json.dumps(meta))
            source.write_bytes(b'changed')
            with patch('salon.database_backup.psycopg.connect') as connect, self.assertRaises(CommandError):
                restore(source,'new_copy','new_copy')
            connect.assert_not_called()
