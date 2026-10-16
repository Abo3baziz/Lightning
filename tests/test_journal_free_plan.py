"""Deployment refuses paid, metered, unknown or unverifiable account plans."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("journal_deploy_free", ROOT / "cloudflare/journal/deploy_free.py")
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


def test_only_sqlite_bindings_are_configured():
    config = deploy.check_config(ROOT / "cloudflare/journal/wrangler.toml")
    assert set(config["durable_objects"]["bindings"][0]) == {"name","class_name"}


@pytest.mark.parametrize("plan", ["workers_paid","workers_standard","r2","unknown"])
def test_paid_or_metered_plan_is_refused_even_if_base_price_is_zero(plan):
    with pytest.raises(deploy.FreePlanRequired):
        deploy.check_subscriptions(dict(success=True,result=[dict(price=0,state="Provisioned",rate_plan=dict(id=plan))]))


@pytest.mark.parametrize("document", [{},dict(success=False,result=[]),dict(success=True,result={},),
    dict(success=True,result=[],result_info=dict(total_pages=2)),
    dict(success=True,result=[dict(price=0,state="Trial",rate_plan=dict(id="free"))])])
def test_unverified_or_trial_inventory_never_authorizes_deployment(document):
    with pytest.raises(deploy.FreePlanRequired):
        deploy.check_subscriptions(document)


def test_default_free_account_and_explicit_zero_price_free_plan_are_accepted():
    deploy.check_subscriptions(dict(success=True,result=[]))
    deploy.check_subscriptions(dict(success=True,result=[dict(price=0,state="Provisioned",rate_plan=dict(id="free"))]))


def test_accidental_storage_binding_is_refused(tmp_path):
    config = (ROOT / "cloudflare/journal/wrangler.toml").read_text()
    path = tmp_path / "wrangler.toml"
    path.write_text(config + '\n[[r2_buckets]]\nbinding="ACCIDENTAL"\nbucket_name="not-permitted"\n')
    with pytest.raises(deploy.FreePlanRequired):
        deploy.check_config(path)
