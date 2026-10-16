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


from .areas.spec import AMOUNT, DATE, FLAG, INT, LONG, MONTH, RATE, TEXT, Command, choice, items, listof, optional, ref  # noqa: F401


def _registry():
    from .areas import AREAS
    commands = {}
    for area in AREAS:
        for name, entry in area.COMMANDS.items():
            if name in commands or any(other.call == entry.call for other in commands.values()):
                raise JournalError(f"Command {name} is registered twice")  # The proxy maps each call to one command.
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
    _check(entry.args, groups["args"])


def _check(specs, args):
    fields(args, specs)
    for name, spec in specs.items():
        _value(name, spec, args[name])


def _value(name, spec, value):
    if type(spec) is tuple:  # ("items", {field: spec}) records, or ("list", spec) values.
        if type(value) is not list or len(value) > (50 if spec[0] == "items" else 200):
            raise ValidationError("Too many lines")
        for item in value:
            _check(spec[1], item) if spec[0] == "items" else _value(name, spec[1], item)
        return
    if spec.startswith("?"):
        if value is None:
            return
        spec = spec[1:]
    if spec.startswith("ref:"):
        uuid(value)
    elif spec.startswith("choice:"):
        if value not in spec[len("choice:"):].split("|"):
            raise ValidationError(f"Choose a supported {name.replace('_', ' ')}")
    elif spec == FLAG:
        if type(value) is not bool:
            raise ValidationError("Choose yes or no")
    elif spec == INT:
        if type(value) is not int or not -(2**53) < value < 2**53:
            raise ValidationError("Enter a whole number")
    elif type(value) is not str or len(value) > (4000 if spec == LONG else 200):
        raise ValidationError("Text is missing or too long")
    elif spec == DATE:
        try:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError
        except ValueError as error:
            raise ValidationError("Enter a valid date") from error
    elif spec == MONTH:
        try:
            if len(value) != 7 or date.fromisoformat(value + "-01").isoformat()[:7] != value:
                raise ValueError
        except ValueError as error:
            raise ValidationError("Enter a valid month") from error
    elif spec in (AMOUNT, RATE):
        try:
            amount = Decimal(value)
            if (not amount.is_finite() or abs(amount) > Decimal("9000000000")
                    or amount.as_tuple().exponent < (-6 if spec == RATE else -2)):
                raise ValueError
        except (InvalidOperation, ValueError) as error:
            raise ValidationError("Enter an amount up to 9 billion with at most two decimal places") from error


def target_slot(kind, groups):
    entry = command(kind)
    if entry.target is None:
        return None
    table, name = entry.target
    # An integer-id row is named by its UUID; a keyed row (a setting) by its key columns.
    identity = [groups["args"][column] for column in name] if type(name) is tuple else groups["args"][name]
    return table + ":" + canonical(identity).decode()


def _local(adapter, spec, value):
    if type(spec) is tuple and spec[0] == "list":
        return [_local(adapter, spec[1], item) for item in value]
    if type(spec) is tuple:
        return [{name: _local(adapter, inner, item[name]) for name, inner in spec[1].items()} for item in value]
    bare = spec.lstrip("?")
    return adapter.local(bare[len("ref:"):], value) if bare.startswith("ref:") and value is not None else value


def run(adapter, kind, record, groups):
    """Inside the adapter's writing(): call the service with local ids."""
    entry = command(kind)
    values = {name: _local(adapter, spec, groups["args"][name]) for name, spec in entry.args.items()}
    if entry.adapt is not None:
        values = entry.adapt(values)  # Shape lists into what the service signature takes.
    if callable(entry.call):  # A module-level workflow taking the container.
        result = entry.call(adapter.c, **values)
    else:
        owner = adapter.c
        for part in entry.call.split("."):  # "service.method", or a container method
            owner = getattr(owner, part)
        try:
            result = owner(**values)
        except JournalError:
            raise
        except ValueError as error:  # Some services refuse with a plain ValueError.
            raise ValidationError(str(error)) from error
    if entry.creates:
        created = result if type(result) is int else result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        if type(created) is not int:
            raise JournalError("The service did not return the created record")
        adapter.bind(entry.creates, record, created)
    return result
