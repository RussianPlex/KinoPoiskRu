# -*- coding: utf-8 -*-
import datetime, string, re, time, unicodedata, hashlib, urlparse, types, sys

KINOPOISK_IS_DEBUG = True

# Current log level.
# Supported values are: 0 = none, 1 = error, 2 = warning, 3 = info, 4 = fine, 5 = finest.
kinoPoiskLogLevel = 5 # Default is error.

KINOPOISK_PAGE_ENCODING = 'cp1251'

# Разные страницы сайта.
KINOPOISK_BASE = 'http://www.kinopoisk.ru/'
KINOPOISK_TITLE_PAGE_URL = KINOPOISK_BASE + 'level/1/film/%s/'
KINOPOISK_PEOPLE = KINOPOISK_BASE + 'level/19/film/%s/'
KINOPOISK_STUDIO = KINOPOISK_BASE + 'level/91/film/%s/'
KINOPOISK_POSTERS = KINOPOISK_BASE + 'level/17/film/%s/page/%d/'
KINOPOISK_ART = KINOPOISK_BASE + 'level/13/film/%s/page/%d/'
KINOPOISK_MOVIE_THUMBNAIL = 'http://st.kinopoisk.ru/images/film/%s'

# Страница поиска.
KINOPOISK_SEARCH = 'http://www.kinopoisk.ru/index.php?first=no&kp_query=%s'

# Compiled regex matchers.
MATCHER_MOVIE_DURATION = re.compile('\s*(\d+).*?', re.UNICODE | re.DOTALL)


SCORE_PENALTY_ITEM_ORDER = 3
SCORE_PENALTY_YEAR_WRONG = 4

# Рейтинги.
DEFAULT_MPAA = u'R'
MPAA_AGE = {u'G': 0, u'PG': 11, u'PG-13': 13, u'R': 16, u'NC-17': 17}

# Русские месяца, пригодится для определения дат.
RU_MONTH = {u'января': '01', u'февраля': '02', u'марта': '03', u'апреля': '04', u'мая': '05', u'июня': '06', u'июля': '07', u'августа': '08', u'сентября': '09', u'октября': '10', u'ноября': '11', u'декабря': '12'}

# Под кого маскируемся =).
UserAgent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_2) AppleWebKit/534.51.22 (KHTML, like Gecko) Version/5.1.1 Safari/534.51.22'

# TODO(zhenya): load these from user preferences.
MAX_POSTERS = 5
MAX_BACKGROUND_ART = 5
CACHE_TIME = CACHE_1DAY


def Start():
  sendToInfoLog('***** START ***** %s' % USER_AGENT)
  # Setting cache experation time.
  HTTP.CacheTime = CACHE_TIME

class PlexMovieAgent(Agent.Movies):
  name = 'KinoPoiskRu'
  languages = [Locale.Language.Russian]
  accepts_from = ['com.plexapp.agents.localmedia']

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
    sendToInfoLog('SEARCH START <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
    mediaName = media.name
    mediaYear = media.year
    sendToInfoLog('searching for name="%s", year="%s", guid="%s", hash="%s"...' %
        (str(mediaName), str(mediaYear), str(media.guid), str(media.hash)))

    # Получаем страницу поиска
    sendToFinestLog('quering kinopoisk...')
    page = XMLElementFromURLWithRetries(KINOPOISK_SEARCH % mediaName)
    if page:
      # Если страница получена, берем с нее перечень всех названий фильмов.
      sendToFineLog('got a kinopoisk page to parse...')
      divInfoElems = page.xpath('//self::div[@class="info"]/p[@class="name"]/a[contains(@href,"/level/1/film/")]/..')
      itemIndex = 0
      if len(divInfoElems):
        sendToFineLog('found %d results' % len(divInfoElems))
        for divInfoElem in divInfoElems:
          try:
            anchorFilmElem = divInfoElem.xpath('./a[contains(@href,"/level/1/film/")]/attribute::href')
            if len(anchorFilmElem):
              # Parse kinopoisk movie title id, title and year.
              match = re.search('\/film\/(.+?)\/', anchorFilmElem[0])
              if match:
                kinoPoiskId = match.groups(1)[0]
                title = divInfoElem.xpath('.//a[contains(@href,"/level/1/film/")]/text()')[0]
                year = divInfoElem.xpath('.//span[@class="year"]/text()')[0]
                score = computeTitleScore(mediaName, mediaYear, title, year, itemIndex)
                results.Append(MetadataSearchResult(id=kinoPoiskId, name=title, year=year, lang=lang, score=score))
              else:
                sendToErrorLog('unable to parse movie title id')
            else:
              sendToWarnLog('unable to find film anchor elements for title "%s"' % mediaName)
          except:
            sendToErrorLog(getExceptionInfo('failed to parse div.info container'))
          itemIndex += 1
      else:
        sendToWarnLog('nothing was found on kinopoisk for media name "%s"' % mediaName)
        # TODO(zhenya): investigate whether we need this clause at all (haven't seen this happening).
        # Если не нашли там текст названия, значит сайт сразу дал нам страницу с фильмом (хочется верить =)
        try:
          title = page.xpath('//h1[@class="moviename-big"]/text()')[0].strip()
          kinoPoiskId = re.search('\/film\/(.+?)\/', page.xpath('//a[contains(@href,"/level/19/film/")]/attribute::href')[0]).groups(1)[0]
          year = page.xpath('//a[contains(@href,"year")]/text()')[0].strip()
          score = computeTitleScore(mediaName, mediaYear, title, year, itemIndex)
          results.Append(MetadataSearchResult(id=kinoPoiskId, name=title, year=year, lang=lang, score=score))
        except:
          sendToErrorLog(getExceptionInfo('failed to parse a KinoPoisk page'))
    else:
      sendToWarnLog('nothing was found on kinopoisk for media name "%s"' % mediaName)

    # Sort results according to their score (Сортируем результаты).
    results.Sort('score', descending=True)
    if kinoPoiskLogLevel >= 3:
      sendToInfoLog('search produced %d results:' % len(results))
      index = 0
      for result in results:
        sendToInfoLog(' ... result %d: id="%s", name="%s", year="%s", score="%d".' % (index, result.id, result.name, str(result.year), result.score))
        index += 1
    sendToInfoLog('SEARCH END <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


  ##############################################################################
  ############################# U P D A T E ####################################
  ##############################################################################
  def update(self, metadata, media, lang):
    """Updates the media title provided a KinoPoisk movie title id (metadata.guid).
       This method fetches an appropriate KinoPoisk page, parses it, and populates
       the passed media item record.
    """
    sendToInfoLog('UPDATE START <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
    part = media.items[0].parts[0]
    filename = part.file.decode('utf-8')
    sendToInfoLog('filename="%s", guid="%s"' % (filename, metadata.guid))

    matcher = re.compile(r'//(\d+)\?')
    match = matcher.search(metadata.guid)
    if match:
      kinoPoiskId = match.groups(1)[0]
    else:
      sendToErrorLog('KinoPoisk movie title id is not specified!')
      raise Exception('ERROR: KinoPoisk movie title id is required!')
    sendToFineLog('parsed KinoPoisk movie title id: "%s"' % kinoPoiskId)

    self.updateMediaItem(metadata, kinoPoiskId)
    sendToInfoLog('UPDATE END <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


  def updateMediaItem(self, metadata, kinoPoiskId):

    parseAllActors = False

    titlePage =  XMLElementFromURLWithRetries(KINOPOISK_TITLE_PAGE_URL % kinoPoiskId)
    if titlePage:
      sendToFineLog('got a KinoPoisk page for movie title id: "%s"' % kinoPoiskId)
      try:
        resetMediaMetadata(metadata)
        parseTitleInfo(titlePage, metadata)                                       # Title. Название на русском языке.
        parseOriginalTitleInfo(titlePage, metadata)                               # Original title. Название на оригинальном языке.
        parseSummaryInfo(titlePage, metadata)                                     # Summary. Описание.
        parseRatingInfo(titlePage, metadata, kinoPoiskId)                         # Rating. Рейтинг.

        parseInfoTableTagAndUpdateMetadata(titlePage, metadata)

        parseStudioInfo(metadata, kinoPoiskId)                                    # Studio. Студия.


        parsePeoplePageInfo(titlePage, metadata, kinoPoiskId, parseAllActors)     # Actors, etc. Актёры. др.

        parsePostersInfo(metadata, kinoPoiskId)                                   # Posters. Постеры.
        parseBackgroundArtInfo(metadata, kinoPoiskId)                             # Background art. Задники.
      except:
        sendToErrorLog(getExceptionInfo('failed to update metadata for id %s' % kinoPoiskId))


def parseInfoTableTagAndUpdateMetadata(page, metadata):
  """ Parses the main info <table> tag, which we find by
      a css classname "info".
  """
  mainInfoTagRows = page.xpath('//table[@class="info"]/tr')
  sendToFineLog('parsed %d rows from the main info table tag' % len(mainInfoTagRows))
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
      sendToFinestLog('skipping an unsupported row: %s' % rowTypeKey)
      pass
    else:
      sendToWarnLog('UNRECOGNIZED row type: %s' % rowTypeKey)


def parseTitleInfo(page, metadata):
  title = page.xpath('//h1[@class="moviename-big"]/text()')[0].strip()
  if len(title):
    title = title.strip('- ')
    sendToFineLog(' ... parsed title: "%s"' % title)
    metadata.title = title


def parseOriginalTitleInfo(page, metadata):
  origTitle = page.xpath('//span[@style="color: #666; font-size: 13px"]/text()')
  if len(origTitle):
    origTitle = ' '.join(origTitle)
    origTitle = sanitizeString(origTitle).strip('- ')
    sendToFineLog(' ... parsed original title: "%s"' % origTitle)
    metadata.original_title = origTitle


def parseActorsInfoIntoMap(page):
  actorsMap = {}
  actors = page.xpath('//td[@class="actor_list"]/div/span')
  sendToFineLog(' ... parsed %d actor tags' % len(actors))
  for actorSpanTag in actors:
    actorList = actorSpanTag.xpath('./a[contains(@href,"/level/4/people/")]/text()')
    if len(actorList):
      for actor in actorList:
        if actor != u'...':
          sendToFineLog(' . . . . actor: "%s"' % actor)
          actorsMap[actor] = actor
  return actorsMap


def parseSummaryInfo(page, metadata):
  summaryParts = page.xpath('//div[@class="block_left_padtop"]/table/tr/td/table/tr/td/span[@class="_reachbanner_"]/div/text()')
  if len(summaryParts):
    summary = ' '.join(summaryParts)
    summary = sanitizeString(summary).strip()
    sendToFineLog(' ... parsed summary: "%s..."' % summary[:30])
    metadata.summary = summary


def parseRatingInfo(page, metadata, kinoPoiskId):
  ratingText = page.xpath('//form[@class="rating_stars"]/div[@id="block_rating"]//a[@href="/level/83/film/' + kinoPoiskId + '/"]/span/text()')
  if len(ratingText):
    try:
      rating = float(ratingText[0])
      sendToFineLog(' ... parsed rating "%s"' % str(rating))
      metadata.rating = rating
    except:
      sendToErrorLog(getExceptionInfo('unable to parse rating'))


def parseStudioInfo(metadata, kinoPoiskId):
  page = XMLElementFromURLWithRetries(KINOPOISK_STUDIO % kinoPoiskId)
  if not page:
    return
  studios = page.xpath(u'//table/tr/td[b="Производство:"]/../following-sibling::tr/td/a/text()')
  if len(studios):
    # Берем только первую студию.
    studio = studios[0].strip()
    sendToFineLog(' ... parsed studio: %s' % studio)
    metadata.studio = studio


def parseDirectorsInfo(infoRowElem, metadata):
  directors = infoRowElem.xpath('.//a/text()')
  sendToFineLog(' ... parsed %d director tags' % len(directors))
  if len(directors):
    for director in directors:
      if director != u'...':
        sendToFineLog(' . . . . director: "%s"' % director)
        metadata.directors.add(director)


def parseYearInfo(infoRowElem, metadata):
  yearText = infoRowElem.xpath('.//a/text()')
  if len(yearText):
    sendToFineLog(' ... parsed year: %s' % yearText[0])
    try:
      metadata.year = int(yearText[0])
    except:
      sendToErrorLog(getExceptionInfo('unable to parse year'))


def parseWritersInfo(infoRowElem, metadata):
  writers = infoRowElem.xpath('.//a/text()')
  sendToFineLog(' ... parsed %d writer tags' % len(writers))
  if len(writers):
    for writer in writers:
      if writer != u'...':
        sendToFineLog(' . . . . writer "%s"' % writer)
        metadata.writers.add(writer)


def parseGenresInfo(infoRowElem, metadata):
  genres = infoRowElem.xpath('.//a/text()')
  sendToFineLog(' ... parsed %d genre tags' % len(genres))
  if len(genres):
    for genre in genres:
      if genre != u'...':
        genre = genre.capitalize()
        sendToFineLog(' . . . . genre: "%s"' % genre)
        metadata.genres.add(genre)


def parseTaglineInfo(infoRowElem, metadata):
  taglineParts = infoRowElem.xpath('./td[@style]/text()')
  if len(taglineParts):
    tagline = ' '.join(taglineParts)
    tagline = sanitizeString(tagline)
    tagline = tagline.strip('- ')
    sendToFineLog(' ... parsed tagline: "%s"' % tagline[:20])
    metadata.tagline = tagline


def parseContentRatingInfo(infoRowElem, metadata):
  metadata.content_rating = None
  contentRatingElems = infoRowElem.xpath('.//a/img/attribute::src')
  if len(contentRatingElems) == 1:
    match = re.search('\/([^/.]+?)\.gif$',contentRatingElems[0])
    if match:
      contentRating = match.groups(1)[0]
      sendToFineLog(' ... parsed content rating: "%s"' % str(contentRating))
      metadata.content_rating = contentRating


def parseDurationInfo(infoRowElem, metadata):
  durationElems = infoRowElem.xpath('./td[@class="time"]/text()')
  if len(durationElems) > 0:
    try:
      match = MATCHER_MOVIE_DURATION.search(durationElems[0])
      if match:
        duration = int(int(match.groups(1)[0])) * 1000
        sendToFineLog(' ... parsed duration: "%s"' % str(duration))
        metadata.duration = duration
    except:
      sendToErrorLog(getExceptionInfo('unable to parse duration'))


def parseOriginallyAvailableInfo(infoRowElem, metadata):
  originalDateElems = infoRowElem.xpath('.//a/text()')
  if len(originalDateElems):
    try:
      (dd, mm, yy) = originalDateElems[0].split()
      if len(dd) == 1:
        dd = '0' + dd
      mm = RU_MONTH[mm]
      originalDate = Datetime.ParseDate(yy+'-'+mm+'-'+dd).date()
      sendToFineLog(' ... parsed originally available date: "%s"' % str(originalDate))
      metadata.originally_available_at = originalDate
    except:
      sendToErrorLog(getExceptionInfo('unable to parse originally available date'))


def parsePeoplePageInfo(titlePage, metadata, kinoPoiskId, parseAllActors):
  """ Parses people - mostly actors - here (on this page)
      we have access to extensive information about all who participated
      creating this movie.
      @param actors - actors that are parsed from the main movie title page;
      @param parseAllActors - true when we wan to parse all actors from this page;
  """
  # First, parse actors from the main title page.
  actorsMap = parseActorsInfoIntoMap(titlePage)
  mainActors = []
  otherActors = []

  # Now, parse a dedicated 'people' page.
  page = XMLElementFromURLWithRetries(KINOPOISK_PEOPLE % kinoPoiskId)
  if not page:
    sendToFinestLog('NO people page')
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
            sendToFinestLog('skipping an unsupported tag "%s"' % tagName)
          else:
            sendToFinestLog('skipping an unknown tag "%s"' % tagName)
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
              sendToFineLog(' . . . . parsed main actor "%s" with role "%s"' % (personName, roleName))
              mainActors.append((personName, roleName))
              del actorsMap[personName]
            elif parseAllActors:
              sendToFineLog(' . . . . parsed other actor "%s" with role "%s"' % (personName, roleName))
              otherActors.append((personName, roleName))
      else:
        personType = None
    except:
      sendToErrorLog(getExceptionInfo('unable to parse a people tag'))

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
  # Получение адресов постеров.
  pages = []
  page = XMLElementFromURLWithRetries(KINOPOISK_POSTERS % (kinoPoiskId, 1))
  if page:
    pages.append(page)
    nav = page.xpath('//div[@class="navigator"]/ul/li[@class="arr"]/a')
    if nav:
      nav = nav[-1].xpath('./attribute::href')[0]
      nav = re.search('page\/(\d+?)\/$', nav)
      try:
        for p_i in range(2, int(nav.groups(1)[0]) + 1):
          page =  XMLElementFromURLWithRetries(KINOPOISK_POSTERS % (kinoPoiskId, p_i))
          if page:
            pages.append(page)
      except:
        sendToErrorLog(getExceptionInfo('unable to parse posters page (1)'))

  # Получение URL постеров.
  totalFetched = 0
  if len(pages):
    for page in pages:
      imageUrls = page.xpath('//table[@class="fotos" or @class="fotos fotos1" or @class="fotos fotos2"]/tr/td/a/attribute::href')
      for imageUrl in imageUrls:
        sendToFineLog(' ... checking image with URL "%s"' % str(imageUrl))

        # Получаем страницу с картинкою.
        page = XMLElementFromURLWithRetries(KINOPOISK_BASE + imageUrl.lstrip('/'))
        if not page:
          continue
        imageUrlList = page.xpath('//table[@id="main_table"]/tr/td/a/img/attribute::src')
        if not len(imageUrlList):
          imageUrlList = page.xpath('//table[@id="main_table"]/*/td/img/attribute::src')
        if len(imageUrlList):
          totalFetched += 1
          imageUrl = ensureAbsoluteUrl(imageUrlList[0])
          name = imageUrl.split('/')[-1]
          if name not in metadata.posters:
            try:
              sendToFineLog(' ... fetching poster "%s" from URL "%s"' % (str(name), str(imageUrl)))
              imgResource = Proxy.Media(HTTP.Request(imageUrl), sort_order = 1)
              sendToFinestLog(' ... fetching poster SUCCESS')
              metadata.posters[name] = imgResource
            except:
              totalFetched -= 1
              sendToErrorLog(getExceptionInfo('unable to parse posters page (2)'))
          if totalFetched >= MAX_POSTERS:
            return
  else:
    sendToFineLog(' ... determined NO poster addresses')

  # If nothing is found, let's grab at least a small thumb.
  # На всякий случай забираем картинку низкого качества.
  if totalFetched <= 2:
    try:
      sendToFinestLog(' ... got too few posters, also getting a thumb')
      name = kinoPoiskId + '.jpg'
      imageUrl = KINOPOISK_MOVIE_THUMBNAIL % name
      if name not in metadata.posters:
        sendToFineLog(' ... fetching thumbnail "%s" from URL "%s"' % (str(name), str(imageUrl)))
        metadata.posters[name] = Proxy.Media(HTTP.Request(imageUrl), sort_order = 1)
        sendToFinestLog(' ... fetching thumbnail SUCCESS')
    except:
      sendToErrorLog(getExceptionInfo('unable to parse posters page (3)'))


def parseBackgroundArtInfo(metadata, kinoPoiskId):
  # Получение адресов задников
  pages = []
  page = XMLElementFromURLWithRetries(KINOPOISK_ART % (kinoPoiskId, 1))
  if page:
    pages.append(page)
    nav = page.xpath('//div[@class="navigator"]/ul/li[@class="arr"]/a')
    if nav:
      nav = nav[-1].xpath('./attribute::href')[0]
      nav = re.search('page\/(\d+?)\/$', nav)
      try:
        for p_i in range(2, int(nav.groups(1)[0]) + 1):
          page =  XMLElementFromURLWithRetries(KINOPOISK_ART % (kinoPoiskId, p_i))
          if page:
            pages.append(page)
      except:
        sendToErrorLog(getExceptionInfo('unable to parse background art page (1)'))

  # Получение урлов задников.
  totalFetched = 0
  if len(pages):
    for page in pages:
      imageUrls = page.xpath('//table[@class="fotos" or @class="fotos fotos1" or @class="fotos fotos2"]/tr/td/a/attribute::href')
      for imageUrl in imageUrls:
        # Получаем страницу с картинкою.
        page = XMLElementFromURLWithRetries(KINOPOISK_BASE + imageUrl.lstrip('/'))
        if not page:
          continue
        imageUrlList = page.xpath('//table[@id="main_table"]/tr/td/a/img/attribute::src')
        if not len(imageUrlList):
          imageUrlList = page.xpath('//table[@id="main_table"]/*/td/img/attribute::src')
        if len(imageUrlList) > 0:
          totalFetched += 1
          imageUrl = ensureAbsoluteUrl(imageUrlList[0])
          name = imageUrl.split('/')[-1]
          if name not in metadata.art:
            try:
              sendToFineLog(' ... fetching background art "%s" from URL "%s"' % (str(name), str(imageUrl)))
              imgResource = Proxy.Media(HTTP.Request(imageUrl), sort_order = 1)
              sendToFinestLog(' ... fetching poster SUCCESS')
              metadata.art[name] = imgResource
            except:
              totalFetched -= 1
              sendToErrorLog(getExceptionInfo('unable to parse background art page (2)'))
          if totalFetched >= MAX_BACKGROUND_ART:
            return
  else:
    sendToFineLog(' ... determined NO background art addresses')


def XMLElementFromURLWithRetries(url):
  """ Fetches a given URL and converts it to XML.
      Функция преобразования html-кода в xml-код.
  """
  sendToFinestLog('requesting URL: "%s"...' % url)
  res = httpRequest(url)
  if res:
    res = str(res).decode(KINOPOISK_PAGE_ENCODING)
#    sendToFinestLog(res)
    return HTML.ElementFromString(res)
  return None


def computeTitleScore(mediaName, mediaYear, title, year, itemIndex):
  # TODO(zhenya): consider title match when scoring.
  score = 100
  # Item order on the list penalizes the score.
  score = score - (itemIndex * SCORE_PENALTY_ITEM_ORDER)
  if mediaYear is not None and mediaYear != year:
    score = score - SCORE_PENALTY_YEAR_WRONG
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
      return HTTP.Request(url, headers = {'User-agent': UserAgent, 'Accept': 'text/html'})
    except:
      sendToErrorLog(getExceptionInfo('Error fetching URL: "%s".' % url))
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
  if url[0] == '/':
    url = url[1:]
  return KINOPOISK_BASE + url


def getExceptionInfo(msg):
  excInfo = sys.exc_info()
  return '%s; exception: %s; cause: %s' % (msg, excInfo[0], excInfo[1])


def sendToFinestLog(msg):
  if kinoPoiskLogLevel >= 5:
    sendToLog('FINEST: ' + msg)


def sendToFineLog(msg):
  if kinoPoiskLogLevel >= 4:
    sendToLog('FINE: ' + msg)


def sendToInfoLog(msg):
  if kinoPoiskLogLevel >= 3:
    sendToLog('INFO: ' + msg)


def sendToWarnLog(msg):
  if kinoPoiskLogLevel >= 2:
    sendToLog('WARN: ' + msg)


def sendToErrorLog(msg):
  if kinoPoiskLogLevel >= 1:
    sendToLog('ERROR: ' + msg)


def sendToLog(msg):
  if KINOPOISK_IS_DEBUG:
    print msg
  else:
    Log(msg)
