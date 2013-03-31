# -*- coding: utf-8 -*-
#
# Russian metadata plugin for Plex, which uses http://www.kinopoisk.ru/ to get the tag data.
# Плагин для обновления информации о фильмах использующий КиноПоиск (http://www.kinopoisk.ru/).
# Copyright (C) 2013 Zhenya Nyden
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#
# @author zhenya (Yevgeny Nyden)
# @revision @REPOSITORY.REVISION@

import sys

MAX_ACTORS = 10
MAX_ALL_ACTORS = 50

# Actor role suffix that's going to be stripped.
ROLE_USELESS_SUFFFIX = u', в титрах '


class PeopleParser:
  def __init__(self, logger, isDebug = False):
    self.log = logger
    self.isDebug = isDebug

  def parse(self, page, loadAllActors):
    """ Parses a given people page. Parsed actors are stored in
        data['actors'] as (name, role) string tuples.
    """
    # Find the <a> tag for the actors section header and
    # grab all elements that follow it.
    self.log.Info(' <<< Parsing people page...')
    infoBlocks = page.xpath('//a[@name="actor"]/following-sibling::*')
    count = 0
    actors = []
    if loadAllActors:
      maxActors =  MAX_ALL_ACTORS
    else:
      maxActors =  MAX_ACTORS
    for infoBlock in infoBlocks:
      personBlockNodes = infoBlock.xpath('div[@class="actorInfo"]/div[@class="info"]/div[@class="name"]/*')
      if count > maxActors or (len(personBlockNodes) == 0 and count > 1):
        # Stop on the first miss after second element - it probably means
        # we got to the next section (<a> tag of the "Продюсеры" section).
        break
      count = count + 1
      if len(personBlockNodes) > 0:
        actorName = None
        try:
          actorName = personBlockNodes[0].text.encode('utf8')
          roleNode = personBlockNodes[0].getparent().getparent()[1]
          actorRole = roleNode.text.encode('utf8')
          inTitleInd = roleNode.text.find(ROLE_USELESS_SUFFFIX)
          if inTitleInd > 0:
            # Remove useless suffix.
            actorRole = actorRole[0:inTitleInd]
          actorRole = actorRole.strip().strip('. ')
          actors.append((actorName, actorRole))
          self.log.Debug('   <<< parsed actor: name="%s", role="%s"...' % (actorName, actorRole))
        except:
          self.log.Error('   <<< error parsing actor "%s"!' % str(actorName))
          if self.isDebug:
            excInfo = sys.exc_info()
            self.log.Exception('   exception: %s; cause: %s' % (excInfo[0], excInfo[1]))
    data = {'actors': actors}
    self.log.Info(' <<< Parsed %d actors.' % len(actors))
    return data
