import datetime, string, re, time, unicodedata, hashlib, urlparse, types

AGENT_VERSION = '0.1'
USER_AGENT = 'Plex WikipediaRu Metadata Agent (+http://www.plexapp.com/) v.%s' % AGENT_VERSION

##############  Preference item names.
PREF_CACHE_TIME_NAME = 'wikiru_pref_cache_time'
PREF_MAX_RESULTS_NAME = 'wikiru_pref_wiki_results'
PREF_CATEGORIES_NAME = 'wikiru_pref_ignore_categories'
PREF_MIN_PAGE_SCORE = 'wikiru_pref_min_page_score'
PREF_GET_ALL_ACTORS = 'wikiru_pref_get_all_actors'

##############  WIKIpedia URLs.
WIKI_QUERY_URL = 'http://ru.wikipedia.org/w/api.php?action=query&list=search&srprop=timestamp&format=xml&srsearch=%s_(фильм)'
WIKI_TITLEPAGE_URL = 'http://ru.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=timestamp|user|comment|content&format=xml&titles=%s'
WIKI_IDPAGE_URL = 'http://ru.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=timestamp|user|comment|content&format=xml&pageids=%s'
WIKI_QUERYFILE_URL = 'http://ru.wikipedia.org/w/api.php?action=query&prop=imageinfo&iiprop=url&format=xml&titles=Файл:%s'

IMDB_TITLEPAGE_URL = 'http://www.imdb.com/title/tt%s'

############## Compiled regexes
# The {{Фильм }} tag (we consider Телесериал as well).
MATCHER_FILM = re.compile(u'\{\{\s*(\u0424\u0438\u043B\u044C\u043C|\u0422\u0435\u043B\u0435\u0441\u0435\u0440\u0438\u0430\u043B)\s*(([^\{\}]*?\{\{[^\{\}]*?\}\}[^\{\}]*?)*|.*?)\s*\}\}', re.S | re.M | re.U | re.I)
# IMDB rating, something like this "<span class="rating-rating">5.0<span>".
MATCHER_IMDB_RATING = re.compile('<span\s+class\s*=\s*"rating-rating">\s*(\d+\.\d+)\s*<span', re.M | re.S)
MATCHER_FIRST_INTEGER = re.compile('\s*(\d+)\D*', re.U)
MATCHER_FIRST_LETTER = re.compile('^\w', re.U)
MATCHER_PO_ZAKAZU = re.compile(u'(.*?)\s+\u043F\u043E\s+\u0437\u0430\u043A\u0430\u0437\u0443.*', re.U | re.I)
# Year: some number after " Год ".
MATCHER_SOME_YEAR = re.compile(u'\b\u0413\u043E\u0434\b.*\D(\d{4})\D.*', re.U | re.I)
# WIKI category, something like "Категория:Мосфильм"...
MATCHER_CATEGORY = re.compile(u'^\u041A\u0430\u0442\u0435\u0433\u043E\u0440\u0438\u044F:([\s\w]+)\s*$', re.M | re.U)
# Represents an actor/roles line in the "В Ролях" section.
MATCHER_ACTOR_LINE = re.compile('^\s*\W*\s*(\w+\s+\w+(\s+\w+)?)(\s*?|.*?)$', re.U | re.M)
MATCHER_ACTOR_ROLE = re.compile('^\W*(\w.*?\w)\W*$', re.U | re.I)

############## MoviePosterDB constants.
MPDB_ROOT = 'http://movieposterdb.plexapp.com'
MPDB_JSON = MPDB_ROOT + '/1/request.json?imdb_id=%s&api_key=p13x2&secret=%s&width=720&thumb_width=100'
MPDB_SECRET = 'e3c77873abc4866d9e28277a9114c60c'

############## Constants that influence matching score on titles.
SCORE_FIRST_ITEM_BONUS = 5
SCORE_ORDER_PENALTY = 3
SCORE_WIKIMATCH_IMPORTANCE = 2
SCORE_NOFILMDATA_PENALTY = 15
SCORE_BADYEAR_PENALTY = 15
SCORE_NOYEAR_PENALTY = 10

DEFAULT_ACTOR_ROLE = 'актер'

# ruslania - good source of images and taglines?
#      content = HTTP.Request('http://ruskino.ru/mov/search', params).content.strip()
#      content = HTTP.Request('http://www.ozon.ru/?context=search&text=Место%20встречи%20изменить%20нельзя', None, {}, 360).content.strip()
#      query = 'http://www.ozon.ru/?context=search&text=' + str.replace(titleMaybe, ' ', '%20')
# [might want to look into language/country stuff at some point]
# param info here: http://code.google.com/apis/ajaxsearch/documentation/reference.html
#
# Kina-Teatr.ru URLs.
#KTRU_QUERY_URL = 'http://www.kino-teatr.ru/search/'

# TODO(zhenya): clean up extraneous log statements.

def Start():
  Log('START::::::::: %s' % USER_AGENT)
  # Setting cache experation time.
  prefCache = Prefs[PREF_CACHE_TIME_NAME]
  if prefCache == "1 минута":
    cacheExp = CACHE_1MINUTE
  elif prefCache == "1 час":
    cacheExp = CACHE_1HOUR
  elif prefCache == "1 день":
    cacheExp = CACHE_1DAY
  elif prefCache == "1 неделя":
    cacheExp = CACHE_1DAY
  elif prefCache == "1 месяц":
    cacheExp = CACHE_1MONTH
  elif prefCache == "1 год":
    cacheExp = CACHE_1MONTH * 12
  else:
    cacheExp = CACHE_1WEEK
  HTTP.CacheTime = cacheExp
  Log('PREF: Setting cache expiration to %d seconds (%s)' % (cacheExp, prefCache))
  Log('PREF: WIKI max results is set to %s' % Prefs[PREF_MAX_RESULTS_NAME])
  Log('PREF: Min page score is set to %s' % Prefs[PREF_MIN_PAGE_SCORE])
  Log('PREF: Ignore WIKI categories is set to %s' % str(Prefs[PREF_CATEGORIES_NAME]))
  Log('PREF: Parse all actors is set to %s' % str(Prefs[PREF_GET_ALL_ACTORS]))


class PlexMovieAgent(Agent.Movies):
  name = 'WikipediaRu'
  languages = [Locale.Language.Russian]
  accepts_from = ['com.plexapp.agents.localmedia']


  ##############################################################################
  ############################# S E A R C H ####################################
  ##############################################################################
  def search(self, results, media, lang, manual=False):
    """ Searches for matches on Russian wikipedia using the title and year
        passed via the media object. All matches are saved in a list of results
        as MetadataSearchResult objects. For each results, we determine a
        wiki page id, title, year, and the score (how good we think the match
        is on the scale of 1 - 100).
    """
    year = None
    if media.year:
      year = safeEncode(media.year)

    # Looking for wiki pages for this title.
    self.findWikiPageMatches(media.name, year, results, lang)

    results.Sort('score', descending=True)

    Log('Search produced %d results:' % len(results))
    for result in results:
      Log('  ... result: id="%s", name="%s", year="%s", score="%d".' % (result.id, result.name, str(result.year), result.score))


  ##############################################################################
  ############################# U P D A T E ####################################
  ##############################################################################
  def update(self, metadata, media, lang):
    """Updates the media title provided a page id on Russian wikipedia.
       Here, we look into the metadata.guid to parse WIKI page id and use
       it to fetch the page, which is going to be used to populate the
       media item record. Another field that could be used is metadata.title.
    """
    part = media.items[0].parts[0]
    filename = part.file.decode('utf-8')
    plexHash = part.plexHash
    Log('WikipediaRu.update: filename="%s", plexHash="%s", guid="%s"' % (filename, plexHash, metadata.guid))

    matcher = re.compile(r'//(\d+)\?')
    match = matcher.search(metadata.guid)
    if match:
      wikiId = match.groups(1)[0]
    else:
      raise Exception('ERROR: no wiki id is found!')

    # Set the title. FIXME, this won't work after a queued restart.
    # Only do this once, otherwise we'll pull new names that get edited
    # out of the database.
    if media and metadata.title is None:
      metadata.title = media.title

    imdbId = None
    imdbData = None
    wikiImgName = None
    wikiPageUrl = WIKI_IDPAGE_URL % wikiId
    parseCategories = not Prefs[PREF_CATEGORIES_NAME]
    isGetAllActors = Prefs[PREF_GET_ALL_ACTORS]
    tmpResult = self.getAndParseItemsWikiPage(wikiPageUrl, metadata, parseCategories = parseCategories, isGetAllActors = isGetAllActors)
    if tmpResult is not None:
      wikiContent = tmpResult['all']
      if 'image' in tmpResult:
        wikiImgName = tmpResult['image']
      if 'imdb_id' in tmpResult:
        imdbId = tmpResult['imdb_id']
        imdbData = self.getDataFromImdb(imdbId)

    if imdbData is not None:
      # Content rating.
      if 'rating' in imdbData:
        metadata.rating = float(imdbData['rating'])
        # metadata.content_rating =  G/PG/etc.

    # Getting artwork.
    self.fetchAndSetWikiArtwork(metadata, wikiImgName, imdbId)


  def fetchAndSetWikiArtwork(self, metadata, wikiImgName, imdbId):
    """ Fetches images from the WIKI and other Internet sources to set
        metadata.posters values.
        We borrowed MoviePosterDB code to try to load movie posters
        using the imdb id if its present. If imdb id is not set or
        no images are found using MoviePosterDB, we use wikiImgName
        (if it's set) to load a WIKI image.
    """
    # TODO(zhenya): need to validate the size and proportions of the image.
    # TODO(zhenya): look for other images on IMDB or Google if wikiImgName is not set?
    posters_valid_names = list()
    art_valid_names = list()
    try:
      # Fetching movie posters using moviePosterDB code.
      sortOrder = 0
      if imdbId is not None:
        imdb_code = imdbId.replace('tt', '').lstrip('t0')
        sortOrder = self.moviePosterDBupdate(metadata, posters_valid_names, imdb_code)

      # Fetching an image from the wikipedia.
      if wikiImgName is not None:
        wikiImgQueryUrl = WIKI_QUERYFILE_URL % wikiImgName
        xmlResult = getXmlFromWikiApiPage(wikiImgQueryUrl)
        pathMatch = xmlResult.xpath('//api/query/pages/page')
        if len(pathMatch) == 0:
          Log('ERROR: unable to parse page "%s".' % wikiImgQueryUrl)
          raise Exception

        missing = pathMatch[0].get('missing')
        if missing is not None:
          Log('ERROR: file "%s" does not seem to exist.' % wikiImgName)
          raise Exception

        pathMatch = pathMatch[0].xpath('//imageinfo/ii')
        if len(pathMatch) == 0:
          Log('ERROR: image section is not found in a WIKI response.')
          raise Exception

        thumbUrl = pathMatch[0].get('url')
        if thumbUrl is not None:
          url = thumbUrl
          metadata.posters[url] = Proxy.Preview(HTTP.Request(thumbUrl), sort_order = sortOrder)
          posters_valid_names.append(url)
          Log('Setting a poster from wikipedia: "%s"' % url)
    except:
      Log('ERROR: unable to fetch art work.')

    metadata.posters.validate_keys(posters_valid_names)
    metadata.art.validate_keys(art_valid_names)


  def moviePosterDBupdate(self, metadata, posters_valid_names, imdb_code):
    """ Code borowed from moviePosterDB.
        Fetches and sets movie posters on the metadata object
        given imdb id (w/o the 'tt' prefix).
    """
    # TODO(zhenya): now we can't pass imdb id since there is only one id variable
    # - metadata.id - and we use it to represent a WIKI id. When support for an
    # alternative id is added, we could pass it and the next agent (e.g. themoviedb)
    # could use it.
    secret = Hash.MD5( ''.join([MPDB_SECRET, imdb_code]))[10:22]
    queryJSON = JSON.ObjectFromURL(MPDB_JSON % (imdb_code, secret), cacheTime=10)

    i = 0
    if not queryJSON.has_key('errors') and queryJSON.has_key('posters'):
      for poster in queryJSON['posters']:
        imageUrl = MPDB_ROOT + '/' + poster['image_location']
        thumbUrl = MPDB_ROOT + '/' + poster['thumbnail_location']
        full_image_url = imageUrl + '?api_key=p13x2&secret=' + secret

        if poster['language'] == 'RU' or poster['language'] == 'US':
          metadata.posters[full_image_url] = Proxy.Preview(HTTP.Request(thumbUrl), sort_order = i)
          posters_valid_names.append(full_image_url)
          i += 1
          Log('Setting a poster from MPDB: "%s"' % imageUrl)
    return i


  def makeIdentifier(self, string):
    string = re.sub( r"\s+", " ", string.strip())
    string = unicodedata.normalize('NFKD', safeEncode(string))
    string = re.sub(r"['\"!?@#$&%^*\(\)_+\.,;:/]","", string)
    string = re.sub(r"[_ ]+","_", string)
    string = string.strip('_')
    return string.strip().lower()


  def stringToId(self, string):
    hash = hashlib.sha1()
    hash.update(string.encode('utf-8'))
    return hash.hexdigest()


  def titleAndYearToId(self, title, year):
    if title is None:
      title = ''
    if isBlank(year):
      string = "%s" % self.makeIdentifier(title)
    else:
      string = "%s_%s" % (self.makeIdentifier(title).lower(), year)
    return self.stringToId("%s" % string)


  def getAndParseItemsWikiPage(self, wikiPageUrl, metadata = None, parseCategories = False, isGetAllActors = False):
    """Given a WIKI page URL, gets it and parses its content.

       This method is used to determine score for a given wiki URL,
       and also to write the fetched and parsed data into the
       passed metadata object if it's present.

       Returns None if there was an error or a dictionary with the
       following key/value pairs:
         'id', 'year', 'imdb_id', 'image', 'score', 'film', and 'all'.
       The later is the parsed and sanatized WIKI page content.
       Value for 'film' represents the {{Фильм}} tag if it's found.
       All values are strings.

       Score is value [0, 15] that indicates how good a match is.
    """
    # TODO(zhenya): need to have two modes - full and partial (see where this method is being called from).
    # TODO(zhenya): move scoring out of this method.

    contentDict = {}
    score = 0
    try:
      # First, clearing all metadata's properties and lists if metadata present.
      if metadata is not None:
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

      xmlResult = getXmlFromWikiApiPage(wikiPageUrl)
      pathMatch = xmlResult.xpath('//api/query/pages/page')
      if len(pathMatch) == 0:
        Log('ERROR: unable to parse page "%s".' % wikiPageUrl)
        return None

      missing = pathMatch[0].get('missing')
      if missing is not None:
        Log('ERROR: page "%s" does not seem to exist.' % wikiPageUrl)
        return None

      contentDict['id'] = pathMatch[0].get('pageid')
      pathMatch = pathMatch[0].xpath('//revisions/rev')
      if len(pathMatch) == 0:
        Log('ERROR: page revision is not found in a WIKI response.')
        return None

      # This is the content of the entire page for our title.
      wikiText = safeEncode(pathMatch[0].text)
      sanitizedText = sanitizeWikiText(wikiText)
      contentDict['all'] = sanitizedText

      # Parsing categories.
      if parseCategories and metadata is not None:
        # Looking for something like "Категория:Мосфильм"...
        categories = MATCHER_CATEGORY.findall(sanitizedText)
        for category in categories:
          metadata.collections.add(category)

      # Summary: section Сюжет.
      summary = getWikiSectionContent(u'\u0421\u044E\u0436\u0435\u0442', sanitizedText)
      if summary is not None:
        score += 2
        if metadata is not None:
          metadata.summary = summary
      # Adding "Интересные факты" when present to the summary.
      facts = getWikiSectionContent(u'\u0418\u043D\u0442\u0435\u0440\u0435\u0441\u043D\u044B\u0435 \u0444\u0430\u043A\u0442\u044B', sanitizedText)
      if facts is not None:
        score += 1
        if metadata is not None:
          metadata.summary = metadata.summary + '\n\nИнтересные факты:\n' + facts

      # Looking for the {{Фильм}} tag.
      match = MATCHER_FILM.search(sanitizedText)
      year = None
      if match:
        filmContent = match.groups(1)[1]
#        Log('    filmContent: \n' + filmContent)
        contentDict['film'] = filmContent
        score += 2

        # imdb: a number after "| imdb_id = "
        value = searchForFilmTagMatch('imdb_id', 'imdb_id', filmContent, contentDict)
        if value is not None:
          score += 1

        # Title: text after "| РусНаз = ".
        title = searchForFilmTagMatch(u'\u0420\u0443\u0441\u041D\u0430\u0437', 'title', filmContent)
        if title is not None:
          score += 1
          if metadata is not None:
            metadata.title = title

        # Tagline: something after triple-quoted title.
        # Example: '''Камень желаний''' (tagline content...
        matcher = re.compile('^\s*\'\'\'\s*\W?\s*' + title + '\s*\W?\s*\'\'\'(\s+[^\s\(]\s+|)\s*(.+)$', re.U | re.I | re.M)
        match = matcher.search(sanitizedText)
        if match:
          score += 1
          if metadata is not None:
            tagline = match.groups(1)[1]
            if not str(tagline).isdigit(): # Bizarre issue when no match is found.
              tagline = sanitizeWikiTextMore(tagline)
              if MATCHER_FIRST_LETTER.search(tagline):
                tagline = tagline.capitalize() # Only capitalizing if the first one is a letter.
              Log('::::::::::: tagline: %s...' % tagline[:40])
              metadata.tagline = tagline

        # Original title: text after "| ОригНаз = ".
        title = searchForFilmTagMatch(u'\u041E\u0440\u0438\u0433\u041D\u0430\u0437', 'original_title', filmContent)
        if title is not None:
          score += 1
          if metadata is not None:
            metadata.original_title = title

        # Year: a number after "| Год = ".
        value = searchForFilmTagMatch(u'\u0413\u043E\u0434', 'year', filmContent)
        if value is not None:
          score += 1
          year = str(parseInt(value))
          # Year is set below.

        # Duration: a number after "| Время = ".
        duration = searchForFilmTagMatch(u'\u0412\u0440\u0435\u043C\u044F', 'duration', filmContent)
        if duration is not None:
          score += 1
          if metadata is not None:
            metadata.duration = parseInt(duration) * 1000

        # Studio: a number after "| Компания = ".
        studios = searchForFilmTagMatch(u'\u041A\u043E\u043C\u043F\u0430\u043D\u0438\u044F', 'studio', filmContent, isMultiLine = True)
        if studios is not None and len(studios) > 0:
          score += 1
          if metadata is not None:
            studio = MATCHER_PO_ZAKAZU.sub(r'\1', studios[0])  # Removing annoying "по заказу..." if it's present.
            metadata.studio = studio  # Only one studio is supported.

        # Image: file name after "| Изображение = ".
        imageName = searchForFilmTagMatch(u'\u0418\u0437\u043E\u0431\u0440\u0430\u0436\u0435\u043D\u0438\u0435', 'image', filmContent, contentDict)
        if imageName is not None:
          score += 1

        # Genre: "<br/> or ,"-separated values after "| Жанр = ".
        genres = searchForFilmTagMatch(u'\u0416\u0430\u043D\u0440', 'genres', filmContent, isMultiLine = True)
        if genres is not None and len(genres) > 0:
          score += 1
          if metadata is not None:
            for genre in genres:
              metadata.genres.add(genre)

        # Directors: "<br/> or ,"-separated values after "| Режиссёр = ".
        directors = searchForFilmTagMatch(u'\u0420\u0435\u0436\u0438\u0441\u0441\u0451\u0440', 'directors', filmContent, isMultiLine = True)
        if directors is not None and len(directors) > 0:
          score += 1
          if metadata is not None:
            for director in directors:
              metadata.directors.add(director)

        # Writers: "<br/> or ,"-separated values after "| Сценарист = ".
        writers = searchForFilmTagMatch(u'\u0421\u0446\u0435\u043D\u0430\u0440\u0438\u0441\u0442', 'writers', filmContent, isMultiLine = True)
        if writers is not None and len(writers) > 0:
          score += 1
          if metadata is not None:
            for writer in writers:
              metadata.writers.add(writer)

        # Actors: "<br/> or ,"-separated values after "| Актёры = ".
        roles = searchForFilmTagMatch(u'\u0410\u043A\u0442\u0451\u0440\u044B', 'roles', filmContent, isMultiLine = True)
        if roles is not None and len(roles) > 0:
          score += 1
          if metadata is not None:
            parseActorsInfo(roles, metadata, sanitizedText, isGetAllActors)

        # Country: "<br/> or ,"-separated values after "| Страна = ".
        countries = searchForFilmTagMatch(u'\u0421\u0442\u0440\u0430\u043D\u0430', 'countries', filmContent, isMultiLine = True)
        if countries is not None and len(countries) > 0:
          score += 1
          if metadata is not None:
            parseWikiCountries(countries, metadata)

      # If there was no film tag, looking for year else where.
      if year is None:
        match = MATCHER_SOME_YEAR.search(sanitizedText)
        if match:
          year = match.groups(1)[0]
      if year is not None:
        contentDict['year'] = year
        if metadata is not None:
          metadata.year = int(year)
          metadata.originally_available_at = Datetime.ParseDate('%s-01-01' % year).date()

    except:
      Log('ERROR: unable to parse wiki page!')

    Log(':::::::::::::::::::: score ' + str(score) + ' for URL:\n    ' + wikiPageUrl)
    contentDict['score'] = score
    return contentDict


  def findWikiPageMatches(self, mediaName, mediaYear, results, lang):
    """ Using Wikipedia query API, tries to determine most probable pages
        for the media item we are looking for. The matches are added to the
        passed results list as MetadataSearchResult objects.

        Note, that we still need to fetch a page for every match to
        determine page id, title year, and get the score.
    """
    try:
      Log('Searching for titles with name="%s" and year="%s"' % (str(mediaName), str(mediaYear)))
      prefMaxResults = int(Prefs[PREF_MAX_RESULTS_NAME])
      minPageScore = int(Prefs[PREF_MIN_PAGE_SCORE])
      pageMatches = []
      queryStr = mediaName
      if mediaYear is not None:
        queryStr += '_' + mediaYear
      xmlResult = getXmlFromWikiApiPage(WIKI_QUERY_URL % queryStr)
      pathMatch = xmlResult.xpath('//api/query/searchinfo')
      if len(pathMatch) == 0:
        Log('ERROR: searchinfo is not found in a WIKI response.')
        raise Exception
      else:
        if pathMatch[0].get('totalhits') == '0':
          # TODO - implement case
          Log('INFO: No hits found! Getting a suggestion... NOT SUPPORTED YET!')
          raise Exception
        else:
          pageMatches = xmlResult.xpath('//api/query/search/p')

      # Grabbing the first N results (if there are any).
      matchOrder = 0
      for match in pageMatches:
        pageTitle = safeEncode(match.get('title'))
        pageId = None
        titleYear = None
        matchesMap = self.getAndParseItemsWikiPage(WIKI_TITLEPAGE_URL % pageTitle)
        if matchesMap is not None:
          if 'id' in matchesMap:
            pageId = matchesMap['id']
          if 'year' in matchesMap:
            titleYear = int(matchesMap['year'])
        if isBlank(pageId):
          pageId = self.titleAndYearToId(pageTitle, mediaYear)

        score = scoreMovieMatch(mediaName, mediaYear, matchOrder, pageTitle, matchesMap)
        if score > minPageScore:  # Ignoring very low scored matches.
          results.Append(MetadataSearchResult(id = pageId,
                                              name = pageTitle,
                                              year = titleYear,
                                              lang = lang,
                                              score = score))
          matchOrder += 1
        if matchOrder == prefMaxResults:
          break # Got enough matches, stop.
    except:
      Log('ERROR: Unable to produce WIKI matches!')


  def getDataFromImdb(self, imdbId):
    """ Fetches and parses a title page from IMDB given title id.
        Parsed data is retuned in a dictionary with the following keys:
          'rating'.
        All values are strings or lists of strings.
    """
    imdbData = {}
    try:
      content = HTTP.Request(IMDB_TITLEPAGE_URL % imdbId).content
      if content:
        match = MATCHER_IMDB_RATING.search(content)
        if match:
          rating = match.groups(1)[0]
          Log('Parsed IMDB rating: "%s"' % rating)
          imdbData['rating'] = rating
        else:
          Log('IMDB rating is NOT found!')
    except:
      Log('ERROR: unable to fetch or parse IMDB data.')
    return imdbData


def scoreMovieMatch(mediaName, mediaYear, matchOrder, pageTitle, matchesMap):
  # Checking the title from filename with title in the match.
  # If no words from title are found in the media name, this is not our match. 
  titleScore = compareTitles(mediaName, pageTitle)
  Log('AAAAAAAAAAAAAAAAAAAAAAAA %s' % str(titleScore))
  if titleScore == 0:
    score = 0
  else:
    score = 50 + titleScore

  if matchOrder == 0:
    score += SCORE_FIRST_ITEM_BONUS
  else:  
    # Score is diminishes as we move down the list.
    score = score - (matchOrder * SCORE_ORDER_PENALTY)

  # Adding matches from the wikipage (2 points for each find).
  if 'score' in matchesMap:
    wikiScore = int(matchesMap['score'])
    if wikiScore == 0:
      score = score - SCORE_NOFILMDATA_PENALTY
    else:
      score += int(wikiScore * SCORE_WIKIMATCH_IMPORTANCE)

  # Wiki year matching year from filename is a good sign.
  if 'year' in matchesMap:
    yearFromWiki = matchesMap['year']
    if mediaYear is not None:
      if yearFromWiki == mediaYear:
        score += 20
      elif abs(int(yearFromWiki) - int(mediaYear)) < 3:
        score += 5 # Might be a mistake.
      else:
        score = score - SCORE_BADYEAR_PENALTY # If years don't match - penalize the score.
  else:
    score = score - SCORE_NOYEAR_PENALTY

  if score > 100:
    score = 100
  elif score < 0:
    score = 0

  return score


def compareTitles(titleFrom, titleTo):
  """ Takes words from titleFrom string and checks
      if the titleTo contains these words. For each
      match, score is increased by 2.
  """
  score = 0
  title = titleTo.lower()
  for word in titleFrom.lower().split():
    if title.find(word) >= 0:
      score += 2
  return score


def getXmlFromWikiApiPage(wikiPageUrl):
  wikiPageUrl = wikiPageUrl.replace(' ', '%20')  # TODO(zhenya): encode the whole URL?
  requestHeaders = { 'User-Agent': USER_AGENT }
  return XML.ElementFromURL(wikiPageUrl, headers=requestHeaders)


def isBlank(string):
  return string is None or not string or string.strip() == ''


def safeEncode(s, encoding='utf-8'):
  if s is None:
    return None
  if isinstance(s, basestring):
    if isinstance(s, types.UnicodeType):
      return s
    else:
      return s.decode(encoding)
  else:
    return str(s).decode(encoding)


def parseFilmLineItems(line):
  items = []
  matcher = re.compile('\<br\s*/?\>')
  if matcher.search(line):
    line = line.replace(',', '') # When <br/> tags are there, commas are just removed.
    line = matcher.sub(',', line)
  for item in line.split(','):
    item = item.strip(' \t\n\r\f\v"«»')
    if len(item) > 0:
      items.append(string.capwords(item))
  return items


def searchForFilmTagMatch(name, key, text, dict=None, isMultiLine=False):
  """ Searches for a match given a compiled matcher and text.
      Parsed group 1 is returned if it's not blank; otherwise None is returned.
      If dict is present, the value will be placed there for the provided key.
  """
  matcher = re.compile(u'^\s*\|\s*' + name + '\s*=\s*(.*?\||\s*$|.*?\s*$)', re.I | re.M | re.U | re.S)
  match = matcher.search(text)
  if match:
    value = match.groups(1)[0].strip('|\t\n\r\f\v')
    if not isBlank(value):
      if isMultiLine:
        values = parseFilmLineItems(value)
        Log('::::::::::: %s: [%s]' % (key, ', '.join(values)))
        return values
      else:
        Log('::::::::::: %s: "%s"' % (key, value[:40]))
        if dict is not None:
          dict[key] = value.strip()
        return value
  Log('::::::::::: %s: BLANK' % key)
  return None


def sanitizeWikiText(wikiText):
  """ Generic sanitization of wiki text to remove bracket tags
      or links, for example: "[[something]]" or "[[something|somethingelse]]".
  """
  # This takes care of removing links and brackets; for example,
  # "[[link to something|something]]" would turn into just "something".
  matcher = re.compile('\[\[([^\[\]]+?)\|([^\[\]]+?)\]\]', re.M | re.L)
  wikiText = matcher.sub(r'\2', wikiText)

  # This takes care of removing double brackets (e.g. [[something]]).
  matcher = re.compile('\[\[([^\[\]]+?)\]\]', re.M | re.L | re.U)
  wikiText = matcher.sub(r'\1', wikiText)

  # Removing a few tags (file tags - "[[Файл...]]").
  matcher = re.compile(u'\[\[\u0424\u0430\u0439\u043B[^\[\]]+?\]\]', re.U)
  wikiText = matcher.sub('', wikiText)

  # This takes care of removing links and braces; for example,
  # "{{lang-sv|Arn – Tempelriddaren}}" would turn into just "Arn – Tempelriddaren".
  # Note: negative lookahead is because we'd like to skip the Фильм tag.
  matcher = re.compile(u'\{\{\s*((?!\u0424\u0438\u043B\u044C\u043C)[^\{\}]*?)\|([^\{\}]+?)\s*\}\}', re.M | re.L | re.I)
  wikiText = matcher.sub(r' \2 ', wikiText)

  # Removing a few hardcoded decoration tags.
  matcher = re.compile('\s*<small>\s*(.*?)\s*</small>\s*', re.M | re.S | re.U)
  wikiText = matcher.sub(r' \1 ', wikiText)

  # Removing acute characters.
  matcher = re.compile(u'\u0301', re.U)
  wikiText = matcher.sub('', wikiText)

  return wikiText


def sanitizeWikiTextMore(wikiText):
  """ Does more sanitization of wiki text to remove other
      wiki artifacts that are not remove by sanitizeWikiText().
  """
  # Removing brace tags, for example: "{{Длинное описание сюжета}}".
  matcher = re.compile('\s*\{\{[^\}]+?\}\}', re.M | re.L | re.U)
  wikiText = matcher.sub('', wikiText)

  # Removing XML/HTML tags.
  matcher = re.compile('\s*\<(?P<tagname>[a-zA-Z_]+)(\>|\s).*?\</(?P=tagname)\>', re.M | re.U | re.I)
  wikiText = matcher.sub('', wikiText)
  matcher = re.compile('\s*\<[a-zA-Z_]+\s+[^\>/]*?\s*/\>', re.M | re.U | re.I)
  wikiText = matcher.sub('', wikiText)

  # Other hardcoded tags.
  matcher = re.compile('\</?poem\>', re.M | re.I)
  wikiText = matcher.sub('', wikiText)

  return wikiText.strip()


def getWikiSectionContent(sectionTitle, wikiText):
  # TODO(zhenya): fix the last section case (when there is no other "==").
  matcher = re.compile(u'^(?P<quotes>===?)\s' + sectionTitle + '\s(?P=quotes)\s*$\s*(.+?)\s*^==[^=]', re.S | re.M | re.I)
  match = matcher.search(wikiText)
  if match:
    content = sanitizeWikiTextMore(match.groups(1)[1])
    if not isBlank(content):
      Log('::::::::::: section "%s": %s...' % (sectionTitle, content[:40]))
      return content
  return None


def parseActorsInfo(roles, metadata, wikiText, isGetAllActors):
  # Parsing the roles section (В ролях).
  rolesSection = getWikiSectionContent(u'\u0412 \u0440\u043E\u043B\u044F\u0445', wikiText)
  if rolesSection is None:
    return
  actorsMap = {}
  try:
    for m in MATCHER_ACTOR_LINE.finditer(rolesSection):
      actorName = m.groups(1)[0].strip()
      if not isBlank(actorName):
        roleName = MATCHER_ACTOR_ROLE.sub(r'\1', m.groups(1)[2])
        roleName = roleName.replace('|', ' ') # Weird case.
        if isBlank(roleName):
          roleName = DEFAULT_ACTOR_ROLE
        actorsMap[actorName] = roleName
  except:
    Log('ERROR: unable to parse actors!')

  try:
    # Stars should go first so they end up on the top of the list.
    for actorName in roles:
      role = metadata.roles.new()
      role.actor = actorName
      roleName = actorsMap.pop(actorName, None)
      if roleName is None:
        roleName = DEFAULT_ACTOR_ROLE
      role.role = roleName
      # role.photo = 'http:// todo...'
      Log('::::::::::: actor "%s", role="%s"' % (actorName, roleName))

    if isGetAllActors:
      for actorName, roleName in actorsMap.iteritems():
        role = metadata.roles.new()
        role.actor = actorName
        role.role = roleName
        # role.photo = 'http:// todo...'
        Log('::::::::::: actor "%s", role="%s"' % (actorName, roleName))
  except:
    Log('ERROR: unable to add actors!')


def parseWikiCountries(countriesStr, metadata):
  """ Parses countries from a WIKI country Film tag. For example:
        "{{SUN}} <br />{{UKR}}"
        "{{Флаг Израиля}} Израиль<br />{{Флаг США}} США"
        "СССР — Япония"
      List of sanatized country names is returned.
  """
  # TODO(zhenya): Implement parsing countries.
  pass


def parseInt(string):
  " Gets the first number characters and returns them as an int. "
  match = MATCHER_FIRST_INTEGER.search(string)
  if match:
    return int(match.groups(1)[0])
  else:
    return None
  