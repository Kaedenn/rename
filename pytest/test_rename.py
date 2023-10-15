#!/usr/bin/env python3

"""
Test suite for the rename.py script itself
"""

import os
import hashlib
import logging
import pytest
import subprocess
from subprocess import Popen, PIPE
import sys

import rename
BIN_PATH = rename.__file__

def hash_of(path):
  "Get the first eight characters of the path's SHA256 hash"
  return hashlib.sha256(open(path, "rb").read()).hexdigest()[:8]

def invoke(file, *args):
  "Run rename.py with the given arguments"
  argv = [BIN_PATH, file]
  argv.extend(args)
  proc = Popen(argv, stdout=PIPE, stderr=PIPE)
  out, err = proc.communicate()
  return proc.returncode, out.decode(), err.decode()

def do_test_rename(path_in, expected_name, *args, fails=False, logger=None):
  "Assert that renaming the given path produces the desired results"
  stat_in = os.stat(path_in)
  size_in = stat_in.st_size
  hash_in = hash_of(path_in)
  returncode, out, err = invoke(path_in, *args)
  if logger is not None:
    for line in err.splitlines():
      logger.info(line)
  path_out = None
  if fails:
    assert returncode != 0
    assert os.path.exists(path_in)
    if expected_name:
      path_out = os.path.join(os.path.dirname(path_in), expected_name)
      assert path_in == path_out or not os.path.exists(path_out)
  else:
    assert expected_name, "expected_name is required with non-fail tests"
    path_out = os.path.join(os.path.dirname(path_in), expected_name)
    assert returncode == 0
    assert path_in == path_out or not os.path.exists(path_in)
    assert os.path.exists(path_out)
    assert os.path.basename(path_out) == expected_name
    assert os.stat(path_out).st_size == size_in
    assert hash_of(path_out) == hash_in
  return path_out, out, err

def test_rename_empty(temp_files, loggable):
  "Assert that rename.py empty.txt gives the desired result"
  from_path = temp_files["empty.txt"]
  empty_hash = hash_of(from_path)
  do_test = lambda *args, **kwargs: do_test_rename(*args, **kwargs, logger=loggable)
  final_path, out, err = do_test(from_path, empty_hash + ".txt")
  final_path, out, err = do_test(final_path, "empty.txt", "-f", "empty.txt")

def test_rename_simple(temp_files, loggable):
  from_path = temp_files["small.txt"]
  do_test = lambda *args, **kwargs: do_test_rename(*args, **kwargs, logger=loggable)
  final_path, out, err = do_test(from_path, "small.gz", "-f", "%B%.gz")
  final_path, out, err = do_test(final_path, "small.txt", "-f", "%B%.txt")
  final_path, out, err = do_test(final_path, "small.html", "-e", "txt=html")
  final_path, out, err = do_test(final_path, "SMALL.html", "-U")
  final_path, out, err = do_test(final_path, "small.txt", "-L", "-e", "html=txt")
  assert final_path == from_path
  assert os.path.exists(from_path)

  from_path = temp_files["with space.txt"]
  do_test(from_path, None, "-f", "small.txt", fails=True)

# TODO: test -n,--dry
# TODO: test formatstring parse errors
# TODO: test --regex patterns
# TODO: test more elaborate --format patterns with %T, %L, %U, etc

# vim: set ts=2 sts=2 sw=2:

