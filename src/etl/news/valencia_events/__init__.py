"""Valencia events: the sources, one module each, and the helpers they share.

- :mod:`sources` lists every agenda (:data:`sources.SOURCES`); each source
  module reads one public page set and returns raw records.
- :mod:`records` is the raw record shape; :mod:`normalise` turns raw records
  into what the tab and the API read; :mod:`stamps` remembers when an event was
  first detected; :mod:`categories` and :mod:`zones` hold the vocabularies.
- :mod:`http`, :mod:`dates`, :mod:`jsonld` and :mod:`dom` are the plumbing.

The composer — the registered script — is ``src/etl/news/valencia_events_etl.py``.
"""
