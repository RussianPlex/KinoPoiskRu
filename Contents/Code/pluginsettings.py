# -*- coding: utf-8 -*-

"""
Global definitions for KinoPoiskRu plugin.

@version @PLUGIN.REVISION@
@revision @REPOSITORY.REVISION@
@copyright (c) 2014 by Yevgeny Nyden
@license GPLv3, see LICENSE for more details
"""

# Default plugin preferences. When modifying, please also change
# corresponding values in the ../DefaultPrefs.json file.
KINOPOISK_PREF_DEFAULT_MAX_POSTERS = 1
KINOPOISK_PREF_DEFAULT_MAX_ART = 2
KINOPOISK_PREF_DEFAULT_GET_ALL_ACTORS = False
KINOPOISK_PREF_DEFAULT_IMDB_RATING = False
KINOPOISK_PREF_DEFAULT_KP_RATING = False

ENCODING_KINOPOISK_PAGE = 'cp1251'

# Разные страницы сайта.
KINOPOISK_SITE_BASE = 'http://www.kinopoisk.ru/'
KINOPOISK_RESOURCE_BASE = 'http://st.kp.yandex.net/'
KINOPOISK_TITLE_PAGE_URL = KINOPOISK_SITE_BASE + 'film/%s/'
KINOPOISK_CAST_PAGE_URL = KINOPOISK_SITE_BASE + 'film/%s/cast/'
KINOPOISK_STUDIO_PAGE_URL = KINOPOISK_SITE_BASE + 'film/%s/studio/'
KINOPOISK_THUMBNAIL_BIG_URL = KINOPOISK_RESOURCE_BASE + 'images/film_big/%s.jpg'
KINOPOISK_THUMBNAIL_SMALL_URL = KINOPOISK_RESOURCE_BASE + 'images/film/%s.jpg'
KINOPOISK_COVERS_URL = KINOPOISK_SITE_BASE + 'film/%s/covers' # We only care for the first page.
KINOPOISK_POSTERS_URL = KINOPOISK_SITE_BASE + 'film/%s/posters' # We only care for the first page.
KINOPOISK_STILLS_URL = KINOPOISK_SITE_BASE + 'film/%s/stills' # We only care for the first page.
KINOPOISK_SCREENSHOTS_URL = KINOPOISK_SITE_BASE + 'film/%s/screenshots' # We only care for the first page.
KINOPOISK_WALL_URL = KINOPOISK_SITE_BASE + 'film/%s/wall' # We only care for the first page.

KINOPOISK_THUMBNAIL_BIG_SCORE_BONUS = 30

# Страница поиска.
KINOPOISK_SEARCH = KINOPOISK_SITE_BASE + 'index.php?first=no&kp_query=%s'
KINOPOISK_SEARCH_SIMPLE = KINOPOISK_SITE_BASE + 's/type/all/find/%s/set_result_type/simple/'


# TMDB constants.
TMDB_PAGE_ENCODING = 'utf-8'
TMDB_MATCH_MIN_SCORE = 85

TMDB_IMAGE_ORIGINAL_BASE_URL = 'http://image.tmdb.org/t/p/original'
TMDB_IMAGE_THUMB_BASE_URL = 'http://image.tmdb.org/t/p/w376'
