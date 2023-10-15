#!/usr/bin/env python3

"""
Implement printf-style formatting for the file rename program
"""

import datetime
import functools
import hashlib
import logging
import os

from typing import Sequence, Union

import log
log.hotpatch(logging)
logger = log.DeferredLogger(__name__)

TOK_SPECIAL = "%"
TOK_COMMA = ","
TOK_SEPARATOR = "="
TOKENS = {}

TokenType = Union[str, dict]

class FormatError(ValueError):
  "Raised when there's an error processing the format string"

class FormatParseError(FormatError):
  "Raised when there's an error parsing the format string"
  def __init__(self, format_string, index, message, *args, **kwargs):
    self._format_string = format_string
    self._index = index
    self._message = message
    if args or kwargs:
      self._message = self._message.format(*args, **kwargs)
    super().__init__(self.__str__())

  def __str__(self):
    return "Error parsing {!r} at index {}: {}".format(
        self._format_string, self._index, self._message)

class FormatApplyError(FormatError):
  "Raised when there's an error applying a format operation on a file path"
  def __init__(self, file_path, message, *args, **kwargs):
    self._file_path = file_path
    self._message = message
    if args or kwargs:
      self._message = self._message.format(*args, **kwargs)
    super().__init__(self.__str__())

  def __str__(self):
    return "Error formatting {!r}: {}".format(self._file_path, self._message)

def isnumber(value):
  "Like str.isdigit but allowing negatives"
  if value.startswith("-"):
    return value[1:].isdigit()
  return value.isdigit()

def _verify_args(func, nargs, args, kwargs):
  "Assert that the argument count satisfies the requirement count"
  count = len(args)
  if isinstance(nargs, int):
    if count != nargs:
      raise ValueError("{} requires {} arguments; got {} instead".format(
        log.func_name(func), nargs, count))
  elif isinstance(nargs, tuple) and len(nargs) == 2:
    argmin, argmax = nargs
    if argmin is None:
      argmin = count
    if argmax is None:
      argmax = count
    if count < argmin or count > argmax:
      raise ValueError(
          "{} requires between {} and {} arguments; got {} instead".format(
              log.func_name(func), nargs[0], nargs[1], count))
  elif nargs is not None:
    raise ValueError("invalid nargs {!r} to _verify_args".format(nargs))

def _token(char, nargs=None):
  "Decorator-builder for token functions"
  def decorator(func):
    "Decorate func as a formatter function"
    TOKENS[char] = func
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
      "Token wrapper function"
      _verify_args(func, nargs, args, kwargs)
      return func(*args, **kwargs)
    return wrapper
  return decorator

def get_basename(filepath):
  "A file's basename without extension"
  return os.path.basename(filepath).rsplit(os.extsep, 1)[0]

def get_extension(filepath):
  "A file's extension without the separator"
  parts = os.path.basename(filepath).rsplit(os.extsep, 1)
  if len(parts) == 2:
    return parts[-1]
  return ""

@_token(TOK_SPECIAL)
def tok_percent(*args, **kwargs): # pylint: disable=unused-argument
  "A literal percent sign"
  return TOK_SPECIAL

@_token("B", nargs=1)
def tok_basename(*args, **kwargs): # pylint: disable=unused-argument
  "A file's basename without extension"
  return get_basename(args[0])

@_token(".")
def tok_extsep(*args, **kwargs): # pylint: disable=unused-argument
  "The extension separator"
  return os.extsep

@_token("E", nargs=1)
def tok_extension(*args, **kwargs): # pylint: disable=unused-argument
  "A file's extension without the separator"
  return get_extension(args[0])

@_token("H", nargs=1)
def tok_hash(*args, **kwargs): # pylint: disable=unused-argument
  "The first eight characters of a file's SHA256 hash"
  return hashlib.sha256(open(args[0], "rb").read()).hexdigest()[:8]

@_token("S", nargs=1)
def tok_size(*args, **kwargs): # pylint: disable=unused-argument
  "A file's size in bytes"
  return str(os.stat(args[0]).st_size)

@_token("C", nargs=1)
def tok_substr(*args, token, field_value, **kwargs): # pylint: disable=unused-argument
  "A substring of the file's name"
  if TOK_COMMA not in field_value:
    raise FormatApplyError(args[0], "field value {!r} missing separator {}",
        field_value, TOK_COMMA)
  begin_str, end_str = field_value.split(TOK_COMMA, 1)
  if begin_str and not isnumber(begin_str):
    raise FormatApplyError(args[0], "begin {!r} must be empty or numeric", begin_str)
  if end_str and not isnumber(end_str):
    raise FormatApplyError(args[0], "end {!r} must be empty or numeric", end_str)
  name = get_basename(args[0])
  begin_pos = int(begin_str) if begin_str else 0
  end_pos = int(end_str) if end_str else len(name)
  return name[begin_pos:end_pos]

@_token("T", nargs=1)
def tok_tokenize(*args, token, field_value, **kwargs): # pylint: disable=unused-argument
  "The nth field of the file's basename after tokenization"
  if TOK_SEPARATOR not in field_value:
    raise FormatApplyError(args[0], "field value {!r} missing separator {}",
        field_value, TOK_SEPARATOR)
  field, index_str = field_value.rsplit(TOK_SEPARATOR, 1)
  if not index_str.isdigit():
    raise FormatApplyError(args[0], "field index {!r} of {!r} not numeric",
        index_str, field_value)
  name = get_basename(args[0])
  tokens = name.split(field)
  index = int(index_str) - 1
  if index < 0:
    logger.warning("%r: token index %d (for %r) less than zero",
        name, index, field_value)
    logger.warning("interpreting the result as a zero-length string")
    return ""
  if index >= len(tokens):
    logger.warning("%r: token index %d (for %r) too big; file has %d token%s",
        name, index, field_value, len(tokens), "" if len(tokens) == 1 else "s")
    logger.warning("interpreting the result as a zero-length string")
    return ""
  return tokens[index]

@_token("U", nargs=1)
def tok_upper(*args, token, field_value, **kwargs):
  "Like T, but make the field uppercase"
  return tok_tokenize(*args, token=token, field_value=field_value, **kwargs).upper()

@_token("L", nargs=1)
def tok_lower(*args, token, field_value, **kwargs):
  "Like T, but make the field lowercase"
  return tok_tokenize(*args, token=token, field_value=field_value, **kwargs).lower()

@_token("M", nargs=1)
def tok_modtime(*args, field_value, **kwargs): # pylint: disable=unused-argument
  "The file's modification time, formatted as specified"
  if field_value is None:
    raise FormatApplyError(args[0], "invalid token: missing timestamp format")
  mtime = os.stat(args[0]).st_mtime
  return datetime.datetime.fromtimestamp(mtime).strftime(field_value)

def _next_char(format_string, index):
  "Get the next character, raising a ValueError if that isn't possible"
  if index + 1 < len(format_string):
    return format_string[index + 1], index + 1
  raise FormatParseError(format_string, index, "reached end of string")

def _consume_until(format_string, index, char, can_recover=False):
  "Consume characters until the given character is found"
  curr = index
  while curr < len(format_string):
    if format_string[curr] == char:
      return format_string[index:curr], curr
    curr = curr + 1
  if can_recover:
    return "", index
  raise FormatParseError(format_string, index,
      "reached end of string while searching for {!r}", char)

def _consume(format_string, index):
  "Parse out the entire format specifier starting at the given index"
  field_value = None
  nextchar, index = _next_char(format_string, index)
  if nextchar == "(":
    field_value, index = _consume_until(format_string, index + 1, ")")
    nextchar, index = _next_char(format_string, index)
  return nextchar, index, field_value

def parse_format_string(format_string: str) -> Sequence[TokenType]:
  "Parse a printf-style str into a list of format tokens; used by format_path"
  index = 0
  tokens = []
  while index < len(format_string):
    char = format_string[index]
    logger.trace("Parsing %r at %d", format_string, index)
    if char == TOK_SPECIAL:
      sequence, index, field_value = _consume(format_string, index)
      logger.trace("Consumed %r value=%r, index is now %d", sequence,
          field_value, index)
      tokens.append({
        "token": sequence,
        "field_value": field_value,
        "source_string": format_string,
        "source_index": index
      })
    else:
      tokens.append(char)
    index = index + 1
  return tokens

def apply_token(filepath: str, token: TokenType) -> str:
  """
  Given a single token from parse_format_string, apply that token onto the
  given file path to obtain a str.
  """
  format_char = token["token"]
  func = TOKENS.get(format_char)
  if not func:
    logger.error("invalid format token %r (obtained via %r at %d)",
        format_char, token["source_string"], token["source_index"])
    return None
  result = func(filepath, **token)
  logger.debug("apply %r on %r (%s) -> %r", format_char, filepath, ", ".join(
      "{}={!r}".format(entry_key, token[entry_key])
      for entry_key in ("field_value", "source_string", "source_index")
    ), result)
  return result

def format_path(filepath: str, format_string: str) -> str:
  """
  Given a file path and a printf-style format string, return a new string with
  the filename formatted according to the format string.
  """
  tokens = parse_format_string(format_string)
  output = []
  for token in tokens:
    if isinstance(token, str):
      output.append(token)
    elif isinstance(token, dict):
      result = apply_token(filepath, token)
      if result is not None:
        output.append(result)
    else:   # indicates a larger problem; parser shouldn't emit this
      logger.warning("invalid token %r; assuming string", token)
      output.append(str(token))
  result = os.path.join(os.path.dirname(filepath), "".join(output))
  logger.debug("Renaming %r to %r", filepath, result)
  return result

# vim: set ts=2 sts=2 sw=2:
