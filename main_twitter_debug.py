
# tweepy reference with twitter API v1.1 (different from v2!)
#   https://docs.tweepy.org/en/latest/api.html
# tweepy reference with twitter aPI v2:
#   https://docs.tweepy.org/en/latest/client.html

# harder to do stuff as another user:
#   https://developer.twitter.com/en/docs/authentication/overview
#   "If you would like to make requests on behalf of another user, you will need to generate a separate set of Access Tokens for that user using the 3-legged OAuth flow, and pass that user's tokens with your OAuth 1.0a User Context or OAuth 2.0 user context requests."
#
# looks like I need oath 1.0a user context or oath 2.0 with pkce to
# post tweets:
#   https://developer.twitter.com/en/docs/authentication/guides/v2-authentication-mapping
# note: v1 GET users/search (tweepy search_users) has no v2 replacement:
#   https://developer.twitter.com/en/docs/twitter-api/migrate/twitter-api-endpoint-map
#
# looks like what I want is:
#   1) to just use one dev account with "elevated"  access so it can
#       upload images and search users,
#   2) PIN-based OAuth to allow other people to authorize this app

import os
from typing import Dict, Sequence

import tweepy
from dotenv import load_dotenv

import joblib

memory = joblib.Memory('.')

# see https://github.com/theskumar/python-dotenv/blob/master/src/dotenv/main.py for docs
load_dotenv(dotenv_path='.env')


API_KEY = os.environ["API_KEY"]
API_KEY_SECRET = os.environ["API_KEY_SECRET"]
ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["ACCESS_TOKEN_SECRET"]
BEARER_TOKEN = os.environ["BEARER_TOKEN"]


DEBUG_ACCOUNT_ID = 1521314141520027648
MY_ACCOUNT_ID = 805547773944889344


def authenticate_v1():
    # v1 impl for only public stuff
    # auth = tweepy.OAuth2BearerHandler(BEARER_TOKEN)
    # return tweepy.API(auth, wait_on_rate_limit=True)

    # v1 impl for full access
    print("creating tweepy APIv1 client...")
    auth = tweepy.OAuthHandler(API_KEY, API_KEY_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    return tweepy.API(auth, wait_on_rate_limit=True)


def authenticate_v2():
    # v2 impl; only lets you query public stuff?
    # return tweepy.Client(BEARER_TOKEN)
    # v2 impl that lets you act as your developer account
    # NOTE: you need to go into the settings for your app, enable oath1,
    # and set your permission to "read and write". You might need to put
    # some random url in the allowed redirects field to make the form
    # happy
    print("creating tweepy APIv2 client...")
    return tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_KEY_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET,
    )

def authenticate_as_another_account():
    oauth1_user_handler = tweepy.OAuth1UserHandler(
        API_KEY,
        API_KEY_SECRET,
        callback="oob",
    )
    print("Please go to this URL to enable this app, then enter the PIN:")
    print(oauth1_user_handler.get_authorization_url())
    pin = input("Input PIN: ")
    access_token, access_token_secret = oauth1_user_handler.get_access_token(pin)
    print("here are your access token and access token secret:")
    print('access_token', access_token)
    print('access_token_secret', access_token_secret)
    print("you can modify the script to just use these by default")
    print("by modifying the .env file. Or so I assume.")
    oauth1_user_handler.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    return tweepy.API(oauth1_user_handler, wait_on_rate_limit=True)


@memory.cache
def _search_users(api: tweepy.API, *args, **kwargs):
    return api.search_users(*args, **kwargs)


def smoketest_v1():
    # need elevated access to user API v1
    api = authenticate_v1()
    # print(api.get_user(user_id='1521314141520027648')) # debug account

    users = _search_users(api, q='Davis Blalock', page=0, count=10)
    # users = _search_users(api, q='Jonathan Frankle', page=0, count=10)
    # users = _search_users(api, q='MosaicML', page=0, count=10)
    print_attrs = [
        'id',           # unambiguous int unique to each user
        'id_str',       # same as id but as a str
        'name',         # arbitrary text listed as their name
        'screen_name',  # user's handle is @{screen_name}
        'description', # bio
        'followers_count',
        'friends_count',  # how many people user is following
        'statuses_count', # number of tweets
    ]
    for user in users:
        print('------------------------')
        for attr in print_attrs:
            print(f'{attr}:\t{getattr(user, attr)}')
        # print(user.name, user.screen_name, user.description, user.followers_count, user.friends_count, user.statuses_count)


def smoketest_v2():
    client = authenticate_v2()
    # this should print something like:
    # Response(data=<User id=<long int> name=Debugging
    #    username=dblalock_debug>, includes={}, errors=[], meta={})
    print(client.get_me())


def _upload_media(api, filename):
    # welp, looks like there's no way to upload media in v2,
    # which means you need "elevated" access just to upload an image
    # https://twittercommunity.com/t/how-to-show-an-image-in-a-v2-api-tweet/163169/5
    # it's on the public roadmap but with no apparent progress or anyone
    # working on it
    #
    # also, according to same thread, only oathv1 works with v1, so
    # don't bother with oathv2
    res = api.chunked_upload(filename)

    # to add tags to media in v1.1, maybe we want tweet['entities']['user_mentions']
    #   -https://developer.twitter.com/en/docs/twitter-api/migrate/data-formats/standard-v1-1-to-v2
    #   -although kinda seems like this just isn't a thing in v1.1

    return res.media_id


@memory.cache
def smoketest_upload_media():
    # EDIT: only v1 api can upload media
    api = authenticate_v1()
    media_id = _upload_media(api, 'sunset.jpg')
    print("media_id:", media_id)


def smoketest_check_media():
    pass  # nvm, there's no API call to check on media by ID


def smoketest_create_tweet():
    MEDIA_ID = 1522804228418269184

    # prefer v2 for easier tweet creation + tagging of people, and so
    # that non-Elevated dev accounts can use this
    client = authenticate_v2()

    print("creating tweet...")
    # NOTE: a lot of people don't have photo tagging enabled (or at least
    # I don't...?) so tagging in media is flaky. Will just silently not
    # tag them if that's the case.
    # UPDATE: ya, works great when I go in my settings an enable photo
    # tagging. So this is in fact a settings thing. Looks like only
    # @mentioning people will work robustly
    client.create_tweet(text='hello again twitter API with tagging',
                        media_tagged_user_ids=[DEBUG_ACCOUNT_ID, MY_ACCOUNT_ID],
                        media_ids=[MEDIA_ID])


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


def smoketest_find_authors(authors: Sequence[str], verbose: bool = True) -> Dict[str, tweepy.User]:
    api = authenticate_v1()

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
        users = _search_users(api, q=author, page=0, count=10)
        for user in users:
            score = 0
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
            if score > 1:  # needs more than just name matching
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

    return author2user





def main():
    # smoketest_v1()
    # smoketest_v2()
    # authenticate_as_another_account()
    # smoketest_upload_media()
    # smoketest_create_tweet()
    # smoketest_find_authors(['davis blalock', 'jonathan frankle'])
    smoketest_find_authors(['davis blalock', 'divya shanmugam', 'john guttag', 'michael carbin'])



if __name__ == '__main__':
    main()
