# import sys

import argparse
import logging
import pprint
import re
import urllib.request


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
    parser.add_argument('-b', "--base", help="base url")
    parser.add_argument('-l', "--loglevel")
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel.upper(),
                        format='%(asctime)s %(message)s')
    proc_file(args)

