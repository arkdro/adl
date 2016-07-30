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


def load_url(url, timeout):
    with urllib.request.urlopen(url, timeout=timeout) as conn:
        logging.debug('url: %r, %s' % (url, pprint.pformat(conn.info)))
        # raise Exception("skip")
        dest = conn.geturl()
        data = conn.read()
        return (dest, data)


def get_base_page(url):
    """ Get base page. Return the page as a string. """
    timeout = 60
    (dest, data) = load_url(url, timeout)
    logging.debug('dest url: %r, len: %d' % (dest, len(data)))
    return (dest, data)


def find_parts(url, text):
    """ Extract necessary parts from the base page. """
    text2 = extract_parts_body(text)
    parts = extract_parts(text2)
    pass


def extract_parts(text):
    """ Extract data items from text. """
    pass


def extract_parts_body(text):
    """ Extract the text containing data items from the input text. """
    before = 'course_inner_media_gallery'
    after = 'slide-bottom'
    lst1 = re.split(before, text, flags=re.IGNORECASE)
    if len(lst1) < 2:
        raise Exception("no beginning separator")
    lst2 = re.split(after, lst1[1], flags=re.IGNORECASE)
    if len(lst2) < 2:
        raise Exception("no ending separator")
    return lst2[1]


def proc_file(args):
    """ process file """
    (base_url, base_page) = get_base_page(args.base)
    parts = find_parts(base_url, base_page)
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', "--base", help="base url")
    parser.add_argument('-l', "--loglevel")
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel.upper(),
                        format='%(asctime)s %(message)s')
    proc_file(args)

