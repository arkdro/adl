# import sys

import re
import argparse


def write_item(item):
    """ write item to stdout """
    print(item)


def flush_item(item, include, exclude):
    """ flush item """
    if not item:
        return
    if include:
        for i in include:
            if (re.search(i, item, flags=re.MULTILINE | re.IGNORECASE)):
                write_item(item)
                break
        return
    elif exclude:
        for e in exclude:
            if (re.search(e, item, flags=re.MULTILINE | re.IGNORECASE)):
                return
        write_item(item)


def proc_file(file, include, exclude):
    """ process file """
    regex = re.compile('\d+-\d+-\d+ \d+:\d+:\d+ =\w+ REPORT====')
    item = ''
    with open(file, encoding='utf-8') as fd:
        for l in fd:
            if (re.search(regex, l)):
                flush_item(item, include, exclude)
                item = l
            else:
                item += l
    flush_item(item, include, exclude)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', "--exclude", help="exclude", action='append')
    parser.add_argument('-i', "--include", help="include", action='append')
    parser.add_argument('-f', "--input_file", help="input file")
    args = parser.parse_args()
    proc_file(args.input_file, args.include, args.exclude)

