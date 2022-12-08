from __future__ import annotations
from unittest import TestCase
from . import utils as test_utils
import datetime


def dt(*args):
    return str(datetime.datetime(*args))


class TestSeries(test_utils.MockSiteTestMixin, TestCase):
    def test_site(self):
        files = {
            "series.taxonomy": "",
            "seriesa1.md": {"series": "seriesa", "title": "Series A", "date": dt(2016, 1, 1)},
            "seriesa2.md": {"date": dt(2016, 1, 2), "series": "seriesa", "title": "A2"},
            "seriesa3.md": {"date": dt(2016, 1, 3), "series": "seriesa", "title": "A3",
                            "series_title": "Series A part Two"},
            "seriesa4.md": {"date": dt(2016, 1, 4), "series": "seriesa", "title": "A4"},
            "seriesb1.md": {"date": dt(2016, 1, 1), "series": "seriesb",
                            "title": "Series B", "series_title": "Series B part One"},
            "seriesb2.md": {"date": dt(2016, 1, 2), "series": "seriesb", "title": "B2"},
            "seriesc1.md": {"date": dt(2016, 1, 1), "title": "Series C", "series": "seriesc"},
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
            self.assertEquals(len(series.categories), 3)

            # Check the contents of series (check in tags)
            self.assertEquals(series.categories["seriesa"].pages, [seriesa1, seriesa2, seriesa3, seriesa4])
            self.assertEquals(series.categories["seriesb"].pages, [seriesb1, seriesb2])
            self.assertEquals(series.categories["seriesc"].pages, [seriesc1])

            # Check computed series metadata
            s = series.categories["seriesa"].sequence(seriesa1)
            self.assertEquals(s["title"], "Series A")
            self.assertEquals(s["prev"], None)
            self.assertEquals(s["next"], seriesa2)
            self.assertEquals(s["first"], seriesa1)
            self.assertEquals(s["last"], seriesa4)
            self.assertEquals(s["index"], 1)
            self.assertEquals(s["length"], 4)

            s = series.categories["seriesa"].sequence(seriesa2)
            self.assertEquals(s["title"], "Series A")
            self.assertEquals(s["prev"], seriesa1)
            self.assertEquals(s["next"], seriesa3)
            self.assertEquals(s["first"], seriesa1)
            self.assertEquals(s["last"], seriesa4)
            self.assertEquals(s["index"], 2)
            self.assertEquals(s["length"], 4)

            s = series.categories["seriesa"].sequence(seriesa3)
            self.assertEquals(s["title"], "Series A part Two")
            self.assertEquals(s["prev"], seriesa2)
            self.assertEquals(s["next"], seriesa4)
            self.assertEquals(s["first"], seriesa1)
            self.assertEquals(s["last"], seriesa4)
            self.assertEquals(s["index"], 3)
            self.assertEquals(s["length"], 4)

            s = series.categories["seriesa"].sequence(seriesa4)
            self.assertEquals(s["title"], "Series A part Two")
            self.assertEquals(s["prev"], seriesa3)
            self.assertEquals(s["next"], None)
            self.assertEquals(s["first"], seriesa1)
            self.assertEquals(s["last"], seriesa4)
            self.assertEquals(s["index"], 4)
            self.assertEquals(s["length"], 4)

            s = series.categories["seriesb"].sequence(seriesb1)
            self.assertEquals(s["title"], "Series B part One")
            self.assertEquals(s["prev"], None)
            self.assertEquals(s["next"], seriesb2)
            self.assertEquals(s["first"], seriesb1)
            self.assertEquals(s["last"], seriesb2)
            self.assertEquals(s["index"], 1)
            self.assertEquals(s["length"], 2)

            s = series.categories["seriesb"].sequence(seriesb2)
            self.assertEquals(s["title"], "Series B part One")
            self.assertEquals(s["prev"], seriesb1)
            self.assertEquals(s["next"], None)
            self.assertEquals(s["first"], seriesb1)
            self.assertEquals(s["last"], seriesb2)
            self.assertEquals(s["index"], 2)
            self.assertEquals(s["length"], 2)

            s = series.categories["seriesc"].sequence(seriesc1)
            self.assertEquals(s["title"], "Series C")
            self.assertEquals(s["prev"], None)
            self.assertEquals(s["next"], None)
            self.assertEquals(s["first"], seriesc1)
            self.assertEquals(s["last"], seriesc1)
            self.assertEquals(s["index"], 1)
            self.assertEquals(s["length"], 1)

            self.assertIsNone(series.categories["seriesa"].sequence(noseries))
            self.assertIsNone(series.categories["seriesb"].sequence(noseries))
            self.assertIsNone(series.categories["seriesc"].sequence(noseries))
