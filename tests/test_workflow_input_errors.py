"""New review routes must reject untrusted selections without posting money."""
import pytest
from fastapi.testclient import TestClient
from lightning.core.errors import ValidationError
from lightning.ui.web import create_app


@pytest.mark.parametrize('value', [0, -1, True, 2**63, 'one'])
def test_merge_rejects_invalid_ids_before_database_lookup(c, setup, value):
    with pytest.raises(ValidationError):
        c.transactions.merge_preview(value, 1)


@pytest.mark.parametrize('value', ['not-an-id', str(2**64), '9' * 5000])
def test_merge_form_handles_malformed_ids_without_server_errors(c, setup, value):
    client = TestClient(create_app(c))
    before = c.reporting.account_balance(setup[0]['cib'].id)
    assert client.get('/transactions/merge', params={'keep': value, 'drop': '1'}).status_code == 200
    result = client.post('/transactions/merge', data={'keep_id': value, 'drop_id': '1'})
    assert result.status_code == 400
    assert c.reporting.account_balance(setup[0]['cib'].id) == before
