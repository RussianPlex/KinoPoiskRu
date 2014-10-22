# -*- coding: utf-8 -*-
#
# Title page tests.
# @author zhenya (Yevgeny Nyden)
#
# Copyright (C) 2012  Zhenya Nyden
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import sys, unittest
import pluginsettings as S
import testutil as U, testlog
import pageparser # Expect KinoPoiskRu's code in classpath or in the same directory.


def suite(excludeRemoteTests = False):
  suite = unittest.TestSuite()
  if not excludeRemoteTests:
    suite.addTest(PageParserTest('remoteTest_fetchAndParseSearchResults'))
    suite.addTest(PageParserTest('remoteTest_fetchAndParseSearchResults_latin'))
    suite.addTest(PageParserTest('remoteTest_fetchAndParseSearchResults_latin2'))
    suite.addTest(PageParserTest('remoteTest_fetchAndParseSearchResults_rusTitle'))
    suite.addTest(PageParserTest('remoteTest_fetchAndParseSearchResults_rusTitleInLatin'))
    suite.addTest(PageParserTest('remoteTest_queryKinoPoisk_russianTitle'))
    suite.addTest(PageParserTest('remoteTest_queryKinoPoisk_russianTitle_latin'))
  return suite


class PageParserTest(U.PageTest):
  def __init__(self, testName):
    super(PageParserTest, self).__init__(testName, S.ENCODING_KINOPOISK_PAGE, pageparser.USER_AGENT)

  def setUp(self):
    self.parser = pageparser.PageParser(self.log, self.http, testlog.logLevel > 4)
    if testlog.logLevel > 0:
      sys.stdout.flush()
      print '' # Put log statement on a new line.

  def tearDown(self):
    pass

  ######## TESTS START HERE ####################################################

  def remoteTest_fetchAndParseSearchResults(self):
    results = self.parser.fetchAndParseSearchResults(u'здравствуйте я ваша тетя', '1975')
    self.assertIsNotNone(results, 'results is None.')
    self._assertNotLessThen(5, len(results), 'Wrong number of search results.')
    self._assertTitleTuple(results[0], '77276', 'Здравствуйте, я ваша тетя! (ТВ)', '1975', 95)
    self._assertTitleTuple(results[1], '542384', 'Здравствуйте, тетя Лиса!', '1974', 77)
    self._assertTitleTuple(results[2], '18731', 'Здравствуйте, я ваша тетушка', '1998', 77)

  def remoteTest_fetchAndParseSearchResults_latin(self):
    results = self.parser.fetchAndParseSearchResults('Gladiatory.Rima', '2012')
    self.assertIsNotNone(results, 'results is None.')
    self._assertNotLessThen(5, len(results), 'Wrong number of search results.')
    self._assertTitleTuple(results[0], '597580', 'Гладиаторы Рима', '2012', 95)
    self._assertTitleTuple(results[1], '612070', 'Гладиаторы футбола (ТВ)', '2008', 72)
    self._assertTitleTuple(results[2], '4682', 'Гладиатор', '1992', 65)

  def remoteTest_fetchAndParseSearchResults_latin2(self):
    results = self.parser.fetchAndParseSearchResults('zdravstvuete ya vasha tetya', '1975')
    self.assertIsNotNone(results, 'results is None.')
    self._assertNotLessThen(5, len(results), 'Wrong number of search results.')
    self._assertTitleTuple(results[0], '77276', 'Здравствуйте, я ваша тетя! (ТВ)', '1975', 94)
    self._assertTitleTuple(results[1], '18731', 'Здравствуйте, я ваша тетушка', '1998', 75)
    self._assertTitleTuple(results[2], '325776', 'Здравствуйте, мы ваша крыша!', '2005', 69)

  def remoteTest_fetchAndParseSearchResults_rusTitle(self):
    results = self.parser.fetchAndParseSearchResults(u'волшебное дерево', '2009')
    self.assertIsNotNone(results, 'results is None.')
    self._assertNotLessThen(5, len(results), 'Wrong number of search results.')
    self._assertTitleTuple(results[0], '484633', 'Волшебное дерево', '2009', 100)
    self._assertTitleTuple(results[1], '404231', 'Семейное дерево', '2011', 78)
    self._assertTitleTuple(results[2], '123197', 'Волшебное дерево (ТВ)', '2004', 76)
    self._assertTitleTuple(results[3], '502951', 'Winx Club: Волшебное приключение', '2010', 72)

  def remoteTest_fetchAndParseSearchResults_rusTitleInLatin(self):
    results = self.parser.fetchAndParseSearchResults(u'Volshebnoe derevo', '2009')
    self.assertIsNotNone(results, 'results is None.')
    self._assertNotLessThen(5, len(results), 'Wrong number of search results.')
    self._assertTitleTuple(results[0], '484633', 'Волшебное дерево', '2009', 100)
    self._assertTitleTuple(results[1], '404231', 'Семейное дерево', '2011', 78)
    self._assertTitleTuple(results[2], '123197', 'Волшебное дерево (ТВ)', '2004', 76)
    self._assertTitleTuple(results[3], '502951', 'Winx Club: Волшебное приключение', '2010', 72)

  def remoteTest_queryKinoPoisk_russianTitle(self):
    results = self.parser.queryKinoPoisk(u'Бриллиантовая рука', '1968')
    self.assertIsNotNone(results, 'results is None.')
    self._assertNotLessThen(5, len(results), 'Wrong number of search results.')
    self._assertTitleTuple(results[0], '46225', 'Бриллиантовая рука', '1968', 100)
    self._assertTitleTuple(results[1], '573340', 'Русский Голливуд: Бриллиантовая рука 2 (ТВ)', '2010', 65)
    self._assertTitleTuple(results[2], '12514', 'Рука, качающая колыбель', '1992', 47)

  def remoteTest_queryKinoPoisk_russianTitle_latin(self):
    results = self.parser.queryKinoPoisk('Volshebnoe derevo', '2009')
    self.assertIsNotNone(results, 'results is None.')
    self._assertNotLessThen(5, len(results), 'Wrong number of search results.')
    self._assertTitleTuple(results[0], '45497', 'Честное волшебное', '1975', 70)



  ######## TESTS END HERE ######################################################

  def _assertTitleTuple(self, tuple, kinopoiskId, title, year, score):
    self._assertEquals(title, tuple[1].encode('utf8'), 'Wrong title')
    self._assertEquals(year, tuple[2], 'Wrong year')
    self._assertEquals(kinopoiskId, tuple[0], 'Wrong kinopoisk id')
    self._assertEquals(score, tuple[3], 'Wrong score')


if __name__ == '__main__':
  # When changing this code, pls make sure to adjust main.py accordingly.
  (options, args) = U.parseTestOptions()
  testlog.logLevel = options.logLevel
  runner = unittest.TextTestRunner(verbosity=testlog.TEST_RUNNER_VERBOSITY)
  result = runner.run(suite(options.excludeRemote))
  sys.exit(U.getExitCode(result))

