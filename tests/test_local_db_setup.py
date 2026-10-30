import importlib.util
from pathlib import Path

import pytest
from dotenv import dotenv_values


@pytest.fixture
def setup_module(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('local_db_setup', scripts / 'setup_local_db.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_switch_preserves_remote_and_secrets_and_is_idempotent(setup_module, tmp_path):
    path = tmp_path / '.env'
    path.write_text('DATABASE_URL=postgresql://old:secret@remote/db\nANTHROPIC_API_KEY=keep\nEMAIL_SMTP_HOST=hydroxide\nCOMPOSE_PROFILES=custom\n')
    setup_module.configure(path)
    first = dotenv_values(path)
    assert first['PREVIOUS_DATABASE_URL'] == 'postgresql://old:secret@remote/db'
    assert first['ANTHROPIC_API_KEY'] == 'keep'
    assert first['COMPOSE_PROFILES'] == 'custom,proton'
    assert '@postgres:5432/radar' in first['DATABASE_URL']
    assert len(first['POSTGRES_PASSWORD']) >= 32
    assert path.stat().st_mode & 0o777 == 0o600
    setup_module.configure(path)
    assert dotenv_values(path) == first


def test_existing_backup_cannot_be_overwritten(setup_module, tmp_path):
    path = tmp_path / '.env'
    initial = 'DATABASE_URL=postgresql://new:secret@new/db\nPREVIOUS_DATABASE_URL=postgresql://old:secret@old/db\n'
    path.write_text(initial)
    with pytest.raises(ValueError):
        setup_module.configure(path)
    assert path.read_text() == initial


def test_existing_password_is_escaped_and_reused(setup_module, tmp_path):
    path = tmp_path / '.env'
    path.write_text('POSTGRES_PASSWORD="p@ss:/word"\n')
    setup_module.configure(path)
    values = dotenv_values(path)
    assert values['POSTGRES_PASSWORD'] == 'p@ss:/word'
    assert 'p%40ss%3A%2Fword@postgres' in values['DATABASE_URL']
