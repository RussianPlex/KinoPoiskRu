# -*- coding: utf-8 -*-
#
# Title page tests.
# @author zhenya (Yevgeny Nyden)
#
# Copyright (C) 2013  Zhenya Nyden
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

import sys, unittest, datetime
import pluginsettings as S
import testutil as U, testlog
import pageparser # Expect KinoPoiskRu's code in classpath or in the same directory.


# A typical title page: "Медведь" (1988) [orig: "L'ours"].
MEDVED_ID = '22907'
TITLE_PAGE_22907 = 'data/title_22907.html'

# A typical title page: "Побег из Шоушенка" (1994) [eng: "The Shawshank Redemption"].
TITLE_PAGE_326 = 'data/title_326.html'

# Russian movie film "...А зори здесь тихие" (1972).
TITLE_PAGE_43395 = 'data/title_43395.html'

# Movie to test the removal of "Слова" from "жанры" line.
RUBEZH_ID = '683766'


def suite(excludeRemoteTests = False):
  suite = unittest.TestSuite()
  suite.addTest(TitlePageTest('localTest_titlePage_basic'))
  suite.addTest(TitlePageTest('localTest_parseMainActorsFromLanding'))
  if not excludeRemoteTests:
    suite.addTest(TitlePageTest('remoteTest_titlePage_basic'))
    suite.addTest(TitlePageTest('remoteTest_parseMainActorsFromLanding'))
    suite.addTest(TitlePageTest('remoteTest_verifySlovaRemovalFromGenre'))
  return suite


class TitlePageTest(U.PageTest):
  def __init__(self, testName):
    super(TitlePageTest, self).__init__(testName, S.ENCODING_KINOPOISK_PAGE, pageparser.USER_AGENT)

  def setUp(self):
    self.parser = pageparser.PageParser(self.log, self.http, testlog.logLevel > 4)
    if testlog.logLevel > 0:
      sys.stdout.flush()
      print '' # Put log statement on a new line.

  def tearDown(self):
    pass

  ######## TESTS START HERE ####################################################

  def localTest_titlePage_basic(self):
    """ Tests a typical title page loaded from filesystem. """
    data = self._readAndParseLocalFile(TITLE_PAGE_22907)
    self._assertTitlePage22907(data)

  def localTest_parseMainActorsFromLanding(self):
    """ Tests a typical title page loaded from filesystem. """
    page = self.readLocalFile(TITLE_PAGE_22907)
    actors = self.parser.parseMainActorsFromLanding(page)
    self._assertTitlePageActors22907(actors)

  def remoteTest_titlePage_basic(self):
    """ Tests a typical title page loaded from KinoPoisk. """
    data = self.parser.fetchAndParseTitlePage(MEDVED_ID)
    self._assertTitlePage22907(data)
    pass

  def remoteTest_parseMainActorsFromLanding(self):
    """  """
    page = self.http.requestAndParseHtmlPage(S.KINOPOISK_TITLE_PAGE_URL % MEDVED_ID)
    actors = self.parser.parseMainActorsFromLanding(page)
    self._assertTitlePageActors22907(actors)

  def remoteTest_verifySlovaRemovalFromGenre(self):
    """ Test removal of Слова from жанры. """
    data = {}
    page = self.http.requestAndParseHtmlPage(S.KINOPOISK_TITLE_PAGE_URL % RUBEZH_ID)
    self.parser.parseTitlePageInfoTable(data, page)
    self.assertKeyArrayValue(data, 'genres', ['Боевик', 'Криминал'])


  ######## TESTS END HERE ######################################################

  def _readAndParseLocalFile(self, filename):
    page = self.readLocalFile(filename)
    return self.parser.parseTitlePage(page)

  def _assertTitlePage22907(self, data):
    self.assertKeyValue(data, 'title', 'Медведь')
    self.assertKeyValue(data, 'originalTitle', 'L\'ours')
    self.assertKeyValue(data, 'year', 1988)
    self.assertKeyValue(data, 'tagline', 'He\'s an orphan... at the start of a journey. A journey to survive')
    self.assertKeyArrayValue(data, 'directors', ['Жан-Жак Анно'])
    self.assertKeyArrayValue(data, 'countries', ['Франция', 'США'])
    self.assertKeyArrayValue(data, 'writers', ['Жерар Браш', 'Джеймс Оливер Кёрвуд'])
    self.assertKeyArrayValue(data, 'genres', ['Драма', 'Приключения', 'Семейный'])
    self.assertKeyValue(data, 'contentRating', 'PG')
    self.assertKeyValue(data, 'contentRatingAlt', '12+')
    self.assertKeyValue(data, 'summary', 'Среди прекрасных и величественных пейзажей Британской Колумбии случилась', True)
    self.assertKeyValue(data, 'duration', 5640000)
    self.assertKeyValue(data, 'originalDate', datetime.datetime(1988, 10, 19).date())
    self.assertKeyValueApproximateNumber(data, 'rating', 8.272, isFloat=True)
    self.assertKeyValueApproximateNumber(data, 'ratingCount', 8876)
    self.assertKeyValueApproximateNumber(data, 'imdbRating', 7.7, isFloat=True)
    self.assertKeyValueApproximateNumber(data, 'imdbRatingCount', 10650)

  def _assertTitlePageActors22907(self, actors):
    self.assertIsNotNone(actors, 'actors is None.')
    self._assertEquals(5, len(actors), 'Wrong number of actors.')
    self._assertEquals('Медведь Барт', actors[0], 'Wrong actor 0.')
    self._assertEquals('Медведь Юк', actors[1], 'Wrong actor 1.')
    self._assertEquals('Чеки Карио', actors[2], 'Wrong actor 2.')
    self._assertEquals('Джек Уоллес', actors[3], 'Wrong actor 3.')
    self._assertEquals('Андре Лакомб', actors[4], 'Wrong actor 4.')

if __name__ == '__main__':
  # When changing this code, pls make sure to adjust main.py accordingly.
  (options, args) = U.parseTestOptions()
  testlog.logLevel = options.logLevel
  runner = unittest.TextTestRunner(verbosity=testlog.TEST_RUNNER_VERBOSITY)
  result = runner.run(suite(options.excludeRemote))
  sys.exit(U.getExitCode(result))

