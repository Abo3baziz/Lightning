"""Command argument specs shared by area modules (no journal imports)."""


class Command:
    def __init__(self, call, args, *, target=None, creates=None):
        # call: "service.method"; args: name -> spec; target: (table, arg) of the
        # row an existing-record command changes; creates: table of a new row.
        self.call, self.args, self.target, self.creates = call, args, target, creates


TEXT, LONG, DATE, AMOUNT, FLAG = "text", "long", "date", "amount", "flag"


def ref(table):
    return "ref:" + table


def optional(spec):
    return "?" + spec


def choice(*values):
    return "choice:" + "|".join(values)
