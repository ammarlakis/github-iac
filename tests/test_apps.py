import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / f'template/scripts/{name}.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


apps = module('github-apps')
publisher = module('publish-secrets')


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vault = self.root / 'vault'
        self.vault.mkdir()
        self.identity = self.root / 'identity/key.txt'

    def test_public_repository_rejected(self):
        with patch.object(apps, 'run', side_effect=['git@github.com:owner/vault.git', json.dumps({'isPrivate': False})]):
            with self.assertRaisesRegex(ValueError, 'PRIVATE'):
                apps.private_repository(self.vault, 'owner/vault')

    def test_key_generation_upload_and_rerun(self):
        def tool(command, **kwargs):
            if command[:2] == ['age-keygen', '-o']:
                Path(command[2]).write_text('TEST-PRIVATE-KEY')
            if command[:2] == ['age-keygen', '-y']:
                return 'age1testrecipient\n'
            return ''
        with patch.object(apps, 'private_repository'), patch.object(apps, 'require'), patch.object(apps, 'run', side_effect=tool) as run, patch.object(apps.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                apps.initialize_secrets(self.vault, 'owner/vault', self.identity)
                config = apps.load(self.vault / 'secrets-config.yaml')
                config['publisher'] = {'app_id': 123, 'installation_id': 456}
                apps.write_yaml(self.vault / 'secrets-config.yaml', config)
                apps.initialize_secrets(self.vault, 'owner/vault', self.identity)
            self.assertEqual(apps.load(self.vault / 'secrets-config.yaml')['publisher'], {'app_id': 123, 'installation_id': 456})
            self.assertNotIn('TEST-PRIVATE-KEY', output.getvalue())
            self.assertEqual(self.identity.stat().st_mode & 0o777, 0o600)
            generated = [c for c in run.call_args_list if c.args[0][:2] == ['age-keygen', '-o']]
            self.assertEqual(len(generated), 1)
            uploads = [c for c in run.call_args_list if c.args[0][:3] == ['gh', 'secret', 'set']]
            self.assertEqual(len(uploads), 2)
            self.assertEqual(uploads[0].kwargs['content'], 'TEST-PRIVATE-KEY')
            self.assertNotIn('TEST-PRIVATE-KEY', (self.vault / '.sops.yaml').read_text())
            self.assertTrue((self.vault / '.github/workflows/publish-secrets.yaml').exists())

    def test_missing_existing_key_is_not_replaced(self):
        apps.write_yaml(self.vault / 'secrets-config.yaml', {'repository': 'owner/vault', 'age_recipient': 'age1original'})
        with patch.object(apps, 'private_repository'), patch.object(apps, 'require'), patch.object(apps, 'run') as run, patch.object(apps.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)):
            with self.assertRaisesRegex(ValueError, 'restore'):
                apps.initialize_secrets(self.vault, 'owner/vault', self.identity)
            run.assert_not_called()

    def test_age_key_inside_git_is_rejected(self):
        with patch.object(apps, 'private_repository'), patch.object(apps, 'require'), patch.object(apps, 'run') as run, patch.object(apps.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
            with self.assertRaisesRegex(ValueError, 'outside every Git'):
                apps.initialize_secrets(self.vault, 'owner/vault', self.vault / 'key.txt')
            run.assert_not_called()

    @unittest.skipUnless(shutil.which('sops') and shutil.which('age-keygen'), 'SOPS and age required for encryption integration')
    def test_real_encryption_round_trip_without_plaintext_file(self):
        subprocess.run(['age-keygen', '-o', str(self.root / 'age.txt')], check=True, capture_output=True)
        recipient = subprocess.check_output(['age-keygen', '-y', str(self.root / 'age.txt')], text=True).strip()
        apps.write_yaml(self.vault / 'secrets-config.yaml', {'repository': 'owner/vault', 'age_recipient': recipient})
        credentials = {'pem': 'private-key-test-value', 'webhook_secret': 'webhook-test-value', 'client_secret': 'client-test-value'}
        with patch.object(apps, 'private_repository'):
            target = apps.store_credentials(self.vault, 'bot', credentials, 'owner/project', 'BOT')
        self.assertNotIn('private-key-test-value', target.read_text())
        self.assertEqual(list((self.vault / 'secrets/apps').iterdir()), [target])
        with patch.object(apps, 'private_repository'):
            optional = apps.store_credentials(self.vault, 'without-webhook', {'pem': 'private-key-only'}, 'owner/project', 'OTHER')
        decoded = subprocess.check_output(['sops', 'decrypt', str(optional)], env={**apps.os.environ, 'SOPS_AGE_KEY_FILE': str(self.root / 'age.txt')}, text=True)
        self.assertEqual(set(yaml.safe_load(decoded)['repositories']['owner/project']['secrets']), {'OTHER_PRIVATE_KEY'})
        decrypted = subprocess.check_output(['sops', 'decrypt', str(target)], env={**apps.os.environ, 'SOPS_AGE_KEY_FILE': str(self.root / 'age.txt')}, text=True)
        self.assertEqual(yaml.safe_load(decrypted)['repositories']['owner/project']['secrets']['BOT_PRIVATE_KEY'], credentials['pem'])
        with patch.object(apps, 'private_repository'), self.assertRaises(FileExistsError):
            apps.store_credentials(self.vault, 'bot', credentials, 'owner/project', 'BOT')

    def test_app_metadata_does_not_include_credentials(self):
        project = self.root / 'project'
        (project / 'data/apps').mkdir(parents=True)
        shutil.copytree(ROOT / 'template/schemas', project / 'schemas')
        apps.write_yaml(project / '.copier-answers.yml', {'github_owner': 'owner', 'organization': False})
        apps.write_yaml(project / 'data/apps/bot.yaml', {'manifest': {'name': 'bot', 'url': 'https://example.com'}})
        apps.write_yaml(self.vault / 'secrets-config.yaml', {'repository': 'owner/vault', 'age_recipient': 'age1test'})
        credentials = {'id': 123, 'slug': 'bot', 'pem': 'PRIVATE', 'client_secret': 'CLIENT', 'webhook_secret': 'WEBHOOK'}
        with patch.object(apps, 'require'), patch.object(apps, 'private_repository'), patch.object(apps, 'registration_code', return_value='code'), patch.object(apps, 'run', return_value=json.dumps(credentials)), patch.object(apps, 'store_credentials', return_value=Path('encrypted')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                apps.bootstrap_app(project, 'bot', self.vault)
            config = (project / 'data/apps/bot.yaml').read_text()
            for secret in ['PRIVATE', 'CLIENT', 'WEBHOOK']:
                self.assertNotIn(secret, config + output.getvalue())
            self.assertEqual(apps.load(project / 'data/apps/bot.yaml')['app_id'], 123)


class PublisherTests(unittest.TestCase):
    def test_duplicate_secrets_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'secrets').mkdir()
            for name in ['a', 'b']:
                (root / 'secrets' / f'{name}.enc.yaml').touch()
            document = {'repositories': {'owner/project': {'secrets': {'TOKEN': 'value'}}}}
            with patch.object(publisher, 'encrypted_document', return_value=document):
                with self.assertRaisesRegex(ValueError, 'Duplicate'):
                    publisher.read_secrets(root)

    def test_plaintext_inventory_rejected_before_decryption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'app.enc.yaml'
            path.write_text('repositories: {}\n')
            with patch.object(publisher, 'run') as run, self.assertRaisesRegex(ValueError, 'SOPS'):
                publisher.encrypted_document(path)
            run.assert_not_called()

    def test_publishing_token_used_only_for_destinations_and_revoked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = {'repository': 'owner/vault', 'publisher': {'app_id': 1, 'installation_id': 2, 'repository': 'owner/vault', 'private_key_secret': 'PUBLISHER_PRIVATE_KEY'}}
            apps.write_yaml(root / 'secrets-config.yaml', config)
            entries = {('owner/vault', 'PUBLISHER_PRIVATE_KEY'): 'PEM', ('owner/project', 'TOKEN'): 'SECRET-VALUE'}
            with patch.object(publisher, 'read_secrets', return_value=entries), patch.object(publisher, 'installation_token', return_value='EPHEMERAL-TOKEN'), patch.object(publisher, 'run', side_effect=[json.dumps({'isPrivate': True}), '', '']) as run:
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    publisher.publish(root, apply=True)
                self.assertNotIn('SECRET-VALUE', output.getvalue())
                self.assertNotIn('EPHEMERAL-TOKEN', output.getvalue())
                self.assertEqual(run.call_args_list[1].kwargs['content'], 'SECRET-VALUE')
                self.assertEqual(run.call_args_list[1].kwargs['env']['GH_TOKEN'], 'EPHEMERAL-TOKEN')
                self.assertEqual(run.call_args_list[2].args[0], ['gh', 'api', '--method', 'DELETE', '/installation/token'])
