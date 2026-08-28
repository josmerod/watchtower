"""Spanish Public Aid ETL module."""

from .bdns_convocatorias_etl import BdnsConvocatoriasETL
from .spanish_public_aid_etl import SpanishPublicAidETL

__all__ = ["BdnsConvocatoriasETL", "SpanishPublicAidETL"]
