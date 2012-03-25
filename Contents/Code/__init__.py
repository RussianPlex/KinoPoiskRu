# coding=utf-8

import datetime, string, re, time, unicodedata, hashlib, urlparse, types

AGENT_VERSION = '0.1'
USER_AGENT = 'Plex WikipediaRu Metadata Agent (+http://www.plexapp.com/) v.%s' % AGENT_VERSION

##############  Preference item names.
PREF_IS_DEBUG_NAME = 'wikiru_pref_is_debug'
PREF_LOG_LEVEL_NAME = 'wikiru_pref_log_level'
PREF_CACHE_TIME_NAME = 'wikiru_pref_cache_time'
PREF_MAX_RESULTS_NAME = 'wikiru_pref_wiki_results'
PREF_IGNORE_CATEGORIES_NAME = 'wikiru_pref_ignore_categories'
PREF_MIN_PAGE_SCORE = 'wikiru_pref_min_page_score'
PREF_GET_ALL_ACTORS = 'wikiru_pref_get_all_actors'

##############  WIKIpedia URLs.
WIKI_QUERY_URL = 'http://ru.wikipedia.org/w/api.php?action=query&list=search&srprop=timestamp&format=xml&srsearch=%s_(фильм)'
WIKI_TITLEPAGE_URL = 'http://ru.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=timestamp|user|comment|content&format=xml&titles=%s'
WIKI_IDPAGE_URL = 'http://ru.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=timestamp|user|comment|content&format=xml&pageids=%s'
WIKI_QUERYFILE_URL = 'http://ru.wikipedia.org/w/api.php?action=query&prop=imageinfo&iiprop=url&format=xml&titles=Файл:%s'

IMDB_TITLEPAGE_URL = 'http://www.imdb.com/title/tt%s'

############## Unicode russian strings.
RU_Izobrazhenie = u'\u0418\u0437\u043E\u0431\u0440\u0430\u0436\u0435\u043D\u0438\u0435' # Изображение
RU_File = u'\u0424\u0430\u0439\u043B' # Файл
RU_film = u'\u0444\u0438\u043B\u044C\u043C' # фильм
RU_Film = u'\u0424\u0438\u043B\u044C\u043C' # Фильм
RU_multfilm = u'\u043C\u0443\u043B\u044C\u0442\u0444\u0438\u043B\u044C\u043C' # мультфильм
RU_Multfilm = u'\u041C\u0443\u043B\u044C\u0442\u0444\u0438\u043B\u044C\u043C' # Мультфильм
RU_Multserial = u'\u041C\u0443\u043B\u044C\u0442\u0441\u0435\u0440\u0438\u0430\u043B' # Мультсериал
RU_Teleserial = u'\u0422\u0435\u043B\u0435\u0441\u0435\u0440\u0438\u0430\u043B' # Телесериал
WIKI_FILM_TAGNAME = RU_Film + '|' + RU_Multfilm + '|' + RU_Teleserial + '|' + RU_Multserial
WIKI_TITLE_ANNOTATION = RU_film + '|' + RU_multfilm


############## Compiled regexes.
# WIKI film tag: {{Фильм }} or {{Мультфильм }} or {{Телесериал }}.
MATCHER_FILM_TAG = re.compile('\{\{\s*(' + WIKI_FILM_TAGNAME + ')\\b\s*(([^\{\}]*?\{\{[^\{\}]*?\}\}[^\{\}]*?)*|.*?)\s*\}\}', re.S | re.M | re.U | re.I)
# IMDB rating, something like this "<span class="rating-rating">5.0<span>".
MATCHER_IMDB_RATING = re.compile('<div\s+class\s*=\s*"star-box-giga-star">\s*(\d+\.\d+)\s*</div>', re.M | re.S)
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
# Wiki's (фильм) or (мультфильм) title annotation.
MATCHER_FILM_TITLE_ANNOTATION = re.compile('\s*\((' + WIKI_TITLE_ANNOTATION + ')\)\s*$', re.U | re.I)
MATCHER_SANITIZED_YEAR = re.compile('.*?(\d\d\d\d).*', re.S)

############## MoviePosterDB constants.
MPDB_ROOT = 'http://movieposterdb.plexapp.com'
MPDB_JSON = MPDB_ROOT + '/1/request.json?imdb_id=%s&api_key=p13x2&secret=%s&width=720&thumb_width=100'
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
# Kino-Teatr.ru URLs.
#KTRU_QUERY_URL = 'http://www.kino-teatr.ru/search/'


class LocalSettings():
  """ These instance variables are populated from plugin preferences. """
  # Current log level.
  # Supported values are: 0 = none, 1 = error, 2 = warning, 3 = info, 4 = fine, 5 = finest.
  logLevel = 1
  isDebug = False
  maxResults = 5
  minPageScore = 20
  ignoreCategories = False
  getAllActors = False

localPrefs = LocalSettings()


def Start():
  sendToInfoLog('***** START ***** %s' % USER_AGENT)
  readPluginPreferences()

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
    sendToInfoLog('SEARCH START <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
    year = None
    if media.year:
      year = safeEncode(media.year)
    sendToInfoLog('searching for name="%s", year="%s", guid="%s", hash="%s"...' %
        (str(media.name), str(year), str(media.guid), str(media.hash)))

    # Looking for wiki pages for this title.
    self.findWikiPageMatches(media.name, year, results, lang)
    if not len(results):
      # Modify (relax) the query and look for more pages.
      self.findWikiPageMatches(media.name, year, results, lang, isRelax=True)
    results.Sort('score', descending=True)
    if localPrefs.logLevel >= 3:
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
    """Updates the media title provided a page id on Russian wikipedia.
       Here, we look into the metadata.guid to parse WIKI page id and use
       it to fetch the page, which is going to be used to populate the
       media item record. Another field that could be used is metadata.title.
    """
    sendToInfoLog('UPDATE START <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
    part = media.items[0].parts[0]
    filename = part.file.decode('utf-8')
    sendToInfoLog('filename="%s", guid="%s"' % (filename, metadata.guid))

    matcher = re.compile(r'//(\d+)\?')
    match = matcher.search(metadata.guid)
    if match:
      wikiId = match.groups(1)[0]
    else:
      sendToErrorLog('no wiki id is found!')
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
    parseCategories = not localPrefs.ignoreCategories
    tmpResult = self.getAndParseItemsWikiPage(wikiPageUrl, metadata, parseCategories = parseCategories, isGetAllActors = localPrefs.getAllActors)
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
    sendToInfoLog('UPDATE END <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


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
    # http://www.google.com/search?hl=en&biw=1200&bih=947&tbm=isch&q=Приключения%20Электроника
    sendToFinestLog('fetchAndSetWikiArtwork: WIKI image "%s".' % str(wikiImgName))
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
        sendToFinestLog('loading URL "%s".' % str(wikiImgQueryUrl))
        xmlResult = getXmlFromWikiApiPage(wikiImgQueryUrl)
        pathMatch = xmlResult.xpath('//api/query/pages/page')
        if not len(pathMatch):
          sendToErrorLog('unable to parse page "%s".' % wikiImgQueryUrl)
          raise Exception

        missing = pathMatch[0].get('missing')
        if missing is not None:
          sendToErrorLog('file "%s" does not seem to exist.' % wikiImgName)
          raise Exception

        pathMatch = pathMatch[0].xpath('//imageinfo/ii')
        if not len(pathMatch):
          sendToErrorLog('image section is not found in a WIKI response.')
          raise Exception

        thumbUrl = pathMatch[0].get('url')
        if thumbUrl is not None and thumbUrl not in metadata.posters:
          response = sendHttpRequest(thumbUrl)
          metadata.posters[thumbUrl] = Proxy.Preview(response, sort_order = sortOrder)
          posters_valid_names.append(thumbUrl)
          sendToFineLog('Setting a poster from wikipedia: "%s"' % thumbUrl)
    except:
      sendToErrorLog('unable to fetch art work.')

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
    sendToFinestLog('looking for images on MPDB...')
    secret = Hash.MD5( ''.join([MPDB_SECRET, imdb_code]))[10:22]
    queryJSON = JSON.ObjectFromURL(MPDB_JSON % (imdb_code, secret), cacheTime=10)
    i = 0
    if not queryJSON.has_key('errors') and queryJSON.has_key('posters'):
      sendToFinestLog('found images on MPDB')
      for poster in queryJSON['posters']:
        imageUrl = MPDB_ROOT + '/' + poster['image_location']
        thumbUrl = MPDB_ROOT + '/' + poster['thumbnail_location']
        full_image_url = imageUrl + '?api_key=p13x2&secret=' + secret

        if poster['language'] == 'RU' or poster['language'] == 'US':
          metadata.posters[full_image_url] = Proxy.Preview(sendHttpRequest(thumbUrl), sort_order = i)
          posters_valid_names.append(full_image_url)
          i += 1
          sendToFineLog('adding a poster from MPDB: "%s"' % imageUrl)
        else:
          sendToFinestLog('MPDB poster is skipped: "%s"' % imageUrl)
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
       and also to write the fetched and parsed data into a
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
      if not len(pathMatch):
        sendToErrorLog('unable to parse page "%s".' % wikiPageUrl)
        return None

      missing = pathMatch[0].get('missing')
      if missing is not None:
        sendToErrorLog('page "%s" does not seem to exist.' % wikiPageUrl)
        return None

      contentDict['id'] = pathMatch[0].get('pageid')
      pathMatch = pathMatch[0].xpath('//revisions/rev')
      if not len(pathMatch):
        sendToErrorLog('page "%s" revision is not found in a WIKI response.' % wikiPageUrl)
        return None

      # This is the content of the entire page for our title.
      sendToFineLog('WIKI page is fetched, parsing it...')
      wikiText = safeEncode(pathMatch[0].text)
      sanitizedText = sanitizeWikiText(wikiText)
      contentDict['all'] = sanitizedText

      # Parsing categories.
      if parseCategories and metadata is not None:
        # Looking for something like "Категория:Мосфильм"...
        categories = MATCHER_CATEGORY.findall(sanitizedText)
        sendToFineLog('WIKI page contains %d <categories>' % len(categories))
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
      match = MATCHER_FILM_TAG.search(wikiText)
      year = None
      if match:
        filmContent = sanitizeWikiFilmTagText(match.groups(1)[1])
        sendToFinestLog('*** WIKI film tag:\n%s' % filmContent)
        contentDict['film'] = filmContent
        score += 2

        # imdb: a number after "| imdb_id = "
        value = searchForFilmTagMatch('imdb_id', 'imdb_id', filmContent, contentDict)
        if value is not None:
          score += 1

        # Title: text after "| РусНаз = ".
        title = searchForFilmTagMatch(u'\u0420\u0443\u0441\u041D\u0430\u0437', 'title', filmContent)
        if title is None:
          # Try a different name - "Название"
          title = searchForFilmTagMatch(u'\u041D\u0430\u0437\u0432\u0430\u043D\u0438\u0435', 'title', filmContent)
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
                sendToFineLog(' ... tagline: %s...' % tagline[:50])
                metadata.tagline = tagline

        # Original title: text after "| ОригНаз = ".
        origTitle = searchForFilmTagMatch(u'\u041E\u0440\u0438\u0433\u041D\u0430\u0437', 'original_title', filmContent)
        if origTitle is not None:
          score += 1
          if metadata is not None:
            metadata.original_title = origTitle

        # Year: a number after "| Год = ".
        year = filmTagParseYear(filmContent)

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
        imageName = searchForFilmTagMatch(RU_Izobrazhenie, 'image', filmContent, contentDict)
        if imageName is not None:
          score += 1

        # Genre: "<br/> or ,"-separated values after "| Жанр = ".
        genres = searchForFilmTagMatch(u'\u0416\u0430\u043D\u0440', 'genres', filmContent, isMultiLine = True, treatSlashAsBreak=True)
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
        if roles is None:
          # Also look for "в ролях".
          roles = searchForFilmTagMatch(u'\u0432\s+\u0440\u043E\u043B\u044F\u0445', 'roles', filmContent, isMultiLine = True)
        if roles is not None and len(roles) > 0:
          score += 1
          if metadata is not None:
            parseActorsInfo(roles, metadata, sanitizedText, isGetAllActors)

        # Country: "<br/> or ,"-separated values after "| Страна = ".
        countries = searchForFilmTagMatch(u'\u0421\u0442\u0440\u0430\u043D\u0430', 'countries', filmContent, isMultiLine = True, treatSlashAsBreak=True)
        if countries is not None and len(countries) > 0:
          score += 1
          if metadata is not None:
            parseWikiCountries(countries, metadata)
      else:
        sendToInfoLog('WIKI page contains NO <film tag>')

      # If there was no film tag, looking for year else where.
      if year is None:
        match = MATCHER_SOME_YEAR.search(sanitizedText)
        if match:
          year = match.groups(1)[0]
      if year is not None:
        score += 1
        contentDict['year'] = year
        if metadata is not None:
          metadata.year = int(year)
          metadata.originally_available_at = Datetime.ParseDate('%s-01-01' % year).date()

    except:
      sendToErrorLog('unable to parse wiki page: "%s"!' % wikiPageUrl)

    sendToFinestLog('::::::: initial score::: %d for WIKI page URL:\n    %s' % (score, wikiPageUrl))
    contentDict['score'] = score
    return contentDict


  def findWikiPageMatches(self, mediaName, mediaYear, results, lang, isRelax=False):
    """ Using Wikipedia query API, tries to determine most probable pages
        for the media item we are looking for. The matches are added to the
        passed results list as MetadataSearchResult objects.

        Note, that we still need to fetch a page for every match to
        determine page id, title year, and get the score.
    """
    try:
      sendToFineLog('using maxResults=%s and minPageScore=%s' % (str(localPrefs.maxResults), str(localPrefs.minPageScore)))
      pageMatches = []
      queryStr = mediaName
      if not isRelax and mediaYear is not None:
        queryStr += '_' + mediaYear
      xmlResult = getXmlFromWikiApiPage(WIKI_QUERY_URL % queryStr)
      pathMatch = xmlResult.xpath('//api/query/searchinfo')
      if not len(pathMatch):
        sendToErrorLog('searchinfo is not found in a WIKI response for "%s"!' % str(mediaName))
        raise Exception
      else:
        if pathMatch[0].get('totalhits') == '0':
          # TODO - implement case
          sendToFineLog('No hits found! Getting a suggestion... NOT SUPPORTED YET!')
          raise Exception
        else:
          pageMatches = xmlResult.xpath('//api/query/search/p')

      # Grabbing the first N results (if there are any).
      itemIndex = 0
      for match in pageMatches:
        pageTitle = safeEncode(match.get('title'))
        pageId = None
        titleYear = None
        sendToFineLog('@@@@@@@@@@@@@@@ checking WIKI title page for "%s"...' % pageTitle)
        matchesMap = self.getAndParseItemsWikiPage(WIKI_TITLEPAGE_URL % pageTitle)
        if matchesMap is not None:
          if 'id' in matchesMap:
            pageId = matchesMap['id']
          if 'year' in matchesMap:
            titleYear = int(matchesMap['year'])
        if isBlank(pageId):
          pageId = self.titleAndYearToId(pageTitle, mediaYear)

        score = scoreMovieMatch(mediaName, mediaYear, itemIndex, pageTitle, matchesMap)
        sendToFinestLog('::::::: final score::::: %d for WIKI title page "%s"' % (score, pageTitle))
        if score > localPrefs.minPageScore:  # Ignoring very low scored matches.
          results.Append(MetadataSearchResult(id = pageId,
                                              name = pageTitle,
                                              year = titleYear,
                                              lang = lang,
                                              score = score))
          itemIndex += 1
        else:
          sendToFineLog('::::::: "%s" page is SKIPPED' % pageTitle)
        if itemIndex == localPrefs.maxResults:
          break # Got enough matches, stop.
    except:
      sendToErrorLog('unable to produce WIKI matches for "%s"!' % str(mediaName))


  def getDataFromImdb(self, imdbId):
    """ Fetches and parses a title page from IMDB given title id.
        Parsed data is returned in a dictionary with the following keys:
          'rating'.
        All values are strings or lists of strings.
    """
    imdbData = {}
    try:
      content = sendHttpRequest(IMDB_TITLEPAGE_URL % imdbId).content
      if content:
        match = MATCHER_IMDB_RATING.search(content)
        rating = None
        if match:
          rating = match.groups(1)[0]
          imdbData['rating'] = rating
        sendToFineLog('  ... IMDB rating: "%s"' % str(rating))
    except:
      sendToErrorLog('unable to fetch or parse IMDB data for id %s.' % str(imdbId))
    return imdbData


def scoreMovieMatch(mediaName, mediaYear, itemIndex, pageTitle, matchesMap):
  """ Checking the title from filename with title in the match.
      If no words from title are found in the media name, this is not our match.
  """
  sendToFinestLog('media name = "' + str(mediaName) + '", year = "' + str(mediaYear) + '", page title = "' + str(pageTitle) + '"...')
  score = compareTitles(mediaName, pageTitle)
  sendToFinestLog('title compare score: ' + str(score))
  if not score:
    # Title is too different - consider it's no match.
    return 0

  if not itemIndex:
    score += SCORE_FIRST_ITEM_BONUS
  else:  
    # Score is diminishes as we move down the list.
    score = score - (itemIndex * SCORE_ORDER_PENALTY)

  # Adding matches from the wikipage (2 points for each find).
  if 'score' in matchesMap:
    wikiScore = int(matchesMap['score'])
    if not wikiScore:
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


def compareTitles(mediaName, pageTitle):
  """ Takes words from mediaName string and checks
      if the titleTo contains these words. For each
      match, score is increased by 2.
  """
  # Remove wiki's (фильм) or similar annotations from page title.
  sanatizedTitle = MATCHER_FILM_TITLE_ANNOTATION.sub('', pageTitle).lower()
  if mediaName == sanatizedTitle:
    return 50 # Word-for-word, case ignored match.
  score = 0
  for word in mediaName.split():
    if sanatizedTitle.find(word) >= 0:
      score += 2
      if score >= 10:
        break
  if score > 0:
    return 30 + score
  else:
    return 0


def getXmlFromWikiApiPage(wikiPageUrl):
  wikiPageUrl = wikiPageUrl.replace(' ', '%20')  # TODO(zhenya): encode the whole URL?
  requestHeaders = { 'User-Agent': USER_AGENT, 'Accept': 'text/html'}
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


def parseFilmLineItems(line, treatSlashAsBreak=False):
  items = []
  matcher = re.compile('\<br\s*/?\>', re.I | re.U)
  if matcher.search(line):
    line = line.replace(',', '') # When <br/> tags are there, commas are just removed.
    line = matcher.sub(',', line)
  for item in line.split(','):
    item = item.strip(' \t\n\r\f\v"«»')
    if len(item) > 0:
      if treatSlashAsBreak:
        for subItem in item.split('/'):
          items.append(string.capwords(subItem))
      else:
        items.append(string.capwords(item))
  return items


def searchForFilmTagMatch(name, key, text, dict=None, isMultiLine=False, treatSlashAsBreak=False):
  """ Searches for a match given a compiled matcher and text.
      Parsed group 1 is returned if it's not blank; otherwise None is returned.
      If dict is present, the value will be placed there for the provided key.
  """
  matcher = re.compile('^\s*\|\s*' + name + '\s*=\s*(.*?\||\s*$|.*?\s*$)', re.I | re.M | re.U | re.S)
  match = matcher.search(text)
  if match:
    value = match.groups(1)[0].strip('|\t\n\r\f\v')
    if not isBlank(value):
      if isMultiLine:
        values = parseFilmLineItems(value, treatSlashAsBreak)
        sendToFineLog('  ... %s: [%s]' % (key, ', '.join(values)))
        return values
      else:
        value = value.strip()
        sendToFineLog('  ... %s: "%s"' % (key, value[:40]))
        if dict is not None:
          dict[key] = value
        return value
  sendToFineLog('  ... %s: BLANK' % key)
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
  matcher = re.compile('\[\[' + RU_File +'[^\[\]]+?\]\]', re.U)
  wikiText = matcher.sub('', wikiText)

  # This takes care of removing links and braces; for example,
  # "{{lang-sv|Arn – Tempelriddaren}}" would turn into just "Arn – Tempelriddaren".
  # Need a negative lookahead to skip the {{Фильм}} tag.
  matcher = re.compile('\{\{\s*((?!' + WIKI_FILM_TAGNAME + ')[^\{\}]*?)\|([^\{\}]+?)\s*\}\}', re.M | re.L | re.I)
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


def sanitizeWikiFilmTagText(wikiText):
  """ Generic sanitization of wiki Film tag text.
  """
  # Unwrap image file tag, so "[[Файл:Dorogaja kopejka.jpg|220 px]]" or "[[Файл:Dorogaja kopejka.jpg]]"
  # would become just "Dorogaja kopejka.jpg".
  matcher = re.compile('(' + RU_Izobrazhenie + '\s*=\s*)\[\[' + RU_File + '\s*:\s*([^\[\]]+?)(\|([^\[\]]+?))?\]\].*', re.U | re.I)
  wikiText = matcher.sub(r'\1\2', wikiText)
  return sanitizeWikiText(wikiText)


def getWikiSectionContent(sectionTitle, wikiText):
  matcher = re.compile('^(?P<quotes>===?)\s' + sectionTitle + '\s(?P=quotes)\s*$\s*(.+?)\s*^(==|\{\{)[^=]', re.S | re.U | re.M | re.I)
  match = matcher.search(wikiText)
  if match:
    content = sanitizeWikiTextMore(match.groups(1)[1])
    if not isBlank(content):
      sendToFinestLog('------ section "%s": %s...' % (sectionTitle, content[:40]))
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
    sendToErrorLog('unable to parse actors!')

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
      sendToFineLog('  ... actor "%s", role="%s"' % (actorName, roleName))

    if isGetAllActors:
      for actorName, roleName in actorsMap.iteritems():
        role = metadata.roles.new()
        role.actor = actorName
        role.role = roleName
        # role.photo = 'http:// todo...'
        sendToFineLog('  ... actor "%s", role="%s"' % (actorName, roleName))
  except:
    sendToErrorLog('unable to add actors!')


def parseWikiCountries(countriesStr, metadata):
  """ Parses countries from a WIKI country Film tag. For example:
        "{{SUN}} <br />{{UKR}}"
        "{{Флаг Израиля}} Израиль<br />{{Флаг США}} США"
        "СССР — Япония"
      List of sanitized country names is returned.
  """
  # TODO(zhenya): Implement parsing countries.
  pass


def filmTagParseYear(filmContent):
  """ Parses year from a film tag (a number after "| Год = "), also
      considering the following entries: "Премьера" and "первый_показ".
  """
  # Year:
  value = searchForFilmTagMatch(u'\u0413\u043E\u0434', 'year', filmContent)
  if value is None:
    # Looking for Премьера instead.
    value = searchForFilmTagMatch(u'\u041F\u0440\u0435\u043C\u044C\u0435\u0440\u0430', 'year', filmContent)
  if value is None:
    # Looking for первый_показ.
    value = searchForFilmTagMatch(u'\u043F\u0435\u0440\u0432\u044B\u0439_\u043F\u043E\u043A\u0430\u0437', 'year', filmContent)
  if value is not None:
    match = MATCHER_SANITIZED_YEAR.search(value)
    if match:
      return match.groups()[0] # Year is set below.
  return None


def parseInt(string):
  """ Gets the first number characters and returns them as an int. """
  match = MATCHER_FIRST_INTEGER.search(string)
  if match:
    return int(match.groups(1)[0])
  else:
    return None


def sendHttpRequest(url):
  # Note that these headers are not strictly necessary.
  headers = {'User-agent': USER_AGENT, 'Accept': 'text/html'}
  return HTTP.Request(url, headers = headers)


def sendToFinestLog(msg):
  if localPrefs.logLevel >= 5:
    if localPrefs.isDebug:
      print 'FINEST: ' + msg
    else:
      Log.Debug(msg)


def sendToFineLog(msg):
  if localPrefs.logLevel >= 4:
    if localPrefs.isDebug:
      print 'FINE: ' + msg
    else:
      Log.Info(msg)


def sendToInfoLog(msg):
  if localPrefs.logLevel >= 3:
    if localPrefs.isDebug:
      print 'INFO: ' + msg
    else:
      Log.Debug(msg)


def sendToWarnLog(msg):
  if localPrefs.logLevel >= 2:
    if localPrefs.isDebug:
      print 'WARN: ' + msg
    else:
      Log.WARN(msg)


def sendToErrorLog(msg):
  if localPrefs.logLevel >= 1:
    if localPrefs.isDebug:
      print 'ERROR: ' + msg
    else:
      Log.ERROR(msg)

      
def readPluginPreferences():
  prefLogLevel = Prefs[PREF_LOG_LEVEL_NAME]
  if prefLogLevel == u'ничего':
    localPrefs.logLevel = 0
  elif prefLogLevel == u'предупреждения':
    localPrefs.logLevel = 2
  elif prefLogLevel == u'информативно':
    localPrefs.logLevel = 3
  elif prefLogLevel == u'подробно':
    localPrefs.logLevel = 4
  elif prefLogLevel == u'очень подробно':
    localPrefs.logLevel = 5
  else:
    localPrefs.logLevel = 1 # Default is error.
  localPrefs.isDebug = Prefs[PREF_IS_DEBUG_NAME]

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

  localPrefs.maxResults = int(Prefs[PREF_MAX_RESULTS_NAME])
  localPrefs.minPageScore = int(Prefs[PREF_MIN_PAGE_SCORE])
  localPrefs.ignoreCategories = Prefs[PREF_IGNORE_CATEGORIES_NAME]
  localPrefs.getAllActors = Prefs[PREF_GET_ALL_ACTORS]

  sendToInfoLog('PREF: Setting debug to %s.' % str(localPrefs.isDebug))
  sendToInfoLog('PREF: Setting log level to %d (%s).' % (localPrefs.logLevel, prefLogLevel))
  sendToInfoLog('PREF: Setting cache expiration to %d seconds (%s)' % (cacheExp, prefCache))
  sendToInfoLog('PREF: WIKI max results is set to %s' % localPrefs.maxResults)
  sendToInfoLog('PREF: Min page score is set to %s' % localPrefs.minPageScore)
  sendToInfoLog('PREF: Ignore WIKI categories is set to %s' % str(localPrefs.ignoreCategories))
  sendToInfoLog('PREF: Parse all actors is set to %s' % str(localPrefs.getAllActors))
