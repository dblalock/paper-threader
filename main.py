
import argparse
from typing import Dict, List, Sequence
from unicodedata import name

import arxiv_utils as arxiv
import paper_threader as pt
import twitter_utils as twit

# def save_followers(username: str):
#     return twit.save_followers(username)


def main() -> None:
    # what are the commands I even want to support here?
    # save_followers: username -> None
    # users_for_paper: abs link -> stdout dump
    # skeleton_for_paper: abs link -> stdout dump
    # pasteboard_to_markdown: out_path -> None
    # preview_markdown_thread: in_path, out_path -> None
    # tweet_markdown: in_path, None

    # ---------------------------------------------- general args / setup
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
        '--save_my_twitter_keys',
        default=False,
        action='store_true',
        help=('Run this to get ACCESS_TOKEN and ACCESS_TOKEN_SECRET to ' +
              'put in a .env file (by default, writes to ' +
              f'{twit.DEFAULT_USER_ENV_PATH}). ' +
              'These are tied to your account and allow posting as you.'),
    )
    parser.add_argument(
        '--user_env',
        default='',
        type=str,
        help=(f'Path to user .env file that specifies credentials for' +
              'the twitter acccount to do stuff as. Only matters for' +
              'creating tweets'),
    )
    parser.add_argument(
        '--for_real',
        default=False,
        action='store_true',
        help=(f'Shorthand to set --user_env to {twit.DEFAULT_USER_ENV_PATH} instead of None'),
    )

    # ------------------------------------------------- commands
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
        '--skeleton_for_paper',
        default='',
        type=str,
        help=('URL of arxiv abstract; writes/prints a markdown file ' +
              'with a bare-bones tweet thread to manually work modify; ' +
              'not to be mixed with auto-tweeting due to duplicate ' +
              'final tweets'),
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
        '--tag_users_in_image_max_tweets',
        default=2,
        type=int,
        help=('Whether to tag authors in the first image. This is a' +
              'nicer tweet to look at, but also gives them a ' +
              'notification for every tweet in the thread. ' +
              'Recommended for short threads. Takes an int, ' +
              "and doesn't tag the users if the thread has more tweets " +
              'than the provided number.'),
    )
    parser.add_argument(
        '--omit_mention_authors',
        default=False,
        action='store_true',
        help=('Omit mentioning authors in final tweet. Helpful for' +
              'awkward situations in which only a small fraction of' +
              'authors are on twitter.'),
    )
    parser.add_argument(
        '--authors_to_mention',
        default='',
        type=str,
        nargs='+',
        help=('A list of authors to mention in the tweet'),
    )

    args = parser.parse_args()
    if args.for_real and not args.user_env:
        args.user_env = twit.DEFAULT_USER_ENV_PATH

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
        twit.save_followers(args.save_followers_of_user)
        return

    if args.users_for_abstract:
        pt.authors_usernames_for_paper(args.users_for_abstract, verbose=True)
        return

    if args.save_my_twitter_keys:
        twit.authenticate_as_another_account()
        return

    if args.pasteboard_to_markdown:
        markdown = pt.pasteboard_to_markdown()
        _save_or_print(markdown)
        return

    if args.skeleton_for_paper:
        url = args.skeleton_for_paper
        title, authors, abstract = arxiv.scrape_arxiv_abs_page(url)
        author_users = pt.find_authors(authors)
        author_usernames = [user.screen_name for user in author_users]
        text = pt.skeleton_for_paper(paper_title=title,
                                     paper_link=url,
                                     author_usernames=author_usernames,
                                     abstract=abstract)
        _save_or_print(text)
        return

    create_tweets_kwargs = dict(
        authors = args.authors_to_mention,
        omit_mention_authors=args.omit_mention_authors,
        tag_users_in_image_max_tweets=args.tag_users_in_image_max_tweets)

    if args.markdown_to_thread_preview:
        if not args.out_path:
            args.out_path = 'preview-' + args.in_path
        markdown = _contents_at_input_path()
        tweets = pt.markdown_to_thread(markdown, **create_tweets_kwargs)
        # print("================================ tweets")
        # for tweet in tweets:
        #     print("----")
        #     print(tweet)
        preview_md = pt.thread_to_markdown_preview(tweets)
        # print(preview_md)
        # print("================================ preview")
        _save_or_print(preview_md)

    if args.tweet_markdown:
        if args.user_env:
            twit.override_env(args.user_env)
        markdown = _contents_at_input_path()
        tweets = pt.markdown_to_thread(markdown, **create_tweets_kwargs)
        # kwargs = {}
        # if len(tweets) > args.tag_users_in_image_max_tweets:
        #     kwargs['tag_users'] = []  # prevent tagging users
        twit.create_thread(tweets)


if __name__ == '__main__':
    main()

