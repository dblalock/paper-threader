
import math
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any, List, Tuple, Union

import bs4
import mistletoe as mt  # md -> thread
import numpy as np
from bs4 import BeautifulSoup
from markdownify import markdownify as md  # html -> md

import arxiv_utils

TEST_HTML_EASY = 'test-summary-easy.html'
TEST_HTML_HARD = 'test-summary-hard.html'
FINAL_TWEET_FMT_STRING_PATH = 'final-tweet-format.txt'


MAX_TWEET_TEXT_LENGTH = 272  # 280 minus space for " [##/##]"
ELLIPSIS = '…'
MAX_TWEET_TEXT_SNIPPET_LENGTH = MAX_TWEET_TEXT_LENGTH - (2 * len(ELLIPSIS))

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
    # soup = BeautifulSoup(html, features='lxml')
    # paragraphs = soup.find_all('p')

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

    ret = md(html, strip=['b', 'i', 'em', 'span', 'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ol', 'ul'])  # wow, markdownify is magic
    ret = ret.replace('⭐', '')

    # remove links to image wrapping images
    # step 1: ensure each [![]( is on its own line (not sure why needed)
    ret = re.sub(re.escape('[![]('), '\n[![](', ret)
    # step 2: [![]($1)](*) -> ![]($1)
    return re.sub('\[\!\[\]\(([\S]*)\)\]\([\S]*\)', r'![](\1)\n', ret)



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

    # assume first link is paper link
    first_anchor = soup.find('a')
    # print(first_anchor)

    def _unpack_anchor_tag(tag) -> Tuple[str, str]:
        return tag.string, tag['href']

    paper_title, paper_link = _unpack_anchor_tag(first_anchor)
    # print(paper_title)
    # print(paper_link)
    first_anchor.extract()

    # convert other links to raw text (rips out links)
    for a in soup.find_all('a'):
        a.unwrap()

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


@dataclass
class Tweet:
    text: str
    imgs: List[str] = field(default_factory=list)

    def __str__(self):
        ret = self.text
        for img in self.imgs:
            ret += f'\n - {img[:70]}'
        return ret


@dataclass
class PaperTweetThread:
    tweets: List[Tweet]
    tag_users: List[str] = field(default_factory=list)


def _generate_final_tweet_elem(paper_link: str):
    with open(FINAL_TWEET_FMT_STRING_PATH, 'r') as f:
        tail_tweet_format_str = f.read()
    return TextElem(text=tail_tweet_format_str.format(paper_link))


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

        chunk_text = text[:split_at] + ELLIPSIS
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


def _markdown_to_tweet_list(markdown: str) -> Tuple[List[Tweet], str]:
    """Raw conversion of markdown to tweet objects. No thread features"""

    tweet_elems, paper_title, paper_link = _markdown_to_text_img_elems(markdown)
    final_elem = _generate_final_tweet_elem(paper_link)
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
        tweets = [Tweet(text=text) for text in texts]

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

    print("================================ tweets")
    for tweet in all_tweets:
        print(tweet)

    return all_tweets, paper_link



def markdown_to_thread(markdown: str):
    tweets, paper_link = _markdown_to_tweet_list(markdown)

    title, authors, abstract = arxiv_utils.scrape_arxiv_abs_page(paper_link)




def thread_to_markdown_preview(inp: Any) -> str:
    pass


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
