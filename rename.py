#!/usr/bin/env python3

"""
Rename a file (or set of files) according to the given rule(s).
"""

# IDEA: %(mime)E for file's mimetype determined via file(1) command
# IDEA: %I, the index of the file being processed (starting at 1)

import argparse
import logging
import os
import re
import shlex
import sys
import textwrap

import formatstring
from formatstring import get_basename, get_extension
import log
log.hotpatch(logging)

logging.basicConfig(format="%(module)s:%(lineno)s: %(levelname)s: %(message)s",
                    level=logging.INFO)
logger = logging.getLogger(__name__)

FORMAT_DEFAULT = "%H%.%E"

def read_file(path=None, fobj=None):
  "Read the file, into a list of lines omitting empty lines"
  lines = []
  if not path and not fobj:
    raise ValueError("either path or fobj required")
  if path and fobj:
    raise ValueError("path and fobj are mutually exclusive")
  if path:
    fobj = open(path, "rt")
  for line in fobj.read().splitlines():
    if line:
      lines.append(line)
  return lines

def gather_files(paths, list_file):
  "Build the final list of files to rename"
  files = set()
  for path in paths:
    if path == "-":
      files.update(read_file(fobj=sys.stdin))
    else:
      files.add(path)
  if list_file:
    files.update(read_file(path=list_file))
  logger.debug("Processing %d file(s)", len(files))
  return files

def parse_regex_arg(arg):
  "Parse the value to the -p,--regex argument"
  if not arg.startswith("s/") or not arg.endswith("/") or arg.count("/") != 3:
    logger.error("failed to parse argument %r: not in s/OLD/NEW/ format", arg)
    return None, None
  return arg[2:-1].split("/", 1)

def split_path(file_path):
  "Split a path into directory, basename, and extension pieces"
  file_dir = os.path.dirname(file_path)
  file_base = os.path.basename(file_path)
  return file_dir, get_basename(file_base), get_extension(file_base)

def join_path(file_dir, file_base, file_ext):
  "Join the split path into a single final path, allowing for no extension"
  file_name = file_base
  if file_ext:
    file_name = file_base + os.extsep + file_ext
  return os.path.join(file_dir, file_name)

def rename_file(from_path, to_path, overwrite=False):
  "Actually rename a file"
  final_path = to_path
  if os.path.isdir(to_path):
    final_path = os.path.join(to_path, os.path.basename(from_path))
    logger.info("destination %r is a directory, renaming to %r", to_path, final_path)
    to_path = final_path
  if os.path.exists(to_path):
    if overwrite:
      logger.warning("overwriting %r with %r", to_path, from_path)
    else:
      logger.error("failed to rename %r to %r: destination exists", from_path, to_path)
      return False
  os.rename(from_path, final_path)
  return True

def main():
  program = os.path.basename(sys.argv[0])
  ap = argparse.ArgumentParser(epilog=textwrap.dedent(f"""
  Rename files according to the specified rules. By default, if no rules are
  given, then --format={FORMAT_DEFAULT!r} is assumed.

  "basename" refers to the file's name without the extension or the extension
  separator. Files can have at most one extension. For example, the basename
  and extension of "archive.tar.gz" are "archive.tar" and "gz", respectively.

  Renaming is done via the following steps and the output of one operation is
  passed directly to the next.
    --format              apply printf-style formatting
    --regex               apply a regular expression via the re module
    --map-ext             remap an extension *once*, if present
    --upper or --lower    change the case of the file's basename

  -f,--format expects a printf-style format string and supports the following
  format specifiers:
    %%    a literal percent symbol
    %.    the extension separator character
    %B    original file's basename, without extension or separator
    %E    original file's extension, without separator
    %H    first eight characters of the file's SHA256 hash
    %S    file size in bytes
    %(begin,end)C       filename[begin:end], either of which can be negative
    %(,end)C            shorthand for `%(0,end)C`
    %(begin,)C          shorthand for `%(begin,<length of name>)C`
    %(token=number)T
          the "number"th field of the file's name, when tokenized using the
          given token, with numbering starting at 1
    %(token=number)L    `%(token=number)T` made lowercase
    %(token=number)U    `%(token=number)T` made uppercase
    %(format)M          the file's modification time, via strftime(format)

  -e,--map-ext will only be applied once. For example, the arguments
    {program} -e csv=txt -e txt=html rows.csv text.txt
  will rename "rows.csv" to "rows.txt" and "text.txt" to "text.html".
  """), formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("path", nargs="*", help="file(s) to process")
  ap.add_argument("-i", "--file", metavar="PATH",
      help="file listing the files to process, one per line")

  ag = ap.add_argument_group("renaming rules")
  ag.add_argument("-e", "--map-ext", action="append", metavar="OLD=NEW",
      help="replace extension OLD with NEW")
  ag.add_argument("-p", "--regex", action="append", metavar="s/OLD/NEW/",
      help="replace using a regular expression via the re module")
  ag.add_argument("-f", "--format",
      help="rename using an advanced formatting string")
  mg = ag.add_mutually_exclusive_group()
  mg.add_argument("-U", "--upper", action="store_true",
      help="make the resulting name uppercase (not including extension)")
  mg.add_argument("-L", "--lower", action="store_true",
      help="make the resulting name lowercase (not including extension)")

  ag = ap.add_argument_group("behavior")
  mg = ag.add_mutually_exclusive_group()
  mg.add_argument("-n", "--dry", action="store_true",
      help="dry run mode: don't actually rename files")
  mg.add_argument("-o", "--overwrite", action="store_true",
      help="overwrite existing destination files")
  mg.add_argument("-F", "--force", action="store_true",
      help="continue on error; implies --overwrite")

  ag = ap.add_argument_group("output")
  ag.add_argument("--as-mv", metavar="PATH",
      help="write 'mv OLD NEW' commands to %(metavar)s; implies --dry")
  ag.add_argument("--mv-command", metavar="COMMAND", default="mv",
      help="command used by --as-mv (default %(default)r)")
  ag.add_argument("--mv-arg", metavar="ARG", action="append",
      help="additional arguments to pass to --mv-command")

  ag.add_argument("--as-symlink", metavar="PATH",
      help="write 'ln -s NEW OLD' commands to %(metavar)s; implies --dry")
  ag.add_argument("--symlink-command", metavar="COMMAND", default="ln",
      help="command used by --as-symlink (default %(default)r)")
  ag.add_argument("--symlink-arg", metavar="ARG", action="append",
      help="arguments to pass to --symlink-command (default: ['-s']")

  ag.add_argument("--as-hardlink", metavar="PATH",
      help="write 'ln NEW OLD' commands to %(metavar)s; implies --dry")
  ag.add_argument("--hardlink-command", metavar="COMMAND", default="ln",
      help="command used by --as-hardlink (default %(default)r)")
  ag.add_argument("--hardlink-arg", metavar="ARG", action="append",
      help="arguments to pass to --hardlink-command (default: none")

  ag = ap.add_argument_group("diagnostics")
  mg = ag.add_mutually_exclusive_group()
  mg.add_argument("-v", "--verbose", action="store_true",
      help="enable verbose diagnostic output")
  mg.add_argument("-t", "--trace", action="store_true",
      help="enable trace-level diagnostic output")
  args = ap.parse_args()
  if args.verbose:
    logger.setLevel(logging.DEBUG)
    formatstring.logger.setLevel(logging.DEBUG)
  elif args.trace:
    logger.setLevel(logging.TRACE) # pylint: disable=no-member
    formatstring.logger.setLevel(logging.TRACE) # pylint: disable=no-member
  logger.debug("Parsed arguments: %r", args)

  if args.as_mv or args.as_symlink or args.as_hardlink:
    args.dry = True
  if args.force:
    args.overwrite = True

  files = gather_files(args.path, args.file)
  if not files:
    ap.error("no files given")

  pattern, replace = None, None
  if args.regex is not None:
    pattern, replace = parse_regex_arg(args.regex)
    if pattern is None or replace is None:
      ap.error("failed to parse --regex; aborting")

  if not any((args.map_ext, args.regex, args.format, args.upper, args.lower)):
    logger.debug("defaulting to --format=%s", FORMAT_DEFAULT)
    args.format = FORMAT_DEFAULT

  results = []
  for idx, filepath in enumerate(files):
    logger.debug("Processing file %d of %d: %r", idx+1, len(files), filepath)
    curr_path = filepath

    if args.format is not None:
      try:
        new_path = formatstring.format_path(curr_path, args.format)
        logger.debug("format(%r) %r -> %r", args.format, curr_path, new_path)
        curr_path = new_path
      except formatstring.FormatError as err:
        logger.error(err)
        if not args.force:
          ap.error("aborting")

    if pattern is not None and replace is not None:
      # TODO
      new_path = curr_path
      logger.debug("regex s/%r/%r/ %r -> %r", pattern, replace, curr_path, new_path)
      curr_path = new_path

    if args.map_ext is not None:
      ext_map = dict([entry.split("=", 1) for entry in args.map_ext])
      file_dir, file_base, file_ext = split_path(curr_path)
      if file_ext in ext_map:
        file_ext = ext_map[file_ext]
        new_path = join_path(file_dir, file_base, file_ext)
        logger.debug("map_ext %r -> %r", curr_path, new_path)
        curr_path = new_path

    if args.upper:
      file_dir, file_base, file_ext = split_path(curr_path)
      file_base = file_base.upper()
      new_path = join_path(file_dir, file_base, file_ext)
      logger.debug("upper: %r -> %r", curr_path, new_path)
      curr_path = new_path

    if args.lower:
      file_dir, file_base, file_ext = split_path(curr_path)
      file_base = file_base.lower()
      new_path = join_path(file_dir, file_base, file_ext)
      logger.debug("lower: %r -> %r", curr_path, new_path)
      curr_path = new_path

    add_entry = True
    if not curr_path:
      logger.error("failed to rename %r: new path is empty", filepath)
      add_entry = False
    elif curr_path == filepath:
      logger.warning("failed to rename %r: filename unchanged", filepath)
      add_entry = False
    elif os.path.exists(curr_path):
      if not args.overwrite and not args.force:
        logger.error("failed to rename %r: new path %r exists", filepath, curr_path)
        add_entry = False
      else:
        logger.warning("renaming %r: overwriting %r", filepath, curr_path)

    if add_entry:
      logger.debug("planning to rename %r to %r", filepath, curr_path)
      results.append((filepath, curr_path))

  logger.debug("planning to rename %d file%s", len(results),
      "s" if len(results) != 1 else "")

  if not results:
    logger.error("no action to take; aborting")
    raise SystemExit(1)

  for filepath, newpath in results:
    if args.as_mv:
      ap.error("not implemented yet") # TODO
    if args.as_symlink:
      ap.error("not implemented yet") # TODO
    if args.as_hardlink:
      ap.error("not implemented yet") # TODO
    if args.dry:
      logger.info("DRY: mv %r %r", filepath, newpath)
      print("mv {} {}".format(shlex.quote(filepath), shlex.quote(newpath)))
    else:
      logger.info("Renaming %r to %r", filepath, newpath)
      rename_file(filepath, newpath, overwrite=args.overwrite)

if __name__ == "__main__":
  main()

# vim: set ts=2 sts=2 sw=2:
