"""The services the app's screens use on a journal profile (J6f).

Reads go straight to the confirmed copy. A covered write becomes a command
proposal: on the home it is confirmed at once and returns what the service
returned (or raises its refusal); on any other device it is saved and raises
`PendingOnHome`, which the screen shows as saved-and-waiting. Writes that are
not covered still reach the connection guard and are refused.
"""
from __future__ import annotations

import inspect
from datetime import date
from enum import Enum

from lightning.core.errors import ValidationError
from lightning.core.money import to_decimal

from .codec import origin_id, unpack
from .commands import COMMANDS


class PendingOnHome(Exception):
    """Saved on this device; it takes effect when the home confirms it. Not a
    LightningError, so screens that show refusals inline let it reach the app."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class JournalServices:
    def __init__(self, device):
        self._device = device
        # Module-level workflow commands (a function `call`) are reached by their own screens, not through here.
        self._calls = {entry.call: name for name, entry in COMMANDS.items() if type(entry.call) is str}

    def __getattr__(self, name):
        service = getattr(self._device.c, name)
        if any(call.split(".")[0] == name for call in self._calls):
            return _Service(self, name, service)
        return service

    def _run(self, call, method, args, kwargs):
        action = self._calls[call]
        entry = COMMANDS[action]
        signature = inspect.signature(method)
        bound = signature.bind(*args, **kwargs)
        for name, value in bound.arguments.items():
            if name not in entry.args and value is not signature.parameters[name].default:
                raise ValidationError("This option is not available on a synchronized profile yet.")
        bound.apply_defaults()
        adapter = self._device.adapter
        values = {name: _wire(adapter, spec, bound.arguments.get(name)) for name, spec in entry.args.items()}
        if self._device.home is None:
            self._rehearse(method, args, kwargs)
        wire = self._device.command(action, **values)
        identifier = origin_id(unpack(wire)["body"]["origin"])
        home = self._device.home
        state = home.status(identifier) if home else None
        if state is None or state["status"] in ("staged", "review"):
            raise PendingOnHome("Saved on this device. It takes effect when the home confirms it.")
        if state["status"] == "rejected":
            raise ValidationError(adapter.errors.pop(identifier, "The home could not apply this action."))
        return adapter.results.pop(identifier, None)


    def _rehearse(self, method, args, kwargs):
        """Run the action against this device's confirmed copy and roll it back, so
        a refusal the service would give shows at once, in its own words."""
        try:
            with self._device.store.db.transaction():
                with self._device.adapter.writing():
                    method(*args, **kwargs)
                raise _Rehearsed
        except _Rehearsed:
            pass


class _Rehearsed(Exception):
    pass


class _Service:
    def __init__(self, outer, name, service):
        self._outer, self._name, self._service = outer, name, service

    def __getattr__(self, method):
        target = getattr(self._service, method)
        call = f"{self._name}.{method}"
        if call not in self._outer._calls:
            return target
        def journaled(*args, **kwargs):
            return self._outer._run(call, target, args, kwargs)
        return journaled


def _wire(adapter, spec, value):
    """A service argument as the command carries it (UUIDs, exact text)."""
    if type(spec) is tuple and spec[0] == "list":
        return [_wire(adapter, spec[1], item) for item in value or []]
    if type(spec) is tuple:  # Records may arrive as tuples in the field order.
        return [{name: _wire(adapter, inner, item[name] if isinstance(item, dict) else item[index])
                 for index, (name, inner) in enumerate(spec[1].items())} for item in value or []]
    bare = spec.lstrip("?")
    if value is None:
        return None
    if isinstance(value, Enum):
        value = value.value
    if bare.startswith("ref:"):
        return adapter.uid(bare[len("ref:"):], int(value))
    if bare in ("amount", "rate"):
        return format(to_decimal(value), "f")
    if bare in ("date", "month") and isinstance(value, date):
        return value.isoformat()[:7 if bare == "month" else 10]
    if bare == "int":
        return int(value)
    if bare == "flag":
        return bool(value)
    return value if type(value) is str else str(value)
