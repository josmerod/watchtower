# test_deal_aggregator.py
import unittest
from unittest import mock # For mocking the fetcher modules

# Modules to be tested
import deal_aggregator
from deal_fetchers import chollometro_fetcher, producthunt_fetcher, limitedtimed_fetcher

# Sample deal data for testing
sample_deal_electronics = {'title': 'Laptop', 'category': 'electronics', 'location': None, 'discounted_price': 500, 'currency': 'EUR'}
sample_deal_travel_valencia = {'title': 'Trip to Valencia', 'category': 'travel', 'location': 'Valencia, Spain', 'discounted_price': 200, 'currency': 'EUR'}
sample_deal_travel_madrid = {'title': 'Trip to Madrid', 'category': 'travel', 'location': 'Madrid, Spain', 'discounted_price': 180, 'currency': 'EUR'}
sample_deal_travel_unknown_spain = {'title': 'Trip somewhere in Spain', 'category': 'travel', 'location': 'Somewhere, Spain', 'discounted_price': 150, 'currency': 'EUR'}
sample_deal_food_valencia = {'title': 'Restaurant Valencia', 'category': 'food', 'location': 'Valencia, Spain', 'discounted_price': 50, 'currency': 'EUR'}
sample_deal_travel_france = {'title': 'Trip to France', 'category': 'travel', 'location': 'Paris, France', 'discounted_price': 300, 'currency': 'EUR'}


class TestDealAggregator(unittest.TestCase):

    @mock.patch.object(chollometro_fetcher, 'fetch_chollometro_deals')
    @mock.patch.object(producthunt_fetcher, 'fetch_producthunt_deals')
    @mock.patch.object(limitedtimed_fetcher, 'fetch_limitedtimed_deals')
    def test_aggregation_no_filters(self, mock_ltd_fetch, mock_ph_fetch, mock_chollo_fetch):
        # Setup mock return values
        mock_chollo_fetch.return_value = [sample_deal_electronics, sample_deal_travel_valencia]
        mock_ph_fetch.return_value = [sample_deal_travel_madrid]
        mock_ltd_fetch.return_value = []

        deals = deal_aggregator.get_all_deals(apply_filters=False)

        self.assertEqual(len(deals), 3)
        self.assertIn(sample_deal_electronics, deals)
        self.assertIn(sample_deal_travel_valencia, deals)
        self.assertIn(sample_deal_travel_madrid, deals)
        mock_chollo_fetch.assert_called_once()
        mock_ph_fetch.assert_called_once()
        mock_ltd_fetch.assert_called_once()

    @mock.patch.object(chollometro_fetcher, 'fetch_chollometro_deals')
    @mock.patch.object(producthunt_fetcher, 'fetch_producthunt_deals')
    @mock.patch.object(limitedtimed_fetcher, 'fetch_limitedtimed_deals')
    def test_filter_travel_valencia_focus(self, mock_ltd_fetch, mock_ph_fetch, mock_chollo_fetch):
        mock_chollo_fetch.return_value = [sample_deal_electronics, sample_deal_travel_valencia, sample_deal_food_valencia]
        mock_ph_fetch.return_value = [sample_deal_travel_madrid, sample_deal_travel_france]
        mock_ltd_fetch.return_value = []

        # Default filter is Valencia, Spain
        deals = deal_aggregator.get_all_deals(apply_filters=True, travel_location_filter="Valencia, Spain")

        self.assertEqual(len(deals), 4) # Valencia travel + Madrid travel (Spain) + electronics + food Valencia
        self.assertIn(sample_deal_travel_valencia, deals) # Matches Valencia
        self.assertIn(sample_deal_travel_madrid, deals) # Matches Spain (broader)
        self.assertIn(sample_deal_electronics, deals) # Non-travel included
        self.assertIn(sample_deal_food_valencia, deals) # Non-travel included
        self.assertNotIn(sample_deal_travel_france, deals) # France travel excluded

    @mock.patch.object(chollometro_fetcher, 'fetch_chollometro_deals')
    @mock.patch.object(producthunt_fetcher, 'fetch_producthunt_deals')
    @mock.patch.object(limitedtimed_fetcher, 'fetch_limitedtimed_deals')
    def test_filter_travel_spain_general_focus(self, mock_ltd_fetch, mock_ph_fetch, mock_chollo_fetch):
        mock_chollo_fetch.return_value = [sample_deal_electronics, sample_deal_travel_valencia, sample_deal_travel_unknown_spain]
        mock_ph_fetch.return_value = [sample_deal_travel_madrid, sample_deal_travel_france]
        mock_ltd_fetch.return_value = []

        deals = deal_aggregator.get_all_deals(apply_filters=True, travel_location_filter="Spain")

        # Should include all Spanish travel deals and non-travel deals
        self.assertEqual(len(deals), 4)
        self.assertIn(sample_deal_travel_valencia, deals)
        self.assertIn(sample_deal_travel_madrid, deals)
        self.assertIn(sample_deal_travel_unknown_spain, deals)
        self.assertIn(sample_deal_electronics, deals)
        self.assertNotIn(sample_deal_travel_france, deals)

    @mock.patch.object(chollometro_fetcher, 'fetch_chollometro_deals')
    @mock.patch.object(producthunt_fetcher, 'fetch_producthunt_deals')
    @mock.patch.object(limitedtimed_fetcher, 'fetch_limitedtimed_deals')
    def test_no_deals_returned(self, mock_ltd_fetch, mock_ph_fetch, mock_chollo_fetch):
        mock_chollo_fetch.return_value = []
        mock_ph_fetch.return_value = []
        mock_ltd_fetch.return_value = []

        deals_filtered = deal_aggregator.get_all_deals(apply_filters=True)
        deals_unfiltered = deal_aggregator.get_all_deals(apply_filters=False)

        self.assertEqual(len(deals_filtered), 0)
        self.assertEqual(len(deals_unfiltered), 0)

    @mock.patch.object(chollometro_fetcher, 'fetch_chollometro_deals', side_effect=Exception("API down"))
    @mock.patch.object(producthunt_fetcher, 'fetch_producthunt_deals')
    @mock.patch.object(limitedtimed_fetcher, 'fetch_limitedtimed_deals')
    def test_fetcher_exception_handling(self, mock_ltd_fetch, mock_ph_fetch, mock_chollo_fetch_exception):
        # mock_chollo_fetch_exception is already configured by side_effect
        mock_ph_fetch.return_value = [sample_deal_electronics]
        mock_ltd_fetch.return_value = []

        # We expect it to print an error but not crash, and return deals from other sources
        # Suppress print for cleaner test output if possible, or just check len
        deals = deal_aggregator.get_all_deals(apply_filters=False)

        self.assertEqual(len(deals), 1)
        self.assertIn(sample_deal_electronics, deals)
        mock_chollo_fetch_exception.assert_called_once()
        mock_ph_fetch.assert_called_once()
        mock_ltd_fetch.assert_called_once()

    @mock.patch.object(chollometro_fetcher, 'fetch_chollometro_deals')
    def test_location_case_insensitivity(self, mock_chollo_fetch):
        deal_travel_valencia_lower = {'title': 'Trip to Valencia', 'category': 'travel', 'location': 'valencia, spain', 'discounted_price': 200, 'currency': 'EUR'}
        mock_chollo_fetch.return_value = [deal_travel_valencia_lower, sample_deal_electronics]

        # producthunt_fetcher and limitedtimed_fetcher will be implicitly mocked if not specified in decorator for the method
        # For safety, let's mock them to return empty lists
        with mock.patch.object(producthunt_fetcher, 'fetch_producthunt_deals', return_value=[]), \
             mock.patch.object(limitedtimed_fetcher, 'fetch_limitedtimed_deals', return_value=[]):
            deals = deal_aggregator.get_all_deals(apply_filters=True, travel_location_filter="Valencia, Spain") # Filter uses "Valencia, Spain"

            self.assertEqual(len(deals), 2) # travel deal + electronics
            self.assertIn(deal_travel_valencia_lower, deals)
            self.assertIn(sample_deal_electronics, deals)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
