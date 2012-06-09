# -*- coding: utf-8 -*-

# Russian metadata plugin for Plex, which uses http://www.kinopoisk.ru/ to get the tag data.
# Плагин для обновления информации о фильмах использующий КиноПоиск (http://www.kinopoisk.ru/).
# Copyright (C) 2012  Zhenya Nyden

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import datetime, string, re, time, math, operator, unicodedata, hashlib, urlparse, types, sys

ENCODING_KINOPOISK_PAGE = 'cp1251'
ENCODING_PLEX = 'utf-8'

# Разные страницы сайта.
KINOPOISK_BASE = 'http://www.kinopoisk.ru/'
KINOPOISK_TITLE_PAGE_URL = KINOPOISK_BASE + 'level/1/film/%s/'
KINOPOISK_PEOPLE = KINOPOISK_BASE + 'level/19/film/%s/'
KINOPOISK_STUDIO = KINOPOISK_BASE + 'level/91/film/%s/'
KINOPOISK_POSTERS = KINOPOISK_BASE + 'level/17/film/%s/page/%d/'
KINOPOISK_ART = KINOPOISK_BASE + 'level/13/film/%s/page/%d/'
KINOPOISK_MOVIE_THUMBNAIL = 'http://st.kinopoisk.ru/images/film/%s.jpg'
KINOPOISK_MOVIE_THUMBNAIL_WIDTH = 130
KINOPOISK_MOVIE_THUMBNAIL_HEIGHT = 168

# Страница поиска.
KINOPOISK_SEARCH = 'http://www.kinopoisk.ru/index.php?first=no&kp_query=%s'

# Compiled regex matchers.
MATCHER_MOVIE_DURATION = re.compile('\s*(\d+).*?', re.UNICODE | re.DOTALL)
MATCHER_WIDTH_FROM_STYLE = re.compile('.*width\s*:\s*(\d+)px.*', re.UNICODE)
MATCHER_HEIGHT_FROM_STYLE = re.compile('.*height\s*:\s*(\d+)px.*', re.UNICODE)

SCORE_PENALTY_ITEM_ORDER = 3
SCORE_PENALTY_YEAR_WRONG = 4
SCORE_PENALTY_NO_MATCH = 50

IMAGE_SCORE_ITEM_ORDER_BONUS_MAX = 30
IMAGE_SCORE_RESOLUTION_BONUS_MAX = 20
IMAGE_SCORE_RATIO_BONUS_MAX = 40
IMAGE_SCORE_THUMB_BONUS = 10
IMAGE_SCORE_MAX_NUMBER_OF_ITEMS = 5
POSTER_SCORE_MIN_RESOLUTION_PX = 60 * 1000
POSTER_SCORE_MAX_RESOLUTION_PX = 600 * 1000
POSTER_SCORE_BEST_RATIO = 0.7
ART_SCORE_BEST_RATIO = 1.5
ART_SCORE_MIN_RESOLUTION_PX = 200 * 1000
ART_SCORE_MAX_RESOLUTION_PX = 1000 * 1000

# Рейтинги.
DEFAULT_MPAA = u'R'
MPAA_AGE = {u'G': 0, u'PG': 11, u'PG-13': 13, u'R': 16, u'NC-17': 17}

# Русские месяца, пригодится для определения дат.
RU_MONTH = {u'января': '01', u'февраля': '02', u'марта': '03', u'апреля': '04', u'мая': '05', u'июня': '06', u'июля': '07', u'августа': '08', u'сентября': '09', u'октября': '10', u'ноября': '11', u'декабря': '12'}

# Под кого маскируемся =).
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_2) AppleWebKit/534.51.22 (KHTML, like Gecko) Version/5.1.1 Safari/534.51.22'

# Preference item names.
PREF_IS_DEBUG_NAME = 'kinopoisk_pref_is_debug'
PREF_LOG_LEVEL_NAME = 'kinopoisk_pref_log_level'
PREF_CACHE_TIME_NAME = 'kinopoisk_pref_cache_time'
PREF_MAX_POSTERS_NAME = 'kinopoisk_pref_max_posters'
PREF_MAX_ART_NAME = 'kinopoisk_pref_max_art'
PREF_GET_ALL_ACTORS = 'kinopoisk_pref_get_all_actors'
PREF_CACHE_TIME_DEFAULT = CACHE_1MONTH
PREF_MAX_POSTERS_DEFAULT = 6
PREF_MAX_ART_DEFAULT = 4


class LocalSettings():
  """ These instance variables are populated from plugin preferences. """
  maxPosters = PREF_MAX_POSTERS_DEFAULT
  maxArt = PREF_MAX_ART_DEFAULT
  getAllActors = False

localPrefs = LocalSettings()


def Start():
  Log.Debug('***** START ***** %s' % USER_AGENT)
  readPluginPreferences()


def ValidatePrefs():
  readPluginPreferences()


class PlexMovieAgent(Agent.Movies):
  name = 'KinoPoiskRu'
  languages = [Locale.Language.Russian]
  accepts_from = ['com.plexapp.agents.localmedia']
  contributes_to = ['com.plexapp.agents.wikipediaru']

  ##############################################################################
  ############################# S E A R C H ####################################
  ##############################################################################
  def search(self, results, media, lang, manual=False):
    """ Searches for matches on KinoPoisk using the title and year
        passed via the media object. All matches are saved in a list of results
        as MetadataSearchResult objects. For each results, we determine a
        page id, title, year, and the score (how good we think the match
        is on the scale of 1 - 100).
    """
    Log.Debug('SEARCH START <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
    mediaName = media.name
    mediaYear = media.year
    Log.Debug('searching for name="%s", year="%s", guid="%s", hash="%s"...' %
        (str(mediaName), str(mediaYear), str(media.guid), str(media.hash)))

    # Получаем страницу поиска
    Log.Debug('quering kinopoisk...')

    page = XMLElementFromURLWithRetries(KINOPOISK_SEARCH % mediaName.replace(' ', '%20'))
    if page is None:
      Log.Warn('nothing was found on kinopoisk for media name "%s"' % mediaName)
    else:
      # Если страница получена, берем с нее перечень всех названий фильмов.
      Log.Debug('got a kinopoisk page to parse...')
      divInfoElems = page.xpath('//self::div[@class="info"]/p[@class="name"]/a[contains(@href,"/level/1/film/")]/..')
      itemIndex = 0
      if len(divInfoElems):
        Log.Debug('found %d results' % len(divInfoElems))
        for divInfoElem in divInfoElems:
          try:
            anchorFilmElem = divInfoElem.xpath('./a[contains(@href,"/level/1/film/")]/attribute::href')
            if len(anchorFilmElem):
              # Parse kinopoisk movie title id, title and year.
              match = re.search('\/film\/(.+?)\/', anchorFilmElem[0])
              if match is None:
                Log.Error('unable to parse movie title id')
              else:
                kinoPoiskId = match.groups(1)[0]
                title = divInfoElem.xpath('.//a[contains(@href,"/level/1/film/")]/text()')[0]
                year = divInfoElem.xpath('.//span[@class="year"]/text()')[0]
                score = computeTitleScore(mediaName, mediaYear, title, year, itemIndex)
                results.Append(MetadataSearchResult(id=kinoPoiskId, name=title, year=year, lang=lang, score=score))
            else:
              Log.Warn('unable to find film anchor elements for title "%s"' % mediaName)
          except:
            Log.Error(getExceptionInfo('failed to parse div.info container'))
          itemIndex += 1
      else:
        Log.Warn('nothing was found on kinopoisk for media name "%s"' % mediaName)
        # TODO(zhenya): investigate whether we need this clause at all (haven't seen this happening).
        # Если не нашли там текст названия, значит сайт сразу дал нам страницу с фильмом (хочется верить =)
        try:
          title = page.xpath('//h1[@class="moviename-big"]/text()')[0].strip()
          kinoPoiskId = re.search('\/film\/(.+?)\/', page.xpath('//a[contains(@href,"/level/19/film/")]/attribute::href')[0]).groups(1)[0]
          year = page.xpath('//a[contains(@href,"year")]/text()')[0].strip()
          score = computeTitleScore(mediaName, mediaYear, title, year, itemIndex)
          results.Append(MetadataSearchResult(id=kinoPoiskId, name=title, year=year, lang=lang, score=score))
        except:
          Log.Error(getExceptionInfo('failed to parse a KinoPoisk page'))

    # Sort results according to their score (Сортируем результаты).
    results.Sort('score', descending=True)
#    Log.Debug('search produced %d results:' % len(results))
#    index = 0
#    for result in results:
#      Log.Debug(' ... result %d: id="%s", name="%s", year="%s", score="%d".' % (index, result.id, result.name, str(result.year), result.score))
#      index += 1
    Log.Debug('SEARCH END <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


  ##############################################################################
  ############################# U P D A T E ####################################
  ##############################################################################
  def update(self, metadata, media, lang):
    """Updates the media title provided a KinoPoisk movie title id (metadata.guid).
       This method fetches an appropriate KinoPoisk page, parses it, and populates
       the passed media item record.
    """
    Log.Debug('UPDATE START <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
    part = media.items[0].parts[0]
    filename = part.file.decode(ENCODING_PLEX)
    Log.Debug('filename="%s", guid="%s"' % (filename, metadata.guid))

    matcher = re.compile(r'//(\d+)\?')
    match = matcher.search(metadata.guid)
    if match is None:
      Log.Error('KinoPoisk movie title id is not specified!')
      raise Exception('ERROR: KinoPoisk movie title id is required!')
    else:
      kinoPoiskId = match.groups(1)[0]
    Log.Debug('parsed KinoPoisk movie title id: "%s"' % kinoPoiskId)

    self.updateMediaItem(metadata, kinoPoiskId)
    Log.Debug('UPDATE END <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


  def updateMediaItem(self, metadata, kinoPoiskId):
    titlePage =  XMLElementFromURLWithRetries(KINOPOISK_TITLE_PAGE_URL % kinoPoiskId)
    if titlePage is not None:
      Log.Debug('got a KinoPoisk page for movie title id: "%s"' % kinoPoiskId)
      try:
        resetMediaMetadata(metadata)
        parseTitleInfo(titlePage, metadata)                                       # Title. Название на русском языке.
        parseOriginalTitleInfo(titlePage, metadata)                               # Original title. Название на оригинальном языке.
        parseSummaryInfo(titlePage, metadata)                                     # Summary. Описание.
        parseRatingInfo(titlePage, metadata, kinoPoiskId)                         # Rating. Рейтинг.
        parseInfoTableTagAndUpdateMetadata(titlePage, metadata)
        parseStudioInfo(metadata, kinoPoiskId)                                    # Studio. Студия.
        parsePeoplePageInfo(titlePage, metadata, kinoPoiskId)                     # Actors, etc. Актёры. др.
        parsePostersInfo(metadata, kinoPoiskId)                                   # Posters. Постеры.
        parseBackgroundArtInfo(metadata, kinoPoiskId)                             # Background art. Задники.
      except:
        Log.Error(getExceptionInfo('failed to update metadata for id %s' % kinoPoiskId))


def parseInfoTableTagAndUpdateMetadata(page, metadata):
  """ Parses the main info <table> tag, which we find by
      a css classname "info".
  """
  mainInfoTagRows = page.xpath('//table[@class="info"]/tr')
  Log.Debug('parsed %d rows from the main info table tag' % len(mainInfoTagRows))
  directors = []
  for infoRowElem in mainInfoTagRows:
    headerTypeElem =  infoRowElem.xpath('./td[@class="type"]/text()')
    if len(headerTypeElem) != 1:
      continue
    rowTypeKey = headerTypeElem[0]
    if rowTypeKey == u'режиссер' or rowTypeKey == u'директор фильма':
      parseDirectorsInfo(infoRowElem, metadata)             # Director. Режиссер.
    elif rowTypeKey == u'год':
      parseYearInfo(infoRowElem, metadata)                  # Year. Год.
    elif rowTypeKey == u'сценарий':
      parseWritersInfo(infoRowElem, metadata)               # Writers. Сценаристы.
    elif rowTypeKey == u'жанр':
      parseGenresInfo(infoRowElem, metadata)                # Genre. Жанры.
    elif rowTypeKey == u'слоган':
      parseTaglineInfo(infoRowElem, metadata)               # Tagline. Слоган.
    elif rowTypeKey == u'рейтинг MPAA':
      parseContentRatingInfo(infoRowElem, metadata)         # Content rating. Рейтинг MPAA.
    elif rowTypeKey == u'время':
      parseDurationInfo(infoRowElem, metadata)              # Duration. Время.
    elif rowTypeKey == u'премьера (мир)':
      parseOriginallyAvailableInfo(infoRowElem, metadata)   # Originally available. Премьера в мире.
    elif rowTypeKey == u'продюсер' or \
         rowTypeKey == u'страна' or \
         rowTypeKey == u'оператор' or \
         rowTypeKey == u'композитор' or \
         rowTypeKey == u'художник' or \
         rowTypeKey == u'монтаж' or \
         rowTypeKey == u'бюджет' or \
         rowTypeKey == u'сборы в США' or \
         rowTypeKey == u'релиз на DVD' or \
         rowTypeKey == u'зрители' or \
         rowTypeKey == u'монтаж':
      # These tags are not supported yet.
      # TODO(zhenya): add some of these to the summary.
      Log.Debug('skipping an unsupported row: %s' % rowTypeKey)
      pass
    else:
      Log.Warn('UNRECOGNIZED row type: %s' % rowTypeKey)


def parseTitleInfo(page, metadata):
  title = page.xpath('//h1[@class="moviename-big"]/text()')[0].strip()
  if len(title):
    title = title.strip('- ')
    Log.Debug(' ... parsed title: "%s"' % title)
    metadata.title = title


def parseOriginalTitleInfo(page, metadata):
  origTitle = page.xpath('//span[@style="color: #666; font-size: 13px"]/text()')
  if len(origTitle):
    origTitle = ' '.join(origTitle)
    origTitle = sanitizeString(origTitle).strip('- ')
    Log.Debug(' ... parsed original title: "%s"' % origTitle)
    metadata.original_title = origTitle


def parseActorsInfoIntoMap(page):
  actorsMap = {}
  actors = page.xpath('//td[@class="actor_list"]/div/span')
  Log.Debug(' ... parsed %d actor tags' % len(actors))
  for actorSpanTag in actors:
    actorList = actorSpanTag.xpath('./a[contains(@href,"/level/4/people/")]/text()')
    if len(actorList):
      for actor in actorList:
        if actor != u'...':
          Log.Debug(' . . . . actor: "%s"' % actor)
          actorsMap[actor] = actor
  return actorsMap


def parseSummaryInfo(page, metadata):
  summaryParts = page.xpath('//div[@class="block_left_padtop"]/table/tr/td/table/tr/td/span[@class="_reachbanner_"]/div/text()')
  if len(summaryParts):
    summary = ' '.join(summaryParts)
    summary = sanitizeString(summary).strip()
    Log.Debug(' ... parsed summary: "%s..."' % summary[:30])
    metadata.summary = summary


def parseRatingInfo(page, metadata, kinoPoiskId):
  ratingText = page.xpath('//form[@class="rating_stars"]/div[@id="block_rating"]//a[@href="/level/83/film/' + kinoPoiskId + '/"]/span/text()')
  if len(ratingText):
    try:
      rating = float(ratingText[0])
      Log.Debug(' ... parsed rating "%s"' % str(rating))
      metadata.rating = rating
    except:
      Log.Error(getExceptionInfo('unable to parse rating'))


def parseStudioInfo(metadata, kinoPoiskId):
  page = XMLElementFromURLWithRetries(KINOPOISK_STUDIO % kinoPoiskId)
  if not page:
    return
  studios = page.xpath(u'//table/tr/td[b="Производство:"]/../following-sibling::tr/td/a/text()')
  if len(studios):
    # Берем только первую студию.
    studio = studios[0].strip()
    Log.Debug(' ... parsed studio: %s' % studio)
    metadata.studio = studio


def parseDirectorsInfo(infoRowElem, metadata):
  directors = infoRowElem.xpath('.//a/text()')
  Log.Debug(' ... parsed %d director tags' % len(directors))
  if len(directors):
    for director in directors:
      if director != u'...':
        Log.Debug(' . . . . director: "%s"' % director)
        metadata.directors.add(director)


def parseYearInfo(infoRowElem, metadata):
  yearText = infoRowElem.xpath('.//a/text()')
  if len(yearText):
    Log.Debug(' ... parsed year: %s' % yearText[0])
    try:
      metadata.year = int(yearText[0])
    except:
      Log.Error(getExceptionInfo('unable to parse year'))


def parseWritersInfo(infoRowElem, metadata):
  writers = infoRowElem.xpath('.//a/text()')
  Log.Debug(' ... parsed %d writer tags' % len(writers))
  if len(writers):
    for writer in writers:
      if writer != u'...':
        Log.Debug(' . . . . writer "%s"' % writer)
        metadata.writers.add(writer)


def parseGenresInfo(infoRowElem, metadata):
  genres = infoRowElem.xpath('.//a/text()')
  Log.Debug(' ... parsed %d genre tags' % len(genres))
  if len(genres):
    for genre in genres:
      if genre != u'...':
        genre = genre.capitalize()
        Log.Debug(' . . . . genre: "%s"' % genre)
        metadata.genres.add(genre)


def parseTaglineInfo(infoRowElem, metadata):
  taglineParts = infoRowElem.xpath('./td[@style]/text()')
  if len(taglineParts):
    tagline = ' '.join(taglineParts)
    tagline = sanitizeString(tagline)
    tagline = tagline.strip('- ')
    Log.Debug(' ... parsed tagline: "%s"' % tagline[:20])
    metadata.tagline = tagline


def parseContentRatingInfo(infoRowElem, metadata):
  metadata.content_rating = None
  contentRatingElems = infoRowElem.xpath('.//a/img/attribute::src')
  if len(contentRatingElems) == 1:
    match = re.search('\/([^/.]+?)\.gif$',contentRatingElems[0])
    if match is not None:
      contentRating = match.groups(1)[0]
      Log.Debug(' ... parsed content rating: "%s"' % str(contentRating))
      metadata.content_rating = contentRating


def parseDurationInfo(infoRowElem, metadata):
  durationElems = infoRowElem.xpath('./td[@class="time"]/text()')
  if len(durationElems) > 0:
    try:
      match = MATCHER_MOVIE_DURATION.search(durationElems[0])
      if match is not None:
        duration = int(int(match.groups(1)[0])) * 1000
        Log.Debug(' ... parsed duration: "%s"' % str(duration))
        metadata.duration = duration
    except:
      Log.Error(getExceptionInfo('unable to parse duration'))


def parseOriginallyAvailableInfo(infoRowElem, metadata):
  originalDateElems = infoRowElem.xpath('.//a/text()')
  if len(originalDateElems):
    try:
      (dd, mm, yy) = originalDateElems[0].split()
      if len(dd) == 1:
        dd = '0' + dd
      mm = RU_MONTH[mm]
      originalDate = Datetime.ParseDate(yy+'-'+mm+'-'+dd).date()
      Log.Debug(' ... parsed originally available date: "%s"' % str(originalDate))
      metadata.originally_available_at = originalDate
    except:
      Log.Error(getExceptionInfo('unable to parse originally available date'))


def parsePeoplePageInfo(titlePage, metadata, kinoPoiskId):
  """ Parses people - mostly actors - here (on this page)
      we have access to extensive information about all who participated
      creating this movie.
      @param actors - actors that are parsed from the main movie title page;
  """
  # First, parse actors from the main title page.
  parseAllActors = Prefs[PREF_GET_ALL_ACTORS]
  actorsMap = parseActorsInfoIntoMap(titlePage)
  mainActors = []
  otherActors = []

  # Now, parse a dedicated 'people' page.
  page = XMLElementFromURLWithRetries(KINOPOISK_PEOPLE % kinoPoiskId)
  if page is None:
    Log.Debug('NO people page')
    for actorName in actorsMap.keys():
      addActorToMetadata(metadata, actorName, None)
    return
  personType = None
  peopleTags = page.xpath('//div[@id="content_block"]/table/tr/td/div[@class="block_left"]/*')
  for peopleTagElem in peopleTags:
    try:
      if peopleTagElem.tag == 'table':
        personType = None
        tagElems = peopleTagElem.xpath('./tr/td[@style="padding-left:20px;border-bottom:2px solid #f60;font-size:16px"]/text()')
        if len(tagElems):
          tagName = tagElems[0]
          if tagName == u'Актеры':
            personType = 'actor'
          elif tagName == u'Директора фильма' or tagName == u'Режиссеры':
            personType = 'director'
          elif tagName == u'Сценаристы':
            personType = 'writer'
          elif tagName == u'Операторы' or \
               tagName == u'Монтажеры' or \
               tagName == u'Композиторы' or \
               tagName == u'Художники':
            # Skip these tags for now.
            personType = None
            Log.Debug('skipping an unsupported tag "%s"' % tagName)
          else:
            Log.Debug('skipping an unknown tag "%s"' % tagName)
      elif peopleTagElem.tag == 'div':
        personNameElems = peopleTagElem.xpath('./div/div/div[@class="name"]/a/text()')
        personName = None
        if len(personNameElems):
          personName = personNameElems[0]
        if personType == 'actor':
          actorRoleElems = peopleTagElem.xpath('./div/div/div[@class="role"]/text()')
          if len(actorRoleElems):
            roleName = str(actorRoleElems[0]).strip().strip('. ')
            if personName in actorsMap:
              Log.Debug(' . . . . parsed main actor "%s" with role "%s"' % (personName, roleName))
              mainActors.append((personName, roleName))
              del actorsMap[personName]
            elif parseAllActors:
              Log.Debug(' . . . . parsed other actor "%s" with role "%s"' % (personName, roleName))
              otherActors.append((personName, roleName))
      else:
        personType = None
    except:
      Log.Error(getExceptionInfo('unable to parse a people tag'))

  # Adding main actors that were found on the 'people' page.
  for personName, roleName in mainActors:
    addActorToMetadata(metadata, personName, roleName)
  # Adding main actors that were NOT found on the 'people' page.
  for actorName in actorsMap.keys():
    addActorToMetadata(metadata, actorName, None)
  # Adding other actors if requested.
  for personName, roleName in otherActors:
    addActorToMetadata(metadata, personName, roleName)


def addActorToMetadata(metadata, actorName, roleName):
  role = metadata.roles.new()
  role.actor = actorName
  if roleName is not None and roleName != '':
    role.role = roleName


def parsePostersInfo(metadata, kinoPoiskId):
  """ Fetches and populates posters metadata.
      Получение адресов постеров.
  """
  Log.Debug('fetching posters for title id "%s"...' % str(kinoPoiskId))
  loadAllPages = localPrefs.maxPosters > 20
  posterPages = fetchImageDataPages(KINOPOISK_POSTERS, kinoPoiskId, loadAllPages)

  # Thumbnail will be added only if there are no other results.
  thumb = {
    'thumbImgUrl': None,
    'fullImgUrl': KINOPOISK_MOVIE_THUMBNAIL % kinoPoiskId,
    'fullImgWidth': KINOPOISK_MOVIE_THUMBNAIL_WIDTH,
    'fullImgHeight': KINOPOISK_MOVIE_THUMBNAIL_HEIGHT,
    'index': 0,
    'score': 0 # Initial score.
  }

  # Получение URL постеров.
  updateImageMetadata(posterPages, metadata, localPrefs.maxPosters, True, thumb)


def parseBackgroundArtInfo(metadata, kinoPoiskId):
  """ Fetches and populates background art metadata.
      Получение адресов задников.
  """
  Log.Debug('fetching background art for title id "%s"...' % str(kinoPoiskId))
  loadAllPages = localPrefs.maxArt > 20
  artPages = fetchImageDataPages(KINOPOISK_ART, kinoPoiskId, loadAllPages)
  if not len(artPages):
    Log.Debug(' ... determined NO background art URLs')
    return

  # Получение урлов задников.
  updateImageMetadata(artPages, metadata, localPrefs.maxArt, False, None)


def XMLElementFromURLWithRetries(url):
  """ Fetches a given URL and converts it to XML.
      Функция преобразования html-кода в xml-код.
  """
  Log.Debug('requesting URL: "%s"...' % url)
  res = httpRequest(url)
  if res is None:
    return None
  else:
    res = str(res).decode(ENCODING_KINOPOISK_PAGE)
#    Log.Debug(res)
    return HTML.ElementFromString(res)


def computeTitleScore(mediaName, mediaYear, title, year, itemIndex):
  """ Compares page and media titles taking into consideration
      media item's year and title values. Returns score [0, 100].
      Search item scores 100 when:
        - it's first on the list of KinoPoisk results; AND
        - it equals to the media title (ignoring case) OR all media title words are found in the search item; AND
        - search item year equals to media year.

      For now, our title scoring is pretty simple - we check if individual words
      from media item's title are found in the title from search results.
      We should also take into consideration order of words, so that "One Two" would not
      have the same score as "Two One".
  """
  Log.Debug('comparing "%s"-%s with "%s"-%s...' % (str(mediaName), str(mediaYear), str(title), str(year)))
  # Max score is when both title and year match exactly.
  score = 100
  if str(mediaYear) != str(year):
    score = score - SCORE_PENALTY_YEAR_WRONG
  mediaName = mediaName.lower()
  title = title.lower()
  if mediaName != title:
    # Look for title word matches.
    words = mediaName.split()
    wordMatches = 0
    encodedTitle = title.encode(ENCODING_PLEX)
    for word in words:
      # FYI, using '\b' was troublesome (because of string encoding issues, I think).
      matcher = re.compile('^(|.*[\W«])%s([\W»].*|)$' % word.encode(ENCODING_PLEX), re.UNICODE)
      if matcher.search(encodedTitle) is not None:
        wordMatches += 1
    wordMatchesScore = float(wordMatches) / len(words)
    score = score - ((float(1) - wordMatchesScore) * SCORE_PENALTY_NO_MATCH)

  # IMPORTANT: always return an int.
  score = int(score)
  Log.Debug('***** title scored %d' % score)
  return score


def resetMediaMetadata(metadata):
  metadata.genres.clear()
  metadata.directors.clear()
  metadata.writers.clear()
  metadata.roles.clear()
  metadata.countries.clear()
  metadata.collections.clear()
  metadata.studio = ''
  metadata.summary = ''
  metadata.title = ''
#        metadata.trivia = ''
#        metadata.quotes = ''
  metadata.year = None
  metadata.originally_available_at = None
  metadata.original_title = ''
  metadata.duration = None


def httpRequest(url):
  """ Fetches a content given its URL.
      Функция для получения html-содержимого.
  """
  time.sleep(1)
  for i in range(3):
    try:
      return HTTP.Request(url, headers = {'User-agent': USER_AGENT, 'Accept': 'text/html'})
    except:
      Log.Error(getExceptionInfo('Error fetching URL: "%s".' % url))
      time.sleep(1)
  return None


def sanitizeString(msg):
  """ Функция для замены специальных символов.
  """
  res = msg.replace(u'\x85', u'...')
  res = res.replace(u'\x97', u'-')
  return res


def ensureAbsoluteUrl(url):
  """ Returns an absolute URL (starts with http://)
      pre-pending base kinoposk URL to the passed URL when necessary.
  """
  if url is None or len(url.strip()) < 10:
    return None
  url = url.strip()
  if url[0:4] == 'http':
    return url
  return KINOPOISK_BASE + url.lstrip('/')


def getExceptionInfo(msg):
  excInfo = sys.exc_info()
  return '%s; exception: %s; cause: %s' % (msg, excInfo[0], excInfo[1])


def parseXpathElementValue(elem, path):
  values = elem.xpath(path)
  if len(values):
    return values[0]
  return None


def updateImageMetadata(pages, metadata, maxImages, isPoster, thumb):
  imageDictList = []
  # Parsing URLs from the passed pages.
  maxImagesToParse = maxImages + 2 # Give it a couple of extras to choose from.
  for page in pages:
    maxImagesToParse = parseImageDataFromPhotoTableTag(page, imageDictList, maxImagesToParse)
    if not maxImagesToParse:
      break

  # Sort results according to their score. Сортируем результаты.
  scorePosterResults(imageDictList, isPoster)
  imageDictList.sort(key=operator.itemgetter('score'))
  imageDictList.reverse()
  Log.Debug('image search produced %d results:' % len(imageDictList))
#  index = 0
#  for result in imageDictList:
#    Log.Debug(' ... result %d: index="%s", score="%s", URL="%s".' % (index, result['index'], result['score'], result['fullImgUrl']))
#    index += 1

  # Thumbnail is added only if there are no other results.
  if not len(imageDictList) and thumb is not None:
    imageDictList.append(thumb)

  # Now, walk over the top N (<max) results and update metadata.
  if isPoster:
    imagesContainer = metadata.posters
  else:
    imagesContainer = metadata.art
  index = 0
  validNames = list()
  for result in imageDictList:
    fullImgUrl = result['fullImgUrl']
    validNames.append(fullImgUrl)
    if fullImgUrl not in imagesContainer:
      thumbImgUrl = result['thumbImgUrl']
      if thumbImgUrl is None:
        img = fullImgUrl
      else:
        img = thumbImgUrl
      try:
        imagesContainer[fullImgUrl] = Proxy.Preview(HTTP.Request(img), sort_order = index)
        index += 1
      except:
        Log.Error(getExceptionInfo('Error generating preview for: "%s".' % str(img)))
    if index >= maxImages:
      break
  imagesContainer.validate_keys(validNames)


def fetchImageDataPages(urlTemplate, kinoPoiskId, getAllPages):
  pages = []
  page = XMLElementFromURLWithRetries(urlTemplate % (kinoPoiskId, 1))
  if page is not None:
    pages.append(page)
    if getAllPages:
      anchorElems = page.xpath('//div[@class="navigator"]/ul/li[@class="arr"]/a')
      if len(anchorElems):
        nav = parseXpathElementValue(anchorElems[-1], './attribute::href')
        match = re.search('page\/(\d+?)\/$', nav)
        if match is not None:
          try:
            for pageIndex in range(2, int(match.groups(1)[0]) + 1):
              page =  XMLElementFromURLWithRetries(urlTemplate % (kinoPoiskId, pageIndex))
              if page is not None:
                pages.append(page)
          except:
            Log.Error(getExceptionInfo('unable to parse image art page'))
  return pages


def parseImageDataFromPhotoTableTag(page, imageDictList, maxImagesToParse):
  anchorElems = page.xpath('//table[@class="fotos" or @class="fotos fotos1" or @class="fotos fotos2"]/tr/td/a')
  for anchorElem in anchorElems:
    imageDict = None
    try:
      currItemIndex = len(imageDictList)
      imageDict = parseImageDataFromAnchorElement(anchorElem, currItemIndex)
    except:
      Log.Error(getExceptionInfo('unable to parse image URLs'))
    if imageDict is None:
      Log.Debug('no URLs - skipping an image')
      continue
    else:
      imageDictList.append(imageDict)
      Log.Debug('GOT URLs for an image: index=%d, thumb="%s", full="%s" (%sx%s)' %
          (imageDict['index'], str(imageDict['thumbImgUrl']), str(imageDict['fullImgUrl']),
          str(imageDict['fullImgWidth']), str(imageDict['fullImgHeight'])))
      maxImagesToParse = maxImagesToParse - 1
      if not maxImagesToParse:
        break
  return maxImagesToParse


def parseImageDataFromAnchorElement(anchorElem, index):
  thumbSizeUrl = None
  fullSizeUrl = None
  fullSizeDimensions = None, None
  fullSizeProxyPageUrl = anchorElem.get('href')
  thumbSizeImgElem = parseXpathElementValue(anchorElem, './img')
  if thumbSizeImgElem is not None:
    thumbSizeUrl = thumbSizeImgElem.get('src')
    if thumbSizeUrl is not None:
      thumbSizeUrl = ensureAbsoluteUrl(thumbSizeUrl)

  if fullSizeProxyPageUrl is not None:
    fullSizeProxyPage = XMLElementFromURLWithRetries(ensureAbsoluteUrl(fullSizeProxyPageUrl))
    if fullSizeProxyPage is not None:
      imageElem = parseXpathElementValue(fullSizeProxyPage, '//img[@id="image"]')
      if imageElem is not None:
        fullSizeUrl = imageElem.get('src')
        fullSizeDimensions = parseImageElemDimensions(imageElem)

  # If we have no full size image URL, we could use the thumb's.
  if fullSizeUrl is None and thumbSizeUrl is not None:
      Log.Debug('found no full size image, will use the thumbnail')
      fullSizeUrl = thumbSizeUrl

  if fullSizeUrl is None and thumbSizeUrl is None:
    return None
  return {
    'thumbImgUrl': thumbSizeUrl,
    'fullImgUrl': ensureAbsoluteUrl(fullSizeUrl),
    'fullImgWidth': fullSizeDimensions[0],
    'fullImgHeight': fullSizeDimensions[1],
    'index': index,
    'score': 0 # Initial score.
    }

def scorePosterResults(imageDictList, isPoster):
  for imageDict in imageDictList:
    Log.Debug('-------Scoring image %sx%s with index %d:\nfull image URL: "%s"\nthumb image URL: %s' %
                    (str(imageDict['fullImgWidth']), str(imageDict['fullImgHeight']), imageDict['index'], str(imageDict['fullImgUrl']), str(imageDict['thumbImgUrl'])))
    score = 0
    fullImgUrl = imageDict['fullImgUrl']
    if fullImgUrl is None:
      imageDict['score'] = 0
      continue

    if imageDict['index'] < IMAGE_SCORE_MAX_NUMBER_OF_ITEMS:
      # Score bonus from index for items below 10 on the list.
      bonus = IMAGE_SCORE_ITEM_ORDER_BONUS_MAX * \
          ((IMAGE_SCORE_MAX_NUMBER_OF_ITEMS - imageDict['index']) / float(IMAGE_SCORE_MAX_NUMBER_OF_ITEMS))
      Log.Debug('++++ adding order bonus: +%s' % str(bonus))
      score += bonus

    fullImgWidth = imageDict['fullImgWidth']
    fullImgHeight = imageDict['fullImgHeight']
    if fullImgWidth is not None and fullImgHeight is not None:
      # Get a resolution bonus if width*height is more than a certain min value.
      if isPoster:
        minPx = POSTER_SCORE_MIN_RESOLUTION_PX
        maxPx = POSTER_SCORE_MAX_RESOLUTION_PX
        bestRatio = POSTER_SCORE_BEST_RATIO
      else:
        minPx = ART_SCORE_MIN_RESOLUTION_PX
        maxPx = ART_SCORE_MAX_RESOLUTION_PX
        bestRatio = ART_SCORE_BEST_RATIO
      pixelsCount = fullImgWidth * fullImgHeight
      if pixelsCount > minPx:
        if pixelsCount > maxPx:
          pixelsCount = maxPx
        bonus = float(IMAGE_SCORE_RESOLUTION_BONUS_MAX) * \
            float((pixelsCount - minPx)) / float((maxPx - minPx))
        Log.Debug('++++ adding resolution bonus: +%s' % str(bonus))
        score += bonus
      else:
        Log.Debug('++++ no resolution bonus for %dx%d' % (fullImgWidth, fullImgHeight))

      # Get an orientation (Portrait vs Landscape) bonus. (we prefer images that are have portrait orientation.
      ratio = fullImgWidth / float(fullImgHeight)
      radioDiff = math.fabs(bestRatio - ratio)
      if radioDiff < 0.5:
        bonus = IMAGE_SCORE_RATIO_BONUS_MAX * (0.5 - radioDiff) * 2.0
        Log.Debug('++++ adding "%s" ratio bonus: +%s' % (str(ratio), str(bonus)))
        score += bonus
      else:
        # Ignoring Landscape ratios.
        Log.Debug('++++ no ratio bonus for %dx%d' % (fullImgWidth, fullImgHeight))
    else:
      Log.Debug('++++ no size set - no resolution and no ratio bonus')

    # Get a bonus if image has a separate thumbnail URL.
    thumbImgUrl = imageDict['thumbImgUrl']
    if thumbImgUrl is not None and fullImgUrl != thumbImgUrl:
      Log.Debug('++++ adding thumbnail bonus: +%d' % IMAGE_SCORE_THUMB_BONUS)
      score += IMAGE_SCORE_THUMB_BONUS

    Log.Debug('--------- SCORE: %d' % int(score))
    imageDict['score'] = int(score)


def readPluginPreferences():
  # Setting cache expiration time.
  prefCache = Prefs[PREF_CACHE_TIME_NAME]
  if prefCache == u'1 минута':
    cacheExp = CACHE_1MINUTE
  elif prefCache == u'1 час':
    cacheExp = CACHE_1HOUR
  elif prefCache == u'1 день':
    cacheExp = CACHE_1DAY
  elif prefCache == u'1 неделя':
    cacheExp = CACHE_1DAY
  elif prefCache == u'1 месяц':
    cacheExp = CACHE_1MONTH
  elif prefCache == u'1 год':
    cacheExp = CACHE_1MONTH * 12
  else:
    cacheExp = PREF_CACHE_TIME_DEFAULT
  HTTP.CacheTime = cacheExp

  localPrefs.maxPosters = int(Prefs[PREF_MAX_POSTERS_NAME])
  localPrefs.maxArt = int(Prefs[PREF_MAX_ART_NAME])
  localPrefs.getAllActors = Prefs[PREF_GET_ALL_ACTORS]

  Log.Debug('PREF: Setting cache expiration to %d seconds (%s).' % (cacheExp, prefCache))
  Log.Debug('PREF: Max poster results is set to %d.' % localPrefs.maxPosters)
  Log.Debug('PREF: Max art results is set to %d.' % localPrefs.maxArt)
  Log.Debug('PREF: Parse all actors is set to %s.' % str(localPrefs.getAllActors))


def parseImageElemDimensions(imageElem):
  """ Determines dimensions of a given image element and returns it as a (width, height) tuple,
      where width and height are of type int or None.
  """
  style = imageElem.get('style')
  width = imageElem.get('width')
  if width is None and style is not None:
    match = MATCHER_WIDTH_FROM_STYLE.search(style)
    if match is not None:
      width = match.groups()[0]
  height = imageElem.get('height')
  if height is None and style is not None:
    match = MATCHER_HEIGHT_FROM_STYLE.search(style)
    if match is not None:
      height = match.groups()[0]
  if width is not None:
    width = int(width)
  if height is not None:
    height = int(height)
  return width, height