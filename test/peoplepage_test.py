# -*- coding: utf-8 -*-
#
# People page tests.
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


import pageparser

# A typical page full of actor records: "Остров проклятых" (2009) [eng: "Shutter Island"].
# On updates, replace file data/actors_397667.html with http://www.kinopoisk.ru/film/397667/cast/
SHUTTER_ISLAND_ID = '397667'
ACTORS_PAGE_397667 = 'data/actors_397667.html'
WALLE_ID = '279102'

# This page has first two actors with wrong DOM, so it should produce parsing errors.
ACTORS_PAGE_397667_ACTOR_ERRORS = 'data/actors_397667_actorErrors.html'

# Actors page is not found.
ACTORS_PAGE_404_ERROR = 'data/404.html'


def suite(excludeRemoteTests = False):
  suite = unittest.TestSuite()
  suite.addTest(PeoplePageTest('localTest_peoplePage_notAll'))
  suite.addTest(PeoplePageTest('localTest_peoplePage_all'))
  suite.addTest(PeoplePageTest('localTest_peoplePage_actorErrors'))
  suite.addTest(PeoplePageTest('localTest_peoplePage_pageError'))
  if not excludeRemoteTests:
    suite.addTest(PeoplePageTest('remoteTest_peoplePage_all'))
    suite.addTest(PeoplePageTest('remoteTest_peoplePage_walle'))
  return suite


class PeoplePageTest(U.PageTest):
  def __init__(self, testName):
    super(PeoplePageTest, self).__init__(testName, S.ENCODING_KINOPOISK_PAGE, pageparser.USER_AGENT)

  def setUp(self):
    self.parser = pageparser.PageParser(self.log, self.http, testlog.logLevel > 4)
    if testlog.logLevel > 0:
      sys.stdout.flush()
      print '' # Put log statement on a new line.

  def tearDown(self):
    pass

  ######## TESTS START HERE ####################################################

  def localTest_peoplePage_notAll(self):
    """ Tests a typical page full of actors loaded from filesystem (with loadAllActors=False). """
    data = self.__readAndParseLocalFile(ACTORS_PAGE_397667, False)
    actors = self.fetchKeyArrayDataItem(data, 'actors', pageparser.MAX_ACTORS)
    self._assertActorsFromPage397667(actors)

  def localTest_peoplePage_all(self):
    """ Tests a typical page full of actors loaded from filesystem (with loadAllActors=True). """
    data = self.__readAndParseLocalFile(ACTORS_PAGE_397667, True)
    actors = self.fetchKeyArrayDataItem(data, 'actors', pageparser.MAX_ALL_ACTORS)
    self._assertActorsFromPage397667(actors)
    self._assertMoreActorsFromPage397667(actors)

  def localTest_peoplePage_actorErrors(self):
    """ Tests handling errors - first two actors errors should not prevent parsing the rest. """
    data = self.__readAndParseLocalFile(ACTORS_PAGE_397667_ACTOR_ERRORS, False)
    actors = self.fetchKeyArrayDataItem(data, 'actors', pageparser.MAX_ACTORS)
    # Checking just three first actors.
    self._assertActor(actors, 0, 'Бен Кингсли', 'Dr. Cawley')
    self._assertActor(actors, 1, 'Макс фон Сюдов', 'Dr. Naehring')
    self._assertActor(actors, 2, 'Мишель Уильямс', 'Dolores')

  def localTest_peoplePage_pageError(self):
    """ Tests handling errors - page parsing error should not throw exceptions. """
    data = self.__readAndParseLocalFile(ACTORS_PAGE_404_ERROR, False)
    self.assertIsNotNone(data, 'Returned data is None.')
    self.fetchKeyArrayDataItem(data, 'actors', 0)

  def remoteTest_peoplePage_all(self):
    """ Tests a typical page full of actors loaded from KinoPoisk (with loadAllActors=True). """
    data = self.parser.fetchAndParseCastPage(SHUTTER_ISLAND_ID, True)
    actors = self.fetchKeyArrayDataItem(data, 'actors', pageparser.MAX_ALL_ACTORS)
    self._assertActorsFromPage397667(actors)
    self._assertMoreActorsFromPage397667(actors)

  def remoteTest_peoplePage_walle(self):
    """  """
    data = self.parser.fetchAndParseCastPage(WALLE_ID, False)
    actors = self.fetchKeyArrayDataItem(data, 'actors', pageparser.MAX_ACTORS)
    self._assertActorsFromPageWallE(actors)

  ######## TESTS END HERE ######################################################

  def __readAndParseLocalFile(self, filename, loadAllActors):
    page = self.readLocalFile(filename)
    return self.parser.parseCastPage(page, loadAllActors)

  def _assertActorsFromPage397667(self, actors):
    # Just 7 should be enough.
    self._assertActor(actors, 0, 'Леонардо ДиКаприо', 'Teddy Daniels')
    self._assertActor(actors, 1, 'Марк Руффало', 'Chuck Aule')
    self._assertActor(actors, 2, 'Бен Кингсли', 'Dr. Cawley')
    self._assertActor(actors, 3, 'Макс фон Сюдов', 'Dr. Naehring')
    self._assertActor(actors, 4, 'Мишель Уильямс', 'Dolores')
    self._assertActor(actors, 5, 'Эмили Мортимер', 'Rachel 1')
    self._assertActor(actors, 6, 'Патришия Кларксон', 'Rachel 2')

  def _assertMoreActorsFromPage397667(self, actors):
    # A few more actors.
    self._assertActor(actors, 10, 'Элиас Котеас', 'Laeddis')
    self._assertActor(actors, 11, 'Робин Бартлетт', 'Bridget Kearns')
    self._assertActor(actors, 12, 'Кристофер Денэм', 'Peter Breene')
    self._assertActor(actors, 40, 'Дэнни Карни', 'Nazi SS Guard') # Should have no ', в титрах не указана'.

  def _assertActorsFromPageWallE(self, actors):
    self._assertActor(actors, 0, 'Бен Бертт', 'WALL·E / M-O, озвучка')
    self._assertActor(actors, 1, 'Элисса Найт', 'EVE, озвучка')
    self._assertActor(actors, 2, 'Джефф Гарлин', 'Captain, озвучка')
    self._assertActor(actors, 3, 'Фред Уиллард', 'Shelby Forthright, BnL CEO')
    self._assertActor(actors, 4, 'Джон Ратценбергер', 'John, озвучка')
    self._assertActor(actors, 5, 'Кэти Нэджими', 'Mary, озвучка')
    self._assertActor(actors, 6, 'Сигурни Уивер', 'Ship\'s Computer, озвучка')
    # TODO(zhenya): uncomment and fix the encoding bug.
#    self._assertActor(actors, 7, 'Ники МакЭлрой', 'Pool Mother, озвучка')

  def _assertActor(self, actors, index, name, role):
    self.assertGreater(len(actors), index, 'Index too large.')
    actorTuple = actors[index]
    self.assertIsNotNone(actorTuple, 'Actor ' + str(index) + ' tuple is None.')
    self.assertEquals(2, len(actorTuple), 'Wrong number of items in actor ' + str(index) + ' tuple.')
    self._assertEquals(name, actorTuple[0], 'Wrong actor ' + str(index) + ' name.')
    self._assertEquals(role, actorTuple[1], 'Wrong actor ' + str(index) + ' role.')

  def _assertEquals(self, expected, fact, msg):
    self.assertTrue(expected == fact, msg + ' Expected "' + str(expected) + '", but was "' + str(fact) + '".')

if __name__ == '__main__':
  # When changing this code, pls make sure to adjust main.py accordingly.
  (options, args) = U.parseTestOptions()
  testlog.logLevel = options.logLevel
  runner = unittest.TextTestRunner(verbosity=testlog.TEST_RUNNER_VERBOSITY)
  result = runner.run(suite(options.excludeRemote))
  sys.exit(U.getExitCode(result))

