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

import json

API_KEY = 'a3dc111e66105f6387e99393813ae4d5'
API_VERSION = '3'


class APIKeyError(Exception):
    pass


class Base():
    """ Base class for all api method objects.
  """
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json',
               'Connection': 'close'}

    def __init__(self, httpUtils, urls, basePath):
        self.httpUtils = httpUtils
        self.baseUri = 'https://api.themoviedb.org/{version}'.format(version=API_VERSION)
        self.basePath = basePath
        self.urls = urls

        self.id = None
        self.guest_session_id = None
        self.credit_id = None
        self.season_number = None
        self.series_id = None
        self.episode_number = None

    def getPath(self, key):
        return self.basePath + self.urls[key]

    def getIdPath(self, key):
        return self.getPath(key).format(id=self.id)

    def getGuestSessionIdPath(self, key):
        return self.getPath(key).format(
            guest_session_id=self.guest_session_id)

    def getCreditIdPath(self, key):
        return self.getPath(key).format(credit_id=self.credit_id)

    def getIdSeasonNumberPath(self, key):
        return self.getPath(key).format(id=self.id,
                                        season_number=self.season_number)

    def getSeriesIdSeasonNumberEpisodeNumberPath(self, key):
        return self.getPath(key).format(series_id=self.series_id,
                                        season_number=self.season_number,
                                        episode_number=self.episode_number)

    def getCompleteUrl(self, path):
        return '{base_uri}/{path}'.format(base_uri=self.baseUri, path=path)

    def getParams(self, params):
        if not API_KEY:
            raise APIKeyError

        api_dict = {'api_key': API_KEY}
        if params:
            params.update(api_dict)
        else:
            params = api_dict
        return params

    def request(self, method, path, params=None, payload=None):
        url = self.getCompleteUrl(path)
        params = self.getParams(params)

        return self.httpUtils.requestAndParseJsonApi(
            method, url, params=params,
            data=json.dumps(payload) if payload else payload,
            headers=self.headers)

    def GET(self, path, params=None):
        return self.request('GET', path, params=params)

    def POST(self, path, params=None, payload=None):
        return self.request('POST', path, params=params, payload=payload)

    def DELETE(self, path, params=None, payload=None):
        return self.request('DELETE', path, params=params, payload=payload)

    def getResultsFromResponse(self, response, key):
        if response and isinstance(response, dict) and key in response:
            return response[key]
        else:
            return []


class Search(object):
    """
  Search functionality

  See: https://docs.themoviedb.apiary.io/#search
  """
    URLS = {
        'movie': '/movie',
        'collection': '/collection',
        'tv': '/tv',
        'person': '/person',
        'list': '/list',
        'company': '/company',
        'keyword': '/keyword',
    }

    def __init__(self, httpUtils):
        self.base = Base(httpUtils, self.URLS, 'search')
        self.results = []

    def movie(self, **kwargs):
        """
    Search for movies by title.

    Args:
        query: CGI escpaed string.
        page: (optional) Minimum value of 1. Expected value is an integer.
        language: (optional) ISO 639-1 code.
        include_adult: (optional) Toggle the inclusion of adult titles.
                       Expected value is True or False.
        year: (optional) Filter the results release dates to matches that
              include this value.
        primary_release_year: (optional) Filter the results so that only
                              the primary release dates have this value.
        search_type: (optional) By default, the search type is 'phrase'.
                     This is almost guaranteed the option you will want.
                     It's a great all purpose search type and by far the
                     most tuned for every day querying. For those wanting
                     more of an "autocomplete" type search, set this
                     option to 'ngram'.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getPath('movie')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'results')
        return response

    def collection(self, **kwargs):
        """
    Search for collections by name.

    Args:
        query: CGI escpaed string.
        page: (optional) Minimum value of 1. Expected value is an integer.
        language: (optional) ISO 639-1 code.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getPath('collection')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def tv(self, **kwargs):
        """
    Search for TV shows by title.

    Args:
        query: CGI escaped string.
        page: (optional) Minimum value of 1. Expected value is an integer.
        language: (optional) ISO 639-1 code.
        first_air_date_year: (optional) Filter the results to only match
                             shows that have a air date with with value.
        search_type: (optional) By default, the search type is 'phrase'.
                     This is almost guaranteed the option you will want.
                     It's a great all purpose search type and by far the
                     most tuned for every day querying. For those wanting
                     more of an "autocomplete" type search, set this
                     option to 'ngram'.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getPath('tv')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def person(self, **kwargs):
        """
    Search for people by name.

    Args:
        query: CGI escpaed string.
        page: (optional) Minimum value of 1. Expected value is an integer.
        include_adult: (optional) Toggle the inclusion of adult titles.
                       Expected value is True or False.
        search_type: (optional) By default, the search type is 'phrase'.
                     This is almost guaranteed the option you will want.
                     It's a great all purpose search type and by far the
                     most tuned for every day querying. For those wanting
                     more of an "autocomplete" type search, set this
                     option to 'ngram'.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getPath('person')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def list(self, **kwargs):
        """
    Search for lists by name and description.

    Args:
        query: CGI escpaed string.
        page: (optional) Minimum value of 1. Expected value is an integer.
        include_adult: (optional) Toggle the inclusion of adult titles.
                       Expected value is True or False.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getPath('list')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def company(self, **kwargs):
        """
    Search for companies by name.

    Args:
        query: CGI escpaed string.
        page: (optional) Minimum value of 1. Expected value is an integer.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getPath('company')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def keyword(self, **kwargs):
        """
    Search for keywords by name.

    Args:
        query: CGI escpaed string.
        page: (optional) Minimum value of 1. Expected value is an integer.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getPath('keyword')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response


class Movies(object):
    """
  Movies functionality.

  See: https://docs.themoviedb.apiary.io/#movies
  """
    URLS = {
        'info': '/{id}',
        'alternative_titles': '/{id}/alternative_titles',
        'credits': '/{id}/credits',
        'images': '/{id}/images',
        'keywords': '/{id}/keywords',
        'releases': '/{id}/releases',
        'videos': '/{id}/videos',
        'translations': '/{id}/translations',
        'similar_movies': '/{id}/similar_movies',
        'reviews': '/{id}/reviews',
        'lists': '/{id}/lists',
        'changes': '/{id}/changes',
        'latest': '/latest',
        'upcoming': '/upcoming',
        'now_playing': '/now_playing',
        'popular': '/popular',
        'top_rated': '/top_rated',
        'account_states': '/{id}/account_states',
        'rating': '/{id}/rating',
    }

    def __init__(self, httpUtils, id=0):
        self.base = Base(httpUtils, self.URLS, 'movie')
        self.base.id = id
        self.results = []

    def info(self, **kwargs):
        """
    Get the basic movie information for a specific movie id.

    Args:
        language: (optional) ISO 639-1 code.
        append_to_response: (optional) Comma separated, any movie method.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('info')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def alternative_titles(self, **kwargs):
        """
    Get the alternative titles for a specific movie id.

    Args:
        country: (optional) ISO 3166-1 code.
        append_to_response: (optional) Comma separated, any movie method.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('alternative_titles')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def credits(self, **kwargs):
        """
    Get the cast and crew information for a specific movie id.

    Args:
        append_to_response: (optional) Comma separated, any movie method.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('credits')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def images(self, **kwargs):
        """
    Get the images (posters and backdrops) for a specific movie id.

    Args:
        language: (optional) ISO 639-1 code.
        append_to_response: (optional) Comma separated, any movie method.
        include_image_language: (optional) Comma separated, a valid
                                ISO 69-1.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('images')

        response = self.base.GET(path, kwargs)
        self.backdrops = self.base.getResultsFromResponse(response, 'backdrops')
        self.posters = self.base.getResultsFromResponse(response, 'posters')
        return response

    def keywords(self, **kwargs):
        """
    Get the plot keywords for a specific movie id.

    Args:
        append_to_response: (optional) Comma separated, any movie method.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('keywords')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def releases(self, **kwargs):
        """
    Get the release date and certification information by country for a
    specific movie id.

    Args:
        append_to_response: (optional) Comma separated, any movie method.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('releases')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def videos(self, **kwargs):
        """
    Get the videos (trailers, teasers, clips, etc...) for a
    specific movie id.

    Args:
        append_to_response: (optional) Comma separated, any movie method.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('videos')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def translations(self, **kwargs):
        """
    Get the translations for a specific movie id.

    Args:
        append_to_response: (optional) Comma separated, any movie method.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('translations')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def similar_movies(self, **kwargs):
        """
    Get the similar movies for a specific movie id.

    Args:
        page: (optional) Minimum value of 1.  Expected value is an integer.
        language: (optional) ISO 639-1 code.
        append_to_response: (optional) Comma separated, any movie method.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('similar_movies')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def reviews(self, **kwargs):
        """
    Get the reviews for a particular movie id.

    Args:
        page: (optional) Minimum value of 1.  Expected value is an integer.
        language: (optional) ISO 639-1 code.
        append_to_response: (optional) Comma separated, any movie method.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('reviews')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def lists(self, **kwargs):
        """
    Get the lists that the movie belongs to.

    Args:
        page: (optional) Minimum value of 1.  Expected value is an integer.
        language: (optional) ISO 639-1 code.
        append_to_response: (optional) Comma separated, any movie method.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('lists')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def changes(self, **kwargs):
        """
    Get the changes for a specific movie id.

    Changes are grouped by key, and ordered by date in descending order.
    By default, only the last 24 hours of changes are returned. The
    maximum number of days that can be returned in a single request is 14.
    The language is present on fields that are translatable.

    Args:
        start_date: (optional) Expected format is 'YYYY-MM-DD'.
        end_date: (optional) Expected format is 'YYYY-MM-DD'.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('changes')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def latest(self, **kwargs):
        """
    Get the latest movie id.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getPath('latest')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def upcoming(self, **kwargs):
        """
    Get the list of upcoming movies. This list refreshes every day.
    The maximum number of items this list will include is 100.

    Args:
        page: (optional) Minimum value of 1.  Expected value is an integer.
        language: (optional) ISO 639-1 code.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getPath('upcoming')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def now_playing(self, **kwargs):
        """
    Get the list of movies playing in theatres. This list refreshes
    every day. The maximum number of items this list will include is 100.

    Args:
        page: (optional) Minimum value of 1.  Expected value is an integer.
        language: (optional) ISO 639-1 code.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getPath('now_playing')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def popular(self, **kwargs):
        """
    Get the list of popular movies on The Movie Database. This list
    refreshes every day.

    Args:
        page: (optional) Minimum value of 1.  Expected value is an integer.
        language: (optional) ISO 639-1 code.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getPath('popular')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def top_rated(self, **kwargs):
        """
    Get the list of top rated movies. By default, this list will only
    include movies that have 10 or more votes. This list refreshes every
    day.

    Args:
        page: (optional) Minimum value of 1.  Expected value is an integer.
        language: (optional) ISO 639-1 code.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getPath('top_rated')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def account_states(self, **kwargs):
        """
    This method lets users get the status of whether or not the movie has
    been rated or added to their favourite or watch lists. A valid session
    id is required.

    Args:
        session_id: see Authentication.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('account_states')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def rating(self, **kwargs):
        """
    This method lets users rate a movie. A valid session id or guest
    session id is required.

    Args:
        session_id: see Authentication.
        guest_session_id: see Authentication.
        value: Rating value.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('rating')

        payload = {
            'value': kwargs.pop('value', None),
        }

        response = self.base.POST(path, kwargs, payload)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response


class Collections(object):
    """
  Collections functionality.

  See: https://docs.themoviedb.apiary.io/#collections
  """
    URLS = {
        'info': '/{id}',
        'images': '/{id}/images',
    }

    def __init__(self, httpUtils, id):
        self.base = Base(httpUtils, self.URLS, 'collection')
        self.base.id = id
        self.results = []

    def info(self, **kwargs):
        """
    Get the basic collection information for a specific collection id.
    You can get the ID needed for this method by making a /movie/{id}
    request and paying attention to the belongs_to_collection hash.

    Movie parts are not sorted in any particular order. If you would like
    to sort them yourself you can use the provided release_date.

    Args:
        language: (optional) ISO 639-1 code.
        append_to_response: (optional) Comma separated, any movie method.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('info')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def images(self, **kwargs):
        """
    Get all of the images for a particular collection by collection id.

    Args:
        language: (optional) ISO 639-1 code.
        append_to_response: (optional) Comma separated, any movie method.
        include_image_language: (optional) Comma separated, a valid
        ISO 69-1.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('info')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response


class Companies(object):
    """
  Companies functionality.

  See: https://docs.themoviedb.apiary.io/#companies
  """
    URLS = {
        'info': '/{id}',
        'movies': '/{id}/movies',
    }

    def __init__(self, httpUtils, id=0):
        self.base = Base(httpUtils, self.URLS, 'company')
        self.base.id = id
        self.results = []

    def info(self, **kwargs):
        """
    This method is used to retrieve all of the basic information about a
    company.

    Args:
        append_to_response: (optional) Comma separated, any movie method.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('info')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def movies(self, **kwargs):
        """
    Get the list of movies associated with a particular company.

    Args:
        page: (optional) Minimum value of 1.  Expected value is an integer.
        language: (optional) ISO 639-1 code.
        append_to_response: (optional) Comma separated, any movie method.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('movies')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response


class Keywords(object):
    """
  Keywords functionality.

  See: https://docs.themoviedb.apiary.io/#keywords
  """
    URLS = {
        'info': '/{id}',
        'movies': '/{id}/movies',
    }

    def __init__(self, httpUtils, id):
        self.base = Base(httpUtils, self.URLS, 'keyword')
        self.base.id = id
        self.results = []

    def info(self, **kwargs):
        """
    Get the basic information for a specific keyword id.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('info')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response

    def movies(self, **kwargs):
        """
    Get the list of movies for a particular keyword by id.

    Args:
        page: (optional) Minimum value of 1.  Expected value is an integer.
        language: (optional) ISO 639-1 code.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('movies')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response


class Reviews(object):
    """
  Reviews functionality.

  See: https://docs.themoviedb.apiary.io/#reviews
  """
    URLS = {
        'info': '/{id}',
    }

    def __init__(self, httpUtils, id):
        self.base = Base(httpUtils, self.URLS, 'review')
        self.base.id = id
        self.results = []

    def info(self, **kwargs):
        """
    Get the full details of a review by ID.

    Returns:
        A dict respresentation of the JSON returned from the API.
    """
        path = self.base.getIdPath('info')

        response = self.base.GET(path, kwargs)
        self.results = self.base.getResultsFromResponse(response, 'changeme')
        return response
