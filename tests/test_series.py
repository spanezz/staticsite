from __future__ import annotations

import datetime
from unittest import TestCase

from . import utils as test_utils


def dt(*args):
    return str(datetime.datetime(*args))


class TestSeries(test_utils.MockSiteTestMixin, TestCase):
    def test_site(self):
        files = {
            "series.taxonomy": "",
            "seriesa1.md": {
                "series": "seriesa",
                "title": "Series A",
                "date": dt(2016, 1, 1),
            },
            "seriesa2.md": {"date": dt(2016, 1, 2), "series": "seriesa", "title": "A2"},
            "seriesa3.md": {
                "date": dt(2016, 1, 3),
                "series": "seriesa",
                "title": "A3",
                "series_title": "Series A part Two",
            },
            "seriesa4.md": {"date": dt(2016, 1, 4), "series": "seriesa", "title": "A4"},
            "seriesb1.md": {
                "date": dt(2016, 1, 1),
                "series": "seriesb",
                "title": "Series B Intro",
                "series_title": "Series B",
            },
            "seriesb2.md": {"date": dt(2016, 1, 2), "series": "seriesb", "title": "B2"},
            "seriesc1.md": {
                "date": dt(2016, 1, 1),
                "title": "Series C",
                "series": "seriesc",
            },
            "noseries.md": {"date": dt(2016, 1, 1), "title": "Other things"},
        }

        with self.site(files) as mocksite:
            seriesa1 = mocksite.page("seriesa1")
            seriesa2 = mocksite.page("seriesa2")
            seriesa3 = mocksite.page("seriesa3")
            seriesa4 = mocksite.page("seriesa4")
            seriesb1 = mocksite.page("seriesb1")
            seriesb2 = mocksite.page("seriesb2")
            seriesc1 = mocksite.page("seriesc1")
            noseries = mocksite.page("noseries")
            series = mocksite.page("series")

            # Check that series have been built (check in tags)
            self.assertIn("seriesa", series.categories)
            self.assertIn("seriesb", series.categories)
            self.assertIn("seriesc", series.categories)
            self.assertEqual(len(series.categories), 3)

            # Check the contents of series (check in tags)
            self.assertEqual(
                series.categories["seriesa"].pages,
                [seriesa1, seriesa2, seriesa3, seriesa4],
            )
            self.assertEqual(series.categories["seriesb"].pages, [seriesb1, seriesb2])
            self.assertEqual(series.categories["seriesc"].pages, [seriesc1])

            # Check computed series metadata
            self.assertEqual(
                series.categories["seriesa"].series_info,
                {
                    "pages": [seriesa1, seriesa2, seriesa3, seriesa4],
                    "length": 4,
                    "first": seriesa1,
                    "last": seriesa4,
                    "title": "Series A",
                },
            )

            s = series.categories["seriesa"].sequence(seriesa1)
            self.assertEqual(s["title"], "Series A")
            self.assertEqual(s["prev"], None)
            self.assertEqual(s["next"], seriesa2)
            self.assertEqual(s["first"], seriesa1)
            self.assertEqual(s["last"], seriesa4)
            self.assertEqual(s["index"], 1)
            self.assertEqual(s["length"], 4)

            s = series.categories["seriesa"].sequence(seriesa2)
            self.assertEqual(s["title"], "Series A")
            self.assertEqual(s["prev"], seriesa1)
            self.assertEqual(s["next"], seriesa3)
            self.assertEqual(s["first"], seriesa1)
            self.assertEqual(s["last"], seriesa4)
            self.assertEqual(s["index"], 2)
            self.assertEqual(s["length"], 4)

            s = series.categories["seriesa"].sequence(seriesa3)
            self.assertEqual(s["title"], "Series A part Two")
            self.assertEqual(s["prev"], seriesa2)
            self.assertEqual(s["next"], seriesa4)
            self.assertEqual(s["first"], seriesa1)
            self.assertEqual(s["last"], seriesa4)
            self.assertEqual(s["index"], 3)
            self.assertEqual(s["length"], 4)

            s = series.categories["seriesa"].sequence(seriesa4)
            self.assertEqual(s["title"], "Series A part Two")
            self.assertEqual(s["prev"], seriesa3)
            self.assertEqual(s["next"], None)
            self.assertEqual(s["first"], seriesa1)
            self.assertEqual(s["last"], seriesa4)
            self.assertEqual(s["index"], 4)
            self.assertEqual(s["length"], 4)

            self.assertEqual(
                series.categories["seriesb"].series_info,
                {
                    "pages": [seriesb1, seriesb2],
                    "length": 2,
                    "first": seriesb1,
                    "last": seriesb2,
                    "title": "Series B",
                },
            )

            s = series.categories["seriesb"].sequence(seriesb1)
            self.assertEqual(s["title"], "Series B")
            self.assertEqual(s["prev"], None)
            self.assertEqual(s["next"], seriesb2)
            self.assertEqual(s["first"], seriesb1)
            self.assertEqual(s["last"], seriesb2)
            self.assertEqual(s["index"], 1)
            self.assertEqual(s["length"], 2)

            s = series.categories["seriesb"].sequence(seriesb2)
            self.assertEqual(s["title"], "Series B")
            self.assertEqual(s["prev"], seriesb1)
            self.assertEqual(s["next"], None)
            self.assertEqual(s["first"], seriesb1)
            self.assertEqual(s["last"], seriesb2)
            self.assertEqual(s["index"], 2)
            self.assertEqual(s["length"], 2)

            s = series.categories["seriesc"].sequence(seriesc1)
            self.assertEqual(s["title"], "Series C")
            self.assertEqual(s["prev"], None)
            self.assertEqual(s["next"], None)
            self.assertEqual(s["first"], seriesc1)
            self.assertEqual(s["last"], seriesc1)
            self.assertEqual(s["index"], 1)
            self.assertEqual(s["length"], 1)

            self.assertIsNone(series.categories["seriesa"].sequence(noseries))
            self.assertIsNone(series.categories["seriesb"].sequence(noseries))
            self.assertIsNone(series.categories["seriesc"].sequence(noseries))
