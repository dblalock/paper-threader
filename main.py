
import argparse
from typing import Dict, List, Sequence
from unicodedata import name

import tweepy

import arxiv_utils as arxiv
import paper_threader as pt
import twitter_utils as twit


def _print_user(user: tweepy.User):
    user_attrs = [
        'id',           # unambiguous int unique to each user
        'name',         # arbitrary text listed as their name
        'screen_name',  # user's handle is @{screen_name}
        'description', # bio
        'followers_count',
    ]
    for attr in user_attrs:
        print(f'{attr}:\t{getattr(user, attr)}')


def _find_authors(authors: Sequence[str], verbose: bool = False) -> List[tweepy.User]:
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


def authors_for_paper(url: str) -> List[tweepy.User]:
    _, authors, _ = arxiv.scrape_arxiv_abs_page(url)
    return _find_authors(authors, verbose=True)


def save_followers(username: str):
    return twit.save_followers(username)


def main() -> None:
    # what are the commands I even want to support here?
    # save_followers: username -> None
    # users_for_paper: abs link -> stdout dump
    # skeleton_for_paper: abs link -> stdout dump
    # pasteboard_to_markdown: out_path -> None
    # preview_markdown_thread: in_path, out_path -> None
    # tweet_markdown: in_path, None

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i',
        '--in_path',
        type=str,
        default='',
        help='path to read from, if applicable',
    )
    parser.add_argument(
        '-o',
        '--out_path',
        type=str,
        default='',
        help='path to write to, if applicable',
    )
    parser.add_argument(
        '--save_followers_of_user',
        type=str,
        default='',
        help=('a twitter username, without the leading "@" to save the' +
              f'followers of as a csv in {twit.FOLLOWER_LISTS_DIR}'),
    )
    parser.add_argument(
        '--users_for_abstract',
        type=str,
        default='',
        help=('URL of arxiv abstract; prints info about twitter' +
              f'users that might correspond to the authors'),
    )
    parser.add_argument(
        '--print_my_twitter_keys',
        default=False,
        action='store_true',
        help=('Run this to get API_KEY and API_SECRET to put in .env; ' +
              'These are tied to your account and allow posting as you.'),
    )
    parser.add_argument(
        '--pasteboard_to_markdown',
        default=False,
        action='store_true',
        help='Tries turning contents of macos clipboard into a markdown file',
    )
    parser.add_argument(
        '--markdown_to_thread_preview',
        default=False,
        action='store_true',
        help=('Turns a markdown file into another md file with hrules ' +
              'where tweet boundaries will be with --tweet_markdown'),
    )
    parser.add_argument(
        '--tweet_markdown',
        default=False,
        action='store_true',
        help=('Tweets contents of a markdown file as a thread. Use ' +
              '--markdown_to_thread_preview to check content first.'),
    )
    parser.add_argument(
        '--skeleton_for_paper',
        default='',
        type=str,
        help=('URL of arxiv abstract; writes/prints a markdown file ' +
              'with a bare-bones tweet thread to manually work modify'),
    )


    args = parser.parse_args()

    def _contents_at_input_path() -> str:
        with open(args.in_path) as f:
            contents = f.read()
        return contents

    def _save_or_print(s: str) -> None:
        if args.out_path:
            with open(args.out_path, 'w') as f:
                f.write(s)
        else:
            print(s)

    if args.save_followers_of_user:
        save_followers(args.save_followers_of_user)
        return

    if args.users_for_abstract:
        authors_for_paper(args.users_for_abstract)
        return

    if args.print_my_twitter_keys:
        twit.authenticate_as_another_account()
        return

    if args.pasteboard_to_markdown:
        markdown = pt.pasteboard_to_markdown()
        _save_or_print(markdown)
        return

    if args.skeleton_for_paper:
        url = args.skeleton_for_paper
        title, authors, abstract = arxiv.scrape_arxiv_abs_page(url)
        author_users = _find_authors(authors)
        author_usernames = [user.screen_name for user in author_users]
        text = pt.skeleton_for_paper(paper_title=title, paper_link=url, author_usernames=author_usernames, abstract=abstract)
        _save_or_print(text)

    if args.markdown_to_thread_preview:
        markdown = _contents_at_input_path()
        tweets = pt.markdown_to_thread(markdown)
        # print("================================ tweets")
        # for tweet in tweets:
        #     print("----")
        #     print(tweet)
        preview_md = pt.thread_to_markdown_preview(tweets)
        # print(preview_md)
        # print("================================ preview")
        _save_or_print(preview_md)

    # TODO pick up here by getting this working
    if args.tweet_markdown:
        markdown = _contents_at_input_path()
        tweets = pt.markdown_to_thread(markdown)
        twit.create_thread(tweets)


if __name__ == '__main__':
    main()

