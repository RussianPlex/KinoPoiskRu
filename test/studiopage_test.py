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


# A studio page (with 2 studios) for title "Дежа вю" (1989).
DEZHAVYU_ID = '44394'
NONE_ID = '443941111'
STUDIO_PAGE_44394 = 'data/studio_44394.html'


def suite(excludeRemoteTests = False):
  suite = unittest.TestSuite()
  suite.addTest(StudioPageTest('localTest_studioPage_basic'))
  if not excludeRemoteTests:
    suite.addTest(StudioPageTest('remoteTest_studioPage_basic'))
    suite.addTest(StudioPageTest('remoteTest_studioPage_notFound'))
  return suite


class StudioPageTest(U.PageTest):
  def __init__(self, testName):
    super(StudioPageTest, self).__init__(testName, S.ENCODING_KINOPOISK_PAGE, pageparser.USER_AGENT)

  def setUp(self):
    self.parser = pageparser.PageParser(self.log, self.http, testlog.logLevel > 4)
    if testlog.logLevel > 0:
      sys.stdout.flush()
      print '' # Put log statement on a new line.

  def tearDown(self):
    pass

  ######## TESTS START HERE ####################################################

  def localTest_studioPage_basic(self):
    """ Tests a typical title page loaded from filesystem. """
    data = self._readAndParseLocalFile(STUDIO_PAGE_44394)
    self.assertKeyArrayValue(data, 'studios', ['Одесская киностудия', 'Студия Фильмов Зебра'])

  def remoteTest_studioPage_basic(self):
    """ Tests a typical studio page loaded from KinoPoisk. """
    data = self.parser.fetchAndParseStudioPage(DEZHAVYU_ID)
    self.assertKeyArrayValue(data, 'studios', ['Одесская киностудия', 'Студия Фильмов Зебра'])

  def remoteTest_studioPage_notFound(self):
    """ Tests 404 page. """
    data = self.parser.fetchAndParseStudioPage(NONE_ID)
    self.fetchKeyArrayDataItem(data, 'studios', 0)


  ######## TESTS END HERE ######################################################

  def _readAndParseLocalFile(self, filename):
    page = self.readLocalFile(filename)
    return self.parser.parseStudioPage(page)


if __name__ == '__main__':
  # When changing this code, pls make sure to adjust main.py accordingly.
  (options, args) = U.parseTestOptions()
  testlog.logLevel = options.logLevel
  runner = unittest.TextTestRunner(verbosity=testlog.TEST_RUNNER_VERBOSITY)
  result = runner.run(suite(options.excludeRemote))
  sys.exit(U.getExitCode(result))

