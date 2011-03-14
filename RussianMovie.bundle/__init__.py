import datetime, re, time, unicodedata, hashlib, urlparse, types

WIKI_QUERY_URL = 'http://ru.wikipedia.org/w/api.php?action=query&list=search&srprop=timestamp&format=xml&srsearch=%s'
WIKI_PAGE_URL = 'http://ru.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=timestamp|user|comment|content&format=xml&titles=%s'
USER_AGENT = 'Plex RussianMovie Agent (+http://www.plexapp.com/) v.%s'
AGENT_VERSION = '0.1'
QUERY_CACHE_TIME = 360
WIKI_RESULTS_NUMBER = 5

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
        found -30 is returned.
    """
    score = 0
    title = titleTo.lower()
    for word in titleFrom.lower().split():
      if title.find(word) >= 0:
        score += 2
    if score == 0:
      score = -30
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
    return matcher.sub(r'\1', wikiText)


  def getAndParseItemsWikiPage(self, pageTitle):
    """Given a page title, gets the corresponding WIKI page
       and parses its content.

       Returns a dictionary with the following keys:
       id, title, year, score, imdb_id, and summary.
       Score is value [0, 10] that indicates how good a
       match is.
    """

    Log('RUSSIANMOVIE.search: STEP 2 <<<<<<<<<<< START')

    contentDict = {}
    score = 0
    try:
      wikiPageUrl = WIKI_PAGE_URL % pageTitle.replace(' ', '%20')
      requestHeaders = { 'User-Agent': USER_AGENT % AGENT_VERSION }
      res = XML.ElementFromURL(wikiPageUrl, headers=requestHeaders, cacheTime=QUERY_CACHE_TIME)
      pathMatch = res.xpath('//api/query/pages/page')
      if len(pathMatch) == 0:
        Log('ERROR: unable to parse page "%s".' % pageTitle)
        return None

      missing = pathMatch[0].get('missing')
      if missing is not None:
        Log('ERROR: page "%s" does not seem to exist.' % pageTitle)
        return None

      contentDict['id'] = pathMatch[0].get('pageid')
      pathMatch = pathMatch[0].xpath('//revisions/rev')
      if len(pathMatch) == 0:
        Log('ERROR: page revision is not found in a WIKI response.')
        return None

      # This is the content of the entire page for our title.
      wikiText = safe_unicode(pathMatch[0].text)
      sanitizedText = self.sanitizeWikiText(wikiText)
#      print '======================================= sanitizedText: \n' + sanitizedText
#      print '=======================================\n'
      # Parsing the summary - something in between "== Сюжет =="
      # and the next section start ("\n\s*==\s").
      matcher = re.compile(u'==\s\u0421\u044E\u0436\u0435\u0442\s==\s*\n(.+?)\n\s*==\s', re.S | re.M)
      match = matcher.search(sanitizedText)
      if match:
        contentDict['summary'] = match.groups(1)[0]
        score += 1

      # Parsing the year - NNNN number after "| Год = "
      matcher = re.compile(u'^\s*\|\s+\u0413\u043E\u0434\s*=\s*(\d{4})\s*$', re.M)
      match = matcher.search(sanitizedText)
      if match:
        contentDict['year'] = match.groups(1)[0]
        score += 1

      # Checking the imdb id; if it's present we add confidence
      matcher = re.compile(u'^\s*\|\s+imdb_id\s*=\s*(\d+)\s*$', re.M)
      match = matcher.search(sanitizedText)
      if match:
        contentDict['imdb_id'] = match.groups(1)[0]
        score += 2

    except:
      Log('ERROR!!!!!!!!! ')

    Log('RUSSIANMOVIE.search: STEP 2 <<<<<<<<<<< FINISH')
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
      wikiQueryUrl = WIKI_QUERY_URL % titleFromFilename.replace(' ', '%20')
      Log("INFO: Quering WIKI with URL: %s" % wikiQueryUrl)
      requestHeaders = { 'User-Agent': USER_AGENT % AGENT_VERSION }

#      content = HTTP.Request(wikiQueryUrl, None, requestHeaders, 10).content.strip()
#      print 'Got content: ' + content
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
      scorePenalty = 0
      for match in pageMatches:
        scorePenalty += 4  # Score is diminishes as we move down the list.
        score = 70 - scorePenalty
        pageTitle = safe_unicode(match.get('title'))
        pageId = None
        titleYear = None
        tmpResult = self.getAndParseItemsWikiPage(pageTitle)
        if tmpResult is not None:
          if 'id' in tmpResult:
            pageId = tmpResult['id']
          if 'year' in tmpResult:
            titleYear = int(tmpResult['year'])
          if 'score' in tmpResult:
            score += (tmpResult['score'] * 2.5) 

        if self.isBlank(pageId):
          pageId = self.titleAndYearToId(pageTitle, yearFromFilename)
        if titleYear is None:
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


  ##############################################################################
  ############################# S E A R C H ####################################
  ##############################################################################
  def search(self, results, media, lang, manual=False):
    """Parses the filename and searches for matches on Russian wikipedia.

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
      Log('  ... result: id=%s, name=%s, year=%d, score=%d' % (result.id, result.name, result.year, result.score))

    #    results.Append(MetadataSearchResult(id = '121433201', name  = 'Uno uno uno', year = 2001, lang  = lang, score = 95))
#    results[0].score = 100
    # Duplicate matches are removed (by page ids).
    duplicateMatches = []
    resultMap = {}
    for result in results:
      if resultMap.has_key(result.id):
        duplicateMatches.append(result)
      else:
        resultMap[result.id] = True

    for dupe in duplicateMatches:
      results.Remove(dupe)

    Log('RUSSIANMOVIE.search: FINISH <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


  ##############################################################################
  ############################# U P D A T E ####################################
  ##############################################################################
  def update(self, metadata, media, lang):
    """Updates the media title provided a page id on Russian wikipedia.
    """
    Log('RUSSIANMOVIE.update: START <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')

#    tmpResult = self.getAndParseItemsWikiPage(pageTitle)
#    if tmpResult is None:

    part = media.items[0].parts[0]
    filename = part.file.decode('utf-8')
    print 'media filename: ' + filename

    for item in media.items:
      print '+++++++++++++++++ 10'
      for part in item.parts:
        if part.plexHash:
          print '+++++++++++++++++ plexHash: ' + part.plexHash
        if part.subtitles:
          for lang in part.subtitles.keys():
            print '+++++++++++++++++ subtitles lang: ' + lang
        if part.file:
          print '+++++++++++++++++ file: ' + part.file
                                                 


#?? why does it break???
#    if metadata.year is not None:
#      print 'metadata: year: ' + metadata.year
#    else:
#      print 'metadata: year: NONE'
#    if metadata.id is not None:
#      print 'metadata: id: ' + metadata.id
#    else:
#      print 'metadata: id: NONE'
#    if metadata.guid is not None:
#      print 'metadata: guid: ' + metadata.guid
#    else:
#      print 'metadata: guid: NONE'

    if metadata.guid is not None:
      print 'metadata.guid: ' + metadata.guid
    else:
      print 'metadata.guid: NONE'

    # Set the title. FIXME, this won't work after a queued restart.
    # Only do this once, otherwise we'll pull new names that get edited 
    # out of the database.
    #
    if media and metadata.title is None:
      metadata.title = media.title

    print 'metadata.title: ' + metadata.title
    try:
      print 'metadata.year: ' + str(metadata.year)
    except:
      print 'metadata.year - unable to print'
    try:
      print 'media.year: ' + str(media.year)
    except:
      print 'media.year - unable to print'

    # Hit our repository.
#    guid = re.findall('tt([0-9]+)', metadata.guid)[0]
#    url = '%s/%s/%s/%s.xml' % (FREEBASE_URL, FREEBASE_BASE, guid[-2:], guid)

    try:
#      movie = XML.ElementFromURL(url, cacheTime=3600)

      metadata.duration = 2 * 60 * 1000

      # Runtime.
#      if int(movie.get('runtime')) > 0:
#        metadata.duration = int(movie.get('runtime')) * 60 * 1000

    # Get the filename and the mod time.
#    filename = media.items[0].parts[0].file.decode('utf-8')
#    mod_time = os.path.getmtime(filename)

#    date = datetime.date.fromtimestamp(mod_time)

    # Fill in the little we can get from a file.
#    metadata.title = media.title
#    metadata.year = date.year
#    metadata.originally_available_at = Datetime.ParseDate(str(date)).date()

#    metadata.title = '2 new title for my movie'
#    metadata.year = 1802
#    metadata.summary = '2 Summary of this movie is simple - it\'s a piece of crap!'
#    metadata.genres.clear()
#    metadata.genres.add('Drama')
#    metadata.genres.add('Family')
#    metadata.directors.add('Mama')
#    metadata.directors.add('Mia')
#    metadata.writers.add('Tio')
#    metadata.writers.add('Cupriano')
#    metadata.tagline = 'tag line........'
#    metadata.content_rating = '2'
#    metadata.trivia = 'triviaaaaaaaaaaaaaaa'
#    metadata.quotes = 'quotesssssssssssss'

#    metadata.ratingKey = '5'
#    Log('aaaaaaaaaaaaaaaaaaa')
#    LogChildren(metadata)
#    metadata.originally_available_at = Datetime.ParseDate('2008-03-11').date()
#    metadata.countries.add('Russia')
#    metadata.roles = {}
#    metadata.studio = ''
#    metadata.posters = {}
#    metadata.arf


      # Genres.
      metadata.genres.clear()
      metadata.genres.add('Drama')
      metadata.genres.add('Action')

      # Directors.
      metadata.directors.clear()
      metadata.directors.add('Mr X')

      # Writers.
      metadata.writers.clear()

      # Actors.
      metadata.roles.clear()

      # Studio
      metadata.studio = 'Nyden Studio'
        
      # Tagline.
      metadata.tagline = 'Here comes my line....'
        
      # Content rating.
#      metadata.content_rating = movie.get('content_rating')

    except:
      print "Error obtaining Plex movie data for " + str(guid)

    Log('RUSSIANMOVIE.update: FINISH <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


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
