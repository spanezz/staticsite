from unittest import TestCase
from staticsite import Site
from . import datafile_abspath, TestPage
import datetime


class TestSeries(TestCase):
    def test_site(self):
        site = Site()
        site.settings.THEME = datafile_abspath("theme")
        site.load()
        series = site.features["series"].series

        seriesa1 = TestPage(site, "seriesa1", date=datetime.datetime(2016, 1, 1), series="seriesa", title="Series A")
        seriesa2 = TestPage(site, "seriesa2", date=datetime.datetime(2016, 1, 2), series="seriesa", title="A2")
        seriesa3 = TestPage(site, "seriesa3", date=datetime.datetime(2016, 1, 3), series="seriesa", title="A3",
                            series_title="Series A part Two")
        seriesa4 = TestPage(site, "seriesa4", date=datetime.datetime(2016, 1, 4), series="seriesa", title="A4")

        seriesb1 = TestPage(site, "seriesb1", date=datetime.datetime(2016, 1, 1), series="seriesb", title="Series B",
                            series_title="Series B part One")
        seriesb2 = TestPage(site, "seriesb2", date=datetime.datetime(2016, 1, 2), series="seriesb", title="B2")

        seriesc1 = TestPage(site, "seriesc1", date=datetime.datetime(2016, 1, 1), series="seriesc")

        noseries = TestPage(site, "noseries", date=datetime.datetime(2016, 1, 1), title="Other things")

        site.add_page(seriesa1)
        site.add_page(seriesa2)
        site.add_page(seriesa3)
        site.add_page(seriesa4)
        # Invert adding seriesb pages to check date-based ordering
        site.add_page(seriesb2)
        site.add_page(seriesb1)
        # Single-page series
        site.add_page(seriesc1)
        site.add_page(noseries)
        site.analyze()

        # Check that series have been built
        self.assertIn("seriesa", series)
        self.assertIn("seriesb", series)
        self.assertIn("seriesc", series)
        self.assertEquals(len(series), 3)

        # Check the contents of series
        self.assertEquals(series["seriesa"].pages, [seriesa1, seriesa2, seriesa3, seriesa4])
        self.assertEquals(series["seriesb"].pages, [seriesb1, seriesb2])
        self.assertEquals(series["seriesc"].pages, [seriesc1])

        # Check computed series metadata
        self.assertEquals(seriesa1.meta["series_title"], "Series A")
        self.assertEquals(seriesa1.meta["series_prev"], None)
        self.assertEquals(seriesa1.meta["series_next"], seriesa2)
        self.assertEquals(seriesa1.meta["series_first"], seriesa1)
        self.assertEquals(seriesa1.meta["series_last"], seriesa4)
        self.assertEquals(seriesa1.meta["series_index"], 1)
        self.assertEquals(seriesa1.meta["series_length"], 4)

        self.assertEquals(seriesa2.meta["series_title"], "Series A")
        self.assertEquals(seriesa2.meta["series_prev"], seriesa1)
        self.assertEquals(seriesa2.meta["series_next"], seriesa3)
        self.assertEquals(seriesa2.meta["series_first"], seriesa1)
        self.assertEquals(seriesa2.meta["series_last"], seriesa4)
        self.assertEquals(seriesa2.meta["series_index"], 2)
        self.assertEquals(seriesa2.meta["series_length"], 4)

        self.assertEquals(seriesa3.meta["series_title"], "Series A part Two")
        self.assertEquals(seriesa3.meta["series_prev"], seriesa2)
        self.assertEquals(seriesa3.meta["series_next"], seriesa4)
        self.assertEquals(seriesa3.meta["series_first"], seriesa1)
        self.assertEquals(seriesa3.meta["series_last"], seriesa4)
        self.assertEquals(seriesa3.meta["series_index"], 3)
        self.assertEquals(seriesa3.meta["series_length"], 4)

        self.assertEquals(seriesa4.meta["series_title"], "Series A part Two")
        self.assertEquals(seriesa4.meta["series_prev"], seriesa3)
        self.assertEquals(seriesa4.meta["series_next"], None)
        self.assertEquals(seriesa4.meta["series_first"], seriesa1)
        self.assertEquals(seriesa4.meta["series_last"], seriesa4)
        self.assertEquals(seriesa4.meta["series_index"], 4)
        self.assertEquals(seriesa4.meta["series_length"], 4)

        self.assertEquals(seriesb1.meta["series_title"], "Series B part One")
        self.assertEquals(seriesb1.meta["series_prev"], None)
        self.assertEquals(seriesb1.meta["series_next"], seriesb2)
        self.assertEquals(seriesb1.meta["series_first"], seriesb1)
        self.assertEquals(seriesb1.meta["series_last"], seriesb2)
        self.assertEquals(seriesb1.meta["series_index"], 1)
        self.assertEquals(seriesb1.meta["series_length"], 2)

        self.assertEquals(seriesb2.meta["series_title"], "Series B part One")
        self.assertEquals(seriesb2.meta["series_prev"], seriesb1)
        self.assertEquals(seriesb2.meta["series_next"], None)
        self.assertEquals(seriesb2.meta["series_first"], seriesb1)
        self.assertEquals(seriesb2.meta["series_last"], seriesb2)
        self.assertEquals(seriesb2.meta["series_index"], 2)
        self.assertEquals(seriesb2.meta["series_length"], 2)

        self.assertEquals(seriesc1.meta["series_title"], "seriesc")
        self.assertEquals(seriesc1.meta["series_prev"], None)
        self.assertEquals(seriesc1.meta["series_next"], None)
        self.assertEquals(seriesc1.meta["series_first"], seriesc1)
        self.assertEquals(seriesc1.meta["series_last"], seriesc1)
        self.assertEquals(seriesc1.meta["series_index"], 1)
        self.assertEquals(seriesc1.meta["series_length"], 1)

        self.assertNotIn("series", noseries.meta)
        self.assertNotIn("series_title", noseries.meta)
        self.assertNotIn("series_prev", noseries.meta)
        self.assertNotIn("series_next", noseries.meta)
        self.assertNotIn("series_first", noseries.meta)
        self.assertNotIn("series_last", noseries.meta)
        self.assertNotIn("series_index", noseries.meta)
        self.assertNotIn("series_length", noseries.meta)
