# -*- coding: utf-8 -*-
#
# Global definitions for KinoPoiskRu plugin.
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

# Default plugin preferences. When modifying, please also change
# corresponding values in the ../DefaultPrefs.json file.
KINOPOISK_PREF_DEFAULT_MAX_POSTERS = 1
KINOPOISK_PREF_DEFAULT_MAX_ART = 2
KINOPOISK_PREF_DEFAULT_GET_ALL_ACTORS = False
KINOPOISK_PREF_DEFAULT_IMDB_SUPPORT = True
KINOPOISK_PREF_DEFAULT_IMDB_RATING = False
KINOPOISK_PREF_DEFAULT_KP_RATING = False

ENCODING_KINOPOISK_PAGE = 'cp1251'

# Разные страницы сайта.
KINOPOISK_SITE_BASE = 'http://www.kinopoisk.ru/'
KINOPOISK_RESOURCE_BASE = 'http://st.kinopoisk.ru/'
KINOPOISK_TITLE_PAGE_URL = KINOPOISK_SITE_BASE + 'level/1/film/%s/'
KINOPOISK_PEOPLE = KINOPOISK_SITE_BASE + 'film/%s/cast/'
KINOPOISK_STUDIO = KINOPOISK_SITE_BASE + 'level/91/film/%s/'
KINOPOISK_POSTERS = KINOPOISK_SITE_BASE + 'level/17/film/%s/page/%d/'
KINOPOISK_ART = KINOPOISK_SITE_BASE + 'level/13/film/%s/page/%d/'
KINOPOISK_MOVIE_THUMBNAIL = KINOPOISK_RESOURCE_BASE + 'images/film/%s.jpg'
KINOPOISK_MOVIE_BIG_THUMBNAIL = KINOPOISK_RESOURCE_BASE + 'images/film_big/%s.jpg'

# Страница поиска.
KINOPOISK_SEARCH = KINOPOISK_SITE_BASE + '/index.php?first=no&kp_query=%s'

KINOPOISK_MOVIE_THUMBNAIL_WIDTH = 130
KINOPOISK_MOVIE_THUMBNAIL_HEIGHT = 168
KINOPOISK_MOVIE_THUMBNAIL_DEFAULT_WIDTH = 600
KINOPOISK_MOVIE_THUMBNAIL_DEFAULT_HEIGHT = 1024

# Русские месяца, пригодятся для определения дат.
RU_MONTH = {
  u'января': '01',
  u'февраля': '02',
  u'марта': '03',
  u'апреля': '04',
  u'мая': '05',
  u'июня': '06',
  u'июля': '07',
  u'августа': '08',
  u'сентября': '09',
  u'октября': '10',
  u'ноября': '11',
  u'декабря': '12'
}
