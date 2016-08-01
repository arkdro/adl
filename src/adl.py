# import sys

import argparse
import html
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
        text = str(data)
        return (dest, text)


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
    abs_link_parts = build_abs_links(url, parts)
    return abs_link_parts


def build_abs_links(base, parts):
    res = [(num, title, urllib.parse.urljoin(base, link))
           for (num, title, link) in parts]
    return res


def is_correct_data_item(text):
    """ Predicate to test if the item is good. """
    tags = ['mediathumbnail', 'mediatext', 'mediatitle', 'medialink',
            'href', 'title']
    res = all(re.search(tag, text) for tag in tags)
    return res


def extract_one_part(text):
    """ Extract link and title from text. """
    link = extract_link(text)
    title = extract_title(text)
    num = extract_number(title)
    return (num, title, link)


def extract_number(text):
    """ Extract number from text. """
    regex = '(\\d+)'
    match = re.search(regex, text)
    if match and len(match.groups()) > 0:
        return match.group(1)


def extract_link(text):
    """ Extract link from text. """
    regex = '''\\bhref\\s*=\\s*['"]([^<>"]+)['"]'''
    match = re.search(regex, text, flags=re.IGNORECASE)
    if match and len(match.groups()) > 0:
        return match.group(1)


def extract_title(text):
    """ Extract title from text. """
    regex = '''\\btitle\\s*=\\s*['"]([^<>"]+)['"]'''
    match = re.search(regex, text, flags=re.IGNORECASE)
    if match and len(match.groups()) > 0:
        cleared = html.unescape(match.group(1))
        return cleared


def extract_parts(text):
    """ Extract data items from text. """
    sep = 'medialisting'
    lst = re.split(sep, text, flags=re.IGNORECASE)
    lst2 = [x for x in lst if is_correct_data_item(x)]
    lst3 = [extract_one_part(x) for x in lst2]
    return lst3


def extract_parts_body(text):
    before = 'course_inner_media_gallery'
    after = 'slide-bottom'
    extract_text_by_borders(before, after, text)


def extract_text_by_borders(before, after, text):
    """ Extract the text containing data items from the input text. """
    lst1 = re.split(before, text, flags=re.IGNORECASE)
    if len(lst1) < 2:
        raise Exception("no beginning separator")
    lst2 = re.split(after, lst1[1], flags=re.IGNORECASE)
    if len(lst2) < 2:
        raise Exception("no ending separator")
    return lst2[0]


def proc_file(args):
    """ process file """
    (base_url, base_page) = get_base_page(args.base)
    parts = find_parts(base_url, base_page)
    logging.debug('parts: %s' % (pprint.pformat(parts)))
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', "--base", help="base url")
    parser.add_argument('-l', "--loglevel")
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel.upper(),
                        format='%(asctime)s %(message)s')
    proc_file(args)

