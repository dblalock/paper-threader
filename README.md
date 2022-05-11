# Paper Threader

Because writing twitter threads about papers is really annoying.

Two top-level uses here:

 - Running standalone commands that make life easier, like automatically finding twitter usernames for all the authors of an arxiv paper at once.
 - Enabling you to copy-paste paper summaries from substack or other rich editors (as long as the image URLs are publicly available) and easily tweet them. Or just write in markdown directly.

If you have this post tweets for you, it will:

 - Auto-tag authors in the first image,
 - Chop up your text into tweets (even with nice ellipses when sentences get broken),
 - Auto-number your tweets
 - Add a configurable paper link / author mention / self-promotion tweet at the end
 - Quote tweet the first tweet in thread at the end to facilitate retweeting

tl;dr this is designed to help Davis actually get around to tweeting paper summaries each week, but hopefully will be useful to others.

## Installation

1. Clone this repo and `pip install -r requirements.txt`
2. Install [pbv](https://github.com/chbrown/macos-pasteboard):
```shell
git clone https://github.com/chbrown/macos-pasteboard
cd macos-pasteboard
make install
```
4. Register as a twitter developer, create an app, and request Elevated API access so you can use the v1.1 API. We need this since the v2 API is still incomplete (it can't upload media or search for users).
5. Create a `.env` file in the root directory of the project and add the following content to it (replacing the values by your own keys):
``` shell
API_KEY=<YOUR API_KEY / CONSUMER KEY GOES HERE>
API_KEY_SECRET=<YOUR API_KEY_SECRET / CONSUMER SECRET GOES HERE>
ACCESS_TOKEN=<YOUR ACCESS_TOKEN GOES HERE>
ACCESS_TOKEN_SECRET=<YOUR ACCESS_TOKEN_SECRET GOES HERE>
```
Alternatively, if a '.env' file is provided for you by a twitter developer and you want to post as yourself, run:
`python main.py --save_my_twitter_keys` and you should be good.

You're done!


## Stuff you can do

You should only need to use `main.py` with various args. You can `python main.py -h` for a full list of options.

 <!-- Here's an overview of all the things it can do (just the nicely formatted output `python main.py -h`). -->
<!-- ```
  -h, --help
    show this help message and exit
  -i, --in_path
    path to read from, if applicable
  -o, --out_path
    path to write to, if applicable
  --save_my_twitter_keys
    Run this to get ACCESS_TOKEN and ACCESS_TOKEN_SECRET to put in a .env
    file (by default, writes to .my.env). These are tied to your account
    and allow posting as you.
  --save_followers_of_user
    a twitter username, without the leading "@" to save thefollowers of
    as a csv in follower_lists
  --users_for_abstract
    URL of arxiv abstract; prints info about twitterusers that might
    correspond to the authors
  --skeleton_for_paper
    URL of arxiv abstract; writes/prints a markdown file with a
    bare-bones tweet thread to manually work modify; not to be mixed with
    auto-tweeting due to duplicate final tweets
  --pasteboard_to_markdown
    Tries turning contents of macos clipboard into a markdown file
  --markdown_to_thread_preview
    Turns a markdown file into another md file with hrules where tweet
    boundaries will be with --tweet_markdown
  --tweet_markdown
    Tweets contents of a markdown file as a thread. Use
    --markdown_to_thread_preview to check content first.
``` -->

Here's a walkthrough. First, here's some standalone functionality for making tweet threads easier:

1. You can `python main.py --save_followers_of_user <user>` to have it generate a CSV of all that user's followers in descending order of follower count. Useful for identifying whale followers. `<user>` shouldn't contain the `@`; e.g.' `davisblalock` not `@davisblalock`. This might take a while if the person has a lot of followers.
Example: `python main.py --save_followers_of_user davisblalock`

2. You can `python main.py users_for_abstract <arxiv_abs_url> ` to have it spit out plausible candidate twitter handles for all the authors of an arxiv paper. This is *way* faster than hunting for them all manually
Example:
```
python main.py --users_for_abstract https://arxiv.org/abs/2003.03033
================================ Davis Blalock
------------------------ candidate (score=9):
name:	Davis Blalock
screen_name:	davisblalock
description:	Research scientist @MosaicML. PhD @MIT_CSAIL. I go through all the ML arXiv submissions each week and share my favorites. Newsletter + archive: https://t.co/xX7NIpazHR
followers_count:	968
================================ Jonathan Frankle
------------------------ candidate (score=9):
name:	Jonathan Frankle
screen_name:	jefrankle
description:	Chief Scientist @MosaicML. Faculty-to-be @Harvard. ~PhD @MIT_CSAIL. Cover @RobertTLange. Making deep learning efficient for everyone, algorithmically. Hiring!
followers_count:	5606
```
Note that it finds me and Jonathan Frankle, but not the author coauthors who don't have twitter. It can spit out multiple candidates per name, but the heuristic scoring function I use is surprisingly good at weeding out false positives.

3. It can spit out a partial tweet thread for you as a markdown file. Contains the paper title, abstract, @mentions of all the (best-guess) authors, and a configurable self-promotion block at the end.
Example:
```
$ python main.py --skeleton_for_paper https://arxiv.org/abs/2003.03033 -o pruning-survey-skeleton.md
$ cat less pruning-survey-skeleton.md
What is the State of Neural Network Pruning?
<abstract omitted for brevity>

Paper: https://arxiv.org/abs/2003.03033

If you like this paper, consider RTing this (or another!) thread to publicize the authors' work, or following the authors: @davisblalock @jefrankle

You might like following me or my newsletter for more paper summaries: https://t.co/xX7NIpazHR
```

4. Let's say you go to [Davis's newsletter](https://dblalock.substack.com/p/2022-5-8-opt-175b-better-depth-estimation?s=r) and you want to turn one of the paper summaries into a tweet thread. Copying images over one by one and dealing with chopping stuff into 280-char segments is super annoying. After highlighting the content you want and copying it (just regular old cmd-C), you can run:
`python main.py --pasteboard_to_markdown -o whatever_name.md`. This pulls down all the images and text into a reasonable-looking markdown file suitable for the commands we'll describe next.

5. If you have a markdown file that captures the text and images you want to put into your thread, you can run:
`python main.py --markdown_to_thread_preview -i whatever_name.md -o preview_whatever_name.md` to get a new visualization (as a markdown file) of how the content will get auto-chopped into tweets using our final command (below). Tweets are separated by hrules. Any markdown preview plugin should let you see all the images.

6. Once you have a source markdown file (not the preview!) whose preview you're happy with, you can
`python main.py --tweet_markdown -i whatever_name.md`
to tweet as the account is specified in `.env`. To tweet as your own account after doing `python main.py --save_my_twitter_keys`, instead do:
```
python main.py --tweet_markdown -i whatever_name.md
```
This will tweet as you, so be ready.

Note that you can skip step 4, the clipboard one, and just use this repo as a way to turn markdown files into polished twitter threads.


## Configuring stuff

You can change the contents of `final-tweet-format-no-authors.txt` and `final-tweet-format-with-authors` to mess with the author list + self-promoting content at the end of the thread. There are two different files so that it doesn't look awkward when no author usernames are found. Think "Finally, consider following the authors: (tweet just ends)".

To manually specify the authors mentioned in a tweet thread, rather than scraping them from the first arxiv link found in the body of the source markdown, you can add the following to the source markdown:
```
TAG_USERS: @davisblalock @dblalock_debug
```
or whatever other usernames you'd like. Leading '@' signs are optional. This is useful for overriding the default username inferences if one or more are incorrect, as well as for debugging.
