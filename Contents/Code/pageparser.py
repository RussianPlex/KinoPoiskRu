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


ENCODING_KINOPOISK_PAGE = 'cp1251'

MAX_ACTORS = 10
MAX_ALL_ACTORS = 50


def parsePeoplePage(page, loadAllActors):
  infoBlocks = page.xpath('//a[@name="actor"]/following-sibling::*')
  count = 0
  actors = []
  if loadAllActors:
    maxActors =  MAX_ALL_ACTORS
  else:
    maxActors =  MAX_ACTORS
  for infoBlock in infoBlocks:
    personBlockNodes = infoBlock.xpath('div[@class="actorInfo"]/div[@class="info"]/div[@class="name"]/*')
    if (len(personBlockNodes) == 0 and count > 1) or count > maxActors:
      break
    count = count + 1
    if len(personBlockNodes) > 0:
      try:
        actorName = personBlockNodes[0].text.encode('utf8')
        roleNode = personBlockNodes[0].getparent().getparent()[1]
        actorRole = roleNode.text.encode('utf8').strip().strip('. ')
        actors.append((actorName, actorRole))
      except:
        pass
  data = {'actors': actors}
  return data
