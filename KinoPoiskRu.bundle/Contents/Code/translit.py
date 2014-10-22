# -*- coding: utf-8 -*-
# -*- test-case-name: pytils.test.test_translit -*-
# pytils - simple processing for russian strings
# Copyright (C) 2006-2007  Yury Yurevich
#
# http://www.pyobject.ru/projects/pytils/
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, version 2
# of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
"""
Simple transliteration
"""

#__id__ = __revision__ = "$Id: translit.py 102 2007-07-12 12:33:36Z the.pythy $"
#__url__ = "$URL: https://pythy.googlecode.com/svn/tags/pytils/0_2_2/pytils/translit.py $"

import re


TRANSTABLE = (
        (u"'", u"'"),
        (u'"', u'"'),
        (u"‘", u"'"),
        (u"’", u"'"),
        (u"«", u'"'),
        (u"»", u'"'),
        (u"–", u"-"),
        (u"…", u"..."),
        (u"№", u"#"),
        ## верхний регистр
        # трехбуквенные замены
        (u"Щ", u"Sch"),
        # при замене русский->английский будет первая замена,
        # т.е. Sch
        # а вот если английский->русский, то вариант SCH и Sch --
        # оба пройдут
        (u"Щ", u"SCH"),
        # двухбуквенные замены
        (u"Ё", u"Yo"),
        (u"Ё", u"YO"),
        (u"Ж", u"Zh"),
        (u"Ж", u"ZH"),
        (u"Ц", u"Ts"),
        (u"Ц", u"TS"),
        (u"Ч", u"Ch"),
        (u"Ч", u"CH"),
        (u"Ш", u"Sh"),
        (u"Ш", u"SH"),
        (u"Ы", u"Yi"),
        (u"Ы", u"YI"),
        (u"Ю", u"Yu"),
        (u"Ю", u"YU"),
        (u"Я", u"Ya"),
        (u"Я", u"YA"),
        (u"ИЙ", u"IY"),
        # однобуквенные замены
        (u"А", u"A"),
        (u"Б", u"B"),
        (u"В", u"V"),
        (u"Г", u"G"),
        (u"Д", u"D"),
        (u"Е", u"E"),
        (u"З", u"Z"),
        (u"И", u"I"),
        (u"Й", u"J"),
        (u"К", u"K"),
        (u"Л", u"L"),
        (u"М", u"M"),
        (u"Н", u"N"),
        (u"О", u"O"),
        (u"П", u"P"),
        (u"Р", u"R"),
        (u"С", u"S"),
        (u"Т", u"T"),
        (u"У", u"U"),
        (u"Ф", u"F"),
        (u"Х", u"H"),
        (u"Э", u"E"),
        (u"Ъ", u"`"),
        (u"Ы", u"Y"),
        (u"Ь", u"'"),
        ## нижний регистр
        # трехбуквенные замены
        (u"щ", u"sch"),
        # двухбуквенные замены
        (u"ё", u"yo"),
        (u"ж", u"zh"),
        (u"ц", u"ts"),
        (u"ч", u"ch"),
        (u"ш", u"sh"),
        (u"ы", u"yi"),
        (u"ю", u"yu"),
        (u"я", u"ya"),
        (u"ий", u"iy"),
        # однобуквенные замены
        (u"а", u"a"),
        (u"б", u"b"),
        (u"в", u"v"),
        (u"г", u"g"),
        (u"д", u"d"),
        (u"е", u"e"),
        (u"з", u"z"),
        (u"и", u"i"),
        (u"й", u"j"),
        (u"к", u"k"),
        (u"л", u"l"),
        (u"м", u"m"),
        (u"н", u"n"),
        (u"о", u"o"),
        (u"о", u"ô"),
        (u"п", u"p"),
        (u"р", u"r"),
        (u"с", u"s"),
        (u"т", u"t"),
        (u"у", u"u"),
        (u"ф", u"f"),
        (u"х", u"h"),
        (u"э", u"e"),
        (u"ъ", u"`"),
        (u"ь", u"'"),
        # для полноты английского алфавит (в slugify)
        # дополняем английскими буквами, которых
        # не в парах
        (u"c", u"c"),
        (u"q", u"q"),
        (u"y", u"y"),
        (u"x", u"x"),
        (u"w", u"w"),
        (u"1", u"1"),
        (u"2", u"2"),
        (u"3", u"3"),
        (u"4", u"4"),
        (u"5", u"5"),
        (u"6", u"6"),
        (u"7", u"7"),
        (u"8", u"8"),
        (u"9", u"9"),
        (u"0", u"0"),
        )  #: Translation table

RU_ALPHABET = [x[0] for x in TRANSTABLE] #: Russian alphabet that we can translate
EN_ALPHABET = [x[1] for x in TRANSTABLE] #: English alphabet that we can detransliterate
ALPHABET = RU_ALPHABET + EN_ALPHABET #: Alphabet that we can (de)transliterate


def translify(in_string):
    """
    Translify russian text

    @param in_string: input string
    @type in_string: C{unicode}

    @return: transliterated string
    @rtype: C{str}

    @raise TypeError: when in_string is not C{unicode}
    @raise ValueError: when string doesn't transliterate completely
    """
    if not isinstance(in_string, unicode):
      raise TypeError("Argument must be unicode, not %s" % type(in_string))

    translit = in_string
    for symb_in, symb_out in TRANSTABLE:
        translit = translit.replace(symb_in, symb_out)

    try:
        translit = str(translit)
    except UnicodeEncodeError:
        raise ValueError("Unicode string doesn't transliterate completely, " + \
                         "is it russian?")

    return translit


def detranslify(in_string):
    """
    Detranslify

    @param in_string: input string
    @type in_string: C{basestring}

    @return: detransliterated string
    @rtype: C{str}

    @raise TypeError: when in_string neither C{str}, no C{unicode}
    @raise ValueError: if in_string is C{str}, but it isn't ascii
    """
    if not isinstance(in_string, basestring):
        raise TypeError("Argument must be basestring, not %s" % type(in_string))

    # в unicode
    try:
        russian = unicode(in_string)
    except UnicodeDecodeError:
        raise ValueError("We expects when in_string is str type," + \
                         "it is an ascii, but now it isn't. Use unicode " + \
                         "in this case.")

    for symb_out, symb_in in TRANSTABLE:
        russian = russian.replace(symb_in, symb_out)

    return russian


def slugify(in_string):
    """
    Prepare string for slug (i.e. URL or file/dir name)

    @param in_string: input string
    @type in_string: C{basestring}

    @return: slug-string
    @rtype: C{str}

    @raise TypeError: when in_string isn't C{unicode} or C{str}
    @raise ValueError: if in_string is C{str}, but it isn't ascii
    """
    if not isinstance(in_string, basestring):
      raise TypeError("Argument must be basestring, not %s" % type(in_string))
    try:
        u_in_string = unicode(in_string).lower()
    except UnicodeDecodeError:
        raise ValueError("We expects when in_string is str type," + \
                         "it is an ascii, but now it isn't. Use unicode " + \
                         "in this case.")
    # convert & to "and"
    u_in_string = re.sub('\&amp\;|\&', ' and ', u_in_string)
    # replace spaces by hyphen
    u_in_string = re.sub('[-\s]+', '-', u_in_string)
    # remove symbols that not in alphabet
    u_in_string = u''.join([symb for symb in u_in_string if symb in ALPHABET])
    # translify it
    out_string = translify(u_in_string)
    # remove non-alpha
    return re.sub('[^\w\s-]', '', out_string).strip().lower()


def dirify(in_string):
    """
    Alias for L{slugify}
    """
    slugify(in_string)


def provide_unicode(stext, encoding, default=u"неизвестно"):
  """
  Provide Unicode from text

  @param stext: text
  @type stext: C{str}

  @param encoding: encoding if input text
  @type encoding: C{str}

  @return: C{unicode}
  """
  try:
    utext = str(stext).decode(encoding)
  except UnicodeDecodeError, err:
    utext = default % {'error': err, 'value': u""}
  return utext


def provide_str(utext, encoding, default="unknown"):
  """
  Provide text from Unicode

  @param utext: unicode text
  @type utext: C{unicode}

  @param encoding: encoding of output text
  @type encoding: C{str}

  @return: C{str}
  """
  try:
    stext = unicode(utext).encode(encoding)
  except UnicodeEncodeError, err:
    stext = default % {'error': err, 'value': ""}
  return stext
