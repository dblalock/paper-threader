
import math
import re
import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List, Optional, Sequence, Tuple, Union

import bs4
import mistletoe as mt  # md -> thread
import numpy as np
import tweepy  # only imported for type checking of author username lookup
from bs4 import BeautifulSoup
from markdownify import markdownify as md  # html -> md

import arxiv_utils as arxiv
import twitter_utils as twit

TEST_HTML_EASY = 'test-summary-easy.html'
TEST_HTML_HARD = 'test-summary-hard.html'
FINAL_TWEET_FMT_STRING_PATH_WITH_AUTHORS = 'final-tweet-format-with-authors.txt'
FINAL_TWEET_FMT_STRING_PATH_NO_AUTHORS = 'final-tweet-format-no-authors.txt'

TAG_USERS_MARKER = 'TAG_USERS:'


MAX_TWEET_TEXT_LENGTH = 272  # 280 minus space for " [##/##]"
ELLIPSIS = '…'
MAX_TWEET_TEXT_SNIPPET_LENGTH = MAX_TWEET_TEXT_LENGTH - (2 * len(ELLIPSIS))

# ================================================================ author lookup

def _print_user(user: tweepy.User):
    user_attrs = [
        # 'id',           # unambiguous int unique to each user
        'name',         # arbitrary text listed as their name
        'screen_name',  # user's handle is @{screen_name}
        'description', # bio
        'followers_count',
    ]
    for attr in user_attrs:
        print(f'{attr}:\t{getattr(user, attr)}')


def find_authors(authors: Sequence[str], verbose: bool = False) -> List[tweepy.User]:
    api = twit.authenticate_v1()

    whitelist_anycase_strings = [
        'research',
        'scien',
        'university',
        'phd',
        'ph.d',
        'p.h.d'
        'faculty',
        'professor',
        'google',
        'msr',
        'microsoft',
        'deepmind',
        'facebook',
        'meta',
        'openai',
        'amazon',
        'stanford',
        'cmu',
        'harvard',
        'student',
        'machine learning',
        'data',
        'neural',
    ]
    whitelist_cased_strings = [
        'MIT',
        'AI',
        'ML',
    ]

    name2scored_users = {}
    for author in authors:
        users = twit.search_users(api, q=author, page=0, count=10)
        for i, user in enumerate(users):
            score = 0
            if i == 0:
                score += 1  # twitter top hit is usually right
            if user.name.lower() == author.lower():
                score += 1
            if user.followers_count > 10:
                score += 1
            lowercase_bio = user.description.lower()
            for substr in whitelist_anycase_strings:
                if substr in lowercase_bio:
                    score += 1
            for substr in whitelist_cased_strings:
                if substr in user.description:
                    score += 1
            if score > 2:  # needs more than just name and 0th position
                name2scored_users[author] = name2scored_users.get(author, []) + [(score, user)]
            name2scored_users.get(author)

    author2user = {}
    for author, candidates in name2scored_users.items():
        if verbose:
            print(f'================================ {author}')
            for score, user in candidates:
                print(f'------------------------ candidate (score={score}):')
                _print_user(user)
        best_user = None
        best_score = -1
        for score, user in candidates:
            if score > best_score:
                best_user = user
                best_score = score
        if best_user is not None:
            author2user[author] = best_user

    # return best-guess usernames of authors in order
    ret = []
    for author in authors:
        if author in author2user:
            ret.append(author2user[author])
    return ret


def authors_usernames_for_paper(url: str, verbose: bool = False) -> List[str]:
    _, authors, _ = arxiv.scrape_arxiv_abs_page(url)
    users = find_authors(authors, verbose=verbose)
    return [user.screen_name for user in users]


# ======================================= substack pasteboard -> markdown

def _run_cmd(cmd: str, fail_on_stderr_output: bool = True):
    ret = subprocess.run(cmd.split(), capture_output=True, text=True, encoding='utf-8')
    failed = ret.returncode != 0
    if fail_on_stderr_output:
        failed |= ret.stderr is not None and len(ret.stderr) > 0
    if failed:
        raise RuntimeError(ret)
    return ret.stdout.strip()


def html_to_markdown(html: str) -> str:
    # soup = BeautifulSoup(html, 'html.parser')
    # print(soup.prettify())
    # print(html)
    # import sys; sys.exit()
    # paragraphs = soup.find_all('p')
    # _text_in_tag
    # print(soup.prettify())
    # # return
    # for p in paragraphs:
    #     print("=====")
    #     if p.string is not None:
    #         # p.string.replace_with(re.sub('(\S)\n(\S)', r'\1\2', p.string.strip()))
    #         # p.string.replace_with(p.string.strip().replace('\n', ''))
    #         # p.string.replace_with(p.string.strip().replace('\n', ''))
    #         p.string.replace_with('foo')
        # p.string = p.string.strip()
        # print(p.string)
        # print(p.contents[0].string)
    # html = str(soup.body)
    # print(html)

    ret = md(html, strip=['b', 'i', 'em', 'span', 'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ol', 'ul'])  # wow, markdownify is magic
    # ret = md(html, convert=['p', 'a', 'img', 'ol', 'ul'])  # wow, markdownify is magic
    # ret = md(html, convert=['p', 'a', 'img'])  # wow, markdownify is magic
    ret = ret.replace('⭐', '')

    # remove links to image wrapping images
    # step 1: ensure each [![]( is on its own line (not sure why needed)
    ret = re.sub(re.escape('[![]('), '\n[![](', ret)
    # step 2: [![]($1)](*) -> ![]($1)
    ret = re.sub('\[\!\[\]\(([\S]*)\)\]\([\S]*\)', r'![](\1)\n', ret)

    # ensure images always have a newline after them; having text
    # right after them causes them to get put in the same tweet as
    # the following text, rather than the text above them.
    img_pattern = '\!\[\]\([\S]*\)'
    non_whitespace_char = '[\S]*'
    full_pattern = '(' + img_pattern + r')\n(' + non_whitespace_char + ')'
    return re.sub(full_pattern, r'\1\n\n\2', ret)
    # return re.sub('(\!\[\]\([\S]*\))\n([\S]*)', r'\1\n\n\2', ret)



# wow, this works perfectly when copying text from substack; looks like
# pasteboard isn't process-specific (just as one might hope)
def pasteboard_to_markdown() -> str:
    html = _run_cmd('pbv public.html')
    return html_to_markdown(html)


# ==================================================== markdown -> thread

@dataclass
class TextElem:
    text: str
    typ: str = 'text'

    def __str__(self):
        return self.text


@dataclass
class ImgElem:
    url: str
    typ: str = 'img'

    def __str__(self):
        return f'{self.typ} @ {self.url[:70]}...'


def _text_in_tag(p: bs4.Tag) -> str:
    contained_text = ''
    for child in p.children:
        # print('----')
        if isinstance(child, bs4.NavigableString):
            contained_text += str(child)
    if contained_text:
        contained_text = re.sub('\s', ' ', contained_text)
        # print("contained_text: ", contained_text)
    return contained_text


# def _markdown_to_text_img_elems(markdown: str, paper_title: str = '', paper_link: str = '') -> Tuple[List[Union[TextElem, ImgElem]], str, str]:
def _markdown_to_text_img_elems(markdown: str) -> Tuple[List[Union[TextElem, ImgElem]], str, str]:
    # string = '1. Input-dependent prompt tuning for multitask learning with many tasks.'
    # markdown = re.sub('^[\s]*(\d*)\.\s', r'\1) ', f'{string}\n{string}', flags=re.MULTILINE)
    # "1. whatever" -> "1): whatever"; avoids mistletoe making it an unordered list
    markdown = re.sub('^([\s]*)(\d*)\.\s', r'\1\2): ', markdown, flags=re.MULTILINE)
    # " - whatever" -> whatever
    # markdown = re.sub('^([\s]*)([\+\-\*]*)\s', r'', markdown, flags=re.MULTILINE)
    # print(markdown)
    # return

    with mt.HTMLRenderer() as renderer:     # or: `with HTMLRenderer(AnotherToken1, AnotherToken2) as renderer:`
        doc = mt.Document(markdown)              # parse the lines into AST
        html = renderer.render(doc)  # render the AST
    # print(html)
    soup = BeautifulSoup(html, 'html.parser')
    # print(soup.prettify())
    # return
    # # print(soup.body)

    # # rip out any hrules
    # hrules = soup.find_all('hr')
    # for hr in hrules:
    #     hr.decompose()

    def _unpack_anchor_tag(tag) -> Tuple[str, str]:
            return tag.string, tag['href']

    # if (not paper_title) or (not paper_link):
    # assume first link is paper link
    first_anchor = soup.find('a')
    paper_title, paper_link = '', ''
    if first_anchor is not None:
        paper_title, paper_link = _unpack_anchor_tag(first_anchor)
        # print(paper_title)
        # print(paper_link)
        first_anchor.extract()

    # convert other links to raw text (rips out links)
    for a in soup.find_all('a'):
        a.unwrap()

    # # clean up paragraphs
    # for p in soup.find_all('p'):
    #     print('------------------------')
    #     print(_text_in_tag(p))
        # print(p.contents)
        # contained_text = ''
        # for child in p.children:
        #     print('----')
        #     if isinstance(child, bs4.NavigableString):
        #         contained_text += str(child)
        # if contained_text:
        #     contained_text = re.sub('\s', ' ', contained_text)
        #     print("contained_text: ", contained_text)

        # if p.string is None and p.strings is not None:
        #     # if p.strings is None:
        #     #     continue
        #     p.string = ' '.join(p.stripped_strings)
        #     p.string.replace_with(re.sub('\s', ' ', p.string))
        #     # p.string = p.string
        #     # print("new p.string: ", p.string)
        # # if len()
        # # p.string.replace_with(p.string)

    children = soup.contents
    # print("================================ children")
    # strip out empty paragraphs or strings
    children = [c for c in children if len(str(c).strip())]

    # print(soup.prettify())
    # return

    tweet_elems = []
    for node in soup.find_all():
        # print("--------------")
        if not isinstance(node, bs4.Tag):
            continue
        # print(type(node), node.name)
        # print(node)
        # assert node.name in ('p', 'img'), f"Unsupported html tag {node.name}!"
        if node.name == 'p':
            text = _text_in_tag(node)
            if not text:
                # print("skipping node: ", node)
                # print("node text", text)
                continue  # ignore empty paragraphs
            # print(text)
            tweet_elems.append(TextElem(text=text))
        if node.name == 'img':
            # print(node['src'])
            tweet_elems.append(ImgElem(url=node['src']))

            # print(node.string)
        # else:
        #     print(type(node))
        # print(node)

    # print("================================ Tweet elems:")
    # for elem in tweet_elems:
    #     print(elem)

    # # nodes = []
    # for child in children:
    #     print("----")
    #     # print(type(child))
    #     # print(child.contents)
    #     if child.string is not None:
    #         # string = child.string.strip().replace('\n', ' ')
    #         # string = string.replace('  ', ' ')
    #         string = re.sub('\s', ' ', child.string)
    #         print(string)
    #     else:
    #         for grandchild in child.contents:
    #             print("--")
    #             print(type(grandchild))
    #             print(grandchild)

    # print('================================')
    # print(soup.body)

    return tweet_elems, paper_title, paper_link


# @dataclass
# class PaperTweetThread:
#     tweets: List[twit.Tweet]
#     tag_users: List[str] = field(default_factory=list)


def _generate_final_tweet_elem(paper_link: str, author_usernames: Optional[List[str]] = None):
    fmt_path = (FINAL_TWEET_FMT_STRING_PATH_WITH_AUTHORS if author_usernames
                else FINAL_TWEET_FMT_STRING_PATH_NO_AUTHORS)

    with open(fmt_path, 'r') as f:
        tail_tweet_format_str = f.read()
    if author_usernames:
        author_mentions = []
        for username in author_usernames:
            if not username:
                continue
            if not username.startswith('@'):
                username = '@' + username
            author_mentions.append(username)
        authors_str = ' '.join(author_mentions)
        text = tail_tweet_format_str.format(link=paper_link, authors=authors_str)
    else:
        text = tail_tweet_format_str.format(link=paper_link)
    return TextElem(text=text)


def skeleton_for_paper(paper_title: str,
                       paper_link: str,
                       author_usernames: List[str],
                       abstract: str) -> str:
    text = f'{paper_title}\n{abstract}'
    tail_elem = _generate_final_tweet_elem(paper_link=paper_link, author_usernames=author_usernames)
    return f'{text}\n\n{tail_elem.text}'


def _shard_text(text: str) -> List[str]:
    text = text.strip()
    if len(text) <= MAX_TWEET_TEXT_LENGTH:
        return [text]

    # text needs to be split up
    allowed_breakpoints = np.array([m.start() for m in re.finditer(' ', text)])
    output_chunks = []
    # idx = allowed_breakpoints[0]
    needs_initial_ellipsis = False

    # try to split text evenly across tweets so we don't get ugly
    # straggling text
    target_num_tweets = int(math.ceil(len(text) / MAX_TWEET_TEXT_SNIPPET_LENGTH))
    padding = 16
    target_chunk_length = int(padding + len(text) / target_num_tweets)
    target_chunk_length = min(target_chunk_length, MAX_TWEET_TEXT_SNIPPET_LENGTH)

    # print(f"sharding text:\n'{text}'")
    # print('target_chunk_length', target_chunk_length)
    # print("text length: ", len(text))

    while True:
        # print('allowed_breakpoints:', allowed_breakpoints)
        # print("mask:", allowed_breakpoints < target_chunk_length)
        which_breakpoint = np.where(allowed_breakpoints < target_chunk_length)[0][-1]
        split_at = allowed_breakpoints[which_breakpoint]
        allowed_breakpoints = allowed_breakpoints[(which_breakpoint + 1):]

        # print('which_breakpoint', which_breakpoint, 'split_at:', split_at)

        chunk_text = text[:split_at].strip()
        if chunk_text[-1] not in ('?', '.', '!'):
            chunk_text = chunk_text + ELLIPSIS
        if needs_initial_ellipsis:
            chunk_text = ELLIPSIS + chunk_text
        output_chunks.append(chunk_text)

        text = text[(split_at + 1):]
        needs_initial_ellipsis = True
        allowed_breakpoints -= (split_at + 1)

        # whole rest of text fits in one tweet
        if len(text) < MAX_TWEET_TEXT_SNIPPET_LENGTH:
            chunk_text = ELLIPSIS + text
            output_chunks.append(chunk_text)
            break

    # for chunk in output_chunks:
    #     print("----", len(chunk))
    #     print(chunk)

    # import sys; sys.exit()

    return output_chunks


def _markdown_to_tweet_list(markdown: str, infer_tag_users_from_text: bool = True, infer_tag_users_from_link: bool = True) -> Tuple[List[twit.Tweet], str]:
    """Raw conversion of markdown to tweet objects. No thread features."""

    tag_users = []
    if infer_tag_users_from_text:
        keep_lines = []
        for line in markdown.splitlines():
            if line.strip().startswith(TAG_USERS_MARKER):
                names = line[len(TAG_USERS_MARKER):].strip().split()
                tag_users += names
                continue
            keep_lines.append(line)
        markdown = '\n'.join(keep_lines)

    tweet_elems, paper_title, paper_link = _markdown_to_text_img_elems(markdown)

    # only try to infer tagged users if not explicitly specified
    if not tag_users and infer_tag_users_from_link:
        if not paper_link:
            # first_paper = markdown.find('https://arxiv.org/abs/')
            first_paper = re.search('https://arxiv.org/abs/[\d]*.[\d]*', markdown)
            # print('first paper found: ', first_paper)
            if first_paper:
                paper_link = first_paper.group()
            # print('matching string: ', paper_link)

        # import sys; sys.exit()
        if paper_link:
            tag_users = authors_usernames_for_paper(paper_link)

    # import sys; sys.exit()

    final_elem = _generate_final_tweet_elem(paper_link, author_usernames=tag_users)
    tweet_elems.append(final_elem)

    # print("================================ Tweet elems:")
    # for elem in tweet_elems:
    #     print(elem)
    # return

    # pull out the first image, if present, to use for the first tweet
    hero_img = ''
    pop_idx = None
    for i, elem in enumerate(tweet_elems):
        if isinstance(elem, ImgElem):
            hero_img = elem.url
            pop_idx = i
            break
    if hero_img:
        tweet_elems = tweet_elems[:pop_idx] + tweet_elems[(pop_idx + 1):]

    # two or more images at the start is undefined behavior
    assert isinstance(tweet_elems[0], TextElem), "Only one image can come before all the text"
    tweet_elems[0].text = paper_title + '\n' + tweet_elems[0].text

    all_tweets = []
    while len(tweet_elems):
        elem = tweet_elems[0]
        tweet_elems = tweet_elems[1:]

        # we pop all following img elems after each text elem, so
        # current elem has to be a text elem
        assert isinstance(elem, TextElem)
        texts = _shard_text(elem.text)
        tweets = [twit.Tweet(text=text) for text in texts]

        imgs = []
        while len(tweet_elems) and isinstance(tweet_elems[0], ImgElem):
            imgs.append(tweet_elems[0].url)
            tweet_elems = tweet_elems[1:]

        if not len(all_tweets):  # first tweet or set thereof
            # # optional header image defaults to first image provided
            # if len(imgs) and not hero_img:
            #     hero_img = imgs[0]
            #     imgs = imgs[1:]

            if hero_img:
                # give hero image to first tweet, and prevent
                # other images from getting assigned to this tweet
                # (desirable so that hero img is big)
                tweets[0].imgs = [hero_img]
                all_tweets.append(tweets[0])
                tweets = tweets[1:]

        # split imgs up across tweets
        imgs_per_tweet = int(math.ceil(len(imgs) / len(tweets)))
        for i, tweet in enumerate(tweets):
            img_start_idx = i * imgs_per_tweet
            img_end_idx = img_start_idx + imgs_per_tweet
            tweet.imgs = imgs[img_start_idx:img_end_idx]

        all_tweets += tweets


    def _number_tweets(tweets: Sequence[twit.Tweet], fmt='[{}/{}]') -> None:
        ntweets = len(tweets)
        for i, tweet in enumerate(tweets):
            tweet.text = f'{tweet.text} {fmt.format(i + 1, ntweets)}'

    _number_tweets(all_tweets)

    # print("================================ tweets")
    # for tweet in all_tweets:
    #     print(tweet)

    # for tagging in initial image
    if tag_users:
        tag_users = [user.strip('@') for user in tag_users]
        all_tweets[0].tag_users = tag_users

    return all_tweets


# def _save_or_print(content: str, saveas: str = '') -> None:
#     if saveas:
#         with open(saveas, 'w') as f:
#             f.write(content)
#     else:
#         print(content)


# def markdown_to_thread(markdown: str, saveas: str = '', preview: bool = True, post_tweet: bool = False, tag_users: Optional[List[str]] = None):

# def markdown_to_thread(markdown: str) -> List[twit.Tweet, str]:
def markdown_to_thread(markdown: str) -> List[twit.Tweet]:
    return _markdown_to_tweet_list(markdown)
    # return tweets

    # title, authors, abstract = arxiv.scrape_arxiv_abs_page(paper_link)

    # author_users = twit.

    # # print("================================")
    # if preview:
    #     content = thread_to_markdown_preview(tweets)
    #     _save_or_print(content, saveas=saveas)

    # if post_tweet:
    #     twit.create_thread(tweets)


def thread_to_markdown_preview(tweets: Sequence[twit.Tweet]) -> str:
    out = ''
    for i, tweet in enumerate(tweets):
        # map 1 linebreak -> 2 linebreaks so yields gets new md paragraph;
        # but don't map 2 linebreaks to 4, etc
        text = tweet.text.replace('\n', '\n\n')
        text = text.replace('\n\n\n\n', '\n\n')
        text = text.replace('\n\n\n\n\n\n', '\n\n\n')
        out += text
        for img in tweet.imgs:
            out += f"\n![]({img})"
        if tweet.tag_users:
            out += '\n*Users to tag in image:*'
            for username in tweet.tag_users:
                username = username if username.startswith('@') else '@' + username
                out += f'\n 1. {username}'
        if i < len(tweets) - 1:
            out += '\n\n----\n\n'
    return out


# ================================================================ debug


def main():
    # markup = '<a href="http://example.com/">I linked to example.com</a>'
    # soup = BeautifulSoup(markup, 'html.parser')
    # print(soup)
    # href = soup.a['href']
    # soup.a.unwrap()
    # print(soup)
    # # soup.p.string.wrap(soup.new_tag("b"))
    # return

    # # print(pasteboard_to_markdown())
    # with open(TEST_HTML_HARD, 'r') as f:
    # # with open(TEST_HTML_EASY, 'r') as f:
    #     html = f.read()
    # print(html_to_markdown(html))
    # with open('cleaned-easy-summary.md', 'r') as f:
    with open('cleaned-hard-summary.md', 'r') as f:
        markdown = f.read()
    markdown_to_thread(markdown)


if __name__ == '__main__':
    # need to run `pbv public.html > whatever.html` on macos to get the full pasteboard saved as an html file
    main()
