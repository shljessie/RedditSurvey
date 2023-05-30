import os
from dotenv import load_dotenv
from praw.models import MoreComments
import praw
import pandas as pd
from collections import Counter
import base64
from urllib.parse import unquote

load_dotenv()

reddit = praw.Reddit(
    client_id= os.getenv('CLIENT_ID'),
    client_secret=os.getenv('SECRET_KEY'),
    user_agent=os.getenv('USER_AGENT'),
)

def extractAllComments(post_url):
  url= post_url
  submission = reddit.submission(url=url)

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
  
  return all_comments


record = pd.read_csv('../data/upload_csv/reddit_comment_history_1.csv')

unique_post_urls = record['reddit_post'].dropna().unique()
# print('check',len(unique_post_urls))

all_comments=[]
for url in unique_post_urls:
  all_comments += extractAllComments(url) 

seen_comments = record['comment_body_encoded'].tolist()

#subtract seen_comments from all comments
#not correct! still working on it! (just made the format!)
# print(all_comments)
# print(base64.b64decode(seen_comments))



# for comment in seen_comments:
#   print(type(comment))
#   print(comment)

## utf decoding not working properly, otherwise good!
seen_comments = [unquote(base64.b64decode(comment.encode('utf-8')).decode('utf-8')) for comment in seen_comments if str(comment) != 'nan']
print(seen_comments)
unseen_comments = list((Counter(all_comments) - Counter(seen_comments)).elements())
print('unseenComments: ',unseen_comments)

# save the seen and unseen comments to a database and label them.
# final database
# list comments to database 
# save seen labeeld comments to final
# save unseen labeled comments to final
# you need t



