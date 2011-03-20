import datetime, string, os, re, time, unicodedata, hashlib, urlparse, types

WIKI_QUERY_URL = 'http://ru.wikipedia.org/w/api.php?action=query&list=search&srprop=timestamp&format=xml&srsearch=%s_(фильм)'
WIKI_TITLEPAGE_URL = 'http://ru.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=timestamp|user|comment|content&format=xml&titles=%s'
WIKI_IDPAGE_URL = 'http://ru.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=timestamp|user|comment|content&format=xml&pageids=%s'
WIKI_QUERYFILE_URL = 'http://ru.wikipedia.org/w/api.php?action=query&prop=imageinfo&iiprop=url&format=xml&titles=Файл:%s'
USER_AGENT = 'Plex RussianMovie Agent (+http://www.plexapp.com/) v.%s'
AGENT_VERSION = '0.1'
QUERY_CACHE_TIME = 3600
WIKI_RESULTS_NUMBER = 5

IMDB_TITLEPAGE_URL = 'http://www.imdb.com/title/tt%s'

############## Compiled regexes
# The {{Фильм }} tag. ##################################
#MATCHER_FILM = re.compile(u'\{\{\u0424\u0438\u043B\u044C\u043C([^{}]*\{\{[^{}]*\}\}[^{}]*)\}\}\s*$', re.S | re.M)
#MATCHER_FILM = re.compile(u'\{\{\u0424\u0438\u043B\u044C\u043C\s*(^\s*\|\s*.*$)^(\s*\}\}|[^\|])', re.S | re.M)
MATCHER_FILM = re.compile(u'\{\{\u0424\u0438\u043B\u044C\u043C\s*(.*?)\s*^[^|]', re.S | re.M)
#MATCHER_FILM = re.compile(u'\{\{\u0424\u0438\u043B\u044C\u043C(.*?)^\}\}$', re.S | re.M)
# imdb ID: "| imdb_id = ".
MATCHER_FILM_IMDBID = re.compile(u'^\s*\|\s*imdb_id\s*=\s*(\d+)\s*$', re.M)
# Title: "| РусНаз = ".
MATCHER_FILM_TITLE = re.compile(u'^\s*\|\s*\u0420\u0443\u0441\u041D\u0430\u0437\s*=\s*([^|]*?)\s*$', re.S | re.M)
# Original title: "| ОригНаз = ".
MATCHER_FILM_ORIGINAL_TITLE = re.compile(u'^\s*\|\s*\u041E\u0440\u0438\u0433\u041D\u0430\u0437\s*=\s*([^|]*?)\s*$', re.S)
# Year: "| Год = ".
MATCHER_FILM_YEAR = re.compile(u'^\s*\|\s*\u0413\u043E\u0434\s*=\s*(\d{4})\s*$', re.M)
# Duration: a number after "| Время = ".
MATCHER_FILM_DURATION = re.compile(u'^\s*\|\s*\u0412\u0440\u0435\u043C\u044F\s+=\s+(\d+)\s+.*$', re.S | re.M)
# Studio: text after "| Компания = ".
MATCHER_FILM_STUDIO = re.compile(u'^\s*\|\s*\u041A\u043E\u043C\u043F\u0430\u043D\u0438\u044F\s*=\s*([^|]*?)\s*$', re.S | re.M)
# Studio: filename after "| Изображение = ".
MATCHER_FILM_IMAGE = re.compile(u'^\s*\|\s*\u0418\u0437\u043E\u0431\u0440\u0430\u0436\u0435\u043D\u0438\u0435\s*=\s*([^|]*?)\s*$', re.S | re.M)
# Genre: text after "| Жанр = ".
MATCHER_FILM_GENRES = re.compile(u'^\s*\|\s*\u0416\u0430\u043D\u0440\s*=\s*([^|]*?)\s*$', re.S | re.M)
# Directors: text after "| Режиссёр = ". 
MATCHER_FILM_DIRECTORS = re.compile(u'^\s*\|\s*\u0420\u0435\u0436\u0438\u0441\u0441\u0451\u0440\s*=\s*([^|]*?)\s*$', re.S | re.M)
# Writers: text after "| Сценарист = ".
MATCHER_FILM_WRITERS = re.compile(u'^\s*\|\s*\u0421\u0446\u0435\u043D\u0430\u0440\u0438\u0441\u0442\s*=\s*([^|]*?)\s*$', re.S | re.M)
# Actors: text after "| Актёры = ".
MATCHER_FILM_ROLES = re.compile(u'^\s*\|\s*\u0410\u043A\u0442\u0451\u0440\u044B\s*=\s*([^|]*?)\s*$', re.S | re.M)
# Country: text after "| Страна = ".
MATCHER_FILM_COUNTRIES = re.compile(u'^\s*\|\s*\u0421\u0442\u0440\u0430\u043D\u0430\s*=\s*([^|]*?)$', re.S | re.M)
# The summary - something in between "== Сюжет ==" and the next section.
MATCHER_SUMMARY = re.compile(u'^==\s\u0421\u044E\u0436\u0435\u0442\s==\s*$\s*(.+?)\s*^==\s', re.S | re.M)

# Filename regexes. ##################################
MATCHER_FILENAME_SPACES = re.compile('(\s\s+|_+)', re.U)
MATCHER_FILENAME_EXTENSION = re.compile('\.\w+$', re.U)
# Filename's item info: the CD, film, серия, часть, etc. at the end (e.g. "- CD1").
MATCHER_FILENAME_CDINFO = re.compile('\s*-\s*(\w*\s*\d{0,3}|\d{0,3}\w*\s*)$', re.U)
# Filename's year: the parenthesized version.
MATCHER_FILENAME_YEAR_PARENS = re.compile('\s*\(\s*(\d{4})\s*\)\s*', re.U)
# Filename's year: year's on the left.
MATCHER_FILENAME_YEAR_LEFT = re.compile('^\s*(\d{4})\s*-?\s*', re.U)
# Filename's year: year's on the right.
MATCHER_FILENAME_YEAR_RIGHT = re.compile('\s*-?\s*(\d{4})\s*$', re.U)


# IMDB rating, something like this "<span class="rating-rating">5.0<span>".
MATCHER_IMDB_RATING = re.compile('<span\s+class\s*=\s*"rating-rating">\s*(\d+\.\d+)\s*<span', re.M | re.S)


# MoviePosterDB constants.
MPDB_ROOT = 'http://movieposterdb.plexapp.com'
MPDB_JSON = MPDB_ROOT + '/1/request.json?imdb_id=%s&api_key=p13x2&secret=%s&width=720&thumb_width=100'
MPDB_SECRET = 'e3c77873abc4866d9e28277a9114c60c'


# TODO(zhenya): parse WIKI categories and make them optional via user preferences.

# Constants that influence matching score on titles.
SCORE_ORDER_PENALTY = 3
SCORE_WIKIMATCH_IMPORTANCE = 2
SCORE_NOFILMDATA_PENALTY = 15
SCORE_BADYEAR_PENALTY = 15
SCORE_NOYEAR_PENALTY = 10
SCORE_BADTITLE_PENALTY = 20

# ruslania - good source of images and taglines?
#      content = HTTP.Request('http://ruskino.ru/mov/search', params).content.strip()
#      content = HTTP.Request('http://www.ozon.ru/?context=search&text=Место%20встречи%20изменить%20нельзя', None, {}, 360).content.strip()
#      query = 'http://www.ozon.ru/?context=search&text=' + str.replace(titleMaybe, ' ', '%20')
# [might want to look into language/country stuff at some point]
# param info here: http://code.google.com/apis/ajaxsearch/documentation/reference.html
#


def Start():
  HTTP.CacheTime = CACHE_1HOUR * 4

class PlexMovieAgent(Agent.Movies):
  name = 'RussianMovie'
  print 'RussianMovie - ctor :START'
  languages = [Locale.Language.Russian]
  print 'RussianMovie - ctor :END'


  ##############################################################################
  ############################# S E A R C H ####################################
  ##############################################################################
  def search(self, results, media, lang, manual=False):
    """Parses the filename and searches for matches on Russian wikipedia.
       Some information is retrieved from IMDB.

       Found matches saved in the results list as MetadataSearchResult objects.
       For each results, we determine match's wiki page id, title, year,
       and the score (how good we think the match is on the scale of 1 - 100).
    """

    Log(': : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : : :')
    Log('RUSSIANMOVIE.search: START <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')

    # Parse title and year from the filename.
    part = media.items[0].parts[0]
    filepath = part.file.decode('utf-8')
    filename = os.path.basename(filepath)
    info = self.parseTitleAndYearFromFilename(filename)
    if info['title'] is None:
      info['title'] = media.name

    # Looking for wiki pages for this title.
    self.findWikiPageMatches(info, results, lang)

    results.Sort('score', descending=True)

    Log('SEARCH got %d results:' % len(results))
    for result in results:
      Log('  ... result: id=%s, name=%s, year=%s, score=%d' % (result.id, result.name, str(result.year), result.score))

    Log('RUSSIANMOVIE.search: FINISH <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


  ##############################################################################
  ############################# U P D A T E ####################################
  ##############################################################################
  def update(self, metadata, media, lang):
    """Updates the media title provided a page id on Russian wikipedia.
       Here, we look into the metadata.guid to parse WIKI page id and use
       it to fetch the page, which is going to be used to populate the
       media item record. Another field that could be used is metadata.title.
    """
    Log('RUSSIANMOVIE.update: START <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')

    
    part = media.items[0].parts[0]
    filename = part.file.decode('utf-8')
    plexHash = part.plexHash
    Log('+++++++++++++++ media filename: ' + filename)
    Log('+++++++++++++++ plexHash: ' + plexHash)
    Log('+++++++++++++++ metadata.guid: ' + metadata.guid)

    matcher = re.compile(r'//(\d+)\?')
    match = matcher.search(metadata.guid)
    wikiId = None
    if match:
      wikiId = match.groups(1)[0]
    else:
      Log('ERROR: no wiki id is found!')
      raise Exception('no wiki id is found!')

    # Set the title. FIXME, this won't work after a queued restart.
    # Only do this once, otherwise we'll pull new names that get edited
    # out of the database.
    #
    if media and metadata.title is None:
      metadata.title = media.title

    imdbId = None
    imdbData = None
    wikiImgName = None
    wikiPageUrl = WIKI_IDPAGE_URL % wikiId
    tmpResult = self.getAndParseItemsWikiPage(wikiPageUrl, metadata)
    if tmpResult is not None:
      wikiContent = tmpResult['all']
      if 'image' in tmpResult:
        wikiImgName = tmpResult['image']
      if 'imdb_id' in tmpResult:
        imdbId = tmpResult['imdb_id']
        imdbData = self.getDataFromImdb(imdbId)

    # Tagline.
#    metadata.tagline = ''
#    metadata.trivia = 'triviaaaaaaaaaaaaaaa'
#    metadata.quotes = 'quotesssssssssssss'

    if imdbData is not None:
      # Content rating.
      if 'rating' in imdbData:
        metadata.rating = float(imdbData['rating'])
        # metadata.content_rating =  G/PG/etc.


    # Getting artwork.
    self.fetchAndSetWikiArtwork(metadata, wikiImgName, imdbId)

#      LogChildren(metadata) ???????? Where is this method ?????????

    Log('RUSSIANMOVIE.update: FINISH <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


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
        imdb_code = imdbId.replace('tt','').lstrip('t0')
        sortOrder = self.moviePosterDBupdate(metadata, posters_valid_names, imdb_code)

      # Fetching an image from the wikipedia.
      if wikiImgName is not None:
        wikiImgQueryUrl = WIKI_QUERYFILE_URL % wikiImgName
        xmlResult = getXmlFromWikiApiPage(wikiImgQueryUrl)
        pathMatch = xmlResult.xpath('//api/query/pages/page')
        if len(pathMatch) == 0:
          Log('ERROR: unable to parse page "%s".' % wikiImgQueryUrl)
          # TODO(zhenya): raise an error.

        missing = pathMatch[0].get('missing')
        if missing is not None:
          Log('ERROR: file "%s" does not seem to exist.' % wikiImgName)
          # TODO(zhenya): raise an error.

        pathMatch = pathMatch[0].xpath('//imageinfo/ii')
        if len(pathMatch) == 0:
          Log('ERROR: image section is not found in a WIKI response.')
          # TODO(zhenya): raise an error.

        thumbUrl = pathMatch[0].get('url')
        if thumbUrl is not None:
          url = thumbUrl
          metadata.posters[url] = Proxy.Preview(HTTP.Request(thumbUrl, cacheTime=QUERY_CACHE_TIME), sort_order = sortOrder)
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
    string = unicodedata.normalize('NFKD', safe_unicode(string))
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


  def parseTitleAndYearFromFilename(self, filename):
    """Parses media item's title and year from the filename.

       If this operation fails, title is set to filename and
       year to empty. Returns an object with properties 'year' and 'title'
       (both might have None values).
    """
    Log('Parsing filename: "%s"' % filename)
    year = None
    title = None

    # Removing file extension, stacking data (CD1, etc.),
    # extra spaces, and underscores.
    name = MATCHER_FILENAME_EXTENSION.sub('', filename)
    name = MATCHER_FILENAME_SPACES.sub(' ', name)
    name = MATCHER_FILENAME_CDINFO.sub('', name)

    # Parsing and removing the parenthesized year if it's present.
    # Note the order - it matters.
    match = MATCHER_FILENAME_YEAR_PARENS.search(name)
    if match:
      year = match.groups(1)[0]
      name = MATCHER_FILENAME_YEAR_PARENS.sub(' ', name)
    if year is None:
      match = MATCHER_FILENAME_YEAR_LEFT.search(name)
      if match:
        year = match.groups(1)[0]
        name = MATCHER_FILENAME_YEAR_LEFT.sub('', name)
      else:
        match = MATCHER_FILENAME_YEAR_RIGHT.search(name)
        if match:
          year = match.groups(1)[0]
          name = MATCHER_FILENAME_YEAR_RIGHT.sub('', name)

    if not isBlank(name):
      title = name.strip()

    Log('Parsed from filename: title="%s", year="%s"' % (str(title), str(year)))
    return {'year': year, 'title': title}


  def parseWikiCountries(self, countriesStr):
    """ Parses countries from a WIKI country Film tag. For example:
          "{{SUN}} <br />{{UKR}}"
          "{{Флаг Израиля}} Израиль<br />{{Флаг США}} США"
          "СССР — Япония"
        List of sanatized country names is returned.
    """
    # TODO(zhenya): implement this method.
    countries = []
    #    countryCodes = parseFilmLineItems(countriesStr)
    return countries


  def getAndParseItemsWikiPage(self, wikiPageUrl, metadata = None):
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
        metadata.studio = ''
        metadata.summary = ''
        metadata.title = ''
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
      wikiText = safe_unicode(pathMatch[0].text)
      sanitizedText = sanitizeWikiText(wikiText)
      contentDict['all'] = sanitizedText

      # Parsing the summary.
      summary = searchForMatch(MATCHER_SUMMARY, 'summary', sanitizedText)
      if summary is not None:
        score += 2
        if metadata is not None:
          metadata.summary = sanitizeWikiTextMore(summary)

      # Looking for the {{Фильм}} tag.
      match = MATCHER_FILM.search(sanitizedText)
      year = None
      if match:
        filmContent = match.groups(1)[0]
        filmContent = filmContent.rstrip('}}') # We might have a trailing '}}'.
#        Log('    filmContent: \n' + filmContent)
        contentDict['film'] = filmContent
        score += 2

        # imdb: a number after "| imdb_id = "
        value = searchForMatch(MATCHER_FILM_IMDBID, 'imdb_id', filmContent, contentDict)
        if value is not None:
          score += 1

        # Title: text after "| РусНаз = ".
        title = searchForMatch(MATCHER_FILM_TITLE, 'title', filmContent)
        if title is not None:
          score += 1
          if metadata is not None:
            metadata.title = title

        # Original title: text after "| ОригНаз = ".
        title = searchForMatch(MATCHER_FILM_ORIGINAL_TITLE, 'original_title', filmContent)
        if title is not None:
          score += 1
          if metadata is not None:
            metadata.original_title = title

        # Year: NNNN number after "| Год = ".
        value = searchForMatch(MATCHER_FILM_YEAR, 'year', filmContent)
        if value is not None:
          score += 1
          year = value
          # Year is set below.

        # Duration: a number after "| Время = ".
        duration = searchForMatch(MATCHER_FILM_DURATION, 'duration', filmContent)
        if duration is not None:
          score += 1
          if metadata is not None:
            metadata.duration = int(duration) * 1000

        # Studio: a number after "| Компания = ".
        studios = searchForMatch(MATCHER_FILM_STUDIO, 'studio', filmContent, isMultiLine = True)
        if studios is not None and len(studios) > 0:
          score += 1
          if metadata is not None:
            # Removing annoying "по заказу..." if it's present.
            matcher = re.compile(u'(.*?)\s*\u043F\u043E\s\u0437\u0430\u043A\u0430\u0437\u0443.*', re.M | re.L)
            # Only one studio is supported.
            metadata.studio = matcher.sub(r'\1', studios[0])

        # Image: file name after "| Изображение = ".
        imageName = searchForMatch(MATCHER_FILM_IMAGE, 'image', filmContent, contentDict)
        if imageName is not None:
          score += 1

        # Genre: "<br />" separated values after "| Жанр = ".
        genres = searchForMatch(MATCHER_FILM_GENRES, 'genres', filmContent, isMultiLine = True)
        if genres is not None and len(genres) > 0:
          score += 1
          if metadata is not None:
            for genre in genres:
              metadata.genres.add(genre)

        # Directors: "<br />" separated values after "| Режиссёр = ".
        directors = searchForMatch(MATCHER_FILM_DIRECTORS, 'directors', filmContent, isMultiLine = True)
        if directors is not None and len(directors) > 0:
          score += 1
          if metadata is not None:
            for director in directors:
              metadata.directors.add(director)

        # Writers: "<br />" separated values after "| Сценарист = ".
        writers = searchForMatch(MATCHER_FILM_WRITERS, 'writers', filmContent, isMultiLine = True)
        if writers is not None and len(writers) > 0:
          score += 1
          if metadata is not None:
            for writer in writers:
              metadata.writers.add(writer)

        # Actors: "<br />" separated values after "| Актёры = ".
        roles = searchForMatch(MATCHER_FILM_ROLES, 'roles', filmContent, isMultiLine = True)
        if roles is not None and len(roles) > 0:
          score += 1
          if metadata is not None:
            for actor in roles:
              role = metadata.roles.new()
              role.role = 'Актер' # TODO(zhenya): find out the role.
              role.actor = actor
              # role.photo = person.get('thumb')  # TODO(zhenya): find out the pic.

        # Country: "<br />" separated values after "| Страна = ".
        countries = searchForMatch(MATCHER_FILM_COUNTRIES, 'countries', filmContent, isMultiLine = True)
        if countries is not None and len(countries) > 0:
          score += 1
          # TODO(zhenya): Implement parsing countries.
          # match = MATCHER_FILM_COUNTRIES.search(filmContent)
          # if match:
          # contentDict['countries'] = self.parseWikiCountries(match.groups(1)[0])

      # If there was no film tag, looking for year else where.
      if year is None:
        value = searchForMatch(MATCHER_FILM_YEAR, 'year', sanitizedText)
        if value is not None:            
          year = value
      if year is not None:
        contentDict['year'] = year
        if metadata is not None:
          metadata.year = int(year)
#          metadata.originally_available_at = Datetime.ParseDate('%s-01-01' % year).date()

    except:
      Log('ERROR: unable to parse wiki page!')

    Log(':::::::::::::::::::: score ' + str(score) + ' for URL:\n    ' + wikiPageUrl)
    contentDict['score'] = score
    return contentDict


  def findWikiPageMatches(self, filenameInfo, results, lang):
    """ Using Wikipedia query API, tries to determine most probable pages
        for the media item we are looking for. The matches are added to the
        passed results list as MetadataSearchResult objects.

        Note, that we still need to fetch a page for every match to
        determine page id, title year, and get the score.
    """
    try:
      pageMatches = []
      # TODO(zhenya): use year in the query.
      yearFromFilename = filenameInfo['year']
      titleFromFilename = filenameInfo['title']
      # TODO(zhenya): encode URL.
      wikiQueryUrl = WIKI_QUERY_URL % titleFromFilename
      xmlResult = getXmlFromWikiApiPage(wikiQueryUrl)
      pathMatch = xmlResult.xpath('//api/query/searchinfo')
      if len(pathMatch) == 0:
        # TODO(zhenya): raise an error?
        Log('ERROR: searchinfo is not found in a WIKI response.')
      else:
        totalhits = pathMatch[0].get('totalhits')
        if int(totalhits) == 0:
          # TODO - implement case
          Log('INFO: No hits found! Getting a suggestion...')
        else:
          pageMatches = xmlResult.xpath('//api/query/search/p')

      # Grabbing the first N results (in case if there are any).
      matchOrder = 0
      for match in pageMatches:
        pageTitle = safe_unicode(match.get('title'))
        pageId = None
        titleYear = None
        wikiPageUrl = WIKI_TITLEPAGE_URL % pageTitle
        matchesMap = self.getAndParseItemsWikiPage(wikiPageUrl)
        if matchesMap is not None:
          if 'id' in matchesMap:
            pageId = matchesMap['id']
          if 'year' in matchesMap:
            titleYear = int(matchesMap['year'])
        if isBlank(pageId):
          pageId = self.titleAndYearToId(pageTitle, yearFromFilename)

        score = scoreMovieMatch(matchOrder, filenameInfo, pageTitle, matchesMap)
        results.Append(MetadataSearchResult(id = pageId,
                                            name = pageTitle,
                                            year = titleYear,
                                            lang = lang,
                                            score = score))
        matchOrder += 1
        if matchOrder == WIKI_RESULTS_NUMBER:
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
      content = HTTP.Request(IMDB_TITLEPAGE_URL % imdbId, cacheTime=QUERY_CACHE_TIME).content
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


def scoreMovieMatch(matchOrder, filenameInfo, pageTitle, matchesMap):
  score = 60 # Starting score.
  yearFromFilename = filenameInfo['year']
  titleFromFilename = filenameInfo['title']

  # Score is diminishes as we move down the list.
  # TODO - take into consideration WIKI_RESULTS_NUMBER
  orderPenalty = matchOrder * SCORE_ORDER_PENALTY
  score = score - orderPenalty

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
    if yearFromFilename is not None:
      if yearFromWiki == yearFromFilename:
        score += 20
      elif abs(int(yearFromWiki) - int(yearFromFilename)) < 3:
        score += 5 # Might be a mistake.
      else:
        score = score - SCORE_BADYEAR_PENALTY # If years don't match - penalize the score.
  else:
    score = score - SCORE_NOYEAR_PENALTY

  # Checking the title from filename with title in the match.
  score += compareTitles(titleFromFilename, pageTitle)

  if score > 100:
    score = 100
  elif score < 0:
    score = 0
  
  return score


def compareTitles(titleFrom, titleTo):
  """ Takes words from titleFrom string and checks
      if the titleTo contains these words. For each
      match, score is increased by 2. If no matches are
      found SCORE_BADTITLE_PENALTY (-20) is returned.
  """
  score = 0
  title = titleTo.lower()
  for word in titleFrom.lower().split():
    if title.find(word) >= 0:
      score += 2
  if score == 0:
    score = score - SCORE_BADTITLE_PENALTY
  return score


def getXmlFromWikiApiPage(wikiPageUrl):
  # TODO(zhenya): encode URL.
  wikiPageUrl = wikiPageUrl.replace(' ', '%20')
  requestHeaders = { 'User-Agent': USER_AGENT % AGENT_VERSION }
  return XML.ElementFromURL(wikiPageUrl, headers=requestHeaders, cacheTime=QUERY_CACHE_TIME)


def isBlank(string):
  return string is None or not string or string.strip() == ''

  
def safe_unicode(s, encoding='utf-8'):
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
  # Making all possible breaks to be the same before split.
  line = line.replace('<br />', '<br/>')
  line = line.replace('<br/>', '<br>')
  for item in line.split('<br>'):
    items.append(string.capwords(item.strip().strip(',')))
  return items


def searchForMatch(matcher, key, text, dict=None, isMultiLine=False):
  """ Searches for a match given a compiled matcher and text.
      Parsed group 1 is returned if it's not blank; otherwise None is returned.
      If dict is present, the value will be placed there for the provided key.
  """
  match = matcher.search(text)
  if match:
    value = match.groups(1)[0]
    if not isBlank(value):
      if isMultiLine:
        values = parseFilmLineItems(value)
        Log('::::::::::: metadata.%s: [%s]' % (key, ', '.join(values)))
        return values
      else:
        Log('::::::::::: metadata.%s: %s' % (key, value[:30]))
        if dict is not None:
          dict[key] = value
        return value
  Log('::::::::::: metadata.%s: BLANK' % key)
  return None

def sanitizeWikiText(wikiText):
  """ Generic sanitization of wiki text to remove bracket tags
      or links, for example: "[[something]]" or "[[something|somethingelse]]".
  """
  # This takes care of removing links and brackets around, for example,
  # "[[link to something|something]]" would turn into just "something".
  matcher = re.compile('\[\[([^\[\]]+?)\|([^\[\]]+?)\]\]', re.M | re.L)
  wikiText = matcher.sub(r'\2', wikiText)

  # This takes care of removing double brackets (e.g. [[something]]).
  matcher = re.compile('\[\[([^\[\]]+?)\]\]', re.M | re.L)
  wikiText = matcher.sub(r'\1', wikiText)

  # Removing even more brackets (file tags - "[[Файл...]]").
#    matcher = re.compile(u'\[\[\u0424\u0430\u0439\u043B[^\[\]]+?\]\]', re.M | re.L)
#    wikiText = matcher.sub('', wikiText)

  return wikiText


def sanitizeWikiTextMore(wikiText):
  """ Does more sanitization of wiki text to remove other
      wiki artifacts that are not remove by sanitizeWikiText().
  """
  # Removing brace tags, for example: "{{Длинное описание сюжета}}".
  matcher = re.compile(u'\s*\{\{[^\}]+?\}\}', re.M | re.L)
  wikiText = matcher.sub('', wikiText)

  # Removing XML/HTML tags.
  matcher = re.compile(u'\s*\<(?P<tagname>[a-zA-Z_]+)\s+.*?\</(?P=tagname)\>', re.M | re.U | re.I)
  wikiText = matcher.sub('', wikiText)

  return wikiText
