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
# @author zhenya (Yevgeny Nyden)
# @version @PLUGIN.REVISION@
# @revision @REPOSITORY.REVISION@

import re, urllib
import common, tmdb, pageparser, pluginsettings as S


LOGGER = Log
IS_DEBUG = True # TODO - DON'T FORGET TO SET IT TO FALSE FOR A DISTRO.

# Plugin preferences.
# When changing default values here, also update the DefaultPrefs.json file.
PREFS = common.Preferences(
  ('kinopoisk_pref_max_posters', S.KINOPOISK_PREF_DEFAULT_MAX_POSTERS),
  ('kinopoisk_pref_max_art', S.KINOPOISK_PREF_DEFAULT_MAX_ART),
  ('kinopoisk_pref_get_all_actors', S.KINOPOISK_PREF_DEFAULT_GET_ALL_ACTORS),
  ('kinopoisk_pref_imdb_support', S.KINOPOISK_PREF_DEFAULT_IMDB_SUPPORT),
  (None, None),
  ('kinopoisk_pref_imdb_rating', S.KINOPOISK_PREF_DEFAULT_IMDB_RATING),
  ('kinopoisk_pref_kp_rating', S.KINOPOISK_PREF_DEFAULT_KP_RATING))


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
    # Получаем страницу поиска
    LOGGER.Debug('quering kinopoisk...')

    encodedName = urllib.quote(mediaName.encode(S.ENCODING_KINOPOISK_PAGE))
    LOGGER.Debug('Loading page "%s"' % encodedName)
    page = common.getElementFromHttpRequest(S.KINOPOISK_SEARCH % encodedName, S.ENCODING_KINOPOISK_PAGE)

    if page is None:
      LOGGER.Warn('nothing was found on kinopoisk for media name "%s"' % mediaName)
    else:
      # Если страница получена, берем с нее перечень всех названий фильмов.
      LOGGER.Debug('got a kinopoisk page to parse...')
      divInfoElems = page.xpath('//self::div[@class="info"]/p[@class="name"]/a[contains(@href,"/level/1/film/")]/..')
      itemIndex = 0
      altTitle = None
      if len(divInfoElems):
        LOGGER.Debug('found %d results' % len(divInfoElems))
        for divInfoElem in divInfoElems:
          try:
            anchorFilmElem = divInfoElem.xpath('./a[contains(@href,"/level/1/film/")]/attribute::href')
            if len(anchorFilmElem):
              # Parse kinopoisk movie title id, title and year.
              match = re.search('\/film\/(.+?)\/', anchorFilmElem[0])
              if match is None:
                LOGGER.Error('unable to parse movie title id')
              else:
                kinoPoiskId = match.groups(1)[0]
                title = common.getXpathRequiredText(divInfoElem, './/a[contains(@href,"/level/1/film/")]/text()')
                year = common.getXpathOptionalText(divInfoElem, './/span[@class="year"]/text()')
                # Try to parse the alternative (original) title. Ignore failures.
                # This is a <span> below the title <a> tag.
                try:
                  altTitle = common.getXpathOptionalText(divInfoElem, '../span[1]/text()')
                  if altTitle is not None:
                    altTitle = altTitle.split(',')[0].strip()
                except:
                  pass
                score = common.scoreMediaTitleMatch(mediaName, mediaYear, title, altTitle, year, itemIndex)
                results.Append(MetadataSearchResult(id=kinoPoiskId, name=title, year=year, lang=lang, score=score))
            else:
              LOGGER.Warn('unable to find film anchor elements for title "%s"' % mediaName)
          except:
            common.logException('failed to parse div.info container')
          itemIndex += 1
      else:
        LOGGER.Warn('nothing was found on kinopoisk for media name "%s"' % mediaName)
        # TODO(zhenya): investigate if we need this clause at all (haven't seen this happening).
        # Если не нашли там текст названия, значит сайт сразу дал нам страницу с фильмом (хочется верить =)
        try:
          title = page.xpath('//h1[@class="moviename-big"]/text()')[0].strip()
          kinoPoiskId = re.search('\/film\/(.+?)\/', page.xpath('.//link[contains(@href, "/film/")]/attribute::href')[0]).groups(0)[0]
          year = page.xpath('//a[contains(@href,"year")]/text()')[0].strip()
          score = common.scoreMediaTitleMatch(mediaName, mediaYear, title, altTitle, year, itemIndex)
          results.Append(MetadataSearchResult(id=kinoPoiskId, name=title, year=year, lang=lang, score=score))
        except:
          common.logException('failed to parse a KinoPoisk page')

    # Sort results according to their score (Сортируем результаты).
    results.Sort('score', descending=True)
    if IS_DEBUG:
      common.printSearchResults(results)
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
    LOGGER.Debug('filename="%s", guid="%s"' % (filename, metadata.guid))

    matcher = re.compile(r'//(\d+)\?')
    match = matcher.search(metadata.guid)
    if match is None:
      LOGGER.Error('KinoPoisk movie title id is not specified!')
      raise Exception('ERROR: KinoPoisk movie title id is required!')
    else:
      kinoPoiskId = match.groups(1)[0]
    LOGGER.Debug('parsed KinoPoisk movie title id: "%s"' % kinoPoiskId)

    self.parser = pageparser.PageParser(
      LOGGER, common.HttpUtils(S.ENCODING_KINOPOISK_PAGE, pageparser.USER_AGENT), IS_DEBUG)
    self.updateMediaItem(metadata, kinoPoiskId)

    if PREFS.imdbSupport:
      imdbId = tmdb.findBestTitleMatch(metadata.title, metadata.year, lang)
      if imdbId is not None:
        metadata.id = imdbId
    LOGGER.Debug('UPDATE END <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


  def updateMediaItem(self, metadata, kinoPoiskId):
    titlePage =  common.getElementFromHttpRequest(S.KINOPOISK_TITLE_PAGE_URL % kinoPoiskId, S.ENCODING_KINOPOISK_PAGE)
    if titlePage is not None:
      # Don't update if the title page was failed to load.
      LOGGER.Debug('SUCCESS: got a KinoPoisk page for movie title id: "%s"' % kinoPoiskId)
      try:
        self.resetMediaMetadata(metadata)
        self.parseInfoTableTagAndUpdateMetadata(titlePage, metadata)    # Title, original title, ratings, and more.
        self.parseStudioPageData(metadata, kinoPoiskId)                 # Studio. Студия.
        self.parseCastPageData(titlePage, metadata, kinoPoiskId)        # Actors, etc. Актёры. др.
        self.parsePostersPageData(metadata, kinoPoiskId)                # Posters. Постеры.
        self.parseStillsPageData(metadata, kinoPoiskId)                 # Background art. Stills.
      except:
        common.logException('failed to update metadata for id %s' % kinoPoiskId)

  def parseInfoTableTagAndUpdateMetadata(self, page, metadata):
    """ Parses the main info <table> tag, which we find by
        a css classname "info".
    """
    data = self.parser.parseTitlePage(page)
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
    data = self.parser.fetchAndParseStudioPage(kinoPoiskId)
    studios = data['studios']
    if len(studios):
      # Only one studio is supported.
      metadata.studio = studios[0]

  def parseCastPageData(self, titlePage, metadata, kinoPoiskId):
    """ Parses people - mostly actors. Here (on this page)
        we have access to extensive information about all who participated in
        creating this movie.
    """
    data = self.parser.fetchAndParseCastPage(kinoPoiskId, PREFS.getAllActors)
    actorRoles = data['actors']
    if len(actorRoles):
      for (actor, role) in actorRoles:
        self.addActorToMetadata(metadata, actor, role)
    else:
      # Parse main actors from the main title page.
      for mainActor in self.parser.parseMainActorsFromLanding(titlePage):
        self.addActorToMetadata(metadata, mainActor, '')

  def parsePostersPageData(self, metadata, kinoPoiskId):
    """ Fetches and populates posters metadata.
    """
    if PREFS.maxPosters == 0:
      metadata.posters.validate_keys([])
      return

    data = self.parser.fetchAndParsePostersData(kinoPoiskId, PREFS.maxPosters)
    posters = data['posters']
    if posters is not None and len(posters) > 0:
      # Now, walk over the top N (<max) results and update metadata.
      index = 0
      validNames = list()
      for poster in posters:
        try:
          metadata.posters[poster.url] = Proxy.Preview(HTTP.Request(poster.thumbUrl), sort_order = index)
          validNames.append(poster.url)
          index += 1
        except:
          pass
      metadata.posters.validate_keys(validNames)

  def parseStillsPageData(self, metadata, kinoPoiskId):
    """ Fetches and populates background art metadata.
        Получение адресов задников.
    """
    if PREFS.maxArt == 0:
      metadata.art.validate_keys([])
      return

    data = self.parser.fetchAndParseStillsData(kinoPoiskId, PREFS.maxArt)
    stills = data['stills']
    if stills is not None and len(stills) > 0:
      # Now, walk over the top N (<max) results and update metadata.
      index = 0
      validNames = list()
      for still in stills:
        try:
          metadata.art[still.url] = Proxy.Preview(HTTP.Request(still.thumbUrl), sort_order = index)
          validNames.append(still.url)
          index += 1
        except:
          pass
      metadata.art.validate_keys(validNames)

  def addActorToMetadata(self, metadata, actorName, roleName):
    """ Adds a new actor/role to a passed media metadata object.
    """
    role = metadata.roles.new()
    role.actor = actorName
    if roleName is not None and roleName != '':
      role.role = roleName

  def resetMediaMetadata(self, metadata):
    """ Resets all relevant fields on a passed media metadata object.
    """
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
