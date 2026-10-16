"""Command proposals (J6c): any covered service action, journaled generically.

A command names an allowlisted service method and its typed arguments, with
records referenced by UUID. The home runs that same method inside confirmation
and publishes the touched rows as exact effects; writes outside the
synchronized tables are refused, so coverage grows by adding tables. A command
on an existing record carries that row's fingerprint hash as its precondition:
if another device changed the row since, the command waits for review.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from lightning.core.errors import ValidationError

from .codec import JournalError, canonical, fields, uuid


from .areas.spec import AMOUNT, DATE, FLAG, LONG, TEXT, Command, choice, optional, ref  # noqa: F401


def _registry():
    from .areas import AREAS
    commands = {}
    for area in AREAS:
        for name, entry in area.COMMANDS.items():
            if name in commands:
                raise JournalError(f"Command {name} is registered twice")
            commands[name] = entry
    return commands


COMMANDS = _registry()
KINDS = {"command." + name: 1 for name in COMMANDS}


def command(kind):
    entry = COMMANDS.get(kind[len("command."):]) if kind.startswith("command.") else None
    if entry is None:
        raise ValidationError("This action is not covered by the journal yet")
    return entry


def validate(kind, groups):
    """Exact argument shape; services still decide every business rule."""
    entry = command(kind)
    fields(groups, ("args",))
    args = groups["args"]
    fields(args, entry.args)
    for name, spec in entry.args.items():
        value = args[name]
        if spec.startswith("?"):
            if value is None:
                continue
            spec = spec[1:]
        if spec.startswith("ref:"):
            uuid(value)
        elif spec.startswith("choice:"):
            if value not in spec[len("choice:"):].split("|"):
                raise ValidationError(f"Choose a supported {name.replace('_', ' ')}")
        elif spec == FLAG:
            if type(value) is not bool:
                raise ValidationError("Choose yes or no")
        elif type(value) is not str or len(value) > (4000 if spec == LONG else 200):
            raise ValidationError("Text is missing or too long")
        elif spec == DATE:
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError
            except ValueError as error:
                raise ValidationError("Enter a valid date") from error
        elif spec == AMOUNT:
            try:
                amount = Decimal(value)
                if not amount.is_finite() or abs(amount) > Decimal("9000000000") or amount.as_tuple().exponent < -2:
                    raise ValueError
            except (InvalidOperation, ValueError) as error:
                raise ValidationError("Enter an amount up to 9 billion with at most two decimal places") from error


def target_slot(kind, groups):
    entry = command(kind)
    if entry.target is None:
        return None
    table, name = entry.target
    return table + ":" + canonical(groups["args"][name]).decode()


def run(adapter, kind, record, groups):
    """Inside the adapter's writing(): call the service with local ids."""
    entry = command(kind)
    values = {}
    for name, spec in entry.args.items():
        value = groups["args"][name]
        bare = spec.lstrip("?")
        values[name] = adapter.local(bare[len("ref:"):], value) if bare.startswith("ref:") and value is not None else value
    service, method = entry.call.split(".")
    result = getattr(getattr(adapter.c, service), method)(**values)
    if entry.creates:
        if getattr(result, "id", None) is None:
            raise JournalError("The service did not return the created record")
        adapter.bind(entry.creates, record, result.id)
    return result
