# -*- coding: utf-8 -*-
#
# Main test suite for the KinoPoiskRu Plex metadata plugin.
#
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
#

import unittest, sys
import testlog, testutil as U, titlepage_test, studiopage_test, \
  pageparser_test, peoplepage_test, imagepages_test, misc_test


if __name__ == '__main__':
  # When changing this code, pls make sure to adjust __main__ method
  # in individual test files accordingly (in case we'd want to run them separately).
  (options, args) = U.parseTestOptions()
  testlog.logLevel = options.logLevel
  runner = unittest.TextTestRunner(verbosity=testlog.TEST_RUNNER_VERBOSITY)

  result = runner.run(titlepage_test.suite(options.excludeRemote))
  exitCode = U.getExitCode(result)

  result = runner.run(studiopage_test.suite(options.excludeRemote))
  exitCode |= U.getExitCode(result)

  result = runner.run(pageparser_test.suite(options.excludeRemote))
  exitCode |= U.getExitCode(result)

  result = runner.run(peoplepage_test.suite(options.excludeRemote))
  exitCode |= U.getExitCode(result)

  result = runner.run(imagepages_test.suite(options.excludeRemote))
  exitCode |= U.getExitCode(result)

  result = runner.run(misc_test.suite(options.excludeRemote))
  exitCode |= U.getExitCode(result)

  sys.exit(exitCode)
