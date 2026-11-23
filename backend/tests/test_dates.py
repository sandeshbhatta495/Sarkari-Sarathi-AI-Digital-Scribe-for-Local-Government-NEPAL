import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from dates import NEPAL_TZ, DateError, ad_to_bs_nepali, to_nepali_digits, today_bs_nepali  # noqa: E402


class NepaliDigitsTest(unittest.TestCase):
    def test_all_digits(self):
        self.assertEqual(to_nepali_digits("0123456789"), "०१२३४५६७८९")

    def test_other_characters_unchanged(self):
        self.assertEqual(to_nepali_digits("Ward 5, ABC-12"), "Ward ५, ABC-१२")

    def test_number_input(self):
        self.assertEqual(to_nepali_digits(5), "५")


class AdToBsTest(unittest.TestCase):
    def test_today_reference(self):
        # Matches the web calendars checked on 2026-11-23: Mangsir 7, 2083.
        self.assertEqual(ad_to_bs_nepali("2026-11-23"), "२०८३-०८-०७")

    def test_new_year_2080(self):
        self.assertEqual(ad_to_bs_nepali("2023-04-14"), "२०८०-०१-०१")

    def test_new_year_2081(self):
        self.assertEqual(ad_to_bs_nepali("2024-04-13"), "२०८१-०१-०१")

    def test_accepts_date_object(self):
        self.assertEqual(ad_to_bs_nepali(datetime.date(2026, 11, 23)), "२०८३-०८-०७")

    def test_accepts_datetime_object(self):
        self.assertEqual(ad_to_bs_nepali(datetime.datetime(2026, 11, 23, 15, 30)), "२०८३-०८-०७")

    def test_strips_spaces(self):
        self.assertEqual(ad_to_bs_nepali(" 2026-11-23 "), "२०८३-०८-०७")


class BadInputTest(unittest.TestCase):
    def test_bad_values(self):
        for bad in [None, "", "   ", "2026/11/23", "23-11-2026", "2026-1-5",
                    "2026-13-45", "2026-02-30", "abc"]:
            with self.subTest(value=bad):
                with self.assertRaises(DateError):
                    ad_to_bs_nepali(bad)

    def test_out_of_range(self):
        for bad in ["1900-01-01", "2100-01-01"]:
            with self.subTest(value=bad):
                with self.assertRaises(DateError):
                    ad_to_bs_nepali(bad)

    def test_error_names_the_field(self):
        with self.assertRaises(DateError) as ctx:
            ad_to_bs_nepali("", field="dob")
        self.assertIn("dob", str(ctx.exception))

    def test_date_error_is_a_value_error(self):
        self.assertTrue(issubclass(DateError, ValueError))


class TodayTest(unittest.TestCase):
    def test_kathmandu_time_is_used(self):
        utc = datetime.timezone.utc
        # 20:00 UTC on 22 Nov is 01:45 on 23 Nov in Kathmandu.
        after = datetime.datetime(2026, 11, 22, 20, 0, tzinfo=utc)
        self.assertEqual(today_bs_nepali(after), "२०८३-०८-०७")
        # 17:00 UTC on 22 Nov is 22:45 on 22 Nov in Kathmandu.
        before = datetime.datetime(2026, 11, 22, 17, 0, tzinfo=utc)
        self.assertEqual(today_bs_nepali(before), "२०८३-०८-०६")

    def test_naive_datetime_is_kathmandu_time(self):
        self.assertEqual(today_bs_nepali(datetime.datetime(2026, 11, 23, 0, 30)), "२०८३-०८-०७")

    def test_real_clock_matches_conversion(self):
        expected = ad_to_bs_nepali(datetime.datetime.now(NEPAL_TZ).date())
        self.assertEqual(today_bs_nepali(), expected)


if __name__ == "__main__":
    unittest.main()
