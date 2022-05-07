
from typing import List

import requests
from bs4 import BeautifulSoup

import joblib

memory = joblib.Memory('.')

# more feature-complete stuff:
# https://github.com/valayDave/arxiv-miner (handles latex)
#
# https://arxiv.org/help/bulk_data
#   notes:
#   -prefer export.arxiv.org for programmatic access
#   -rate limit to 4 reqs/second
#   -for bulk actions, use their api
#
# using the prefererd but weird OA2 API: https://christinakouridi.blog/2019/06/16/harvesting-metadata-of-1-5million-arxiv-papers/
#   -key is to use https://sickle.readthedocs.io/en/latest/
#   -this interface also works for dozens of other paper repos

URL_PRUNING_SURVEY = 'https://arxiv.org/abs/2003.03033'
URL_MADDNESS = 'https://arxiv.org/abs/2106.10860'
URL_ONE_AUTHOR = 'https://arxiv.org/abs/2205.02803'


@memory.cache
def _download_html(url: str):
    return requests.get(url).content


def _extract_title(arxiv_abs_soup: BeautifulSoup) -> str:
    # note: some other crap, like "contact arXiv" is also wrapped in <title>
    title_elem = arxiv_abs_soup.find('title')
    title = title_elem.contents[0]
    if ']' in title:  # should start with [####.#####]
        title = title[title.find(']') + 1:]
    title = title.strip()
    return title


def _extract_authors(arxiv_abs_soup: BeautifulSoup) -> List[str]:
    authors_div = arxiv_abs_soup.find_all(class_='authors')
    assert len(authors_div) == 1  # fail fast if unexpected html structure
    authors_div = authors_div[0]
    anchors = authors_div.find_all('a')
    author_names = [anchor.contents[0].strip() for anchor in anchors]
    return author_names

def _extract_abstract(arxiv_abs_soup: BeautifulSoup) -> str:
    abstract_div = arxiv_abs_soup.find('blockquote')
    return abstract_div.contents[-1].strip()


def scrape_arxiv_abs_page(url: str):
    if 'export.arxiv.org' not in url:
        url = url.replace('arxiv.org', 'export.arxiv.org')
    html = _download_html(url)
    soup = BeautifulSoup(html, 'html.parser')

    # ================================ begin not-officially-supported scraping

    title = _extract_title(soup)
    authors = _extract_authors(soup)
    abstract = _extract_abstract(soup)

    print(f'title:\n{title}')
    print(f'authors:\n{authors}')
    print(f'abstract:\n{abstract}')


if __name__ == '__main__':
    scrape_arxiv_abs_page(URL_PRUNING_SURVEY)
    # scrape_arxiv_abs_page(URL_ONE_AUTHOR)
