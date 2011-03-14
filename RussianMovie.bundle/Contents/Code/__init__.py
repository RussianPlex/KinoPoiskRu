import datetime, string, re, time, unicodedata, hashlib, urlparse, types

WIKI_QUERY_URL = 'http://ru.wikipedia.org/w/api.php?action=query&list=search&srprop=timestamp&format=xml&srsearch=%s'
WIKI_TITLEPAGE_URL = 'http://ru.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=timestamp|user|comment|content&format=xml&titles=%s'
WIKI_IDPAGE_URL = 'http://ru.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=timestamp|user|comment|content&format=xml&pageids=%s'
USER_AGENT = 'Plex RussianMovie Agent (+http://www.plexapp.com/) v.%s'
AGENT_VERSION = '0.1'
QUERY_CACHE_TIME = 3600
WIKI_RESULTS_NUMBER = 5

IMDB_TITLEPAGE_URL = 'http://www.imdb.com/title/tt%s'

############## Compiled regexes
# The {{Фильм }} tag.
#MATCHER_FILM = re.compile(u'\{\{\u0424\u0438\u043B\u044C\u043C([^{}]*\{\{[^{}]*\}\}[^{}]*)\}\}\s*$', re.S | re.M)
#MATCHER_FILM = re.compile(u'\{\{\u0424\u0438\u043B\u044C\u043C\s*(^\s*\|\s*.*$)^(\s*\}\}|[^\|])', re.S | re.M)
MATCHER_FILM = re.compile(u'\{\{\u0424\u0438\u043B\u044C\u043C\s*(.*?)\s*^[^|]', re.S | re.M)
#MATCHER_FILM = re.compile(u'\{\{\u0424\u0438\u043B\u044C\u043C(.*?)^\}\}$', re.S | re.M)
# imdb ID: "| imdb_id = ".
MATCHER_FILM_IMDBID = re.compile(u'^\s*\|\s*imdb_id\s*=\s*(\d+)\s*$', re.M)
# Title: "| РусНаз = ".
MATCHER_FILM_TITLE = re.compile(u'^\s*\|\s*\u0420\u0443\u0441\u041D\u0430\u0437\s*=\s*(.*?)\s*$', re.M | re.S)
# Year: "| Год = ".
MATCHER_FILM_YEAR = re.compile(u'^\s*\|\s*\u0413\u043E\u0434\s*=\s*(\d{4})\s*$', re.M)
# Duration: a number after "| Время = ".
MATCHER_FILM_DURATION = re.compile(u'^\s*\|\s*\u0412\u0440\u0435\u043C\u044F\s+=\s+(\d+)\s+.*$', re.M | re.S)
# Studio: a number after "| Компания = ".
MATCHER_FILM_STUDIO = re.compile(u'^\s*\|\s*\u041A\u043E\u043C\u043F\u0430\u043D\u0438\u044F\s*=\s*(.*?)\s*$', re.S | re.M)
# Genre: text after "| Жанр = ".
MATCHER_FILM_GENRES = re.compile(u'^\s*\|\s*\u0416\u0430\u043D\u0440\s*=\s*(.*?)\s*$', re.S | re.M)
# Directors: text after "| Режиссёр = ". 
MATCHER_FILM_DIRECTORS = re.compile(u'^\s*\|\s*\u0420\u0435\u0436\u0438\u0441\u0441\u0451\u0440\s*=\s*(.*?)\s*$', re.S | re.M)
# Writers: text after "| Сценарист = ".
MATCHER_FILM_WRITERS = re.compile(u'^\s*\|\s*\u0421\u0446\u0435\u043D\u0430\u0440\u0438\u0441\u0442\s*=\s*(.*?)\s*$', re.S | re.M)
# Actors: text after "| Актёры = ".
MATCHER_FILM_ROLES = re.compile(u'^\s*\|\s*\u0410\u043A\u0442\u0451\u0440\u044B\s*=\s*(.*?)\s*$', re.S | re.M)
# Country: text after "| Страна = ".
MATCHER_FILM_COUNTRIES = re.compile(u'^\s*\|\s*\u0421\u0442\u0440\u0430\u043D\u0430\s*=\s*(.*?)$', re.S | re.M)
# The summary - something in between "== Сюжет ==" and the next section.
MATCHER_SUMMARY = re.compile(u'==\s\u0421\u044E\u0436\u0435\u0442\s==\s*\n(.+?)\n\s*==\s', re.S | re.M)



# Constants that influence matching score on titles.
# TODO - add these constants.

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

    Log('RUSSIANMOVIE.search: START <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')

    # Parse title and year from the filename.
    info = self.parseItemInfoFromFilename(media)

    # Looking for wiki pages for this title.
    self.findWikiPageMatches(info, results, lang)

    results.Sort('score', descending=True)

    Log('got %d results' % len(results))
    for result in results:
      if result.score > 100:
        result.score = 100
      elif result.score < 0:
        result.score = 0
      Log('  ... result: id=%s, name=%s, year=%d, score=%d' % (result.id, result.name, result.year, result.score))

#    results[0].score = 100
    # Duplicate matches are removed (by page ids).
#    duplicateMatches = []
#    resultMap = {}
#    for result in results:
#      if resultMap.has_key(result.id):
#        duplicateMatches.append(result)
#      else:
#        resultMap[result.id] = True
#
#    for dupe in duplicateMatches:
#      results.Remove(dupe)

    # Make sure we're using the closest names.
#    for result in results:
#      Log("id=%s score=%s -> Best name being changed from %s to %s" % (result.id, result.score, result.name, bestNameMap[result.id]))
#      result.name = bestNameMap[result.id]

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
        
    wikiPageUrl = WIKI_IDPAGE_URL % wikiId
    tmpResult = self.getAndParseItemsWikiPage(wikiPageUrl)
    if tmpResult is not None:
      wikiContent = tmpResult['all']

      # Title.
      if 'title' in tmpResult:
        metadata.title = tmpResult['title']
        Log('+++++++++++++++ metadata.title: ' + metadata.title)

      # Year.
      if 'year' in tmpResult:
        metadata.year = int(tmpResult['year'])
        Log('+++++++++++++++ metadata.year: ' + str(metadata.year))

      # Tagline.
      metadata.tagline = ''
        
      # Summary.
      if 'summary' in tmpResult:
        metadata.summary = tmpResult['summary']
        Log('+++++++++++++++ metadata.sumary: .........')

      # Duration.
      if 'duration' in tmpResult:
        metadata.duration = int(tmpResult['duration'])
        Log('+++++++++++++++ metadata.duration: ' + tmpResult['duration'])

      # Studio.
      if 'studio' in tmpResult:
        metadata.studio = tmpResult['studio']
        Log('+++++++++++++++ metadata.studio: ' + metadata.studio)

      # Genres.
      metadata.genres.clear()
      if 'genres' in tmpResult:
        for genre in tmpResult['genres']:
          Log('+++++++++++++++ metadata.genre: ' + genre)
          metadata.genres.add(genre)

      # Directors.
      metadata.directors.clear()
      if 'directors' in tmpResult:
        for director in tmpResult['directors']:
          Log('+++++++++++++++ metadata.director: ' + director)
          metadata.directors.add(director)

      # Writers.
      metadata.writers.clear()
      if 'writers' in tmpResult:
        for writer in tmpResult['writers']:
          Log('+++++++++++++++ metadata.writer: ' + writer)
          metadata.writers.add(writer)

      # Actors.
      metadata.roles.clear()
      if 'roles' in tmpResult:
        for actor in tmpResult['roles']:
          Log('+++++++++++++++ metadata.actor: ' + actor)
          role = metadata.roles.new()
          role.role = 'Актер' # TODO(zhenya): find out the role.
          role.actor = actor
          # role.photo = person.get('thumb')  # TODO(zhenya): find out the pic.

      # Countries.
      metadata.countries.clear()
      if 'countries' in tmpResult:
        for country in tmpResult['countries']:
          metadata.countries.add(country)
          Log('+++++++++++++++ metadata.country: ' + country)

      # Requesting more data from imdb if we have an id.
      if 'imdb_id' in tmpResult:
        imdbData = self.getDataFromImdb(tmpResult['imdb_id'])

        # Content rating.
        if 'rating' in imdbData:
          metadata.rating = float(imdbData['rating'])
          # metadata.content_rating =  ??? what's this?


    # Get the filename and the mod time.
#    filename = media.items[0].parts[0].file.decode('utf-8')
#    mod_time = os.path.getmtime(filename)
#    date = datetime.date.fromtimestamp(mod_time)
#    metadata.originally_available_at = Datetime.ParseDate(str(date)).date()
#    metadata.originally_available_at = Datetime.ParseDate('2008-03-11').date()
#    metadata.trivia = 'triviaaaaaaaaaaaaaaa'
#    metadata.quotes = 'quotesssssssssssss'
#    metadata.posters = {}
#    metadata.arf
#      LogChildren(metadata) ???????? Where is this method ?????????

    Log('RUSSIANMOVIE.update: FINISH <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


  def isBlank(self, string):
    return string == '' or string is None or not string


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
    if self.isBlank(year):
      string = "%s" % self.makeIdentifier(title)
    else:
      string = "%s_%s" % (self.makeIdentifier(title).lower(), year)
    return self.stringToId("%s" % string)


  def parseItemInfoFromFilename(self, media):
    """Parses media item's title and year from the filename.

       If this operation fails, title is set to filename and year to empty.
       Returns an object with properties 'year' and 'title'.
    """
    if media.name:
      print 'media.name: ' + media.name
    else:
      print 'media.name: None'
    if media.guid:
      print 'media.guid: ' + media.guid
    else:
      print 'media.guid: None'
    if media.title:
      print 'media.title: ' + media.title
    else:
      print 'media.title: None'
    if media.year:
      print 'media.year: ' + media.year
    else:
      print 'media.year: None'
    if media.id is None:
      print 'media.id is None'
    else:
      print 'media.id: ' + media.id

    year = ''
    title = ''
    match = re.search('^\s*([0-9]{4})[ \-_\.]+(.*?)[ \-_\.]*([0-9]{0,3})$', media.name)
    if match:
      print 'RegEx::: match is found!'
      year = match.groups(1)[0]
      title = match.groups(1)[1]
    else:
      print 'RegEx::: match is NOT found!'

    if not title:
      title = media.name


    # TODO(zhenya): handle other cases (e.g. year is on the right...).

    Log('Parsed from filename: title="' + title + '", year="' + year + '".')
    return {'year': year, 'title': title}


  def compareTitles(self, titleFrom, titleTo):
    """ Takes words from titleFrom string and checks
        if the titleTo contains these words. For each
        match, score is increased by 2. If no matches are
        found -20 is returned.
    """
    score = 0
    title = titleTo.lower()
    for word in titleFrom.lower().split():
      if title.find(word) >= 0:
        score += 2
    if score == 0:
      score = -20
    return score


  def sanitizeWikiText(self, wikiText):
    """Sanitizing wiki text to remove links (e.g. [[something]]).
    """
    # This takes care of removing links and brackets around, for example,
    # "[[link to something|something]]" would turn into just "something".
    matcher = re.compile('\[\[([^\[\]]+?)\|([^\[\]]+?)\]\]', re.M | re.L)
    wikiText = matcher.sub(r'\2', wikiText)

    # This takes care of removing double brackets (e.g. [[something]]).
    matcher = re.compile('\[\[([^\[\]]+?)\]\]', re.M | re.L)
    wikiText = matcher.sub(r'\1', wikiText)

    return wikiText


  def parseFilmLineItems(self, line):
    items = []
    # Making all possible breaks to be the same before split.
    line = line.replace('<br />', '<br/>')
    line = line.replace('<br/>', '<br>')
    for item in line.split('<br>'):
      items.append(string.capwords(item.strip().strip(',')))
    return items


  def parseWikiCountries(self, countriesStr):
    """ Parses countries from a WIKI country Film tag. For example:
          "{{SUN}} <br />{{UKR}}"
          "{{Флаг Израиля}} Израиль<br />{{Флаг США}} США"
          "СССР — Япония"
        List of sanatized country names is returned.
    """
    # TODO(zhenya): implement this method.
    countries = []
    #    countryCodes = self.parseFilmLineItems(countriesStr)
    return countries


  def getAndParseItemsWikiPage(self, wikiPageUrl):
    """Given a WIKI page URL, gets it and parses its content.

       Returns a dictionary with the following keys:
         'id', 'title', 'year', 'studio', 'imdb_id', 'summary',
         'duration', 'genres', 'directors', 'writers', 'roles', 'countries',
         'score', 'film', and 'all'.
       The later is the parsed and sanatized WIKI page content.
       Value for 'film' represents the {{Фильм}} tag if it's found.
       All values are strings or arrays of strings.

       Score is value [0, 10] that indicates how good a match is.
    """
    # TODO(zhenya): need to have two modes - full and partial (see where this method is being called from).
    # TODO(zhenya): move scoring out of this method.

    contentDict = {}
    score = 0
    try:
      requestHeaders = { 'User-Agent': USER_AGENT % AGENT_VERSION }
      res = XML.ElementFromURL(wikiPageUrl, headers=requestHeaders, cacheTime=QUERY_CACHE_TIME)
      pathMatch = res.xpath('//api/query/pages/page')
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
      sanitizedText = self.sanitizeWikiText(wikiText)
      contentDict['all'] = sanitizedText

      # Parsing the summary.
      match = MATCHER_SUMMARY.search(sanitizedText)
      if match:
        contentDict['summary'] = match.groups(1)[0]
        score += 1

      # Looking for the {{Фильм}} tag.
      match = MATCHER_FILM.search(sanitizedText)
      year = None
      if match:
        filmContent = match.groups(1)[0]
        filmContent = filmContent.strip('}}') # We might have a trailing '}}'.
        Log('-------------------- filmContent: \n' + filmContent)
        contentDict['film'] = filmContent
        score += 2

        # imdb: a number after "| imdb_id = "
        match = MATCHER_FILM_IMDBID.search(filmContent)
        if match:
          Log('++++++++ IMDB_ID')
          contentDict['imdb_id'] = match.groups(1)[0]
          score += 1

        # Title: text after "| РусНаз = ".
        match = MATCHER_FILM_TITLE.search(filmContent)
        if match:
          Log('++++++++ TITLE')
          contentDict['title'] = match.groups(1)[0]
          score += 1

        # Year: NNNN number after "| Год = ".
        match = MATCHER_FILM_YEAR.search(filmContent)
        if match:
          Log('++++++++ YEAR')
          year = match.groups(1)[0]
          score += 1

        # Duration: a number after "| Время = ".
        match = MATCHER_FILM_DURATION.search(filmContent)
        if match:
          Log('++++++++ DURATION')
          contentDict['duration'] = str(int(match.groups(1)[0]) * 1000)
          score += 1

        # Studio: a number after "| Компания = ".
        match = MATCHER_FILM_STUDIO.search(filmContent)
        if match:
          Log('++++++++ STUDIO')
          contentDict['studio'] = match.groups(1)[0]
          score += 1

        # Genre: "<br />" separated values after "| Жанр = ".
        match = MATCHER_FILM_GENRES.search(filmContent)
        if match:
          Log('++++++++ GENRES')
          contentDict['genres'] = self.parseFilmLineItems(match.groups(1)[0])
          score += 1

        # Directors: "<br />" separated values after "| Режиссёр = ".
        match = MATCHER_FILM_DIRECTORS.search(filmContent)
        if match:
          Log('++++++++ DIRECTORS')
          contentDict['directors'] = self.parseFilmLineItems(match.groups(1)[0])
          score += 1

        # Writers: "<br />" separated values after "| Сценарист = ".
        match = MATCHER_FILM_WRITERS.search(filmContent)
        if match:
          Log('++++++++ WRITERS')
          contentDict['writers'] = self.parseFilmLineItems(match.groups(1)[0])
          score += 1

        # Actors: "<br />" separated values after "| Актёры = ".
        match = MATCHER_FILM_ROLES.search(filmContent)
        if match:
          Log('++++++++ ACTORS')
          contentDict['roles'] = self.parseFilmLineItems(match.groups(1)[0])
          score += 1

        # Country: "<br />" separated values after "| Страна = ".
        match = MATCHER_FILM_COUNTRIES.search(filmContent)
        if match:
          contentDict['countries'] = self.parseWikiCountries(match.groups(1)[0])

      # If there was no film tag, looking for year else where.
      if year is None:
        match = MATCHER_FILM_YEAR.search(sanitizedText)
        if match:
          year = match.groups(1)[0]
          score += 1
      if year is not None:
        contentDict['year'] = year

    except:
      Log('ERROR: unable to parse wiki page!')

    Log('getAndParseItemsWikiPage ++++++++ score ' + str(score) + ' for URL:\n' + wikiPageUrl)
    contentDict['score'] = score
    return contentDict

  def findWikiPageMatches(self, info, results, lang):
    """ Using Wikipedia query API, tries to determine most probable pages
        for the media item we are looking for. The matches are added to the
        passed results list as MetadataSearchResult objects.

        Note, that we still need to fetch a page for every match to
        determine page id, title year, and get the score.
    """
    try:
      pageMatches = []
      # TODO(zhenya): use year in the query.
      yearFromFilename = info['year']
      titleFromFilename = info['title']
      # TODO(zhenya): encode URL.
      wikiQueryUrl = WIKI_QUERY_URL % titleFromFilename.replace(' ', '%20')
      Log("INFO: Quering WIKI with URL: %s" % wikiQueryUrl)
      requestHeaders = { 'User-Agent': USER_AGENT % AGENT_VERSION }

      res = XML.ElementFromURL(wikiQueryUrl, headers=requestHeaders, cacheTime=QUERY_CACHE_TIME)
      pathMatch = res.xpath('//api/query/searchinfo')
      if len(pathMatch) == 0:
        # TODO(zhenya): raise an error?
        Log('ERROR: searchinfo is not found in a WIKI response.')
      else:
        totalhits = pathMatch[0].get('totalhits')
        if int(totalhits) == 0:
          # TODO - implement case
          Log('INFO: No hits found! Getting a suggestion...')
        else:
          pageMatches = res.xpath('//api/query/search/p')

      # Grabbing the first N results (in case if there are any).
      counts = 0
      orderPenalty = 0
      for match in pageMatches:
        orderPenalty += 4  # Score is diminishes as we move down the list.
        score = 70 - orderPenalty
        pageTitle = safe_unicode(match.get('title'))
        pageId = None
        titleYear = None
        wikiPageUrl = WIKI_TITLEPAGE_URL % pageTitle.replace(' ', '%20')
        tmpResult = self.getAndParseItemsWikiPage(wikiPageUrl)
        if tmpResult is not None:
          if 'id' in tmpResult:
            pageId = tmpResult['id']
          if 'year' in tmpResult:
            titleYear = int(tmpResult['year'])
          if 'score' in tmpResult:
            score += int(tmpResult['score'] * 2.5)

        if self.isBlank(pageId):
          pageId = self.titleAndYearToId(pageTitle, yearFromFilename)
        if titleYear is None:
          # TODO(zhenya): maybe we shouldn't use the filename year?
          if not self.isBlank(yearFromFilename):
            titleYear = int(yearFromFilename)
        else:
          # If year matches the year from filename, increase confidence.
          if not self.isBlank(yearFromFilename):
            score += 5
        # Checking the title from filename with title in the match.
        score += self.compareTitles(titleFromFilename, pageTitle)
        results.Append(MetadataSearchResult(id = pageId,
                                            name = pageTitle,
                                            year = int(titleYear),
                                            lang = lang,
                                            score = score))
        counts += 1
        if counts == WIKI_RESULTS_NUMBER:
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
        MATCHER_IMDB_RATING = re.compile('class="rating-rating">(\d+\.\d+)<', re.M | re.S)
        match = MATCHER_IMDB_RATING.search(content)
        if match:
          imdbData['rating'] = match.groups(1)[0]
    except:
      Log('ERROR: getting IMDB data')
    return imdbData


def safe_unicode(s,encoding='utf-8'):
  if s is None:
    return None
  if isinstance(s, basestring):
    if isinstance(s, types.UnicodeType):
      return s
    else:
      return s.decode(encoding)
  else:
    return str(s).decode(encoding)
