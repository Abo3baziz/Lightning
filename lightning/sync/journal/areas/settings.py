"""Profile settings: every key is profile-wide and synchronized."""
from .spec import LONG, TEXT, Command

TABLES = ("settings",)
COMMANDS = {
    "settings.set": Command("settings.set", dict(key=TEXT, value=LONG), target=("settings", ("key",))),
    "set_profile_currency": Command("set_profile_currency", dict(code=TEXT)),
}


def refresh(c):
    """A replica applied settings rows: services that cache the profile currency follow."""
    base = c.settings.base_currency
    for service in (c.assets, c.accounts, c.transactions, c.reporting):
        service.base_currency = base
    c.reporting.valuer.base = base
    c.fx.profile_currency = base
