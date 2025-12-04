"""Cryptocurrency & Financial Deals ETL Module

This module aggregates cryptocurrency deals, financial service offers,
investment platforms, trading fee discounts, and fintech promotions.

Usage:
    python src/etl/deals/crypto_finance_deals_etl.py

Output:
    - JSON file: data/deals/crypto_finance_deals.json
    - CSV file: data/deals/crypto_finance_deals.csv
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.etl.base import BaseETL
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger("CryptoFinanceDealsETL")


class CryptoFinanceDealsETL(BaseETL):
    """ETL for cryptocurrency and financial deals."""

    def __init__(self):
        super().__init__("crypto_finance_deals")
        self.sources = {
            "coinbase": {
                "name": "Coinbase",
                "referral_url": "https://www.coinbase.com/join/",
                "category": "crypto_exchange",
            },
            "binance": {
                "name": "Binance",
                "promotions_url": "https://www.binance.com/en/activity",
                "category": "crypto_exchange",
            },
            "robinhood": {
                "name": "Robinhood",
                "promotions_url": "https://robinhood.com/us/en/support/articles/",
                "category": "investment_platform",
            },
            "webull": {
                "name": "Webull",
                "promotions_url": "https://www.webull.com/promotion",
                "category": "investment_platform",
            },
        }

    def extract(self) -> dict[str, Any]:
        """Extract crypto and financial deals from multiple sources."""
        logger.info("Starting crypto & financial deals extraction...")

        all_deals = []

        # Add curated crypto and financial deals
        curated_deals = self._get_curated_crypto_finance_deals()
        all_deals.extend(curated_deals)

        logger.info(f"Total extracted {len(all_deals)} crypto & financial deals")
        return {"deals": all_deals, "total_count": len(all_deals)}

    def _get_curated_crypto_finance_deals(self) -> list[dict[str, Any]]:
        """Get manually curated list of crypto and financial deals."""
        curated = [
            {
                "title": "Coinbase $10 Bitcoin Bonus",
                "description": "Get $10 in Bitcoin when you buy or sell $100 or more of cryptocurrency",
                "url": "https://www.coinbase.com/join/",
                "platform": "Coinbase",
                "category": "crypto_exchange",
                "deal_type": "signup_bonus",
                "original_price": 0,
                "current_price": 0,
                "savings": 10,
                "discount_percentage": 0,
                "bonus_amount": 10,
                "bonus_currency": "BTC",
                "minimum_deposit": 100,
                "service_type": "crypto_exchange",
                "geographic_restriction": "US_only",
                "kyc_required": True,
                "fees": "standard_trading",
                "promotion_duration": "ongoing",
                "risk_level": "medium",
                "regulatory_status": "licensed",
                "tags": ["crypto", "bitcoin", "signup bonus", "exchange"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Binance 0% Trading Fees",
                "description": "Zero trading fees on Bitcoin pairs for new users for 30 days",
                "url": "https://www.binance.com/en/activity",
                "platform": "Binance",
                "category": "crypto_exchange",
                "deal_type": "fee_discount",
                "original_price": 50,  # Estimated fees saved
                "current_price": 0,
                "savings": 50,
                "discount_percentage": 100,
                "bonus_amount": 0,
                "bonus_currency": "none",
                "minimum_deposit": 0,
                "service_type": "crypto_exchange",
                "geographic_restriction": "global",
                "kyc_required": True,
                "fees": "zero_for_30_days",
                "promotion_duration": "30_days",
                "risk_level": "medium",
                "regulatory_status": "varies_by_region",
                "tags": ["crypto", "zero fees", "bitcoin", "trading"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Robinhood Free Stock",
                "description": "Get a free stock worth $5-$200 when you sign up and make your first deposit",
                "url": "https://robinhood.com/",
                "platform": "Robinhood",
                "category": "investment_platform",
                "deal_type": "signup_bonus",
                "original_price": 0,
                "current_price": 0,
                "savings": 100,  # Average value
                "discount_percentage": 0,
                "bonus_amount": 100,
                "bonus_currency": "USD_stock",
                "minimum_deposit": 1,
                "service_type": "stock_trading",
                "geographic_restriction": "US_only",
                "kyc_required": True,
                "fees": "commission_free",
                "promotion_duration": "ongoing",
                "risk_level": "medium",
                "regulatory_status": "SIPC_insured",
                "tags": ["stocks", "free stock", "commission free", "investing"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Webull 12 Free Stocks",
                "description": "Get up to 12 free stocks worth up to $30,600 with qualifying deposits",
                "url": "https://www.webull.com/promotion",
                "platform": "Webull",
                "category": "investment_platform",
                "deal_type": "deposit_bonus",
                "original_price": 0,
                "current_price": 0,
                "savings": 1000,  # Conservative estimate
                "discount_percentage": 0,
                "bonus_amount": 30600,
                "bonus_currency": "USD_stock",
                "minimum_deposit": 500,
                "service_type": "stock_trading",
                "geographic_restriction": "US_only",
                "kyc_required": True,
                "fees": "commission_free",
                "promotion_duration": "limited_time",
                "risk_level": "medium",
                "regulatory_status": "SIPC_insured",
                "tags": ["stocks", "free stocks", "deposit bonus", "trading"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "BlockFi Interest Account",
                "description": "Earn up to 8.6% APY on cryptocurrency deposits with no minimums",
                "url": "https://blockfi.com/",
                "platform": "BlockFi",
                "category": "crypto_lending",
                "deal_type": "high_yield",
                "original_price": 10,  # Traditional savings rate
                "current_price": 860,  # 8.6% APY on $10k
                "savings": 850,
                "discount_percentage": 8500,
                "bonus_amount": 0,
                "bonus_currency": "none",
                "minimum_deposit": 0,
                "service_type": "crypto_lending",
                "geographic_restriction": "US_eligible",
                "kyc_required": True,
                "fees": "no_management_fees",
                "promotion_duration": "ongoing",
                "risk_level": "high",
                "regulatory_status": "state_licensed",
                "tags": ["crypto", "high yield", "passive income", "lending"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Celsius Network Rewards",
                "description": "Earn weekly rewards on crypto holdings with up to 17% APY",
                "url": "https://celsius.network/",
                "platform": "Celsius",
                "category": "crypto_lending",
                "deal_type": "high_yield",
                "original_price": 10,
                "current_price": 1700,  # 17% APY on $10k
                "savings": 1690,
                "discount_percentage": 16900,
                "bonus_amount": 0,
                "bonus_currency": "none",
                "minimum_deposit": 0,
                "service_type": "crypto_lending",
                "geographic_restriction": "global_except_us",
                "kyc_required": True,
                "fees": "no_fees",
                "promotion_duration": "ongoing",
                "risk_level": "high",
                "regulatory_status": "varies_by_region",
                "tags": ["crypto", "weekly rewards", "high apy", "defi"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Credit Karma Free Credit Monitoring",
                "description": "Free credit scores, reports, and monitoring with personalized recommendations",
                "url": "https://www.creditkarma.com/",
                "platform": "Credit Karma",
                "category": "financial_tools",
                "deal_type": "free_service",
                "original_price": 180,  # Annual credit monitoring cost
                "current_price": 0,
                "savings": 180,
                "discount_percentage": 100,
                "bonus_amount": 0,
                "bonus_currency": "none",
                "minimum_deposit": 0,
                "service_type": "credit_monitoring",
                "geographic_restriction": "US_canada",
                "kyc_required": True,
                "fees": "completely_free",
                "promotion_duration": "permanent",
                "risk_level": "low",
                "regulatory_status": "consumer_protection",
                "tags": ["credit score", "free", "monitoring", "financial health"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Mint Personal Finance Manager",
                "description": "Free comprehensive budgeting and financial tracking with bill reminders",
                "url": "https://www.mint.com/",
                "platform": "Mint (Intuit)",
                "category": "financial_tools",
                "deal_type": "free_service",
                "original_price": 120,  # Equivalent paid service
                "current_price": 0,
                "savings": 120,
                "discount_percentage": 100,
                "bonus_amount": 0,
                "bonus_currency": "none",
                "minimum_deposit": 0,
                "service_type": "budgeting",
                "geographic_restriction": "US_canada",
                "kyc_required": False,
                "fees": "completely_free",
                "promotion_duration": "permanent",
                "risk_level": "low",
                "regulatory_status": "intuit_backed",
                "tags": ["budgeting", "free", "personal finance", "bill tracking"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Acorns Spare Change Investing",
                "description": "Round up purchases and invest spare change automatically, $5 signup bonus",
                "url": "https://www.acorns.com/",
                "platform": "Acorns",
                "category": "micro_investing",
                "deal_type": "signup_bonus",
                "original_price": 36,  # Annual fee
                "current_price": 31,
                "savings": 5,
                "discount_percentage": 14,
                "bonus_amount": 5,
                "bonus_currency": "USD",
                "minimum_deposit": 5,
                "service_type": "micro_investing",
                "geographic_restriction": "US_only",
                "kyc_required": True,
                "fees": "monthly_subscription",
                "promotion_duration": "limited_time",
                "risk_level": "low",
                "regulatory_status": "SEC_registered",
                "tags": ["micro investing", "round ups", "automatic", "spare change"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "SoFi Money Account Bonus",
                "description": "Get $25 when you open a SoFi Money account and deposit $500",
                "url": "https://www.sofi.com/money/",
                "platform": "SoFi",
                "category": "banking",
                "deal_type": "signup_bonus",
                "original_price": 0,
                "current_price": 0,
                "savings": 25,
                "discount_percentage": 0,
                "bonus_amount": 25,
                "bonus_currency": "USD",
                "minimum_deposit": 500,
                "service_type": "digital_banking",
                "geographic_restriction": "US_only",
                "kyc_required": True,
                "fees": "no_account_fees",
                "promotion_duration": "limited_time",
                "risk_level": "low",
                "regulatory_status": "FDIC_insured",
                "tags": ["banking", "signup bonus", "no fees", "fintech"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "M1 Finance Free Investing",
                "description": "Commission-free investing with automated rebalancing and fractional shares",
                "url": "https://www.m1finance.com/",
                "platform": "M1 Finance",
                "category": "investment_platform",
                "deal_type": "free_service",
                "original_price": 100,  # Annual advisory fees saved
                "current_price": 0,
                "savings": 100,
                "discount_percentage": 100,
                "bonus_amount": 0,
                "bonus_currency": "none",
                "minimum_deposit": 100,
                "service_type": "robo_advisor",
                "geographic_restriction": "US_only",
                "kyc_required": True,
                "fees": "commission_free",
                "promotion_duration": "permanent",
                "risk_level": "medium",
                "regulatory_status": "SIPC_insured",
                "tags": ["investing", "automated", "fractional shares", "free"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Crypto.com Visa Card Rewards",
                "description": "Earn up to 8% cashback in cryptocurrency with Crypto.com Visa cards",
                "url": "https://crypto.com/cards",
                "platform": "Crypto.com",
                "category": "crypto_rewards",
                "deal_type": "cashback_rewards",
                "original_price": 0,
                "current_price": 0,
                "savings": 800,  # 8% on $10k spending
                "discount_percentage": 8,
                "bonus_amount": 0,
                "bonus_currency": "CRO",
                "minimum_deposit": 0,
                "service_type": "crypto_card",
                "geographic_restriction": "global",
                "kyc_required": True,
                "fees": "varies_by_tier",
                "promotion_duration": "ongoing",
                "risk_level": "medium",
                "regulatory_status": "varies_by_region",
                "tags": ["crypto rewards", "visa card", "cashback", "staking"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Gemini Dollar-Cost Averaging",
                "description": "Automated recurring crypto purchases with reduced fees",
                "url": "https://www.gemini.com/dollar-cost-averaging",
                "platform": "Gemini",
                "category": "crypto_exchange",
                "deal_type": "fee_discount",
                "original_price": 25,  # Standard trading fees
                "current_price": 10,
                "savings": 15,
                "discount_percentage": 60,
                "bonus_amount": 0,
                "bonus_currency": "none",
                "minimum_deposit": 25,
                "service_type": "crypto_automation",
                "geographic_restriction": "US_select_international",
                "kyc_required": True,
                "fees": "reduced_for_automation",
                "promotion_duration": "ongoing",
                "risk_level": "medium",
                "regulatory_status": "regulated_exchange",
                "tags": ["crypto", "automated", "dca", "reduced fees"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "YNAB Free Trial + Student Discount",
                "description": "You Need A Budget - 34-day free trial plus student discount",
                "url": "https://www.youneedabudget.com/",
                "platform": "YNAB",
                "category": "financial_tools",
                "deal_type": "free_trial",
                "original_price": 98,  # Annual subscription
                "current_price": 0,
                "savings": 98,
                "discount_percentage": 100,
                "bonus_amount": 0,
                "bonus_currency": "none",
                "minimum_deposit": 0,
                "service_type": "budgeting_software",
                "geographic_restriction": "global",
                "kyc_required": False,
                "fees": "subscription_after_trial",
                "promotion_duration": "34_days",
                "risk_level": "none",
                "regulatory_status": "private_software",
                "tags": [
                    "budgeting",
                    "free trial",
                    "student discount",
                    "financial planning",
                ],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
        ]

        logger.info(f"Added {len(curated)} curated crypto & financial deals")
        return curated

    def transform(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Transform crypto and financial deals data."""
        logger.info("Starting crypto & financial deals transformation...")

        deals = raw_data.get("deals", [])
        transformed_deals = []

        for deal in deals:
            try:
                # Clean up title
                title = deal["title"].strip()
                if len(title) > 150:
                    title = title[:147] + "..."

                # Calculate finance value score
                finance_score = self._calculate_finance_value_score(deal)

                # Determine risk assessment
                risk_assessment = self._determine_risk_assessment(deal)

                transformed_deal = {
                    "title": title,
                    "description": deal.get("description", "")[:400],
                    "url": deal["url"],
                    "platform": deal["platform"],
                    "category": deal["category"],
                    "deal_type": deal["deal_type"],
                    "original_price": deal.get("original_price", 0),
                    "current_price": deal.get("current_price", 0),
                    "savings": deal.get("savings", 0),
                    "discount_percentage": deal.get("discount_percentage", 0),
                    "finance_score": finance_score,
                    "risk_assessment": risk_assessment,
                    "bonus_amount": deal.get("bonus_amount", 0),
                    "bonus_currency": deal.get("bonus_currency", "none"),
                    "minimum_deposit": deal.get("minimum_deposit", 0),
                    "service_type": deal.get("service_type", "unknown"),
                    "geographic_restriction": deal.get("geographic_restriction", "unknown"),
                    "kyc_required": deal.get("kyc_required", True),
                    "fees": deal.get("fees", "unknown"),
                    "promotion_duration": deal.get("promotion_duration", "unknown"),
                    "risk_level": deal.get("risk_level", "medium"),
                    "regulatory_status": deal.get("regulatory_status", "unknown"),
                    "tags": deal.get("tags", []),
                    "created_date": deal.get("created_date"),
                    "fetched_at": deal["fetched_at"],
                    "source": deal["source"],
                }

                transformed_deals.append(transformed_deal)

            except Exception as e:
                logger.warning(f"Error transforming crypto/finance deal: {e}")
                continue

        # Sort by finance score and bonus amount
        transformed_deals.sort(key=lambda x: (x["finance_score"], x["bonus_amount"]), reverse=True)

        logger.info(f"Transformed {len(transformed_deals)} crypto & financial deals")
        return transformed_deals

    def _calculate_finance_value_score(self, deal: dict[str, Any]) -> float:
        """Calculate finance value score for ranking deals."""
        score = 0.0

        # Platform trust weight
        platform = deal.get("platform", "").lower()
        if any(name in platform for name in ["coinbase", "sofi", "robinhood"]):
            score += 5.0  # Highly regulated platforms
        elif any(name in platform for name in ["webull", "m1 finance", "acorns"]):
            score += 4.5  # Well-established fintech
        elif any(name in platform for name in ["binance", "crypto.com", "gemini"]):
            score += 4.0  # Major crypto platforms
        elif any(name in platform for name in ["mint", "credit karma", "ynab"]):
            score += 3.5  # Utility services
        else:
            score += 2.0

        # Deal type weight
        deal_type = deal.get("deal_type", "")
        if deal_type in ["signup_bonus", "deposit_bonus"]:
            score += 5.0  # Direct monetary benefit
        elif deal_type == "high_yield":
            score += 4.5  # Ongoing returns
        elif deal_type == "free_service":
            score += 4.0  # Value through savings
        elif deal_type in ["fee_discount", "cashback_rewards"]:
            score += 3.5  # Usage-based benefits
        elif deal_type == "free_trial":
            score += 2.0  # Temporary benefit

        # Regulatory status bonus
        regulatory = deal.get("regulatory_status", "").lower()
        if any(keyword in regulatory for keyword in ["fdic", "sipc", "sec"]):
            score += 2.0  # US regulated
        elif "licensed" in regulatory:
            score += 1.5
        elif "regulated" in regulatory:
            score += 1.0

        # Risk level adjustment
        risk_level = deal.get("risk_level", "medium").lower()
        if risk_level == "low":
            score += 1.5
        elif risk_level == "medium":
            score += 1.0
        elif risk_level == "high":
            score += 0.5
        elif risk_level == "none":
            score += 2.0

        # Bonus amount consideration
        bonus = deal.get("bonus_amount", 0)
        if bonus > 1000:
            score += 3.0
        elif bonus > 100:
            score += 2.0
        elif bonus > 25:
            score += 1.0
        elif bonus > 0:
            score += 0.5

        # Savings consideration
        savings = deal.get("savings", 0)
        if savings > 500:
            score += 2.0
        elif savings > 100:
            score += 1.5
        elif savings > 50:
            score += 1.0

        # Minimum deposit adjustment (lower is better)
        min_deposit = deal.get("minimum_deposit", 0)
        if min_deposit == 0:
            score += 1.0
        elif min_deposit <= 100:
            score += 0.5

        return round(score, 2)

    def _determine_risk_assessment(self, deal: dict[str, Any]) -> str:
        """Determine overall risk assessment of the financial deal."""
        regulatory = deal.get("regulatory_status", "").lower()
        risk_level = deal.get("risk_level", "medium").lower()
        platform = deal.get("platform", "").lower()
        category = deal.get("category", "").lower()

        # Very low risk indicators
        if any(keyword in regulatory for keyword in ["fdic", "sipc"]) and risk_level == "low":
            return "very_low"

        # Low risk indicators
        if any(keyword in regulatory for keyword in ["sec", "regulated"]) and risk_level in ["low", "none"] or (any(name in platform for name in ["mint", "credit karma"]) and "tools" in category):
            return "low"

        # Medium risk indicators
        if "licensed" in regulatory and risk_level == "medium" or any(name in platform for name in ["coinbase", "robinhood", "sofi"]):
            return "medium"

        # High risk indicators
        if risk_level == "high" or "crypto_lending" in category:
            return "high"
        elif "varies_by_region" in regulatory:
            return "medium_high"

        # Default
        return "medium"

    def load(self, transformed_data: list[dict[str, Any]]) -> bool:
        """Load transformed crypto and financial deals data to files."""
        try:
            # Ensure output directory exists
            output_dir = os.path.join(get_project_root(), "data", "deals")
            ensure_directories([output_dir])

            # Save as JSON
            json_path = os.path.join(output_dir, "crypto_finance_deals.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)

            # Save as CSV
            if transformed_data:
                csv_path = os.path.join(output_dir, "crypto_finance_deals.csv")
                import pandas as pd

                df = pd.DataFrame(transformed_data)
                df.to_csv(csv_path, index=False, encoding="utf-8")

            logger.info(f"Successfully saved {len(transformed_data)} crypto & financial deals to {output_dir}")
            return True

        except Exception as e:
            logger.error(f"Error saving crypto & financial deals data: {e}")
            return False


def main():
    """Main function to run the Crypto & Financial Deals ETL."""
    etl = CryptoFinanceDealsETL()
    success = etl.run()

    if success:
        logger.info("Crypto & Financial Deals ETL completed successfully")
    else:
        logger.error("Crypto & Financial Deals ETL failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
