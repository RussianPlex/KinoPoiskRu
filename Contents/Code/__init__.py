# -*- coding: utf-8 -*-
#
# Russian metadata plugin for Plex, which uses http://www.kinopoisk.ru/ to get the tag data.
# Плагин для обновления информации о фильмах использующий КиноПоиск (http://www.kinopoisk.ru/).
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
# @author ptath
# @author Stillness-2
# @author zhenya (Yevgeny Nyden)
#

import datetime, string, re, time, math, operator, unicodedata, hashlib
import common

IS_DEBUG = True # TODO - DON'T FORGET TO SET IT TO FALSE FOR A DISTRO.

ENCODING_KINOPOISK_PAGE = 'cp1251'

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

# Русские месяца, пригодится для определения дат.
RU_MONTH = {u'января': '01', u'февраля': '02', u'марта': '03', u'апреля': '04', u'мая': '05', u'июня': '06', u'июля': '07', u'августа': '08', u'сентября': '09', u'октября': '10', u'ноября': '11', u'декабря': '12'}


# Plugin preferences.
# When changing default values here, also update the DefaultPrefs.json file.
PREFS = common.Preferences(
  ('kinopoisk_pref_image_choice', common.IMAGE_CHOICE_BEST),
  ('kinopoisk_pref_max_posters', 6),
  ('kinopoisk_pref_max_art', 4),
  ('kinopoisk_pref_get_all_actors', False),
  ('kinopoisk_pref_cache_time', CACHE_1MONTH))


def Start():
  Log.Info('***** START ***** %s' % common.USER_AGENT)
  PREFS.readPluginPreferences()


def ValidatePrefs():
  Log.Info('***** updating preferences...')
  PREFS.readPluginPreferences()


class KinoPoiskRuAgent(Agent.Movies):
  name = 'KinoPoiskRu'
  languages = [Locale.Language.Russian]
  primary_provider = True
  fallback_agent = False
  accepts_from = None
  contributes_to = None


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

    page = common.getElementFromHttpRequest(KINOPOISK_SEARCH % mediaName.replace(' ', '%20'), ENCODING_KINOPOISK_PAGE)
    if page is None:
      Log.Warn('nothing was found on kinopoisk for media name "%s"' % mediaName)
    else:
      # Если страница получена, берем с нее перечень всех названий фильмов.
      Log.Debug('got a kinopoisk page to parse...')
      divInfoElems = page.xpath('//self::div[@class="info"]/p[@class="name"]/a[contains(@href,"/level/1/film/")]/..')
      itemIndex = 0
      altTitle = None
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

                # Try to parse the alternative (original) title. Ignore failures.
                # This is a <span> below the title <a> tag.
                try:
                  altTitle = divInfoElem.xpath('../span[1]/text()')[0]
                  altTitle = altTitle.split(',')[0].strip()
                except:
                  pass
                score = common.scoreMediaTitleMatch(mediaName, mediaYear, title, altTitle, year, itemIndex)
                results.Append(MetadataSearchResult(id=kinoPoiskId, name=title, year=year, lang=lang, score=score))
            else:
              Log.Warn('unable to find film anchor elements for title "%s"' % mediaName)
          except:
            common.logException('failed to parse div.info container')
          itemIndex += 1
      else:
        Log.Warn('nothing was found on kinopoisk for media name "%s"' % mediaName)
        # TODO(zhenya): investigate 1 we need this clause at all (haven't seen this happening).
        # Если не нашли там текст названия, значит сайт сразу дал нам страницу с фильмом (хочется верить =)
        try:
          title = page.xpath('//h1[@class="moviename-big"]/text()')[0].strip()
          kinoPoiskId = re.search('\/film\/(.+?)\/', page.xpath('//a[contains(@href,"/level/19/film/")]/attribute::href')[0]).groups(1)[0]
          year = page.xpath('//a[contains(@href,"year")]/text()')[0].strip()
          score = common.scoreMediaTitleMatch(mediaName, mediaYear, title, altTitle, year, itemIndex)
          results.Append(MetadataSearchResult(id=kinoPoiskId, name=title, year=year, lang=lang, score=score))
        except:
          common.logException('failed to parse a KinoPoisk page')

    # Sort results according to their score (Сортируем результаты).
    results.Sort('score', descending=True)
    if IS_DEBUG:
      common.printSearchResults(results)
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
    filename = part.file.decode(common.ENCODING_PLEX)
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
    titlePage =  common.getElementFromHttpRequest(KINOPOISK_TITLE_PAGE_URL % kinoPoiskId, ENCODING_KINOPOISK_PAGE)
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
        if PREFS.imageChoice != common.IMAGE_CHOICE_NOTHING:
          parsePostersInfo(metadata, kinoPoiskId)                                 # Posters. Постеры.
          parseBackgroundArtInfo(metadata, kinoPoiskId)                           # Background art. Задники.
        else:
          Log.Debug(' ... skipping parsing image art.')
#          metadata.posters.validate_keys([])
#          metadata.art.validate_keys([])
      except:
        common.logException('failed to update metadata for id %s' % kinoPoi1234skId)


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
      common.logException('unable to parse rating')


def parseStudioInfo(metadata, kinoPoiskId):
  page = common.getElementFromHttpRequest(KINOPOISK_STUDIO % kinoPoiskId, ENCODING_KINOPOISK_PAGE)
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
      common.logException('unable to parse year')


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
      common.logException('unable to parse duration')


def parseOriginallyAvailableInfo(infoRowElem, metadata):
  originalDateElems = infoRowElem.xpath('.//a/text()')
  if len(originalDateElems):
    try:
      (dd, mm, yy) = originalDateElems[0].split()
      if len(dd) == 1:
        dd = '0' + dd
      mm = RU_MONTH[mm]
      originalDate = Datetime.ParseDate(yy + '-' + mm + '-' + dd).date()
      Log.Debug(' ... parsed originally available date: "%s"' % str(originalDate))
      metadata.originally_available_at = originalDate
    except:
      common.logException('unable to parse originally available date')


def parsePeoplePageInfo(titlePage, metadata, kinoPoiskId):
  """ Parses people - mostly actors - here (on this page)
      we have access to extensive information about all who participated
      creating this movie.
  """
  # First, parse actors from the main title page.
  parseAllActors = PREFS.getAllActors
  actorsMap = parseActorsInfoIntoMap(titlePage)
  mainActors = []
  otherActors = []

  # Now, parse a dedicated 'people' page.
  page = common.getElementFromHttpRequest(KINOPOISK_PEOPLE % kinoPoiskId, ENCODING_KINOPOISK_PAGE)
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
      common.logException('unable to parse a people tag')

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
  loadAllPages = PREFS.maxPosters > 20
  posterPages = fetchImageDataPages(KINOPOISK_POSTERS, kinoPoiskId, loadAllPages)

  # Thumbnail might be added if there are no other results.
  thumb = common.Thumbnail(None,
    KINOPOISK_MOVIE_THUMBNAIL % kinoPoiskId,
    KINOPOISK_MOVIE_THUMBNAIL_WIDTH,
    KINOPOISK_MOVIE_THUMBNAIL_HEIGHT,
    0,
    0) # Initial score.

  # Получение URL постеров.
  updateImageMetadata(posterPages, metadata, PREFS.maxPosters, True, thumb)


def parseBackgroundArtInfo(metadata, kinoPoiskId):
  """ Fetches and populates background art metadata.
      Получение адресов задников.
  """
  Log.Debug('fetching background art for title id "%s"...' % str(kinoPoiskId))
  loadAllPages = PREFS.maxArt > 20
  artPages = fetchImageDataPages(KINOPOISK_ART, kinoPoiskId, loadAllPages)
  if not len(artPages):
    Log.Debug(' ... determined NO background art URLs')
    return

  # Получение урлов задников.
  updateImageMetadata(artPages, metadata, PREFS.maxArt, False, None)


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


def parseXpathElementValue(elem, path):
  values = elem.xpath(path)
  if len(values):
    return values[0]
  return None


def updateImageMetadata(pages, metadata, maxImages, isPoster, thumb):
  thumbnailList = []
  # Parsing URLs from the passed pages.
  maxImagesToParse = maxImages + 2  # Give it a couple of extras to choose from.
  for page in pages:
    maxImagesToParse = parseImageDataFromPhotoTableTag(page, thumbnailList, isPoster, maxImagesToParse)
    if not maxImagesToParse:
      break

  # Thumbnail is added only if there are no other results.
  if not len(thumbnailList):
    if PREFS.imageChoice == common.IMAGE_CHOICE_ALL and thumb is not None:
      thumbnailList.append(thumb)
  else:
    # Sort results according to their score and chop out extraneous images. Сортируем результаты.
    thumbnailList = sorted(thumbnailList, key=lambda t : t.score, reverse=True)[0:maxImages]
  if IS_DEBUG:
    common.printImageSearchResults(thumbnailList)

  # Now, walk over the top N (<max) results and update metadata.
  if isPoster:
    imagesContainer = metadata.posters
  else:
    imagesContainer = metadata.art
  index = 0
  validNames = list()
  for result in thumbnailList:
    if result.thumbImgUrl is None:
      img = result.fullImgUrl
    else:
      img = result.thumbImgUrl
    validNames.append(result.fullImgUrl)
    try:
      imagesContainer[result.fullImgUrl] = Proxy.Preview(HTTP.Request(img), sort_order = index)
      index += 1
    except:
      common.logException('Error generating preview for: "%s".' % str(img))
  imagesContainer.validate_keys(validNames)


def fetchImageDataPages(urlTemplate, kinoPoiskId, getAllPages):
  pages = []
  page = common.getElementFromHttpRequest(urlTemplate % (kinoPoiskId, 1), ENCODING_KINOPOISK_PAGE)
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
              page =  common.getElementFromHttpRequest(urlTemplate % (kinoPoiskId, pageIndex), ENCODING_KINOPOISK_PAGE)
              if page is not None:
                pages.append(page)
          except:
            common.logException('unable to parse image art page')
  return pages


def parseImageDataFromPhotoTableTag(page, thumbnailList, isPoster, maxImagesToParse):
  anchorElems = page.xpath('//table[@class="fotos" or @class="fotos fotos1" or @class="fotos fotos2"]/tr/td/a')
  currItemIndex = len(thumbnailList)
  for anchorElem in anchorElems:
    thumb = None
    try:
      thumb = parseImageDataFromAnchorElement(anchorElem, currItemIndex)
      currItemIndex += 1
    except:
      common.logException('unable to parse image URLs')
    if thumb is None:
      Log.Debug('no URLs - skipping an image')
      continue
    else:
      common.scoreThumbnailResult(thumb, isPoster)
      if PREFS.imageChoice == common.IMAGE_CHOICE_BEST and \
         thumb.score < common.IMAGE_SCORE_BEST_THRESHOLD:
        continue
      thumbnailList.append(thumb)
      Log.Debug('GOT URLs for an image: index=%d, thumb="%s", full="%s" (%sx%s)' %
          (thumb.index, str(thumb.thumbImgUrl), str(thumb.fullImgUrl),
          str(thumb.fullImgWidth), str(thumb.fullImgHeight)))
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
    fullSizeProxyPage = common.getElementFromHttpRequest(ensureAbsoluteUrl(fullSizeProxyPageUrl), ENCODING_KINOPOISK_PAGE)
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
  return common.Thumbnail(thumbSizeUrl,
    ensureAbsoluteUrl(fullSizeUrl),
    fullSizeDimensions[0],
    fullSizeDimensions[1],
    index,
    0) # Initial score.


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