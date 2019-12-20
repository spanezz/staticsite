from unittest import TestCase
from . import utils as test_utils
import datetime


def dt(*args):
    return datetime.datetime(*args)


class TestSeries(TestCase):
    def test_site(self):
        site = test_utils.Site(TAXONOMIES=["series"])
        site.load_without_content()

        # TODO: say that all categories are series (or make it default to True if called 'series'?)
        site.add_test_page("taxonomy", "series")

        seriesa1 = site.add_test_page("md", "seriesa1",
                                      meta={"series": "seriesa", "title": "Series A", "date": dt(2016, 1, 1)})
        seriesa2 = site.add_test_page("md", "seriesa2",
                                      meta={"date": dt(2016, 1, 2), "series": "seriesa", "title": "A2"})
        seriesa3 = site.add_test_page("md", "seriesa3",
                                      meta={"date": dt(2016, 1, 3), "series": "seriesa", "title": "A3",
                                            "series_title": "Series A part Two"})
        seriesa4 = site.add_test_page("md", "seriesa4",
                                      meta={"date": dt(2016, 1, 4), "series": "seriesa", "title": "A4"})

        seriesb1 = site.add_test_page("md", "seriesb1",
                                      meta={"date": dt(2016, 1, 1), "series": "seriesb",
                                            "title": "Series B", "series_title": "Series B part One"})
        seriesb2 = site.add_test_page("md", "seriesb2",
                                      meta={"date": dt(2016, 1, 2), "series": "seriesb", "title": "B2"})

        seriesc1 = site.add_test_page("md", "seriesc1",
                                      meta={"date": dt(2016, 1, 1), "series": "seriesc"})

        noseries = site.add_test_page("md", "noseries",
                                      meta={"date": dt(2016, 1, 1), "title": "Other things"})

        series = site.pages["series"]

        site.analyze()

        # Check that series have been built (check in tags)
        self.assertIn("seriesa", series.categories)
        self.assertIn("seriesb", series.categories)
        self.assertIn("seriesc", series.categories)
        self.assertEquals(len(series.categories), 3)

        # Check the contents of series (check in tags)
        self.assertEquals(series.categories["seriesa"].meta["pages"], [seriesa1, seriesa2, seriesa3, seriesa4])
        self.assertEquals(series.categories["seriesb"].meta["pages"], [seriesb1, seriesb2])
        self.assertEquals(series.categories["seriesc"].meta["pages"], [seriesc1])

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
        self.assertEquals(s["title"], "seriesc1")
        self.assertEquals(s["prev"], None)
        self.assertEquals(s["next"], None)
        self.assertEquals(s["first"], seriesc1)
        self.assertEquals(s["last"], seriesc1)
        self.assertEquals(s["index"], 1)
        self.assertEquals(s["length"], 1)

        self.assertIsNone(series.categories["seriesa"].sequence(noseries))
        self.assertIsNone(series.categories["seriesb"].sequence(noseries))
        self.assertIsNone(series.categories["seriesc"].sequence(noseries))
