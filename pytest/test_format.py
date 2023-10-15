#!/usr/bin/env python3

"""
Test suite for the printf-like formatting support
"""

import datetime
import hashlib
import os
import pytest
import shutil
import sys

import formatstring

fopath = formatstring.format_path
fobase = lambda fpath, fstr: os.path.basename(fopath(fpath, fstr))

def test_format_simple():
  "Test simple uses of %, B, and E"
  assert fopath("foo", "%%") == "%"
  assert fopath("foo", "bar") == "bar"
  assert fopath("foo", "%.") == os.extsep
  assert fopath("foo/bar.gz", "%B.%E") == "foo/bar.gz"
  assert fopath("foo/bar.tar", "%B.%E.gz") == "foo/bar.tar.gz"
  assert fopath("foo/bar.gz", "%B.tar.gz") == "foo/bar.tar.gz"

def test_format_tokens():
  "Test simple uses of B, E, T, and U"
  name = "foo-bar-baz.gz"
  assert fopath(name, "%B") == "foo-bar-baz"
  assert fopath(name, "%E") == "gz"
  assert fopath(name, "%(-=1)T") == "foo"
  assert fopath(name, "%(-=2)T") == "bar"
  assert fopath(name, "%(-=3)T") == "baz"
  assert fopath(name, "%(-=1)T.%E") == "foo.gz"
  assert fopath(name, "%(-=2)T.%E") == "bar.gz"
  assert fopath(name, "%(-=3)T.%E") == "baz.gz"
  assert fopath(name, "%(-=2)U.%E") == "BAR.gz"

  assert fopath("foo-bar.txt", "%(-=1)U_%(-=2)U.TXT") == "FOO_BAR.TXT"
  assert fopath("FOO_BAR.TXT", "%(_=1)L-%(_=2)L.txt") == "foo-bar.txt"
  assert fopath("foobar.txt", "%(,)C%.%E") == "foobar.txt"
  assert fopath("foobar.txt", "%(1,)C%.%E") == "oobar.txt"
  assert fopath("foobar.txt", "%(,-1)C%.%E") == "fooba.txt"
  assert fopath("foobar.txt", "%(1,2)C%.%E") == "o.txt"

def test_format_paths():
  "Ensure format_path does not alter the dirname component"

def test_format_file(temp_files):
  assert "empty.txt" in temp_files
  assert "small.txt" in temp_files
  for name, file_path in temp_files.items():
    filestat = os.stat(file_path)
    assert fobase(file_path, "%S") == str(filestat.st_size)
    mtime = datetime.datetime.fromtimestamp(filestat.st_mtime)
    assert fobase(file_path, "%(%Y%m%d)M") == mtime.strftime("%Y%m%d")
    fhash = hashlib.sha256(open(file_path, "rb").read()).hexdigest()
    assert fobase(file_path, "%H") == fhash[:8]

  file_name = "one-two-three.txt"
  assert file_name in temp_files
  file_path = temp_files[file_name]
  fsize = os.stat(file_path).st_size
  assert fobase(file_path, "%(-=2)T-%S.%E") == f"two-{fsize}.txt"

# vim: set ts=2 sts=2 sw=2:

