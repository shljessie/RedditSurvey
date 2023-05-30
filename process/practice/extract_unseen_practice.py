"""
Extract Unseen Comments from Reddit

Comment Extraction with PRAW documentation : https://praw.readthedocs.io/en/stable/getting_started/quick_start.html#authorized
"""
import os
from dotenv import load_dotenv
from praw.models import MoreComments
import praw

load_dotenv()

#creating a readonly Reddit instance: https://praw.readthedocs.io/en/stable/getting_started/quick_start.html#read-only
reddit = praw.Reddit(
    client_id= os.getenv('CLIENT_ID'),
    client_secret=os.getenv('SECRET_KEY'),
    user_agent=os.getenv('USER_AGENT'),
)

#If you are only analyzing public comments, entering a username and password is optional.
#Will we need to extract private comments? --> are private comments commentsin private subreddits? check..
#If so, we need to create public instance

#output true
# print(reddit.read_only)

# obtain a submission object
# for submission in reddit.subreddit("test").hot(limit=10):
#     print(submission.title)

# subreddit = reddit.subreddit("redditdev")


#obtain submission object with url
#https://stackoverflow.com/questions/17430409/in-praw-im-trying-to-print-the-comment-body-but-what-if-i-encounter-an-empty
url = "https://www.reddit.com/r/redditdev/comments/idkcm1/praw_why_im_getting_attributeerror_morecomments/"
submission = reddit.submission(url=url)

print(len(submission.comments.list()))
if(len(submission.comments.list()) > 1):
  i = 1
  while True:
    comments = submission.comments
    print('last comment')
    print(comments[-1])
    print('Replace more and show last')
    try:
      print(comments.replace_more()[-1])
      print('Opening more comments...')
    except:
      print('Opened all comments for post: ', submission.title)
    comments = comments.list()
    break

#get all comments
all_comments=[]
for comment in comments:
  all_comments.append(comment.body)
  # print(comment.body)

print('All Comments',all_comments)
#might need to do some preprocessing depending on what the extracted comments look like


# Extract unseen
