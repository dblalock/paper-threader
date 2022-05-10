
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from typing import List, Optional, Union
from unicodedata import name
from uuid import uuid4

import pandas as pd
import requests
import tweepy
from dotenv import load_dotenv

import joblib

memory = joblib.Memory('.')

# see https://github.com/theskumar/python-dotenv/blob/master/src/dotenv/main.py for docs
load_dotenv(dotenv_path='.env')

DEBUG_ACCOUNT_ID = 1521314141520027648

FOLLOWER_LISTS_DIR = 'follower_lists'

API_KEY = os.environ["API_KEY"]
API_KEY_SECRET = os.environ["API_KEY_SECRET"]
ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["ACCESS_TOKEN_SECRET"]
BEARER_TOKEN = os.environ["BEARER_TOKEN"]


@dataclass
class Tweet:
    text: str
    imgs: List[str] = field(default_factory=list)

    def __str__(self):
        ret = self.text
        for img in self.imgs:
            ret += f'\n - {img[:70]}'
        return ret


def authenticate_v1():
    print("creating tweepy APIv1 client...")
    auth = tweepy.OAuthHandler(API_KEY, API_KEY_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    return tweepy.API(auth, wait_on_rate_limit=True)


def authenticate_v2():
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


def _download_img(url: str, tempdir: str) -> str:
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to load image at url: {url}")
    response.raw.decode_content = True

    filename = url.split("/")[-1]
    saveas = os.path.join(tempdir, filename)
    with open(saveas, 'wb') as f:
        shutil.copyfileobj(response.raw, f)

    return saveas


@memory.cache(ignore=['api'])
def _upload_media(api, filename):
    with tempfile.TemporaryDirectory() as d:
        if filename.startswith('http'):
            filename = _download_img(filename, tempdir=d)
        res = api.chunked_upload(filename)
    return res.media_id


# api v1 impl
@memory.cache(ignore=['api'])
def _get_user(api: tweepy.API, screen_name: str):
    return api.get_user(screen_name=screen_name)


# v2 impl fails with 401 Unauthorized on other people's accounts
# @memory.cache(ignore=['client'])
# def _get_user(client: tweepy.Client, username: str):
#     return client.get_user(username=username)


# def _ensure_user_id(api: tweepy.API, usernames: Optional[List[str]]):
# def _ensure_user_id(client: tweepy.Client, user: Optional[Union[str, int, tweepy.User]]):
def _ensure_user_id(api: tweepy.API, user: Optional[Union[str, int, tweepy.User]]):
    if isinstance(user, tweepy.User):
        return user.id  # user object
    if isinstance(user, int) or re.match('\d', user):
        return user  # already an id

    # let's hope it's a screen name
    return _get_user(api, user).id
    # return _get_user(client, user).id


# we need a v1 client (api) and a v2 client (client) since v1 can't
# tag people in media and v2 can't upload media
def create_tweet(api: tweepy.API,
                 client: tweepy.Client,
                 tweet: Tweet,
                 tag_users: Optional[List[tweepy.User]] = None,
                 in_reply_to_tweet_id: Optional[str] = None,
                #  quote_tweet_url: Optional[str] = None) -> tweepy.Response:
                 quote_tweet_id: str = None,
                 debug_mode: bool = False) -> tweepy.Response:

    media_ids = []
    for img in tweet.imgs:
        media_ids.append(_upload_media(api, img))
    media_ids = media_ids or None

    if tag_users:
        tag_users = [_ensure_user_id(user) for user in tag_users]

    if debug_mode:
        # ensure that tweet is unique
        tweet.text = f'{tweet.text[:200]} {str(uuid4())[:13]}'
        print("gonna create a tweet with text: ", tweet.text)

    try:
        # see here for docs on response body:
        #   https://developer.twitter.com/en/docs/twitter-api/tweets/manage-tweets/api-reference/post-tweets # noqa
        return client.create_tweet(
            text=tweet.text,
            media_tagged_user_ids=tag_users,
            media_ids=media_ids,
            in_reply_to_tweet_id=in_reply_to_tweet_id,
            quote_tweet_id=quote_tweet_id,
            # quote_tweet_id=None,  # TODO rm after debug
            # quote_tweet_id=quote_tweet_url,
        )
    except tweepy.Forbidden as e:
        print("Forbidden error! Did you already tweet this exact tweet?")
        raise(e)


# def create_thread(tweets: List[Tweet], tag_users: Optional[List[tweepy.User]]):
def create_thread(tweets: List[Tweet], tag_users: Optional[List[tweepy.User]] = None, quote_first_tweet_at_end: Union[str, bool] = 'auto', debug_mode: bool = False):
    api = authenticate_v1()
    client = authenticate_v2()

    first_tweet_id = None
    previous_tweet_id = None


    # # TODO rm
    # tweets = [tweets[0]]

    for i, tweet in enumerate(tweets):
        print("----------- i =", i)
        print("tryna tweet:\n", tweet)

        # quote_tweet_url = None
        quote_tweet_id = None
        if i == (len(tweets) - 1) and i > 0:
            assert first_tweet_id is not None, f"no first tweet for last #{i}"
            # quote_tweet_url = f'https://twitter.com/twitter/statuses/{first_tweet_id}'
            quote_tweet_id = first_tweet_id

        ret = create_tweet(api=api,
                           client=client,
                           tweet=tweet,
                           tag_users=tag_users if i == 0 else None,
                           in_reply_to_tweet_id=previous_tweet_id,
                           quote_tweet_id=quote_tweet_id,
                           debug_mode=debug_mode,
                        #    quote_tweet_url=quote_tweet_url,
        )
        print("---- tweet creation response:")
        print(ret)
        previous_tweet_id = ret.data['id']
        # print("tweet id: ", previous_tweet_id)
        if i == 0:
            first_tweet_id = previous_tweet_id


# ================================================= simple analytics

@memory.cache
def get_followers(id_or_screen_name: Union[int, str]) -> List[tweepy.User]:
    """Returns all followers in descending order of their follower count"""
    api = authenticate_v1()
    user_id = _ensure_user_id(api, id_or_screen_name)
    followers = []
    cursor = tweepy.Cursor(api.get_followers,
                           user_id=user_id,
                           count=200)
    sleep_secs = 1
    for page in cursor.pages():
        try:
            followers.extend(page)
            sleep_secs = 1
        except tweepy.TweepError as e:
            print("Going to sleep:", e)
            time.sleep(sleep_secs)
            sleep_secs = min(60, sleep_secs * 2)
    return sorted(followers, key=lambda f: f.followers_count, reverse=True)


def save_followers(id_or_screen_name: Union[int, str]):
    followers = get_followers(id_or_screen_name)

    df = pd.DataFrame.from_records([f._json for f in followers])
    df = df[['followers_count', 'screen_name', 'name', 'description']]
    if not os.path.exists(FOLLOWER_LISTS_DIR):
        os.mkdir(FOLLOWER_LISTS_DIR)
    saveas = os.path.join(FOLLOWER_LISTS_DIR, str(id_or_screen_name) + '.csv')
    df.to_csv(saveas, index=False)


    # follower_tuples = [(f.followers_count, f.screen_name, f.name) for f in followers]

# def followers_for_user(id_or_screen_name: Union[int, str]):
#     # client = authenticate_v2()
#     api = authenticate_v1()
#     user_id = _ensure_user_id(api, id_or_screen_name)
#     followers = api.get_followers(user_id=user_id, count=)


#     # user_id = _ensure_user_id(client, id_or_screen_name)
#     # followers = client.get_users_followers(user_id)

#     # TODO


# ================================================================ debug

def test_download_image():
        with tempfile.TemporaryDirectory() as d:
            path = _download_img('https://i.imgur.com/ExdKOOz.png', tempdir=d)
            assert os.path.isfile(path)
            assert os.path.getsize(path) > 0

            # allow manually inspecting the image before it's wiped
            # print(path)
            # input()


def test_ensure_user_ids():
    api = authenticate_v1()
    ids = [_ensure_user_id(api, user) for user in ('davisblalock', DEBUG_ACCOUNT_ID)]

    # can't use v2 impl due to weird 401 unauthorized
    # client = authenticate_v2()
    # ids = [_ensure_user_id(client, user) for user in ('davisblalock', DEBUG_ACCOUNT_ID)]

    print('ids: ', ids)
    assert str(ids[0]) == '805547773944889344'
    assert str(ids[1]) == str(DEBUG_ACCOUNT_ID)


def main():
    # test_download_image()

    # test_ensure_user_ids()

    # save_followers('moinnadeem')
    # save_followers('AveryLamp')

    # dbg_tweet0 = Tweet(text='dbg tweet part 1', imgs=['https://i.imgur.com/ExdKOOz.png'])
    # dbg_tweet1 = Tweet(text='dbg tweet part 2', imgs=['sunset.jpg'])
    # dbg_tweet2 = Tweet(text='dbg tweet part 3')
    # tweets = [dbg_tweet0, dbg_tweet1, dbg_tweet2]
    # dbg_tag_users = [DEBUG_ACCOUNT_ID]
    # create_thread(tweets=tweets,
    #               tag_users=dbg_tag_users,
    #               debug_mode=True)




    # _download_img('https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2F2d0814a5-9d3d-4d3f-923f-bd8c7bdf10e9_1316x718.png')




if __name__ == '__main__':
    # need to run `pbv public.html > whatever.html` on macos to get the full pasteboard saved as an html file
    main()

