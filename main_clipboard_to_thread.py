
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Tuple

import bs4
import mistletoe as mt  # md -> thread
from bs4 import BeautifulSoup
from markdownify import markdownify as md  # html -> md

# from bs4 import BeautifulSoup


TEST_HTML_EASY = 'test-summary-easy.html'
TEST_HTML_HARD = 'test-summary-hard.html'


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

class Node:

    def __init__(tag: str):
        pass


def markdown_to_thread(markdown: str):

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
    print(paper_title)
    print(paper_link)
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
            print(text)
            tweet_elems.append(TextElem(text=text))
        if node.name == 'img':
            # print(node['src'])
            tweet_elems.append(ImgElem(url=node['src']))

            # print(node.string)
        # else:
        #     print(type(node))
        # print(node)

    print("================================ Tweet elems:")
    for elem in tweet_elems:
        print(elem)

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





def thread_to_markdown(inp: Any) -> str:
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

    # string = '[![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2F2d0814a5-9d3d-4d3f-923f-bd8c7bdf10e9_1316x718.png)](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2F2d0814a5-9d3d-4d3f-923f-bd8c7bdf10e9_1316x718.png)'
    # # # [![]($1)](*) -> ![]($1)
    # # print(re.sub('\[', '{', string))
    # # print(re.sub('\]', r'}', string))
    # # print(re.sub('\[\]', r'{}', string))
    # # print(re.sub('\[\!\[\]\(', r'FOO', string))
    # # print(re.sub('\[\!\[\]\([^)]*\)', r'FOO', string))
    # # print(re.sub('\[\!\[\]\([\S]*\)', r'FOO', string))
    # # prefix = re.escape('[![](')
    # # prefix = re.escape('[![]([\S])]([\S])')
    # # prefix = re.escape('[![](')
    # # prefix = '\[\!\[\]\([\S]*\)'  # matches whole expr
    # prefix = '\[\!\[\]\(([\S]*)\)\]\([\S]*\)'  # matches whole expr

    # # print(re.sub(prefix, 'FOO', string))
    # # print(re.sub(prefix, r'![](\1)', string))
    # # print(re.sub('\[\!\[\]\(([\S]*)\)\]\([\S]*\)', r'![](\1)', string))
    # # print(re.sub('\[\!\[\]\(([\S]*)\)\]\([\S]*\)', r'![](\1)', string + '\n' + string))
    # string = re.sub(re.escape('[![]('), '\n[![](', string)
    # print(re.sub('\[\!\[\]\(([\S]*)\)\]\([\S]*\)', r'![](\1)', string + string))
    # # pattern = re.escape('[![](([\S]*))]([\S]*)')
    # # print(re.sub(pattern, r'![](\1)', string + '\n' + string))
    # # print(re.sub(prefix + '\(([\S])\)', '\!\[\]\(foo\)', string))
    # # print(re.sub(re.escape('[![](') + '\[\S\]*\)', '\!\[\]\(foo\)', string))
    # print(re.sub('\[\!\[\]\([\S]*\)', r'FOO', string))
    # print(re.sub('\[\!\[\]([^)]*)]([^)]*)', r'FOO', string))



    # soup = BeautifulSoup(html, 'html.parser')
    # print(soup.prettify())

if __name__ == '__main__':
    # need to run `pbv public.html > whatever.html` on macos to get the full pasteboard saved as an html file
    main()
