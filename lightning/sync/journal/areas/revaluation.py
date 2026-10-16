"""Month-end FX revaluation: run on the home as a command; replicas get its exact rows."""
from .spec import Command

TABLES = ("reevaluation_periods", "reevaluation_entries", "reevaluation_account_posts", "reevaluation_suppressed_accounts")
COMMANDS = {"reevaluations.process_due": Command("reevaluations.process_due", {})}
