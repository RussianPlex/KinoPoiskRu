# -*- coding: utf-8 -*-
#
# Title page tests.
# @author zhenya (Yevgeny Nyden)
#
# Copyright (C) 2014  Yevgeny Nyden
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
import testutil as U, testlog
import tmdbapi


def suite(excludeRemoteTests = False):
  suite = unittest.TestSuite()
  if not excludeRemoteTests:
    suite.addTest(TmdbTest('remoteTest_searchForImdbTitles_en'))
    suite.addTest(TmdbTest('remoteTest_searchForImdbTitles_ru'))
    suite.addTest(TmdbTest('remoteTest_searchForImdbTitles_multiple'))
    suite.addTest(TmdbTest('remoteTest_searchForImdbTitles_noresults'))
  return suite


class TmdbTest(U.PageTest):
  def __init__(self, testName):
    super(TmdbTest, self).__init__(testName)

  def setUp(self):
    self.tmdbApi = tmdbapi.TmdbApi(self.log, self.http, testlog.logLevel > 4)
    if testlog.logLevel > 0:
      sys.stdout.flush()
      print '' # Put log statement on a new line.

  def tearDown(self):
    pass

  ######## TESTS START HERE ####################################################

  def remoteTest_searchForImdbTitles_en(self):
    results = self.tmdbApi.searchForImdbTitles(u'здравствуйте я ваша тетя', '1975', 'en')
    self.assertIsNotNone(results, 'results is None.')
    self._assertNotLessThen(1, len(results), 'Wrong number of search results.')
    self._assertTitleTuple(results[0], 72611, 'Hello, I\'m Your Aunt!', '1975', 96)

  def remoteTest_searchForImdbTitles_ru(self):
    results = self.tmdbApi.searchForImdbTitles(u'здравствуйте я ваша тетя', '1975', 'ru')
    self.assertIsNotNone(results, 'results is None.')
    self._assertNotLessThen(1, len(results), 'Wrong number of search results.')
    self._assertTitleTuple(results[0], 72611, 'Здравствуйте, я ваша тётя!', '1975', 97)

  def remoteTest_searchForImdbTitles_multiple(self):
    results = self.tmdbApi.searchForImdbTitles(u'приключения', '1976', 'ru')
    self.assertIsNotNone(results, 'results is None.')
    self._assertNotLessThen(2, len(results), 'Wrong number of search results.')
    self._assertTitleTuple(results[1], 85355, 'Приключения жёлтого чемоданчика', '1970', 76)

  def remoteTest_searchForImdbTitles_noresults(self):
    results = self.tmdbApi.searchForImdbTitles(u'карамба', '1900', 'ru')
    self.assertIsNotNone(results, 'results is None.')
    self._assertNotLessThen(0, len(results), 'Wrong number of search results.')


  ######## TESTS END HERE ######################################################

  def _assertTitleTuple(self, tuple, imdbId, title, year, score):
    self._assertEquals(title, tuple['name'].encode('utf8'), 'Wrong title')
    self._assertEquals(year, tuple['year'], 'Wrong year')
    self._assertEquals(imdbId, tuple['id'], 'Wrong imdbId')
    self._assertEquals(score, tuple['score'], 'Wrong score')


if __name__ == '__main__':
  # When changing this code, pls make sure to adjust main.py accordingly.
  (options, args) = U.parseTestOptions()
  testlog.logLevel = options.logLevel
  runner = unittest.TextTestRunner(verbosity=testlog.TEST_RUNNER_VERBOSITY)
  result = runner.run(suite(options.excludeRemote))
  sys.exit(U.getExitCode(result))

