# coding: utf-8
from unittest import TestCase
from staticsite.build import Build
from staticsite.site import Site
from staticsite.core import Page
from . import datafile_abspath, example_site, TestArgs, TestPage
import os
import datetime


class TestSeries(TestCase):
    def test_site(self):
        site = Site()

        seriesa1 = TestPage(site, "seriesa1", date=datetime.datetime(2016, 1, 1), series="seriesa")
        seriesa2 = TestPage(site, "seriesa2", date=datetime.datetime(2016, 1, 2), series="seriesa")
        seriesb1 = TestPage(site, "seriesb1", date=datetime.datetime(2016, 1, 1), series="seriesb")
        seriesb2 = TestPage(site, "seriesb2", date=datetime.datetime(2016, 1, 2), series="seriesb")
        noseries = TestPage(site, "noseries", date=datetime.datetime(2016, 1, 1))

        site.add_page(seriesa1)
        site.add_page(seriesa2)
        # Invert adding seriesb pages to check date-based ordering
        site.add_page(seriesb2)
        site.add_page(seriesb1)
        site.add_page(noseries)
        site.load_theme(datafile_abspath("theme"))
        site.analyze()

        # Check that series have been built
        self.assertIn("seriesa", site.series)
        self.assertIn("seriesb", site.series)
        self.assertEquals(len(site.series), 2)

        # Check the contents of series
        self.assertEquals(site.series["seriesa"].pages, [seriesa1, seriesa2])
        self.assertEquals(site.series["seriesb"].pages, [seriesb1, seriesb2])
