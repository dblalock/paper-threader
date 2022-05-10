import os
from dataclasses import dataclass, field
from typing import List, Optional

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
    pass # TODO download image to a temporary file


@memory.cache(ignore=['api'])
def _upload_media(api, filename):
    # TODO if it's a url, download it so that we can upload it
    res = api.chunked_upload(filename)
    return res.media_id



def create_tweet(client: tweepy.Client, tweet: Tweet, tag_users: Optional[List[tweepy.User]]):

    media_ids = []
    for img in tweet.imgs:
        media_ids.append(0) # TODO actually upload the file
    media_ids = media_ids or None

    client.create_tweet(text='hello again twitter API with tagging',
                        media_tagged_user_ids=tag_users,
                        media_ids=media_ids)


def create_thread(client: tweepy.Client, tweet: Tweet, tag_users: Optional[List[tweepy.User]]):
    pass
