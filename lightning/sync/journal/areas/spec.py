"""Command argument specs shared by area modules (no journal imports)."""


class Command:
    def __init__(self, call, args, *, target=None, creates=None, adapt=None):
        # call: "service.method"; args: name -> spec; target: (table, arg) of the
        # row an existing-record command changes; creates: table of a new row;
        # adapt: optional function reshaping mapped arguments for the service.
        self.call, self.args, self.target, self.creates, self.adapt = call, args, target, creates, adapt


TEXT, LONG, DATE, MONTH, AMOUNT, RATE, INT, FLAG = "text", "long", "date", "month", "amount", "rate", "int", "flag"


def ref(table):
    return "ref:" + table


def optional(spec):
    return "?" + spec


def choice(*values):
    return "choice:" + "|".join(values)


def listof(spec):
    """A list (at most 200) of single values, e.g. selected rows."""
    return ("list", spec)


def items(**fields):
    """A list (at most 50) of records with these fields, e.g. split lines."""
    return ("items", fields)
