"""Check the dedicated account's subscriptions before a free-only deployment.

Reads Cloudflare billing metadata; never creates/changes subscriptions. Missing
permission, unknown plans and paid/trial subscriptions block deployment.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tomllib
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class FreePlanRequired(ValueError):
    pass


def check_config(path):
    with Path(path).open("rb") as handle:
        config = tomllib.load(handle)
    allowed = {"name", "main", "compatibility_date", "workers_dev", "vars", "durable_objects", "migrations", "routes"}
    if set(config) - allowed:
        raise FreePlanRequired("Unsupported bindings/settings: free-only deployment requires review")
    if config.get("vars", {}).get("DEPLOYMENT_POLICY") != "free-only" or config.get("workers_dev") is not False:
        raise FreePlanRequired("Keep the explicit free-only policy and private custom-domain deployment")
    if config.get("durable_objects") != {"bindings": [{"name": "PROFILES", "class_name": "ProfileMailbox"}]}:
        raise FreePlanRequired("Only the journal SQLite Durable Object binding is permitted")
    if config.get("migrations") != [{"tag": "v1", "new_sqlite_classes": ["ProfileMailbox"]}]:
        raise FreePlanRequired("Only the reviewed SQLite Durable Object migration is permitted")
    if any(route.get("custom_domain") is not True for route in config.get("routes", [])):
        raise FreePlanRequired("Use a custom-domain endpoint with no origin bypass")
    return config


def check_subscriptions(document):
    if type(document) is not dict or document.get("success") is not True or type(document.get("result")) is not list:
        raise FreePlanRequired("Cannot verify account subscriptions; deployment blocked")
    pagination = document.get("result_info", {})
    if pagination.get("total_pages", 1) != 1:
        raise FreePlanRequired("Incomplete subscription inventory; deployment blocked")
    # Workers Free is the default when no account subscription exists. For a
    # listed subscription, accept only explicit, zero-price free plans. In
    # particular, a zero base-price R2/pay-as-you-go plan is NOT a free-only plan.
    for subscription in document["result"]:
        if type(subscription) is not dict:
            raise FreePlanRequired("Unrecognized subscription record")
        plan = subscription.get("rate_plan", {})
        if (type(plan) is not dict or plan.get("id") not in {"free", "workers_free"}
                or type(subscription.get("price")) not in (int, float) or subscription["price"] != 0
                or subscription.get("state") not in {"Provisioned", "Paid"}
                or plan.get("is_contract") is True or plan.get("externally_managed") is True):
            raise FreePlanRequired("Paid, metered, trial or unrecognized subscription found; use a dedicated Workers Free account")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise FreePlanRequired("Unexpected API redirect; deployment blocked")


def inspect_account(account, token):
    if not re.fullmatch(r"[0-9a-f]{32}", account or "") or not token:
        raise FreePlanRequired("Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in the environment")
    request = Request(f"https://api.cloudflare.com/client/v4/accounts/{account}/subscriptions",
                      headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
    try:
        with build_opener(NoRedirect()).open(request, timeout=15) as response:
            body = response.read(1024 * 1024 + 1)
        if len(body) > 1024 * 1024:
            raise FreePlanRequired("Unexpected subscription response size")
        document = json.loads(body)
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        raise FreePlanRequired("Cannot read account subscriptions; check API access and billing-read permission") from None
    check_subscriptions(document)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("wrangler.toml"))
    parser.add_argument("--deploy", action="store_true")
    args = parser.parse_args()
    try:
        config = check_config(args.config)
        inspect_account(os.environ.get("CLOUDFLARE_ACCOUNT_ID"), os.environ.get("CLOUDFLARE_API_TOKEN"))
        if args.deploy:
            if not config.get("routes"):
                raise FreePlanRequired("Configure the reviewed private custom-domain route before deployment")
            subprocess.run(["npx", "--no-install", "wrangler", "deploy", "--config", str(args.config.resolve())],
                           cwd=args.config.resolve().parent, stdin=subprocess.DEVNULL, check=True)
        print("Free-only preflight passed; no subscription was created or changed.")
    except FreePlanRequired as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
