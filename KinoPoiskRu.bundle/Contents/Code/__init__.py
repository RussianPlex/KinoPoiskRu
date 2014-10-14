# -*- coding: utf-8 -*-

"""
Russian metadata plugin for Plex, which uses http://www.kinopoisk.ru/ to get the tag data.
Плагин для обновления информации о фильмах использующий КиноПоиск (http://www.kinopoisk.ru/).

@version @PLUGIN.REVISION@
@revision @REPOSITORY.REVISION@
@copyright (c) 2014 by Yevgeny Nyden
@license GPLv3, see LICENSE for more details
"""

import common, pageparser, tmdbapi, pluginsettings as S


LOGGER = Log
IS_DEBUG = 'True' == '@DEBUG.MAIN@'


# Plugin preferences.
# When changing default values here, also update the DefaultPrefs.json file.
PREFS = common.Preferences(
  ('kinopoiskru_pref_max_posters', S.KINOPOISK_PREF_DEFAULT_MAX_POSTERS),
  ('kinopoiskru_pref_max_art', S.KINOPOISK_PREF_DEFAULT_MAX_ART),
  ('kinopoiskru_pref_get_all_actors', S.KINOPOISK_PREF_DEFAULT_GET_ALL_ACTORS),
  (None, None),
  ('kinopoiskru_pref_imdb_rating', S.KINOPOISK_PREF_DEFAULT_IMDB_RATING),
  ('kinopoiskru_pref_kp_rating', S.KINOPOISK_PREF_DEFAULT_KP_RATING),
  ('kinopoiskru_pref_avoid_kp_images', S.KINOPOISK_PREF_DEFAULT_AVOID_KP_IMAGES))


def Start():
  LOGGER.Info('***** START ***** %s' % common.USER_AGENT)
  PREFS.readPluginPreferences()


def ValidatePrefs():
  LOGGER.Info('***** updating preferences...')
  PREFS.readPluginPreferences()


class KinoPoiskRuAgent(Agent.Movies):
  name = 'KinoPoiskRu'
  languages = [Locale.Language.Russian]
  primary_provider = True
  fallback_agent = False
  accepts_from = ['com.plexapp.agents.localmedia']
  contributes_to = None
  parser = pageparser.PageParser(
    LOGGER, common.HttpUtils(
      S.ENCODING_KINOPOISK_PAGE, pageparser.USER_AGENT, PREFS.cacheTime), IS_DEBUG)
  tmdbApi = tmdbapi.TmdbApi(
    LOGGER, common.HttpUtils(
      S.TMDB_PAGE_ENCODING, pageparser.USER_AGENT, PREFS.cacheTime), IS_DEBUG)


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
    LOGGER.Debug('SEARCH START <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
    mediaName = media.name
    mediaYear = media.year
    LOGGER.Debug('searching for name="%s", year="%s", guid="%s", hash="%s"...' %
        (str(mediaName), str(mediaYear), str(media.guid), str(media.hash)))

    # Look for matches on KinoPisk (result is returned as an array of tuples [kinoPoiskId, title, year, score]).
    titleResults = KinoPoiskRuAgent.parser.fetchAndParseSearchResults(mediaName, mediaYear)
    for titleResult in titleResults:
      results.Append(MetadataSearchResult(id=titleResult[0], name=titleResult[1], year=titleResult[2], lang=lang, score=titleResult[3]))

    # Sort results according to their score (Сортируем результаты).
    results.Sort('score', descending=True)
    LOGGER.Debug('SEARCH END <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


  ##############################################################################
  ############################# U P D A T E ####################################
  ##############################################################################
  def update(self, metadata, media, lang, force=False):
    """Updates the media title provided a KinoPoisk movie title id (metadata.guid).
       This method fetches an appropriate KinoPoisk page, parses it, and populates
       the passed media item record.
    """
    LOGGER.Debug('UPDATE START <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
    part = media.items[0].parts[0]
    filename = part.file.decode(common.ENCODING_PLEX)
    kinoPoiskId = metadata.id
    if kinoPoiskId:
      LOGGER.Debug('Updating with KinoPoisk id="%s", guid="%s", filename="%s"' %
                   (str(kinoPoiskId), metadata.guid, filename))
      self.updateMediaItem(metadata, kinoPoiskId, lang)
    else:
      LOGGER.Error('KinoPoisk movie title id is not specified!')

    LOGGER.Debug('UPDATE END <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


  def updateMediaItem(self, metadata, kinoPoiskId, lang):
    titlePage =  common.getElementFromHttpRequest(
      S.KINOPOISK_TITLE_PAGE_URL % kinoPoiskId, S.ENCODING_KINOPOISK_PAGE)
    if titlePage is not None:
      # Don't update if the title page was failed to load.
      LOGGER.Debug('SUCCESS: got a KinoPoisk page for movie title id: "%s"' % kinoPoiskId)
      try:
        self.parseInfoTableTagAndUpdateMetadata(titlePage, metadata)    # Title, original title, ratings, and more.

        # Search for a movie on TMDb to supplement our results with more data.
        # IMPORTANT, this must be done after parseInfoTableTagAndUpdateMetadata,
        # which populates the title and the year on the metadata object.
        tmdbId = self.searchForImdbTitleId(metadata.title, metadata.year)

        self.parseStudioPageData(metadata, kinoPoiskId)                 # Studio. Студия.
        self.parseCastPageData(titlePage, metadata, kinoPoiskId)        # Actors, etc. Актёры. др.
        self.updateImagesMetadata(metadata, kinoPoiskId, tmdbId, lang)   # Posters & Background art. Постеры.
      except:
        common.logException('failed to update metadata for id %s' % kinoPoiskId)

  def parseInfoTableTagAndUpdateMetadata(self, page, metadata):
    """ Parses the main info <table> tag, which we find by
        a css classname "info".
    """
    data = KinoPoiskRuAgent.parser.parseTitlePage(page)
    summaryPrefix = ''
    if 'title' in data:
      metadata.title = data['title']
    if 'originalTitle' in data:
      metadata.original_title = data['originalTitle']
    if 'rating' in data:
      metadata.rating = data['rating']
      if PREFS.additionalRating:
        summaryPrefix = 'КиноПоиск: ' + str(data['rating'])
        if 'ratingCount' in data:
          summaryPrefix = summaryPrefix + ' (' + str(data['ratingCount']) + ')'
        summaryPrefix = summaryPrefix + '. '
    if 'imdbRating' in data and PREFS.imdbRating:
      summaryPrefix = summaryPrefix + 'IMDb: ' + str(data['imdbRating'])
      if 'imdbRatingCount' in data:
        summaryPrefix = summaryPrefix + ' (' + str(data['imdbRatingCount']) + ')'
      summaryPrefix = summaryPrefix + '. '
    if summaryPrefix != '':
      summaryPrefix += '\n'
    if 'summary' in data:
      metadata.summary = summaryPrefix + data['summary']
    else:
      metadata.summary = summaryPrefix
    if 'year' in data:
      metadata.year = data['year']
    if 'countries' in data:
      for country in data['countries']:
        metadata.countries.add(country)
    if 'tagline' in data:
      metadata.tagline = data['tagline']
    if 'directors' in data:
      for director in data['directors']:
        metadata.directors.add(director)
    if 'writers' in data:
      for writer in data['writers']:
        metadata.writers.add(writer)
    if 'genres' in data:
      for genre in data['genres']:
        metadata.genres.add(genre)
    if 'contentRating' in data:
      metadata.content_rating = data['contentRating']
    elif 'contentRatingAlt' in data:
      metadata.content_rating = data['contentRatingAlt']
    if 'duration' in data:
      metadata.duration = data['duration']
    if 'originalDate' in data:
      metadata.originally_available_at = data['originalDate']

  def parseStudioPageData(self, metadata, kinoPoiskId):
    """ Parses the studio page.
    """
    data = KinoPoiskRuAgent.parser.fetchAndParseStudioPage(kinoPoiskId)
    studios = data['studios']
    try:
      if len(studios):
        # Only one studio is supported.
        metadata.studio = studios[0]
    except:
      pass

  def parseCastPageData(self, titlePage, metadata, kinoPoiskId):
    """ Parses people - mostly actors. Here (on this page)
        we have access to extensive information about all who participated in
        creating this movie.
    """
    data = KinoPoiskRuAgent.parser.fetchAndParseCastPage(kinoPoiskId, PREFS.getAllActors)
    actorRoles = data['actors']
    if len(actorRoles):
      for (actor, role) in actorRoles:
        self.addActorToMetadata(metadata, actor, role)
    else:
      # Parse main actors from the main title page.
      for mainActor in KinoPoiskRuAgent.parser.parseMainActorsFromLanding(titlePage):
        self.addActorToMetadata(metadata, mainActor, '')

  def updateImagesMetadata(self, metadata, kinoPoiskId, tmdbId, lang):
    """ Fetches and populates posters and background metadata.
    """
    # Fetching images from TMDb.
    tmdbResults = {'posters': [], 'backgrounds': []}
    if tmdbId is not None and \
        (PREFS.maxPosters > 0 or PREFS.maxArt > 0):
      tmdbResults = self.tmdbApi.loadImagesForTmdbId(tmdbId, 'ru')

    # Fetching posters from KinoPoisk.
    posterKeys = []
    if PREFS.maxPosters > 0:
      maxPosters = 1
      if not PREFS.avoidKinoPoiskImages:
        # >1 posters makes us parse the posters page, whereas =1 just grabs one (main) image.
        maxPosters = PREFS.maxPosters

      # Combine results and pick only max of them.
      posters = self.parser.fetchAndParsePostersData(kinoPoiskId, maxPosters, lang)
      posters = sorted(posters + tmdbResults['posters'],
        key=lambda t : t.score, reverse=True)
      if IS_DEBUG:
        LOGGER.Debug('  ----- Got total of %d posters:' % len(posters))
        for p in posters:
          LOGGER.Debug('  + score=%d, url="%s"' % (p.score, str(p.url)))
      posters = posters[0:PREFS.maxPosters]

      # Update the media's metadata.
      index = 0
      for poster in posters:
        try:
          metadata.posters[poster.url] = Proxy.Preview(HTTP.Request(poster.thumbUrl), sort_order = index)
          posterKeys.append(poster.url)
          index += 1
        except:
          pass
    metadata.posters.validate_keys(posterKeys)

    # Fetching background images from KinoPoisk.
    backgroundKeys = []
    if PREFS.maxArt > 0:
      if not PREFS.avoidKinoPoiskImages or len(tmdbResults['backgrounds']) == 0:
        backgrounds = self.parser.fetchAndParseStillsData(kinoPoiskId, PREFS.maxArt, lang)
      else:
        backgrounds = []
      backgrounds = sorted(backgrounds + tmdbResults['backgrounds'],
        key=lambda t : t.score, reverse=True)
      if IS_DEBUG:
        LOGGER.Debug('  ----- Got total of %d backgrounds:' % len(backgrounds))
        for b in backgrounds:
          LOGGER.Debug('  + score=%d, url="%s"' % (b.score, str(b.url)))
      backgrounds = backgrounds[0:PREFS.maxArt]

      index = 0
      for background in backgrounds:
        try:
          metadata.art[background.url] = \
              Proxy.Preview(HTTP.Request(background.thumbUrl), sort_order = index)
          backgroundKeys.append(background.url)
          index += 1
        except:
          pass
    metadata.art.validate_keys(backgroundKeys)

  def addActorToMetadata(self, metadata, actorName, roleName):
    """ Adds a new actor/role to a passed media metadata object.
    """
    try:
      role = metadata.roles.new()
      role.actor = actorName
      if roleName is not None and roleName != '':
        role.role = roleName
    except:
      pass

  def searchForImdbTitleId(self, mediaName, mediaYear):
    """
    """
    match = self.tmdbApi.searchForBestImdbTitle(mediaName, mediaYear, 'ru')
    if match is not None:
      if match['score'] >= S.TMDB_MATCH_MIN_SCORE:
        LOGGER.Debug('Found TMDb id "%s" match with score "%s".' %
                     (str(match['id']), str(match['score'])))
        return match['id']
      else:
        LOGGER.Debug('Skipping TMDb id "%s" match because of low score "%s".' %
                     (str(match['id']), str(match['score'])))
    else:
      LOGGER.Debug('No TMDb matches were found.')
    return None
