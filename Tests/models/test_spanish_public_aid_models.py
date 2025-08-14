"""Tests for Spanish Public Aid models."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.models.spanish_public_aid import (
    SpanishPublicAidModel,
    AidScope,
    AidType,
    AidCategory,
    AidStatus,
    BeneficiaryType,
    PaymentType,
    GeographicScopeModel,
    AmountModel,
    RequirementModel,
    DocumentModel,
    ContactInfoModel,
    AidStatisticsModel,
    AidSearchFilter,
)


class TestSpanishPublicAidModels:
    """Test cases for Spanish Public Aid models."""

    def test_geographic_scope_model(self):
        """Test GeographicScopeModel creation and validation."""
        scope = GeographicScopeModel(
            scope=AidScope.AUTONOMOUS_COMMUNITY,
            autonomous_community="Comunidad Valenciana",
            municipality="Valencia",
        )

        assert scope.scope == AidScope.AUTONOMOUS_COMMUNITY
        assert scope.country == "España"  # Default value
        assert scope.autonomous_community == "Comunidad Valenciana"
        assert scope.municipality == "Valencia"

    def test_amount_model_validation(self):
        """Test AmountModel validation."""
        # Valid amount
        amount = AmountModel(
            min_amount=Decimal("100.00"),
            max_amount=Decimal("1000.00"),
            payment_type=PaymentType.MONTHLY,
        )

        assert amount.min_amount == Decimal("100.00")
        assert amount.max_amount == Decimal("1000.00")
        assert amount.currency == "EUR"  # Default

        # Test negative amount validation
        with pytest.raises(ValueError):
            AmountModel(
                min_amount=Decimal("-100.00"), payment_type=PaymentType.LUMP_SUM
            )

    def test_requirement_model(self):
        """Test RequirementModel creation."""
        requirement = RequirementModel(
            title="Requisito de edad",
            description="Tener entre 18 y 35 años",
            is_mandatory=True,
            documentation_needed=["DNI", "Certificado de empadronamiento"],
        )

        assert requirement.title == "Requisito de edad"
        assert requirement.is_mandatory is True
        assert len(requirement.documentation_needed) == 2

    def test_document_model(self):
        """Test DocumentModel creation."""
        document = DocumentModel(
            name="DNI",
            description="Documento Nacional de Identidad",
            is_mandatory=True,
            format="PDF",
            max_size_mb=5.0,
        )

        assert document.name == "DNI"
        assert document.is_mandatory is True
        assert document.max_size_mb == 5.0

    def test_contact_info_model(self):
        """Test ContactInfoModel creation."""
        contact = ContactInfoModel(
            office_name="Oficina de Ayudas",
            phone="96 123 45 67",
            email="ayudas@gva.es",
            address="Calle Ejemplo, 123, Valencia",
        )

        assert contact.office_name == "Oficina de Ayudas"
        assert contact.phone == "96 123 45 67"
        assert contact.email == "ayudas@gva.es"

    def test_spanish_public_aid_model_creation(self):
        """Test SpanishPublicAidModel creation with required fields."""
        scope = GeographicScopeModel(scope=AidScope.NATIONAL)
        amount = AmountModel(payment_type=PaymentType.LUMP_SUM)

        aid = SpanishPublicAidModel(
            title="Ayuda para vivienda",
            description="Ayuda económica para el alquiler de vivienda",
            aid_type=AidType.GRANT,
            category=AidCategory.HOUSING,
            scope=scope,
            organizing_entity="Ministerio de Vivienda",
            beneficiary_type=BeneficiaryType.INDIVIDUAL,
            amount=amount,
            status=AidStatus.OPEN,
            source_url="https://example.com/aid",
            source_name="Example Source",
        )

        assert aid.title == "Ayuda para vivienda"
        assert aid.aid_type == AidType.GRANT
        assert aid.category == AidCategory.HOUSING
        assert aid.status == AidStatus.OPEN
        assert aid.beneficiary_type == BeneficiaryType.INDIVIDUAL

    def test_spanish_public_aid_model_properties(self):
        """Test SpanishPublicAidModel computed properties."""
        scope = GeographicScopeModel(scope=AidScope.NATIONAL)
        amount = AmountModel(payment_type=PaymentType.LUMP_SUM)

        # Create aid with closing date in future
        future_date = datetime.utcnow() + timedelta(days=5)

        aid = SpanishPublicAidModel(
            title="Test Aid",
            description="Test description",
            aid_type=AidType.GRANT,
            category=AidCategory.HOUSING,
            scope=scope,
            organizing_entity="Test Entity",
            beneficiary_type=BeneficiaryType.INDIVIDUAL,
            amount=amount,
            status=AidStatus.OPEN,
            source_url="https://example.com/aid",
            source_name="Test Source",
            closing_date=future_date,
        )

        # Test is_active property
        assert aid.is_active is True

        # Test days_until_closing property
        days_left = aid.days_until_closing
        assert days_left is not None
        assert days_left >= 4  # Should be around 5 days

        # Test is_urgent property (closing within 7 days)
        assert aid.is_urgent is True

    def test_spanish_public_aid_model_inactive_status(self):
        """Test aid with inactive status."""
        scope = GeographicScopeModel(scope=AidScope.NATIONAL)
        amount = AmountModel(payment_type=PaymentType.LUMP_SUM)

        aid = SpanishPublicAidModel(
            title="Closed Aid",
            description="Test description",
            aid_type=AidType.GRANT,
            category=AidCategory.HOUSING,
            scope=scope,
            organizing_entity="Test Entity",
            beneficiary_type=BeneficiaryType.INDIVIDUAL,
            amount=amount,
            status=AidStatus.CLOSED,  # Closed status
            source_url="https://example.com/aid",
            source_name="Test Source",
        )

        assert aid.is_active is False

    def test_spanish_public_aid_model_past_closing_date(self):
        """Test aid with past closing date."""
        scope = GeographicScopeModel(scope=AidScope.NATIONAL)
        amount = AmountModel(payment_type=PaymentType.LUMP_SUM)

        # Create aid with closing date in past
        past_date = datetime.utcnow() - timedelta(days=5)

        aid = SpanishPublicAidModel(
            title="Expired Aid",
            description="Test description",
            aid_type=AidType.GRANT,
            category=AidCategory.HOUSING,
            scope=scope,
            organizing_entity="Test Entity",
            beneficiary_type=BeneficiaryType.INDIVIDUAL,
            amount=amount,
            status=AidStatus.OPEN,
            source_url="https://example.com/aid",
            source_name="Test Source",
            closing_date=past_date,
        )

        assert aid.is_active is False
        assert aid.days_until_closing == 0

    def test_data_quality_score_validation(self):
        """Test data quality score validation."""
        scope = GeographicScopeModel(scope=AidScope.NATIONAL)
        amount = AmountModel(payment_type=PaymentType.LUMP_SUM)

        # Valid quality score
        aid = SpanishPublicAidModel(
            title="Test Aid",
            description="Test description",
            aid_type=AidType.GRANT,
            category=AidCategory.HOUSING,
            scope=scope,
            organizing_entity="Test Entity",
            beneficiary_type=BeneficiaryType.INDIVIDUAL,
            amount=amount,
            status=AidStatus.OPEN,
            source_url="https://example.com/aid",
            source_name="Test Source",
            data_quality_score=0.8,
        )

        assert aid.data_quality_score == 0.8

        # Invalid quality score (> 1.0)
        with pytest.raises(ValueError):
            SpanishPublicAidModel(
                title="Test Aid",
                description="Test description",
                aid_type=AidType.GRANT,
                category=AidCategory.HOUSING,
                scope=scope,
                organizing_entity="Test Entity",
                beneficiary_type=BeneficiaryType.INDIVIDUAL,
                amount=amount,
                status=AidStatus.OPEN,
                source_url="https://example.com/aid",
                source_name="Test Source",
                data_quality_score=1.5,
            )

    def test_aid_statistics_model(self):
        """Test AidStatisticsModel creation."""
        stats = AidStatisticsModel(
            total_aids=100,
            active_aids=75,
            by_category={"vivienda": 30, "empleo": 25, "educacion": 20},
            by_scope={"nacional": 40, "autonomica": 35, "local": 25},
            by_status={"abierta": 75, "cerrada": 20, "en_evaluacion": 5},
            total_budget=Decimal("1000000.00"),
            average_amount=Decimal("10000.00"),
            closing_soon=10,
        )

        assert stats.total_aids == 100
        assert stats.active_aids == 75
        assert stats.by_category["vivienda"] == 30
        assert stats.total_budget == Decimal("1000000.00")
        assert stats.closing_soon == 10

    def test_aid_search_filter(self):
        """Test AidSearchFilter model."""
        search_filter = AidSearchFilter(
            keywords=["vivienda", "joven"],
            categories=[AidCategory.HOUSING, AidCategory.YOUTH],
            scopes=[AidScope.AUTONOMOUS_COMMUNITY],
            statuses=[AidStatus.OPEN],
            min_amount=Decimal("500.00"),
            max_amount=Decimal("2000.00"),
            autonomous_community="Comunidad Valenciana",
            beneficiary_types=[BeneficiaryType.INDIVIDUAL],
            closing_within_days=30,
            only_active=True,
        )

        assert len(search_filter.keywords) == 2
        assert AidCategory.HOUSING in search_filter.categories
        assert search_filter.min_amount == Decimal("500.00")
        assert search_filter.only_active is True

    def test_model_serialization(self):
        """Test model serialization to dict."""
        scope = GeographicScopeModel(scope=AidScope.NATIONAL)
        amount = AmountModel(payment_type=PaymentType.LUMP_SUM)

        aid = SpanishPublicAidModel(
            title="Test Aid",
            description="Test description",
            aid_type=AidType.GRANT,
            category=AidCategory.HOUSING,
            scope=scope,
            organizing_entity="Test Entity",
            beneficiary_type=BeneficiaryType.INDIVIDUAL,
            amount=amount,
            status=AidStatus.OPEN,
            source_url="https://example.com/aid",
            source_name="Test Source",
        )

        # Test model_dump
        data = aid.model_dump()
        assert isinstance(data, dict)
        assert data["title"] == "Test Aid"
        assert data["aid_type"] == AidType.GRANT.value
        assert "scope" in data
        assert "amount" in data

    def test_model_json_serialization(self):
        """Test model JSON serialization."""
        scope = GeographicScopeModel(scope=AidScope.NATIONAL)
        amount = AmountModel(payment_type=PaymentType.LUMP_SUM)

        aid = SpanishPublicAidModel(
            title="Test Aid",
            description="Test description",
            aid_type=AidType.GRANT,
            category=AidCategory.HOUSING,
            scope=scope,
            organizing_entity="Test Entity",
            beneficiary_type=BeneficiaryType.INDIVIDUAL,
            amount=amount,
            status=AidStatus.OPEN,
            source_url="https://example.com/aid",
            source_name="Test Source",
        )

        # Test model_dump_json
        json_str = aid.model_dump_json()
        assert isinstance(json_str, str)
        assert '"title": "Test Aid"' in json_str

    def test_enum_values(self):
        """Test enum values are correct."""
        assert AidScope.NATIONAL == "nacional"
        assert AidScope.AUTONOMOUS_COMMUNITY == "autonomica"
        assert AidScope.LOCAL == "local"

        assert AidType.GRANT == "ayuda"
        assert AidType.SUBSIDY == "subvencion"
        assert AidType.SCHOLARSHIP == "beca"

        assert AidCategory.HOUSING == "vivienda"
        assert AidCategory.EMPLOYMENT == "empleo"
        assert AidCategory.YOUTH == "juventud"

        assert AidStatus.OPEN == "abierta"
        assert AidStatus.CLOSED == "cerrada"

        assert BeneficiaryType.INDIVIDUAL == "persona_fisica"
        assert BeneficiaryType.COMPANY == "empresa"

        assert PaymentType.LUMP_SUM == "pago_unico"
        assert PaymentType.MONTHLY == "mensual"


if __name__ == "__main__":
    pytest.main([__file__])
