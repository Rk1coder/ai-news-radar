import importlib.util
from pathlib import Path
import stat


def test_setup_preserves_unrelated_secrets_and_keeps_daily_sending_disabled(tmp_path):
    spec=importlib.util.spec_from_file_location('connect_proton',Path(__file__).parents[1]/'scripts/connect_proton.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config=tmp_path/'.env'
    config.write_text('# Existing settings\nDATABASE_URL=keep-existing-value\nEMAIL_ENABLED=true\nEMAIL_RECIPIENTS=old@example.com\nEMAIL_RECIPIENTS=duplicate@example.com\n')
    module.save_settings(config,{'EMAIL_ENABLED':'false','EMAIL_RECIPIENTS':'test@example.com','EMAIL_SMTP_PASSWORD':'bridge-test-value'})
    text=config.read_text()
    assert 'DATABASE_URL=keep-existing-value' in text
    assert 'EMAIL_ENABLED="false"' in text
    assert text.count('EMAIL_RECIPIENTS=')==1
    assert stat.S_IMODE(config.stat().st_mode)==0o600
    assert not list(tmp_path.glob('.proton-*'))


def test_explicit_test_recipient_overrides_unrelated_exported_mail_settings(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('connect_proton',Path(__file__).parents[1]/'scripts/connect_proton.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls=[]
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module.sys,'argv',['connect_proton.py','--account','sender@proton.me','--recipient','chosen@example.com','--send-test'])
    monkeypatch.setattr(module.sys.stdin,'isatty',lambda:True)
    monkeypatch.setattr(module.getpass,'getpass',lambda prompt:'bridge-test-value')
    monkeypatch.setenv('EMAIL_RECIPIENTS','wrong@example.com')
    monkeypatch.setenv('EMAIL_SMTP_USER','wrong-sender@example.com')
    monkeypatch.setattr(module.subprocess,'run',lambda *args,**kwargs:calls.append((args,kwargs)))
    module.main()
    env=calls[-1][1].get('env',{})
    assert env['EMAIL_RECIPIENTS']=='chosen@example.com'
    assert env['EMAIL_SMTP_USER']=='sender@proton.me'
    assert env['EMAIL_SMTP_PASSWORD']=='bridge-test-value'
    assert 'bridge-test-value' not in str(calls[-1][0])
