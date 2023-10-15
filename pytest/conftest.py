#!/usr/bin/env python3

"""
Top-level configuration for the rename.py test suite
"""

import pytest
import logging
import os
import shutil
import sys

# To allow tests to import the modules being tested
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

def pytest_addoption(parser):
  parser.addoption("-L", "--test-log-level", action="store",
      choices=("NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
      default="NOTSET",
      help="configure the test-specific logger's level")

def pytest_configure(config):
  pass

def _create_file(directory, name, size):
  "Create a single file inside the given directory"
  with open(os.path.join(directory, name), "wt") as fobj:
    fobj.write("1" * size)

def _create_file_entry(directory, name, size):
  "Build a file entry for the temp_files fixture"
  _create_file(directory, name, size)
  return os.path.join(directory, name)

@pytest.fixture(scope="function", autouse=True)
def loggable(pytestconfig, caplog):
  "Give a convenient logger instance"
  # Get the log level via --test-log-level
  log_level_name = pytestconfig.getoption("--test-log-level")
  log_level = getattr(logging, log_level_name, logging.NOTSET)
  if not isinstance(log_level, int):
    log_level = logging.NOTSET
  # If that failed, use the log_cli_level
  if not log_level or log_level == logging.NOTSET:
    logging_plugin = pytestconfig.pluginmanager.get_plugin("logging-plugin")
    log_level = logging_plugin.log_cli_level
  # If that failed or isn't set, use INFO
  if not log_level or log_level == logging.NOTSET:
    log_level = logging.INFO

  with caplog.at_level(log_level, logger="test"):
    yield logging.getLogger("test")

@pytest.fixture(scope="function")
def temp_files(pytestconfig, tmp_path_factory, loggable):
  "Create a few temporary files"
  temp_path = tmp_path_factory.mktemp("test-assets")
  temp_files = (
    ("empty.txt", 0),
    ("small.txt", 32),
    ("one-two-three.txt", 128),
    ("with space.txt", 32)
  )
  data = {}
  for file_name, file_size in temp_files:
    data[file_name] = _create_file_entry(temp_path, file_name, file_size)
  yield data

# vim: set ts=2 sts=2 sw=2:

