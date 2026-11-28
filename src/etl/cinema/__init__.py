"""Cinema listings: what is on at the cinemas of València.

One module per source — ``exhicine``, ``babel``, ``filmoteca`` and
``filmaffinity`` — each turning listing pages into session dictionaries over
the helpers of ``common``; ``cinema_sessions_etl`` composes them and writes
``data/cinema/``.
"""
