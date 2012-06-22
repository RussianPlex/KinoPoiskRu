# -*- coding: utf-8 -*-
#
# Russian metadata plugin for Plex, which uses http://api.themoviedb.org/ to get the tag data.
# Copyright (C) 2012 Zhenya Nyden
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
#
# @revision 74

import string, sys, time, re
import common


TMDB_SECRET = 'a3dc111e66105f6387e99393813ae4d5'
TMDB_GETINFO = 'http://api.themoviedb.org/2.1/Movie.search/ru/xml/' + TMDB_SECRET + '/%s'

TMDB_PAGE_ENCODING = 'utf-8'

MATCHER_RELEASED = re.compile(r'\D?(\d\d\d\d)\D')


def searchForImdbTitles(results, mediaName, mediaYear, lang):
  """ Given media name and a candidate title, returns the title result score penalty.
  """
  mediaName = mediaName.lower()
  page = common.getElementFromHttpRequest(TMDB_GETINFO % mediaName.replace(' ', '%20'), TMDB_PAGE_ENCODING)
  if page is None:
    Log.Warn('nothing was found on tmdb for media name "%s"' % mediaName)
  else:
    movieElems = page.xpath('//movies/movie')
    itemIndex = 0
    for movieElem in movieElems:
      imdbId = common.getXpathRequiredNode(movieElem, './imdb_id/text()')
      title = common.getXpathRequiredNode(movieElem, './name/text()')
      altTitle = common.getXpathOptionalNode(movieElem, './alternative_name/text()')
      releaseDate = common.getXpathOptionalNode(movieElem, './released/text()')
      year = common.getReOptionalGroup(MATCHER_RELEASED, releaseDate, 0)
      score = common.scoreMediaTitleMatch(mediaName, mediaYear, title, altTitle, year, itemIndex)
      results.Append(MetadataSearchResult(id=imdbId, name=title, year=year, lang=lang, score=score))
      itemIndex += 1

