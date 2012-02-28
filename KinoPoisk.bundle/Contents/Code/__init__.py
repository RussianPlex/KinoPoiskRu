# -*- coding: utf-8 -*-
import datetime, string, re, time, unicodedata, hashlib, urlparse, types, sys

KINOPOISK_IS_DEBUG = True

# Current log level.
# Supported values are: 0 = none, 1 = error, 2 = warning, 3 = info, 4 = fine, 5 = finest.
kinoPoiskLogLevel = 5 # Default is error.

KINOPOISK_PAGE_ENCODING = 'cp1251'

# Разные страницы сайта
KINOPOISK_BASE = 'http://www.kinopoisk.ru/'
KINOPOISK_TITLE_PAGE_URL = KINOPOISK_BASE + 'level/1/film/%s/'
KINOPOISK_PEOPLE = KINOPOISK_BASE + 'level/19/film/%s/'
KINOPOISK_STUDIO = KINOPOISK_BASE + 'level/91/film/%s/'
KINOPOISK_POSTERS = KINOPOISK_BASE + 'level/17/film/%s/page/%d/'
KINOPOISK_ART = KINOPOISK_BASE + 'level/13/film/%s/page/%d/'

# Страница поиска
KINOPOISK_SEARCH = 'http://www.kinopoisk.ru/index.php?first=no&kp_query=%s'

SCORE_PENALTY_ITEM_ORDER = 3
SCORE_PENALTY_YEAR_WRONG = 4

# Рейтинги
DEFAULT_MPAA = u'R'
MPAA_AGE = {u'G': 0, u'PG': 11, u'PG-13': 13, u'R': 16, u'NC-17': 17}

# Русские месяца, пригодится для определения дат
RU_MONTH = {u'января': '01', u'февраля': '02', u'марта': '03', u'апреля': '04', u'мая': '05', u'июня': '06', u'июля': '07', u'августа': '08', u'сентября': '09', u'октября': '10', u'ноября': '11', u'декабря': '12'}

# Под кого маскируемся =)
UserAgent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_2) AppleWebKit/534.51.22 (KHTML, like Gecko) Version/5.1.1 Safari/534.51.22'


def Start():
  print '+++++++++++++++++++++++++++++++++ START'
  HTTP.CacheTime = CACHE_1DAY

class PlexMovieAgent(Agent.Movies):
  print '+++++++++++++++++++++++++++++++++ CTOR'
  name = 'KinoPoiskRu'
  languages = [Locale.Language.Russian]
  accepts_from = ['com.plexapp.agents.localmedia']

  # Функция для получения html-содержимого
  def httpRequest(self, url):
    time.sleep(1)
    res = None
    for i in range(3):
      try:
        res = HTTP.Request(url, headers = {'User-agent': UserAgent, 'Accept': 'text/html'})
      except:
        Log("Error hitting HTTP url:", url)
        time.sleep(1)
    return res

  # Функция преобразования html-кода в xml-код
  def XMLElementFromURLWithRetries(self, url):
    sendToFinestLog('requesting URL: "%s"...' % url)
    res = self.httpRequest(url)
    if res:
      res = str(res).decode(KINOPOISK_PAGE_ENCODING)
#      sendToFinestLog(res)
      return HTML.ElementFromString(res)
    return None

  def computeTitleScore(self, mediaName, mediaYear, title, year, itemIndex):
    score = 100
    # Item order on the list penalizes the score.
    score = score - (itemIndex * SCORE_PENALTY_ITEM_ORDER)
    if mediaYear is not None and mediaYear != year:
      score = score - SCORE_PENALTY_YEAR_WRONG
    return score

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
    page =  self.XMLElementFromURLWithRetries(KINOPOISK_SEARCH % mediaName)
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
                score = self.computeTitleScore(mediaName, mediaYear, title, year, itemIndex)
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
          score = self.computeTitleScore(mediaName, mediaYear, title, year, itemIndex)
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
    titlePage =  self.XMLElementFromURLWithRetries(KINOPOISK_TITLE_PAGE_URL % kinoPoiskId)
    if titlePage:
      sendToFineLog('got a KinoPoisk page for movie title id: "%s"' % kinoPoiskId)
      try:
        parseTitleInfo(titlePage, metadata)                            # Title. Название на русском языке.
        parseOriginalTitleInfo(titlePage, metadata)                    # Original title. Название на оригинальном языке.
        parseActorsInfo(titlePage, metadata)                           # Actors. Актёры.
        parseSummaryInfo(titlePage, metadata)                          # Summary. Описание.
        parseRatingInfo(titlePage, metadata, kinoPoiskId)              # Rating. Рейтинг.

        parseInfoTableTagAndUpdateMetadata(titlePage, metadata)

        studioPage = self.XMLElementFromURLWithRetries(KINOPOISK_STUDIO % kinoPoiskId)
        parseStudioInfo(studioPage, metadata)                          # Studio. Студия.
        peoplePage = self.XMLElementFromURLWithRetries(KINOPOISK_PEOPLE % kinoPoiskId)
        parsePeoplePageInfo(peoplePage, metadata)                      # Studio. Студия.

      except:
        sendToErrorLog(getExceptionInfo('failed to update metadata for id %s' % kinoPoiskId))


def parseInfoTableTagAndUpdateMetadata(page, metadata):
  """ Parses the main info <table> tag, which we find by
      a css classname "info".
  """
  mainInfoTagRows = page.xpath('//table[@class="info"]/tr')
  sendToFineLog('parsed %d rows from the main info table tag' % len(mainInfoTagRows))
  for infoRowElem in mainInfoTagRows:
    headerTypeElem =  infoRowElem.xpath('./td[@class="type"]/text()')
    if len(headerTypeElem) != 1:
      continue
    rowTypeKey = headerTypeElem[0]
    if rowTypeKey == u'режиссер':
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


def parseActorsInfo(page, metadata):
  actors = page.xpath('//td[@class="actor_list"]/div/span')
  sendToFineLog(' ... parsed %d actor tags' % len(actors))
  metadata.roles.clear()
  for actorSpanTag in actors:
    actorList = actorSpanTag.xpath('./a[contains(@href,"/level/4/people/")]/text()')
    if len(actorList):
      for actor in actorList:
        if actor != u'...':
          sendToFineLog(' . . . . actor: "%s"' % actor)
          role = metadata.roles.new()
          role.actor = actor


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


def parseStudioInfo(page, metadata):
  if page:
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
    metadata.directors.clear()
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
    metadata.writers.clear()
    for writer in writers:
      if writer != u'...':
        sendToFineLog(' . . . . writer "%s"' % writer)
        metadata.writers.add(writer)


def parseGenresInfo(infoRowElem, metadata):
  genres = infoRowElem.xpath('.//a/text()')
  sendToFineLog(' ... parsed %d genre tags' % len(genres))
  if len(genres):
    metadata.genres.clear()
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
  if len(durationElems) == 1:
    try:
      duration = int(durationElems[0].rstrip(u' мин.')) * 60 * 1000
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


def parsePeoplePageInfo(page, metadata):
  """ Parses people - mostly actors, but here (on this page)
      we have access to extensive information about all who participated
      creating this movie.
  """
  if not page:
    return
  # TODO(zhenya): uncomment and fix.
        # people_type = None
        # peoples = page.xpath('//div[@id="content_block"]/table/tr/td/div[@class="block_left"]/*')
        # for info_buf in peoples:
          # try:
            # if info_buf.tag == u'table':
              # info_buf = info_buf.xpath('./tr/td[@style="padding-left:20px;border-bottom:2px solid #f60;font-size:16px"]/text()')
              # if info_buf[0] == u'Актеры':
                # people_type = 'role'
                # metadata.roles.clear()

              # elif info_buf[0] == u'Режиссеры':
                # people_type = 'director'
                # metadata.directors.clear()

              # elif info_buf[0] == u'Сценаристы':
                # people_type = 'writer'
                # metadata.writers.clear()

              # else:
                # people_type = None
          # except:
            # pass
          # try:
            # if people_type != None and info_buf.tag == u'div':

              # if people_type == 'role':


                # role = metadata.roles.new()
                # role.actor = info_buf.xpath('./p/a/text()')[0].strip(u' .')
                # info_buf2 = info_buf.xpath('./a[contains(@href,"/level/4/people/")]/text()')
                # if len(info_buf2):
                  # for actor in info_buf2:
                    # if actor != u'...':
                      # role.actor = actor
                      # Log(actor.decode('utf-8'))
                # Log(role.actor.decode('utf-8'))
                # role.role = info_buf.xpath('./p/text()')[0].strip(u' .')
                # info_buf = info_buf.xpath('./a/img/attribute::src')
                # if not(info_buf[0].endswith('no-poster.gif')):
                  # role.photo = KINOPISK_BASE + info_buf[0].lstrip('/')

              # elif people_type == 'director':
                # metadata.directors.add(info_buf.xpath('./p/a/text()')[0].strip(u' .'))

              # elif people_type == 'writer':
                # metadata.writers.add(info_buf.xpath('./p/a/text()')[0].strip(u' .'))

          # except:
            # pass

def sanitizeString(msg):
  """ Функция для замены специальных символов.
  """
  res = msg.replace(u'\x85', u'...')
  res = res.replace(u'\x97', u'-')
  return res


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
