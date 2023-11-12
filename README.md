# File Rename Utility

Rename one or more files using printf-style formatting.

```
usage: rename.py [-h] [-i PATH] [-e OLD=NEW] [-p s/OLD/NEW/] [-f FORMAT]
                 [-U | -L] [-n | -o | -F] [--as-mv PATH]
                 [--mv-command COMMAND] [--mv-arg ARG] [--as-symlink PATH]
                 [--symlink-command COMMAND] [--symlink-arg ARG]
                 [--as-hardlink PATH] [--hardlink-command COMMAND]
                 [--hardlink-arg ARG] [-v | -t]
                 [path [path ...]]

positional arguments:
  path                  file(s) to process

optional arguments:
  -h, --help            show this help message and exit
  -i PATH, --file PATH  file listing the files to process, one per line

renaming rules:
  -e OLD=NEW, --map-ext OLD=NEW
                        replace extension OLD with NEW
  -p s/OLD/NEW/, --regex s/OLD/NEW/
                        replace using a regular expression via the re module
  -f FORMAT, --format FORMAT
                        rename using an advanced formatting string
  -U, --upper           make the resulting name uppercase (not including
                        extension)
  -L, --lower           make the resulting name lowercase (not including
                        extension)

behavior:
  -n, --dry             dry run mode: don't actually rename files
  -o, --overwrite       overwrite existing destination files
  -F, --force           continue on error; implies --overwrite

output:
  --as-mv PATH          write 'mv OLD NEW' commands to PATH; implies --dry
  --mv-command COMMAND  command used by --as-mv (default 'mv')
  --mv-arg ARG          additional arguments to pass to --mv-command
  --as-symlink PATH     write 'ln -s NEW OLD' commands to PATH; implies --dry
  --symlink-command COMMAND
                        command used by --as-symlink (default 'ln')
  --symlink-arg ARG     arguments to pass to --symlink-command (default:
                        ['-s']
  --as-hardlink PATH    write 'ln NEW OLD' commands to PATH; implies --dry
  --hardlink-command COMMAND
                        command used by --as-hardlink (default 'ln')
  --hardlink-arg ARG    arguments to pass to --hardlink-command (default: none

diagnostics:
  -v, --verbose         enable verbose diagnostic output
  -t, --trace           enable trace-level diagnostic output

Rename files according to the specified rules. By default, if no rules are
given, then --format='%H%.%E' is assumed.

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
  rename.py -e csv=txt -e txt=html rows.csv text.txt
will rename "rows.csv" to "rows.txt" and "text.txt" to "text.html".
```
