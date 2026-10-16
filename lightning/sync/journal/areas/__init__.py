"""Journal areas: each module lists its synchronized tables and its commands.

Add an area by writing its module and naming it here. A service action that
writes any table outside every enabled area's TABLES is refused by the home.
"""
from . import cash, currency, deposits, investments, master, people, physical, plans, settings

AREAS = (cash, currency, master, people, plans, settings, investments, deposits, physical)
