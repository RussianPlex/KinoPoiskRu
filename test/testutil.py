# -*- coding: utf-8 -*-
#
# Test utilities for the RussianPlex project.
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
# @author zhenya (Yevgeny Nyden)
#

from optparse import OptionParser
import codecs, types, unittest, urllib, urllib2, testlog
import pluginsettings as S
from lxml import etree
from testlog import TestLogger as Logger

# Expect code in classpath or in the same directory.
import common
import json

TEST_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.22 (KHTML, like Gecko) Chrome/25.0.1364.172 Safari/537.22'


def parseTestOptions():
  parser = OptionParser()
  parser.add_option('-x', '--exclude-remote', action='store_true', default=False, dest='excludeRemote',
      help='Excludes tests that attempt to download remote content.')
  parser.add_option('-l', '--log', action='store', type='int', default=1, dest='logLevel',
      help='Sets the log level; supported values: [0,5].')
  return parser.parse_args()


def getExitCode(result):
  exitCode = 0
  if len(result.errors) > 0 or len(result.failures) > 0:
    exitCode = 1
  return exitCode

class PageTest(unittest.TestCase):
  def __init__(self, testName, encoding='utf-8', userAgent=TEST_USER_AGENT):
    super(PageTest, self).__init__(testName)
    self.log = Logger(testlog.logLevel)
    self.http = TestHttp(encoding, userAgent)

  def dumpObject(self, obj):
    for attr in dir(obj):
      print "obj.%s = %s" % (attr, getattr(obj, attr))

  def readLocalFile(self, filename):
    self.log.Debug('Reading local file "%s"...' % filename)
    fileHandle = codecs.open(filename, "r", S.ENCODING_KINOPOISK_PAGE)
    fileContent = fileHandle.read()
    return etree.HTML(fileContent)

  def assertKeyValueApproximateNumber(self, data, key, approxValue, percent=15, isFloat=False):
    self.assertIn(key, data, '%s is not parsed.' % key)
    valueStr = data[key]
    if isFloat:
      self.assertTrue(isinstance(valueStr, float), 'Value for %s is not a float.' % key)
    else:
      self.assertTrue(isinstance(valueStr, int), 'Value for %s is not an int.' % key)
    value = float(valueStr)
    if abs(approxValue - value) > approxValue * percent / 100:
      self.fail('Value for "%s" %g differs from the expected %g by more than %d%%.' % (key, value, approxValue, percent))

  def assertKeyValue(self, data, key, expected, limitCompare=False):
    self.assertIn(key, data, '%s is not parsed.' % key)
    value = data[key]
    if limitCompare:
      value = value[:len(expected)]
    self._assertEquals(expected, value, 'Wrong %s.' % key)

  def assertKeyArrayValue(self, data, key, expected):
    # If you get errors when comparing strings (funny character at the end),
    # copy-paste expected string from the console and not from the website!
    self.assertIn(key, data, '%s is not parsed.' % key)
    value = data[key]
    self.assertTrue(isinstance(value, types.ListType), '%s value is not a list.' % key)
    if len(expected) != len(value):
      self.fail('Wrong number of value items. Expected %d but was %d. Expected %s but was %s' %
                (len(expected), len(value), common.arrayToUnicodeString(expected), common.arrayToUnicodeString(value)))
    self._assertEquals(len(expected), len(value), 'Wrong number of value items.')
    ind = 0
    for expectedItem in expected:
      self._assertEquals(expectedItem, value[ind], 'Wrong %s - item %d.' % (key, ind))
      ind = ind + 1

  def fetchKeyArrayDataItem(self, data, key, numberItems):
    self.assertIsNotNone(data, 'data is None.')
    self.assertIn(key, data, 'Data for %s is not found.' % key)
    valueArray = data[key]
    self.assertIsNotNone(valueArray, 'Data for %s is not set.' % key)
    self._assertEquals(numberItems, len(valueArray), 'Wrong number of items for %s.' % key)
    return valueArray

  def _assertEquals(self, expected, fact, msg):
    if not isinstance(expected, unicode) and not isinstance(expected, basestring):
      expected = str(expected)
    if not isinstance(fact, unicode) and not isinstance(fact, basestring):
      fact = str(fact)
    self.assertTrue(expected == fact, msg + ' Expected "' + expected + '", but was "' + fact + '".')

  def _assertNotLessThen(self, expected, fact, msg):
    self.assertTrue(fact >= expected, msg + ' Expected at least "' + str(expected) + '", but was "' + str(fact) + '".')


class TestHttp():
  def __init__(self, encoding, userAgent):
    self.encoding = encoding
    self.userAgent = userAgent

  def requestAndParseHtmlPage(self, url):
    opener = urllib2.build_opener()
    opener.addheaders = [
      ('User-agent', self.userAgent),
      ('Accept', 'text/html'),
      ('Accept-Charset', 'ISO-8859-1;q=0.7,*;q=0.3'),
      ('Accept-Language', 'en-US,en;q=0.8'),
      ('Cache-Control', 'max-age=0'),
    ]
    response = opener.open(url)
    content = response.read().decode(self.encoding)
    return etree.HTML(content)


  def requestAndParseJsonApi(self, method, url, params, data, headers):
    opener = urllib2.build_opener()
    opener.addheaders = []
    for key, value in headers.items():
      opener.addheaders.append((key, value))
    opener.addheaders.append(('Cache-Control', 'max-age=0'))
    encodedParams = urllib.urlencode(params)
    response = opener.open(url + '?' + encodedParams)
    content = response.read()
#    content = response.read().decode(self.encoding)
    return json.loads(content)


  def requestImageJpeg(self, url):
    """ Requests an image given its URL and returns a request object.
    """
    try:
      opener = urllib2.build_opener()
      opener.addheaders = [
        ('User-agent', self.userAgent),
        ('Accept', 'image/jpeg'),
        ('Cache-Control', 'max-age=0')
      ]
      return opener.open(url)
    except:
      pass
    return None
