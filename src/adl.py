# import sys

import argparse
import concurrent.futures
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
    res = extract_text_by_borders(before, after, text)
    return res


def extract_text_by_borders(before, after, text):
    """ Extract the text containing data items from the input text. """
    lst1 = re.split(before, text, maxsplit=1,
                    flags=re.IGNORECASE | re.MULTILINE)
    if len(lst1) < 2:
        raise Exception("no beginning separator")
    lst2 = re.split(after, lst1[1], maxsplit=1, flags=re.IGNORECASE)
    if len(lst2) < 2:
        raise Exception("no ending separator")
    return lst2[0]


def proc_file(args):
    """ process file """
    (base_url, base_page) = get_base_page(args.base)
    parts = find_parts(base_url, base_page)
    logging.debug('parts: %s' % (pprint.pformat(parts)))
    get_parts(parts)
    return


def get_one_part(item, timeout):
    """ fetch one part """
    logging.debug('get_one_part, input item: {}'.format(item))
    (num, title, url) = item
    (dest, text) = load_url(url, timeout)
    transcript_url = extract_transcript_url(dest, text)
    logging.debug('get_one_part, tr: {}'.format(transcript_url))
    notes_url = extract_notes_url(dest, text)
    logging.debug('get_one_part, no: {}'.format(notes_url))
    video_url = extract_video_url(dest, text)
    logging.debug('get_one_part, vi: {}'.format(video_url))
    subtitle_url = extract_subtitle_url(dest, text)
    logging.debug('get_one_part, sub: {}'.format(subtitle_url))
    out_item = (transcript_url, notes_url, video_url, subtitle_url)
    logging.debug('get_one_part, output item: {}'.format(out_item))
    return out_item


def extract_subtitle_url(dest, text):
    before = '''<div[^<>]+\\bid\\s*=\\s*['"]vid_transcript['"]'''
    after = '''<\\/div>'''
    inner = extract_text_by_borders(before, after, text)
    before2 = '''Subtitle'''
    after2 = '''<\\/'''
    inner2 = extract_text_by_borders(before2, after2, inner)
    link = extract_link(inner2)
    res = urllib.parse.urljoin(dest, link)
    return res


def extract_video_url(dest, text):
    before = '''<div[^<>]+\\bid\\s*=\\s*['"]vid_transcript['"]'''
    after = '''Subtitle'''
    inner = extract_text_by_borders(before, after, text)
    link = extract_link(inner)
    res = urllib.parse.urljoin(dest, link)
    return res


def extract_notes_url(dest, text):
    before = '''<div[^<>]+\\bid\\s*=\\s*['"]vid_related['"]'''
    after = '''<\\/div>'''
    inner = extract_text_by_borders(before, after, text)
    link = extract_link(inner)
    res = urllib.parse.urljoin(dest, link)
    return res


def extract_transcript_url(dest, text):
    before = '''<div[^<>]+\\bid\\s*=\\s*['"]vid_playlist['"]'''
    after = '''<\\/div>'''
    inner = extract_text_by_borders(before, after, text)
    link = extract_link(inner)
    res = urllib.parse.urljoin(dest, link)
    return res


def get_parts(parts):
    """ fetch parts in parallel """
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        timeout = 60
        # Start the load operations and mark each future with its URL
        future_to_url = {executor.submit(get_one_part, item, timeout):
                         item for item in parts}
        for future in concurrent.futures.as_completed(future_to_url):
            item = future_to_url[future]
            try:
                data = future.result()
            except Exception as exc:
                logging.error('%r generated an exception: %s' % (item, exc))
            else:
                logging.debug('%r page is %d bytes' % (item, len(data)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', "--base", help="base url")
    parser.add_argument('-l', "--loglevel")
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel.upper(),
                        format='%(asctime)s %(message)s')
    proc_file(args)

