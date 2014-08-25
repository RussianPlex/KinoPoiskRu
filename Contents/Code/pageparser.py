# -*- coding: utf-8 -*-

"""
Russian metadata plugin for Plex, which uses http://www.kinopoisk.ru/ to get the tag data.
Плагин для обновления информации о фильмах использующий КиноПоиск (http://www.kinopoisk.ru/).

@version @PLUGIN.REVISION@
@revision @REPOSITORY.REVISION@
@copyright (c) 2014 by Yevgeny Nyden
@license GPLv3, see LICENSE for more details
"""

import sys, re, datetime, urllib, operator
import common, pluginsettings as S
import translit

MAX_ACTORS = 10
MAX_ALL_ACTORS = 50

# Actor role suffix that's going to be stripped.
ROLE_USELESS_SUFFFIX = u', в титрах '

MATCHER_MOVIE_DURATION = re.compile('\s*(\d+).*?', re.UNICODE | re.DOTALL)
MATCHER_IMDB_RATING = re.compile('IMDb:\s*(\d+\.?\d*)\s*\(\s*([\s\d]+)\s*\)', re.UNICODE | re.DOTALL)
#MATCHER_IMDB_RATING = re.compile('IMDb:\s*(\d+\.?\d*)\s?\((.*)\)', re.UNICODE)

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.22 (KHTML, like Gecko) Chrome/25.0.1364.172 Safari/537.22'

MOVIE_THUMBNAIL_SMALL_WIDTH = 130
MOVIE_THUMBNAIL_SMALL_HEIGHT = 168
MOVIE_THUMBNAIL_BIG_WIDTH = 780
MOVIE_THUMBNAIL_BIG_HEIGHT = 1024

# Compiled regex matchers.
MATCHER_WIDTH_FROM_STYLE = re.compile('.*width\s*:\s*(\d+)px.*', re.UNICODE)
MATCHER_HEIGHT_FROM_STYLE = re.compile('.*height\s*:\s*(\d+)px.*', re.UNICODE)
MATCHER_LEADING_NONALPHA = re.compile('^[\s\d\.\(\)]*', re.UNICODE | re.MULTILINE)


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


class PageParser:
  def __init__(self, logger, httpUtils, isDebug = False):
    self.log = logger
    self.isDebug = isDebug
    self.httpUtils = httpUtils

  def fetchAndParseCastPage(self, kinoPoiskId, loadAllActors):
    """ Fetches a cast page from KinoPoisk.ru and parses it via the
        #parseCastPage method.
    """
    url = S.KINOPOISK_CAST_PAGE_URL % kinoPoiskId
    self.log.Info(' <<< Fetching cast page: "%s"...' % url)
    page = self.httpUtils.requestAndParseHtmlPage(url)
    if page is None:
      self.log.Debug(' <<< Not found!')
      return {}
    return self.parseCastPage(page, loadAllActors)

  def parseCastPage(self, page, loadAllActors):
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
      actorsToParse =  MAX_ALL_ACTORS
    else:
      actorsToParse =  MAX_ACTORS
    for infoBlock in infoBlocks:
      personBlockNodes = infoBlock.xpath('div[@class="actorInfo"]/div[@class="info"]/div[@class="name"]/*')
      if actorsToParse == 0 or (len(personBlockNodes) == 0 and count > 1):
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
          actorsToParse = actorsToParse - 1
          self.log.Debug(' ... parsed actor: name="%s", role="%s"' % (actorName, actorRole))
        except:
          self.log.Warn(' ooo error parsing actor "%s"!' % str(actorName))
          if self.isDebug:
            excInfo = sys.exc_info()
            self.log.Exception('   exception: %s; cause: %s' % (excInfo[0], excInfo[1]))
    data = {'actors': actors}
    self.log.Info(' <<< Parsed %d actors.' % len(actors))
    return data

  def fetchAndParseSearchResults(self, mediaName, mediaYear):
    """ Searches for movie titles on KinoPoisk.
        @param mediaName Movie title parsed from a filename.
        @param mediaName Movie year parsed from a filename.
        @return Array of tuples: [kinoPoiskId, title, year, score]
    """
    self.log.Info('Quering kinopoisk...')
    results = self.queryKinoPoisk(mediaName, mediaYear)

    # Check media name is all ASCII characters, and if it is,
    # issue another query to KinoPoisk using a translified media name;
    # lastly, merge the scored results.
    if common.isAsciiString(mediaName):
      translifiedMediaName = translit.detranslify(mediaName)
      moreResults = self.queryKinoPoisk(translifiedMediaName, mediaYear)
      resultsMap = dict()
      for result in results:
        resultsMap[result[0]] = result
      results = [] # Recreate and repopulate the results array removing duplicates.
      for result in moreResults:
        currId = result[0]
        if currId in resultsMap.keys():
          origResult = resultsMap[currId]
          del resultsMap[currId]
          if result[3] >= origResult[3]:
            results.append(result)
          else:
            results.append(origResult)
        else:
          results.append(result)
      results.extend(resultsMap.viewvalues())

    # Sort all results based on their score.
    results.sort(key=operator.itemgetter(3))
    results.reverse()
    if self.isDebug:
      self.log.Debug('Search produced %d results:' % len(results))
      index = -1
      for result in results:
        index = index + 1
        self.log.Debug(' ... %d: score="%d", id="%s", name="%s", year="%s".' %
            (index, result[3], result[0], result[1], str(result[2])))
    return results


  def queryKinoPoisk(self, mediaName, mediaYear):
    """ Ищет фильм на кинопоиске.
        Returns title results as they are returned (no sorting is done here!).
    """
    results = []
    encodedName = urllib.quote(mediaName.encode(S.ENCODING_KINOPOISK_PAGE))
    page = self.httpUtils.requestAndParseHtmlPage(S.KINOPOISK_SEARCH_SIMPLE % encodedName)
    if page is None:
      self.log.Warn(' ### nothing was found on kinopoisk for media name "%s"' % mediaName)
      return results

    # Страница получена, берем с нее перечень всех названий фильмов.
    self.log.Debug('got a KinoPoisk query results page to parse...')
    divInfoElems = page.xpath('//div[@class="info"][p[@class="name"]/a[contains(@href,"/level/1/film/")]]')

    # Если не нашли там текст названия, значит сайт сразу дал нам страницу с фильмом (хочется верить).
    # TODO(zhenya): investigate if we need this clause at all (haven't seen this happening).
    if not len(divInfoElems):
      self.log.Warn('nothing was found on kinopoisk for media name "%s"' % mediaName)
      try:
        itemTitle = common.getXpathOptionalText(page, '//h1[@class="moviename-big"]/text()')
        if itemTitle is not None:
          itemKinoPoiskId = re.search('\/film\/(.+?)\/', page.xpath('.//link[contains(@href, "/film/")]/attribute::href')[0]).groups(0)[0]
          itemYear = common.parseYearFromString(page.xpath('//a[contains(@href,"year")]/text()')[0])
          itemAltTitle = None # TODO: parse original title.
          itemScore = common.scoreMediaTitleMatch(mediaName, mediaYear, itemTitle, itemAltTitle, itemYear, 0)
          results.append([itemKinoPoiskId, itemTitle, itemYear, itemScore])
      except:
        self.logException('failed to parse a KinoPoisk query results page')
      return results

    # Inspect query results titles and score them.
    itemIndex = -1
    self.log.Debug('found %d results (div info tags)' % len(divInfoElems))
    for divInfoElem in divInfoElems:
      itemIndex += 1
      try:
        anchorFilmElem = divInfoElem.xpath('.//a[contains(@href,"/level/1/film/")]/attribute::href')
        if not len(anchorFilmElem):
          self.log.Warn('unable to find film anchor elements for title "%s"' % mediaName)
          continue

        # Parse kinopoisk movie title id, title and year.
        match = re.search('\/film\/(.+?)\/', anchorFilmElem[0])
        if match is None:
          self.log.Error('unable to parse movie title id')
          continue

        itemKinoPoiskId = match.groups(1)[0]
        itemTitle = common.getXpathRequiredText(divInfoElem, './/a[contains(@href,"/level/1/film/")]/text()')
        itemYear = common.parseYearFromString(common.getXpathOptionalText(divInfoElem, './/span[@class="year"]/text()'))
        itemAltTitle = None
        try:
          # Try to parse the alternative (original) title. Ignore failures.
          # This is a <span> below the title <a> tag.
          altTitleCandidate = common.getXpathOptionalText(divInfoElem, './/span[@class="gray"]/text()')
          if altTitleCandidate is not None:
            # Strip any non alpha character in front (unfortunately, this may also remove a leading part
            # of a movie title if it starts with a digit).
            altTitleCandidate = MATCHER_LEADING_NONALPHA.sub('', altTitleCandidate).rstrip()
            if len(altTitleCandidate) > 0:
              itemAltTitle = altTitleCandidate
        except:
          pass
#        self.log.Debug(' ... kinoPoiskId="%s"; title="%s"; year="%s"...' % (itemKinoPoiskId, itemTitle, str(itemYear)))
        itemScore = common.scoreMediaTitleMatch(mediaName, mediaYear, itemTitle, itemAltTitle, itemYear, itemIndex)
        results.append([itemKinoPoiskId, itemTitle, itemYear, itemScore])
      except:
        self.logException('failed to parse div.info container')

    return results


  def fetchAndParseTitlePage(self, kinoPoiskId):
    """ Fetches a title page from KinoPoisk.ru and parses it via the
        #parseTitlePage method.
    """
    url = S.KINOPOISK_TITLE_PAGE_URL % kinoPoiskId
    self.log.Info(' <<< Fetching title page: "%s"...' % url)
    page = self.httpUtils.requestAndParseHtmlPage(url)
    if page is None:
      self.log.Debug(' <<< Not found!')
      return {}
    return self.parseTitlePage(page)

  def parseTitlePage(self, page):
    """ Parses a title page into a map with the following keys:
         * title
         * originalTitle
         * tagline
         * summary
         * year
         * countries
         * directors
         * writers
         * genres
         * contentRating    - IMDB (US) content rating;
         * contentRatingAlt - alternative (Russian) content rating;
         * rating - KinoPoisk movie rating;
         * imdbRating - (string) IMDB movie rating;
         * imdbRatingCount - (string) IMDB movie rating casted voices count;
         * ratingCount
         * duration
         * originalDate
    """
    data = {}
    self.log.Info(' <<< Parsing title page...')

    # Parse title.
    self.parseStringFromText(data, page, '//h1[@class="moviename-big"]/text()', 'title', '- ')

    # Parse original title.
    self.parseStringFromText(data, page, '//span[@itemprop="alternativeHeadline"]/text()', 'originalTitle')

    # Parse data from the table.info tag (year, country, directors, writers, content rating, etc).
    self.parseTitlePageInfoTable(data, page)

    # Parse description.
    self.parseStringFromText(data, page, '//div[@class="block_left_padtop"]//div[@itemprop="description"]/text()', 'summary')

    # Parse rating.
    self.parseStringFromText(data, page, '//*[@id="block_rating"]//span[@class="rating_ball"]/text()', 'rating', isFloat=True)
    self.parseStringFromText(data, page, '//*[@id="block_rating"]//span[@class="ratingCount"]/text()', 'ratingCount', isInteger=True)
    self.parseImdbRating(data, page)

    return data

  def fetchAndParseStudioPage(self, kinoPoiskId):
    """ Fetches a studio page and parses it via the
        #parseStudioPage method.
    """
    url = S.KINOPOISK_STUDIO_PAGE_URL % kinoPoiskId
    self.log.Info(' <<< Fetching studio page: "%s"...' % url)
    page = self.httpUtils.requestAndParseHtmlPage(url)
    if page is None:
      self.log.Debug(' <<< Not found!')
      return {}
    return self.parseStudioPage(page)

  def parseStudioPage(self, page):
    """ Parses a studio page and stores parsed results in
    """
    self.log.Info(' <<< Parsing studio page...')
    data = {}
    studios = []
    studioElems = page.xpath(u'//table/tr/td[b="Производство:"]/../following-sibling::tr/td/a/text()')
    for studio in studioElems:
      studios.append(studio.strip().encode('utf8'))
    data['studios'] = studios
    self.log.Info(' <<< Parsed %d studios.' % len(studios))
    return data

  def fetchAndParsePosterThumbnailData(self, kinoPoiskId):
    """ Attempts to fetch the main poster large thumbnail (film poster on the title page)
        and parses the response via the #parsePosterThumbnailData method.
    """
    bigThumbUrl = S.KINOPOISK_THUMBNAIL_BIG_URL % kinoPoiskId
    imageResponse = self.httpUtils.requestImageJpeg(bigThumbUrl)
    mainPoster = None
    if imageResponse is not None and 'image/jpeg' == imageResponse.headers['content-type']:
      mainPoster = common.Thumbnail(bigThumbUrl,
        bigThumbUrl,
        MOVIE_THUMBNAIL_BIG_WIDTH,
        MOVIE_THUMBNAIL_BIG_HEIGHT,
        0, # Index - main thumb is always the first one.
        S.KINOPOISK_THUMBNAIL_BIG_SCORE_BONUS, # Big thumb should have a score boost.
        'ru') # We are sure about the main poster's locale.
      self.log.Info(' <<< Big thumb is found.')
    else:
      smallThumbUrl = S.KINOPOISK_THUMBNAIL_SMALL_URL % kinoPoiskId
      imageResponse = self.httpUtils.requestImageJpeg(smallThumbUrl)
      if imageResponse is not None and 'image/jpeg' == imageResponse.headers['content-type']:
        self.log.Info(' <<< Big thumb is not found, adding a small one...')
        mainPoster = common.Thumbnail(smallThumbUrl,
          smallThumbUrl,
          MOVIE_THUMBNAIL_SMALL_WIDTH,
          MOVIE_THUMBNAIL_SMALL_HEIGHT,
          0, # Index - main thumb is always the first one.
          0, # Initial score.
          'ru')  # We are sure about the main thumb locale.
    return mainPoster

  def fetchAndParsePostersData(self, kinoPoiskId, maxPosters, lang):
    """ Fetches various poster pages, parses, scores, and orders posters data.
        This will include parsing poster from the main title page and possibly
        from the posters (first) page.
    """
    # Получение ярлыка (большого если есть или маленького с главной страницы).
    mainPoster = self.fetchAndParsePosterThumbnailData(kinoPoiskId)
    if maxPosters > 1:
      url = S.KINOPOISK_COVERS_URL % kinoPoiskId
      posters = self.fetchAndParseImagesPage(url, maxPosters)
    else:
      posters = []
    if mainPoster:
      posters.append(mainPoster)
    for poster in posters:
      common.scoreThumbnailResult(poster, True, lang)
    return posters

  def fetchAndParseImagesPage(self, url, maxPosters):
    """ Fetches and parses the first page of the movie posters or stills.
        @param {number} maxPosters Max number of posters (may still return more!).
    """
    self.log.Info(' <<< Fetching images page: "%s"...' % url)
    posterPage = self.httpUtils.requestAndParseHtmlPage(url)
    if posterPage is None:
      self.log.Debug('    NOT found!')
      return []
    return self.parseImagesPage(posterPage, maxPosters)

  def parseImagesPage(self, page, maxItems):
    """ Parses a posters page or a page with images (posters and backgrounds).
        We have the same method to parse both since they are almost identical.
        @param {number} maxItems Max number of items (may still return more!).
    """
    self.log.Info(' <<< Parsing images page...')
    posters = []

    # Find all anchor tags that wrap small thumbnail img tags.
    anchorElems = page.xpath('//table[@class="fotos" or @class="fotos " or @class="fotos fotos1" or @class="fotos fotos2"]//td/a')
    ind = 1 # Start with 1 as 0 is reserved for the main thumb.
    maxItems = maxItems + 2  # Give it a few more images to choose from.
    for anchorElem in anchorElems:
      thumb = self.parseImageDataFromAnchorElement(anchorElem, ind)
      posters.append(thumb)
      ind += 1
      if ind > maxItems:
        break

    self.log.Info(' <<< Parsed %d images.' % len(posters))
    return posters

  def parseImageDataFromAnchorElement(self, anchorElem, index):
    """ Given an anchor element from a posters page,
        fetches the corresponding poster (individual) page and
        parses poster's data into a Thumbnail object.
        @return common.Thumbnail or None if failed to parse.
    """
    fullSizeUrl = None
    dimensions = None, None

    # Read thumbnail image url from the <img> src tag attribute.
    thumbUrl = common.getXpathOptionalNode(anchorElem, './img/attribute::src')
    if thumbUrl is not None:
      thumbUrl = ensureAbsoluteUrl(thumbUrl.strip())

    # Fetch and parse individual page with image.
    posterPageUrl = ensureAbsoluteUrl(anchorElem.get('href').strip())
    self.log.Debug('fetching image page: "%s".' % posterPageUrl)
    posterPage = self.httpUtils.requestAndParseHtmlPage(posterPageUrl)
    if posterPage is not None:
      imageElem = common.getXpathOptionalNode(posterPage, '//img[@id="image"]')
      if imageElem is not None:
        fullSizeUrl = imageElem.get('src')
        dimensions = parseImageElemDimensions(imageElem)

    # If we have no full size image URL, we could use the thumb's.
    if fullSizeUrl is None and thumbUrl is not None:
      self.log.Debug(' - found no full size image, will use the thumbnail')
      fullSizeUrl = thumbUrl

    if fullSizeUrl is None and thumbUrl is None:
      return None

    thumb = common.Thumbnail(thumbUrl, ensureAbsoluteUrl(fullSizeUrl),
      dimensions[0], dimensions[1], index, 0, 'null')
    if self.isDebug:
      self.log.Debug(' ... parsed a thumbnail:')
      print '    ' + str(thumb)
    return thumb

  def fetchAndParseStillsData(self, kinoPoiskId, maxStills, lang):
    """ Fetches pages that contain fun art ("backgrounds"), parses and scores them.
    """
    backgrounds = self.fetchAndParseImagesPage(
      S.KINOPOISK_STILLS_URL % kinoPoiskId, maxStills)
    if len(backgrounds) == 0:
      backgrounds = self.fetchAndParseImagesPage(
        S.KINOPOISK_SCREENSHOTS_URL % kinoPoiskId, maxStills)
    if len(backgrounds) == 0:
      backgrounds = self.fetchAndParseImagesPage(
        S.KINOPOISK_WALL_URL % kinoPoiskId, maxStills)

    for background in backgrounds:
      common.scoreThumbnailResult(background, False, lang)
    return backgrounds

  def parseTitlePageInfoTable(self, data, page):
    """ Parses the main info <table> tag, which we find by a css classname "info".
    """
    infoTableRows = page.xpath('//div[@id="infoTable"]/table/tr')
    self.log.Debug(' <<< parsed %d rows from the main info table tag.' % len(infoTableRows))
    for infoRowElem in infoTableRows:
      headerTypeElem =  infoRowElem.xpath('./td[@class="type"]/text()')
      if len(headerTypeElem) != 1:
        continue
      rowTypeKey = headerTypeElem[0]
      if rowTypeKey == u'год':
        self.parseStringFromText(data, infoRowElem, './/a/text()', 'year', isInteger=True)
      elif rowTypeKey == u'страна':
        self.parseStringsFromText(data, infoRowElem, './/a/text()', 'countries')
      elif rowTypeKey == u'слоган':
        self.parseStringFromText(data, infoRowElem, './td[2]/text()', 'tagline', '«»-')
      elif rowTypeKey == u'режиссер':
        self.parseStringsFromText(data, infoRowElem, './/a/text()', 'directors')
      elif rowTypeKey == u'сценарий':
        self.parseStringsFromText(data, infoRowElem, './/a/text()', 'writers')
      elif rowTypeKey == u'жанр':
        self.parseStringsFromText(data, infoRowElem, './/a[contains(@href,"/lists/")]/text()', 'genres', True)
      elif rowTypeKey == u'рейтинг MPAA':
        self.parseContentRatingInfo(data, infoRowElem)
      elif rowTypeKey == u'возраст':
        self.parseContentRatingAltInfo(data, infoRowElem)
      elif rowTypeKey == u'время':
        self.parseDurationInfo(data, infoRowElem)
      elif rowTypeKey == u'премьера (мир)':
        self.parseOriginallyAvailableInfo(data, infoRowElem)
      # Also available: 'продюсер', 'оператор', 'композитор', 'художник', 'монтаж',
      # 'бюджет', 'сборы в США', 'релиз на DVD', 'зрители', 'монтаж'.

  def parseImdbRating(self, data, page):
    try:
      tmpData = {}
      self.parseStringFromText(tmpData, page, '//*[@id="block_rating"]/div[@class="block_2"]/div[2]/text()', 'imdbRatingStr')
      if 'imdbRatingStr' in tmpData:
        match = MATCHER_IMDB_RATING.search(tmpData['imdbRatingStr'])
        if match is not None:
          data['imdbRating'] = float(match.groups()[0])
          self.log.Debug(' ... parsed IMDb rating: "%s"' % data['imdbRating'])
          try:
            data['imdbRatingCount'] = int(match.groups()[1].replace(' ', ''))
            self.log.Debug(' ... parsed IMDb rating count: "%s"' % data['imdbRatingCount'])
          except:
            self.log.Warn(' ooo unable to parse "imdbRatingCount"')
    except:
      self.log.Warn(' ooo unable to parse "imdbRating"')

  def parseStringFromText(self, data, elem, path, key, sanitizeChars=None, isInteger=False, isFloat=False):
    try:
      item = common.getXpathOptionalText(elem, path)
      if item is None:
        self.log.Warn(' ooo unable to parse "%s"' % key)
      else:
        item = sanitizeString(item).encode('utf8').strip()
        if sanitizeChars is not None:
          item = item.strip(sanitizeChars)
        if isInteger:
          item = removeWhiteSpace(item)
          data[key] = int(item)
        elif isFloat:
          item = removeWhiteSpace(item)
          data[key] = float(item)
        else:
          data[key] = item
        self.log.Debug(' ... parsed "%s": "%s"' % (key, item))
    except:
      self.logException(' ### unable to parse string for key "%s"' % key)

  def parseStringsFromText(self, data, elem, path, name, capitalize=False):
    result = []
    for textStr in elem.xpath(path):
      if textStr != u'...':
        if capitalize:
          textStr = unicode(textStr).title()
        result.append(textStr.encode('utf8'))
    self.log.Debug(' ... parsed %d "%s" tags %s.' % (len(result), name, common.arrayToUnicodeString(result)))
    if len(result):
      data[name] = result

  def parseContentRatingInfo(self, data, infoRowElem):
    contentRatingElems = infoRowElem.xpath('.//a/img/attribute::src')
    if len(contentRatingElems) == 1:
      try:
        match = re.search('\/([^/.]+?)\.gif$', contentRatingElems[0])
        if match is not None:
          contentRating = match.groups(1)[0]
          data['contentRating'] = contentRating
          self.log.Debug(' ... parsed content rating "%s"' % contentRating)
      except:
        self.logException(' ### unable to parse duration')

  def parseContentRatingAltInfo(self, data, infoRowElem):
    spanText = common.getXpathOptionalText(infoRowElem, './td/span/text()')
    if spanText is not None:
      try:
        match = re.search('.*?(\d+).*?$', spanText)
        if match is not None:
          contentRating = match.groups(1)[0]
          data['contentRatingAlt'] = contentRating + '+'
          self.log.Debug(' ... parsed content rating alt "%s"' % contentRating)
      except:
        self.logException(' ### unable to parse content rating alt')

  def parseDurationInfo(self, data, infoRowElem):
    try:
      durationElems = infoRowElem.xpath('./td[@class="time"]/text()')
      if len(durationElems) > 0:
        match = MATCHER_MOVIE_DURATION.search(durationElems[0])
        if match is not None:
          duration = int(int(match.groups(1)[0])) * 1000 * 60
          self.log.Debug(' ... parsed duration: "%s"' % str(duration))
          data['duration'] = duration
    except:
      self.logException(' ### unable to parse duration')

  def parseOriginallyAvailableInfo(self, data, infoRowElem):
    try:
      originalDateElems = infoRowElem.xpath('.//a/text()')
      if len(originalDateElems):
        (dd, mm, yy) = originalDateElems[0].split()
        originalDate = datetime.datetime(int(yy), int(RU_MONTH[mm]), int(dd)).date()
        self.log.Debug(' ... parsed originally available date: "%s"' % str(originalDate))
        data['originalDate'] = originalDate
    except:
      self.logException(' ### unable to parse originally available date')

  def logException(self, msg):
    self.log.Error(msg)
    if self.isDebug:
      excInfo = sys.exc_info()
      self.log.Exception('exception: %s; cause: %s' % (excInfo[0], excInfo[1]))

  def parseMainActorsFromLanding(self, page):
    """ Parses film actors from the main movie title page.
        This method could be used if a title doesn't have a dedicated movie page.
        @return Array.<string>
    """
    actorsList = []
    actors = page.xpath('//div[@id="actorList"]/ul/li/a/text()')
    for actor in actors:
      try:
        if actor != u'...':
          actorsList.append(unicode(actor).title().encode('utf8'))
      except:
        self.logException(' ### unable to parse title page actor')
    self.log.Debug(' ... parsed %d actors from the main page.' % len(actorsList))
    return actorsList


def ensureAbsoluteUrl(url):
  """ Returns an absolute URL (starts with http://)
      pre-pending base kinoposk URL to the passed URL when necessary.
  """
  if url is None or len(url.strip()) < 10:
    return None
  url = url.strip()
  if url[0:4] == 'http':
    return url
  return S.KINOPOISK_SITE_BASE + url.lstrip('/')

def sanitizeString(msg):
  """ Функция для замены специальных символов.
  """
  res = msg.replace(u'\x85', u'...')
  res = res.replace(u'\xc2', u'')
  return res.replace(u'\x97', u'-')

def removeWhiteSpace(msg):
  """ Removes "unusual" white space from a string.
  """
  return msg.replace(u'\xa0', u'')

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
