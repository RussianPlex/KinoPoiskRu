# -*- coding: utf-8 -*-
#
# Log (similar to the one in Plex Extension Framework) to use in unit tests.
#
# Copyright (C) 2013  Zhenya Nyden
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
#


TEST_RUNNER_VERBOSITY = 2

logLevel = 0


class TestLogger():

  def __init__(self, level):
    """ Supported levels:
          0 -> None;
          1 -> Critical (including Exception);
          2 -> Error;
          3 -> Warning;
          4 -> Info;
          5 -> Debug.
    """
    self.level = level

# TODO(zhenya): print varargs as well.

  def Debug(self, fmt, *args, **kwargs):
    if self.level > 4:
      print 'DEBUG: ' + fmt

  def Info(self, fmt, *args, **kwargs):
    if self.level > 3:
      print 'INFO: ' + fmt

  def Warn(self, fmt, *args, **kwargs):
    if self.level > 2:
      print 'WARN: ' + fmt

  def Error(self, fmt, *args, **kwargs):
    if self.level > 1:
      print 'ERROR: ' + fmt

  def Critical(self, fmt, *args, **kwargs):
    if self.level > 0:
      print 'CRITICAL: ' + fmt

  def Exception(self, fmt, *args, **kwargs):
    if self.level > 0:
      print 'EXCEPTION: ' + fmt


