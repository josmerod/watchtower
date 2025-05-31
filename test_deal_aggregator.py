# test_deal_aggregator.py
import unittest
from unittest import mock # For mocking the fetcher modules

# Modules to be tested
import deal_aggregator
from deal_fetchers import chollometro_fetcher, limitedtimed_fetcher # producthunt_fetcher is the old one

# Sample deal data for testing
sample_deal_electronics = {'title': 'Laptop', 'category': 'electronics', 'location': None, 'discounted_price': 500, 'currency': 'EUR'}
sample_deal_travel_valencia = {'title': 'Trip to Valencia', 'category': 'travel', 'location': 'Valencia, Spain', 'discounted_price': 200, 'currency': 'EUR'}
sample_deal_travel_madrid = {'title': 'Trip to Madrid', 'category': 'travel', 'location': 'Madrid, Spain', 'discounted_price': 180, 'currency': 'EUR'}
sample_deal_travel_unknown_spain = {'title': 'Trip somewhere in Spain', 'category': 'travel', 'location': 'Somewhere, Spain', 'discounted_price': 150, 'currency': 'EUR'}
sample_deal_food_valencia = {'title': 'Restaurant Valencia', 'category': 'food', 'location': 'Valencia, Spain', 'discounted_price': 50, 'currency': 'EUR'}
sample_deal_travel_france = {'title': 'Trip to France', 'category': 'travel', 'location': 'Paris, France', 'discounted_price': 300, 'currency': 'EUR'}

# New sample deals for additional fetchers
sample_deal_producthunt = {'title': 'PH Deal', 'category': 'software', 'location': None, 'source_platform': 'ProductHunt', 'discounted_price': 0}
sample_deal_appsumo = {'title': 'AppSumo LTD', 'category': 'software', 'location': None, 'source_platform': 'AppSumo', 'discounted_price': 49}
sample_deal_stacksocial = {'title': 'StackSocial Course', 'category': 'online course', 'location': None, 'source_platform': 'StackSocial', 'discounted_price': 19}


class TestDealAggregator(unittest.TestCase):

    @mock.patch('deal_aggregator.fetch_stacksocial_deals')
    @mock.patch('deal_aggregator.fetch_appsumo_deals')
    @mock.patch('deal_aggregator.fetch_producthunt_deals')
    @mock.patch.object(limitedtimed_fetcher, 'fetch_limitedtimed_deals')
    @mock.patch.object(chollometro_fetcher, 'fetch_chollometro_deals')
    def test_aggregation_no_filters(self, mock_chollo_fetch, mock_ltd_fetch,
                                     mock_ph_deals_fetch, mock_as_fetch, mock_ss_fetch):
        # Setup mock return values
        mock_chollo_fetch.return_value = [sample_deal_electronics, sample_deal_travel_valencia]
        mock_ltd_fetch.return_value = [] # No limited time deals for this test
        mock_ph_deals_fetch.return_value = [sample_deal_producthunt]
        mock_as_fetch.return_value = [sample_deal_appsumo]
        mock_ss_fetch.return_value = [sample_deal_stacksocial]

        deals = deal_aggregator.get_all_deals(apply_filters=False)

        expected_deal_count = 2 + 0 + 1 + 1 + 1 # Chollometro + LTD + PH + AppSumo + StackSocial
        self.assertEqual(len(deals), expected_deal_count)
        self.assertIn(sample_deal_electronics, deals)
        self.assertIn(sample_deal_travel_valencia, deals)
        self.assertIn(sample_deal_producthunt, deals)
        self.assertIn(sample_deal_appsumo, deals)
        self.assertIn(sample_deal_stacksocial, deals)

        mock_chollo_fetch.assert_called_once()
        mock_ltd_fetch.assert_called_once()
        mock_ph_deals_fetch.assert_called_once()
        mock_as_fetch.assert_called_once()
        mock_ss_fetch.assert_called_once()

    @mock.patch('deal_aggregator.fetch_stacksocial_deals')
    @mock.patch('deal_aggregator.fetch_appsumo_deals')
    @mock.patch('deal_aggregator.fetch_producthunt_deals')
    @mock.patch.object(limitedtimed_fetcher, 'fetch_limitedtimed_deals')
    @mock.patch.object(chollometro_fetcher, 'fetch_chollometro_deals')
    def test_filter_travel_valencia_focus(self, mock_chollo_fetch, mock_ltd_fetch,
                                           mock_ph_deals_fetch, mock_as_fetch, mock_ss_fetch):
        mock_chollo_fetch.return_value = [sample_deal_electronics, sample_deal_travel_valencia, sample_deal_food_valencia]
        mock_ltd_fetch.return_value = []
        # Product Hunt (old) used to return a travel deal for Madrid, new one returns non-travel
        mock_ph_deals_fetch.return_value = [sample_deal_producthunt] # Non-travel
        mock_as_fetch.return_value = [sample_deal_appsumo]     # Non-travel
        mock_ss_fetch.return_value = [sample_deal_stacksocial, sample_deal_travel_france] # Non-travel and one non-Spain travel

        deals = deal_aggregator.get_all_deals(apply_filters=True, travel_location_filter="Valencia, Spain")

        # Expected:
        # Valencia travel (1 from Chollometro: sample_deal_travel_valencia)
        # Non-travel deals (1 electronics, 1 food_valencia from Chollometro; 1 PH; 1 AppSumo; 1 StackSocial non-travel)
        # Excluded: sample_deal_travel_france (StackSocial)
        # Total = 1 (Valencia travel) + 3 (Chollometro non-travel) + 1 (PH) + 1 (AS) + 1 (SS non-travel) = 7
        # Let's re-evaluate the logic for Chollometro: sample_deal_electronics, sample_deal_food_valencia are non-travel.
        # sample_deal_travel_valencia is travel and matches.
        # sample_deal_producthunt, sample_deal_appsumo, sample_deal_stacksocial are non-travel.
        # sample_deal_travel_france is travel but does not match Valencia/Spain.

        self.assertIn(sample_deal_travel_valencia, deals) # Matches Valencia
        self.assertIn(sample_deal_electronics, deals)    # Non-travel included
        self.assertIn(sample_deal_food_valencia, deals)  # Non-travel included
        self.assertIn(sample_deal_producthunt, deals)    # Non-travel PH included
        self.assertIn(sample_deal_appsumo, deals)        # Non-travel AppSumo included
        self.assertIn(sample_deal_stacksocial, deals)    # Non-travel StackSocial included

        self.assertNotIn(sample_deal_travel_france, deals) # France travel excluded

        # Count: 1 (Valencia) + 2 (Chollo non-travel) + 1 (PH) + 1 (AS) + 1 (SS non-travel) = 6
        self.assertEqual(len(deals), 6)


    @mock.patch('deal_aggregator.fetch_stacksocial_deals')
    @mock.patch('deal_aggregator.fetch_appsumo_deals')
    @mock.patch('deal_aggregator.fetch_producthunt_deals')
    @mock.patch.object(limitedtimed_fetcher, 'fetch_limitedtimed_deals')
    @mock.patch.object(chollometro_fetcher, 'fetch_chollometro_deals')
    def test_filter_travel_spain_general_focus(self, mock_chollo_fetch, mock_ltd_fetch,
                                                mock_ph_deals_fetch, mock_as_fetch, mock_ss_fetch):
        mock_chollo_fetch.return_value = [sample_deal_electronics, sample_deal_travel_valencia, sample_deal_travel_unknown_spain, sample_deal_travel_madrid]
        mock_ltd_fetch.return_value = []
        mock_ph_deals_fetch.return_value = [sample_deal_producthunt] # Non-travel
        mock_as_fetch.return_value = [sample_deal_appsumo]     # Non-travel
        mock_ss_fetch.return_value = [sample_deal_stacksocial, sample_deal_travel_france] # Non-travel and one non-Spain travel

        deals = deal_aggregator.get_all_deals(apply_filters=True, travel_location_filter="Spain")

        # Expected: All Spanish travel deals + all non-travel deals
        # Chollometro: Valencia, Unknown Spain, Madrid (3 travel) + electronics (1 non-travel)
        # PH: 1 non-travel
        # AppSumo: 1 non-travel
        # StackSocial: 1 non-travel
        # Excluded: sample_deal_travel_france
        self.assertIn(sample_deal_travel_valencia, deals)
        self.assertIn(sample_deal_travel_madrid, deals)
        self.assertIn(sample_deal_travel_unknown_spain, deals)
        self.assertIn(sample_deal_electronics, deals)
        self.assertIn(sample_deal_producthunt, deals)
        self.assertIn(sample_deal_appsumo, deals)
        self.assertIn(sample_deal_stacksocial, deals)
        self.assertNotIn(sample_deal_travel_france, deals)

        self.assertEqual(len(deals), 7) # 3 Chollo travel + 1 Chollo non-travel + 1 PH + 1 AS + 1 SS

    @mock.patch('deal_aggregator.fetch_stacksocial_deals')
    @mock.patch('deal_aggregator.fetch_appsumo_deals')
    @mock.patch('deal_aggregator.fetch_producthunt_deals')
    @mock.patch.object(limitedtimed_fetcher, 'fetch_limitedtimed_deals')
    @mock.patch.object(chollometro_fetcher, 'fetch_chollometro_deals')
    def test_no_deals_returned(self, mock_chollo_fetch, mock_ltd_fetch,
                               mock_ph_deals_fetch, mock_as_fetch, mock_ss_fetch):
        mock_chollo_fetch.return_value = []
        mock_ltd_fetch.return_value = []
        mock_ph_deals_fetch.return_value = []
        mock_as_fetch.return_value = []
        mock_ss_fetch.return_value = []

        deals_filtered = deal_aggregator.get_all_deals(apply_filters=True)
        deals_unfiltered = deal_aggregator.get_all_deals(apply_filters=False)

        self.assertEqual(len(deals_filtered), 0)
        self.assertEqual(len(deals_unfiltered), 0)

    @mock.patch('deal_aggregator.fetch_stacksocial_deals')
    @mock.patch('deal_aggregator.fetch_appsumo_deals', side_effect=Exception("AppSumo API down"))
    @mock.patch('deal_aggregator.fetch_producthunt_deals')
    @mock.patch.object(limitedtimed_fetcher, 'fetch_limitedtimed_deals')
    @mock.patch.object(chollometro_fetcher, 'fetch_chollometro_deals')
    def test_fetcher_exception_handling_new_source(self, mock_chollo_fetch, mock_ltd_fetch,
                                               mock_ph_deals_fetch, mock_as_fetch_exception, mock_ss_fetch):
        mock_chollo_fetch.return_value = [sample_deal_electronics]
        mock_ltd_fetch.return_value = []
        mock_ph_deals_fetch.return_value = [sample_deal_producthunt]
        # mock_as_fetch_exception is configured by side_effect
        mock_ss_fetch.return_value = [sample_deal_stacksocial]

        deals = deal_aggregator.get_all_deals(apply_filters=False)

        # Expected: Chollometro (1) + PH (1) + StackSocial (1) = 3
        self.assertEqual(len(deals), 3)
        self.assertIn(sample_deal_electronics, deals)
        self.assertIn(sample_deal_producthunt, deals)
        self.assertIn(sample_deal_stacksocial, deals)
        self.assertNotIn(sample_deal_appsumo, deals)

        mock_chollo_fetch.assert_called_once()
        mock_ltd_fetch.assert_called_once()
        mock_ph_deals_fetch.assert_called_once()
        mock_as_fetch_exception.assert_called_once()
        mock_ss_fetch.assert_called_once()

    @mock.patch('deal_aggregator.fetch_producthunt_deals') # Only need this for the specific test variant
    @mock.patch.object(limitedtimed_fetcher, 'fetch_limitedtimed_deals', return_value=[]) # Mock others to return empty
    @mock.patch.object(chollometro_fetcher, 'fetch_chollometro_deals')
    @mock.patch('deal_aggregator.fetch_appsumo_deals', return_value=[])
    @mock.patch('deal_aggregator.fetch_stacksocial_deals', return_value=[])
    def test_location_case_insensitivity(self, mock_ss_fetch_empty, mock_as_fetch_empty,
                                         mock_chollo_fetch, mock_ltd_fetch_empty, mock_ph_fetch_empty):
        deal_travel_valencia_lower = {'title': 'Trip to Valencia', 'category': 'travel', 'location': 'valencia, spain', 'discounted_price': 200, 'currency': 'EUR'}
        mock_chollo_fetch.return_value = [deal_travel_valencia_lower, sample_deal_electronics]

        # All other fetchers (PH, AppSumo, StackSocial, LTD) are mocked to return empty lists for this specific test.
        # This ensures we are testing the Chollometro data and filter interaction correctly.
        deals = deal_aggregator.get_all_deals(apply_filters=True, travel_location_filter="Valencia, Spain")

        self.assertEqual(len(deals), 2) # travel deal + electronics
        self.assertIn(deal_travel_valencia_lower, deals)
        self.assertIn(sample_deal_electronics, deals)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
