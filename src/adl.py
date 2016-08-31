# import sys

import argparse
import concurrent.futures
import html
import logging
import os.path
import pathlib
import posixpath
import pprint
import re
import urllib.parse
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
        return int(match.group(1))


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
    get_parts(args.outdir, parts)
    return


def prepare_one_part(item, timeout):
    """ prepare links for one part """
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


def get_one_part(outdir, item, timeout):
    """ fetch one part """
    links = prepare_one_part(item, timeout)
    num = item[0]
    outdir2 = build_item_outdir(num, outdir)
    basenames = build_base_name(links)
    fetch_files(outdir2, item, basenames, links, timeout)
    return True


def build_item_outdir(num, outdir):
    num_str = "{:02}".format(num)
    name = os.path.join(outdir, num_str)
    return name


def build_base_name(links):
    """ build a base name based on video or notes """
    (_, notes, video, _) = links
    basename = extract_basename(video)
    if basename:
        return basename
    else:
        basename = extract_basename(notes)
        return basename


def extract_basename(url):
    """ extract base name from an url. Remove ending speed. """
    path = urllib.parse.urlsplit(url).path
    filename = posixpath.basename(path)
    basename = posixpath.splitext(filename)[0]
    regex = '''_\\d+[kmg]$'''
    name2 = re.split(regex, basename, maxsplit=1, flags=re.IGNORECASE)
    return (basename, name2[0])


def fetch_files(outdir, item, basenames, links, timeout):
    """ fetch files using links. Store files using basename. """
    (transcript_url, notes_url, video_url, subtitle_url) = links
    (vidname, basename) = basenames
    ensure_dir(outdir)
    fetch_transcript(outdir, basename, transcript_url, timeout)
    fetch_notes(outdir, basename, notes_url, timeout)
    fetch_subtitles(outdir, vidname, subtitle_url, timeout)
    fetch_video(outdir, vidname, video_url, timeout)


def ensure_dir(outdir):
    path = pathlib.Path(outdir)
    if not path.exists():
        path.mkdir(parents=True)


def fetch_video(outdir, basename, url, timeout):
    logging.debug('fetch_video, url: {}'.format(url))
    name = build_vidname(outdir, url)
    fetch_file_to_local_file(name, url, timeout)


def fetch_subtitles(outdir, basename, url, timeout):
    fetch_file(outdir, basename, url, timeout, '')


def fetch_notes(outdir, basename, url, timeout):
    fetch_file(outdir, basename, url, timeout, 'notes')


def fetch_transcript(outdir, basename, url, timeout):
    fetch_file(outdir, basename, url, timeout, 'tr')


def fetch_file(outdir, basename, url, timeout, tag):
    name = build_filename(outdir, basename, tag, url)
    fetch_file_to_local_file(name, url, timeout)


def fetch_file_to_local_file(name, url, timeout):
    size = 64 * 1024
    total = 0
    with urllib.request.urlopen(url, timeout=timeout) as conn,\
    open(name, mode='wb') as fd:
        logging.debug('fetch to local, headers: {}'.format(conn.getheaders()))
        while True:
            chunk = conn.read(size)
            total += len(chunk)
            if not total % 2 ** 20:
                logging.debug('fetch to local, chunk, total: {}'.format(total))
            if chunk:
                fd.write(chunk)
            else:
                logging.debug('fetch to local, last, total: {}'.format(total))
                break


def build_filename(outdir, basename, tag, url):
    parsed = urllib.parse.urlparse(url)
    filename = os.path.basename(parsed.path)
    (_, ext) = os.path.splitext(filename)
    if tag:
        tagged_name = basename + '-' + tag + ext
    else:
        tagged_name = basename + ext
    fullname = os.path.join(outdir, tagged_name)
    return fullname


def build_vidname(outdir, url):
    parsed = urllib.parse.urlparse(url)
    filename = os.path.basename(parsed.path)
    fullname = os.path.join(outdir, filename)
    return fullname


def extract_subtitle_url(dest, text):
    before = '''<div[^<>]+\\bid\\s*=\\s*['"]vid_transcript['"]'''
    after = '''<\\/div>'''
    inner = extract_text_by_borders(before, after, text)
    before2 = '''Subtitle'''
    after2 = '''<\\/a>'''
    inner2 = extract_text_by_borders(before2, after2, inner)
    link = extract_link(inner2)
    res = urllib.parse.urljoin(dest, link)
    return res


def extract_video_url(dest, text):
    before = '''<div[^<>]+\\bid\\s*=\\s*['"]vid_transcript['"]'''
    after = '''Subtitle'''
    inner = extract_text_by_borders(before, after, text)
    before2 = '''\\bArchive\\b'''
    after2 = '''<\\/'''
    inner2 = extract_text_by_borders(before2, after2, inner)
    link = extract_link(inner2)
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


def get_parts(outdir, parts):
    """ fetch parts in parallel """
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        timeout = 60
        # Start the load operations and mark each future with its URL
        future_to_url = {executor.submit(get_one_part, outdir, item, timeout):
                         item for item in parts}
        for future in concurrent.futures.as_completed(future_to_url):
            item = future_to_url[future]
            try:
                data = future.result()
            except Exception as exc:
                logging.error('%r generated an exception: %s' % (item, exc))
            else:
                logging.debug('%r page, result: %r' % (item, data))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', "--outdir", help="output directory", default=".")
    parser.add_argument('-b', "--base", help="base url")
    parser.add_argument('-l', "--loglevel")
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel.upper(),
                        format='%(asctime)s %(threadName)s %(thread)d %(message)s')
    proc_file(args)

