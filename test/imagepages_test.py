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

MOVIE_WITH_BIG_THUMB_ID = '42664'
MOVIE_RUS_ID = '42664'
MOVIE_ENG_ID = '325'
MOVIE_OPERATIONI_ID = '42782'

def suite(excludeRemoteTests = False):
  suite = unittest.TestSuite()
  suite.addTest(ImagePagesTest('localTest_parsePosterThumbnailData_None'))
  if not excludeRemoteTests:
    suite.addTest(ImagePagesTest('remoteTest_parsePosterThumbnailData_withBig'))
    suite.addTest(ImagePagesTest('remoteTest_parsePosterThumbnailData_rus'))
    suite.addTest(ImagePagesTest('remoteTest_parsePosterThumbnailData_eng'))
    suite.addTest(ImagePagesTest('remoteTest_fetchAndParsePostersData_one'))
    suite.addTest(ImagePagesTest('remoteTest_fetchAndParsePostersData_more'))
  return suite


class ImagePagesTest(U.PageTest):
  def __init__(self, testName):
    super(ImagePagesTest, self).__init__(testName, S.ENCODING_KINOPOISK_PAGE, pageparser.USER_AGENT)

  def setUp(self):
    self.parser = pageparser.PageParser(self.log, self.http, testlog.logLevel > 4)
    if testlog.logLevel > 0:
      sys.stdout.flush()
      print '' # Put log statement on a new line.

  def tearDown(self):
    pass

  ######## TESTS START HERE ####################################################

  def localTest_parsePosterThumbnailData_None(self):
    """ Tests a typical poster page loaded from filesystem. """
    thumb = self.parser.parsePosterThumbnailData(None, MOVIE_WITH_BIG_THUMB_ID)
    self.assertIsNotNone(thumb, 'Thumb is None.')
    self._assertEquals(pageparser.MOVIE_THUMBNAIL_SMALL_WIDTH, thumb.width, 'Wrong thumb width.')
    self._assertEquals(pageparser.MOVIE_THUMBNAIL_SMALL_HEIGHT, thumb.height, 'Wrong thumb height.')
    self._assertEquals(S.KINOPOISK_THUMBNAIL_SMALL_URL % MOVIE_WITH_BIG_THUMB_ID, thumb.url, 'Wrong thumb url.')

  def remoteTest_parsePosterThumbnailData_withBig(self):
    """ Tests a typical poster page loaded from kinopoisk.ru. """
    thumb = self.parser.fetchAndParsePosterThumbnailData(MOVIE_WITH_BIG_THUMB_ID)
    self.assertIsNotNone(thumb, 'Thumb is None.')
    self._assertEquals(pageparser.MOVIE_THUMBNAIL_BIG_WIDTH, thumb.width, 'Wrong thumb width.')
    self._assertEquals(pageparser.MOVIE_THUMBNAIL_BIG_HEIGHT, thumb.height, 'Wrong thumb height.')
    self._assertEquals(S.KINOPOISK_THUMBNAIL_BIG_URL % MOVIE_WITH_BIG_THUMB_ID, thumb.url, 'Wrong thumb url.')

  def remoteTest_parsePosterThumbnailData_rus(self):
    """ Tests a poster page for a Russian movie title loaded from kinopoisk.ru. """
    data = self.parser.fetchAndParseImagesPage(MOVIE_RUS_ID, 15)
    self.assertIsNotNone(data, 'data is None.')
    self.assertIn('posters', data, 'posters are not parsed.')
    posters = data['posters']
    self.assertIsNotNone(posters, 'posters data is present.')
    self._assertEquals(11, len(posters), 'Wrong number of posters parsed.')
    self.assertThumbnail(posters[0], 1, 0, # Note that index 0 is reserved for the main thumb.
      'http://st.kp.yandex.net/images/poster/sm_2209261.jpg',
      'http://st-im.kinopoisk.ru/im/poster/2/2/0/kinopoisk.ru-Ivan-Vasilevich-menyaet-professiyu-2209261.jpg',
      360, 573)
    self.assertThumbnail(posters[7], 8, 0,
      'http://st.kp.yandex.net/images/poster/sm_1351545.jpg',
      'http://st-im.kinopoisk.ru/im/poster/1/3/5/kinopoisk.ru-Ivan-Vasilevich-menyaet-professiyu-1351545.jpg',
      600, 862)

  def remoteTest_parsePosterThumbnailData_eng(self):
    """ Tests a poster page for an English movie title loaded from kinopoisk.ru. """
    data = self.parser.fetchAndParseImagesPage(MOVIE_ENG_ID, 15)
    self.assertIsNotNone(data, 'data is None.')
    self.assertIn('posters', data, 'posters are not parsed.')
    posters = data['posters']
    self.assertIsNotNone(posters, 'posters data is present.')
    self._assertEquals(30, len(posters), 'Wrong number of posters parsed.')
    self.assertThumbnailApprox(posters[0], 1, 0, # Note that index 0 is reserved for the main thumb.
      'jpg', 'jpg')
    self.assertThumbnailApprox(posters[20], 21, 0, 'jpg', 'jpg')

  def remoteTest_fetchAndParsePostersData_one(self):
    """ Tests the main poster parsing method with maxPosters=1. """
    data = self.parser.fetchAndParsePostersData(MOVIE_OPERATIONI_ID, 1)
    self.assertIsNotNone(data, 'data is None.')
    self.assertIn('posters', data, 'posters are not parsed.')
    posters = data['posters']
    self.assertIsNotNone(posters, 'posters data is present.')
    self._assertEquals(1, len(posters), 'Wrong number of posters parsed.')
    self.assertThumbnail(posters[0], 0, 1000,
      'http://st.kinopoisk.ru/images/film_big/42782.jpg',
      'http://st.kinopoisk.ru/images/film_big/42782.jpg',
      780, 1024)

  def remoteTest_fetchAndParsePostersData_more(self):
    """ Tests the main poster parsing method with maxPosters=1. """
    data = self.parser.fetchAndParsePostersData(MOVIE_OPERATIONI_ID, 10)
    self.assertIsNotNone(data, 'data is None.')
    self.assertIn('posters', data, 'posters are not parsed.')
    posters = data['posters']
    self.assertIsNotNone(posters, 'posters data is present.')
    self._assertEquals(3, len(posters), 'Wrong number of posters parsed.')
    self.assertThumbnail(posters[0], 1, 90,
      'http://st.kp.yandex.net/images/poster/sm_2329344.jpg',
      'http://st-im.kinopoisk.ru/im/poster/2/3/2/kinopoisk.ru-Operatsiya-_ABY_BB-i-drugiye-priklyucheniya-Shurika-2329344.jpg',
      614, 865)
    self.assertThumbnail(posters[1], 0, 89,
      'http://st.kinopoisk.ru/images/film_big/42782.jpg',
      'http://st.kinopoisk.ru/images/film_big/42782.jpg',
      780, 1024)
    self.assertThumbnail(posters[2], 2, 35,
      'http://st.kp.yandex.net/images/poster/sm_2054233.jpg',
      'http://st-im.kinopoisk.ru/im/poster/2/0/5/kinopoisk.ru-Operatsiya-_ABY_BB-i-drugiye-priklyucheniya-Shurika-2054233.jpg',
      800, 502)


  ######## TESTS END HERE ######################################################

  def _requestAndParseImagesPage(self, kinoPoiskId, numOfPages):
    pages = []
    for pageInd in range(1, numOfPages + 1):
      pages.append(self.requestHtmlPage(S.KINOPOISK_POSTERS_URL % (kinoPoiskId, pageInd), S.ENCODING_KINOPOISK_PAGE))
    return self.parser.parseImagesPage(pages, 10)

  def assertThumbnail(self, thumb, index, score, thumbUrl, url, width, height):
    self.assertIsNotNone(thumb, 'Thumbnail %d - is not set.' % index)
    self._assertEquals(index, thumb.index, 'Thumbnail %d - wrong index.' % index)
    self._assertEquals(score, thumb.score, 'Thumbnail %d - wrong score.' % index)
    self._assertEquals(thumbUrl, thumb.thumbUrl, 'Thumbnail %d - wrong thumb url.' % index)
    self._assertEquals(url, thumb.url, 'Thumbnail %d - wrong url.' % index)
    self._assertEquals(width, thumb.width, 'Thumbnail %d - wrong width.' % index)
    self._assertEquals(height, thumb.height, 'Thumbnail %d - wrong height.' % index)

  def assertThumbnailApprox(self, thumb, index, score, thumbUrlExt, urlExt):
    self.assertIsNotNone(thumb, 'Thumbnail %d - is not set.' % index)
    self._assertEquals(index, thumb.index, 'Thumbnail %d - wrong index.' % index)
    self._assertEquals(score, thumb.score, 'Thumbnail %d - wrong score.' % index)
    self.assertIsNotNone(thumb.thumbUrl, 'Thumbnail %d - thumb url is None.' % index)
    self.assertTrue(thumb.thumbUrl.find('http://') == 0,
        'Thumbnail %d - wrong thumb url: %s' % (index, thumb.thumbUrl))
    self._assertEquals(thumbUrlExt, thumb.thumbUrl[len(thumb.thumbUrl) - len(thumbUrlExt):],
      'Thumbnail %d - wrong thumb url extension.' % index)
    self.assertIsNotNone(thumb.url, 'Thumbnail %d - url is None.' % index)
    self.assertTrue(thumb.url.find('http://') == 0,
        'Thumbnail %d - wrong url: %s' % (index, thumb.url))
    self._assertEquals(urlExt, thumb.url[len(thumb.url) - len(urlExt):],
        'Thumbnail %d - wrong url extension.' % index)
    self.assertIsNotNone(thumb.width, 'Thumbnail width is None.')
    self.assertTrue(thumb.width > 10, 'Thumbnail #%d width seems to be wrong: %d.' % (index, thumb.width))
    self.assertIsNotNone(thumb.height, 'Thumbnail height is None.')
    self.assertTrue(thumb.height > 10, 'Thumbnail #%d height seems to be wrong: %d.' % (index, thumb.height))


if __name__ == '__main__':
  # When changing this code, pls make sure to adjust main.py accordingly.
  (options, args) = U.parseTestOptions()
  testlog.logLevel = options.logLevel
  runner = unittest.TextTestRunner(verbosity=testlog.TEST_RUNNER_VERBOSITY)
  result = runner.run(suite(options.excludeRemote))
  sys.exit(U.getExitCode(result))

