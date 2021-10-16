# -*- coding: utf-8 -*-

"""
Code to access the official TMDB json api.
A good deal of this code was copied from the tmdbsimple project
(https://github.com/celiao/tmdbsimple). It was originally implemented
by Celia Oakley and licenced with GPLv3.

@version @PLUGIN.REVISION@
@revision @REPOSITORY.REVISION@
@copyright (c) 2014 by Yevgeny Nyden
@license GPLv3, see LICENSE.MD for more details
"""

import re, common, pluginsettings as S

from tmdbclient import Search, Movies

MATCHER_RELEASED = re.compile(r'(\d\d\d\d)-\d\d-\d\d', re.UNICODE)


class TmdbApi:
    def __init__(self, logger, httpUtils, isDebug=False):
        self.log = logger
        self.isDebug = isDebug
        self.httpUtils = httpUtils

    def searchForImdbTitles(self, mediaName, mediaYear, lang='ru', searchByTitleOnly=False):
        """ Given media name and media year looks for media title matches on TMDb.
        @param mediaName: CGI escaped media name string.
        @param mediaYear: (optional) Filter the results release dates to matches that
                   include this value.
        @param lang: (optional) ISO 639-1 code.
    """
        yearSearch = ''
        if not searchByTitleOnly:
            yearSearch = mediaYear
        mediaName = mediaName.lower()
        search = Search(self.httpUtils)
        response = search.movie(
            query=mediaName.encode(S.TMDB_PAGE_ENCODING),
            year=yearSearch,
            language=lang
        )
        results = []
        if response is None:
            self.log.Warn('nothing was found on tmdb for media name "%s"' % mediaName)
        else:
            itemIndex = 0
            for s in search.results:
                try:
                    tmdbId = str(s['id'])
                    title = s['title']
                    altTitle = s['original_title']
                    year = common.getReOptionalGroup(MATCHER_RELEASED, s['release_date'], 0)
                    score = common.scoreMediaTitleMatch(mediaName, mediaYear, title, altTitle, year, itemIndex)
                    results.append({'id': tmdbId, 'title': title, 'year': year, 'score': score})
                    itemIndex = itemIndex + 1
                except:
                    self.log.Warn('failed to parse movie element')

        orderedResults = sorted(results, key=lambda item: item['score'], reverse=True)
        if self.isDebug:
            self.log.Debug('Search produced %d results:' % len(orderedResults))
            index = -1
            for result in orderedResults:
                index = index + 1
                self.log.Debug(' ... %d: id="%s", title="%s", year="%s", score="%d".' %
                               (index, result['id'], result['title'], str(result['year']), result['score']))
        return orderedResults

    def searchForBestImdbTitle(self, mediaName, mediaYear, lang):
        """ Given media name and media year returns the best possible match from TMDb.
        @param mediaName: CGI escaped media name string.
        @param mediaYear: (optional) Filter the results release dates to matches that
                   include this value.
        @param lang: (optional) ISO 639-1 code.
        @return The best title found or None.
    """
        matches = self.searchForImdbTitles(mediaName, mediaYear, lang)
        if len(matches) == 0 and mediaYear:
            # Repeat a search w/o the year - helps when wrong year was specified.
            matches = self.searchForImdbTitles(mediaName, mediaYear, lang, True)
        if len(matches) > 0:
            return matches[0]
        else:
            return None

    def loadImagesForTmdbId(self, tmdbId, lang):
        """ Returns image results as a dict:
         results['posters']
         results[.backgrounds']
    """
        movies = Movies(self.httpUtils, tmdbId)
        languages = 'null,' + lang
        if lang != 'en':
            languages = languages + ',en'
        response = movies.images(
            include_image_language=languages
        )

        results = {}
        if response is None:
            self.log.Warn('no images were found for tmdb id "%s"' % str(tmdbId))
        else:
            # Parse posters records.
            itemIndex = 0
            posters = []
            for posterJson in movies.posters:
                poster = self.parseAndScoreImageData(posterJson, itemIndex, True, lang)
                if poster is not None:
                    posters.append(poster)
                    itemIndex = itemIndex + 1
            results['posters'] = sorted(posters, key=lambda t: t.score, reverse=True)

            # Parse funart (backgrounds) records.
            itemIndex = 0
            backgrounds = []
            for backgroundJson in movies.backdrops:
                background = self.parseAndScoreImageData(backgroundJson, itemIndex, False, lang)
                if background is not None:
                    backgrounds.append(background)
                    itemIndex = itemIndex + 1
            results['backgrounds'] = sorted(backgrounds, key=lambda t: t.score, reverse=True)

        return results

    def parseAndScoreImageData(self, imageJson, itemIndex, isPortrait, preferredLang):
        try:
            url = S.TMDB_IMAGE_ORIGINAL_BASE_URL + imageJson['file_path']
            thumbUrl = S.TMDB_IMAGE_THUMB_BASE_URL + imageJson['file_path']
            lang = imageJson['iso_639_1']
            imageData = common.Thumbnail(
                thumbUrl, url, imageJson['width'], imageJson['height'], itemIndex, 0, lang)
            common.scoreThumbnailResult(imageData, isPortrait, preferredLang)
            return imageData
        except:
            self.log.Warn('failed to parse image data')
            return None
