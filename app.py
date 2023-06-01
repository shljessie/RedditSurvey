from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
import re
from werkzeug.utils import secure_filename
from datetime import datetime
from dotenv import load_dotenv
from praw.models import MoreComments
import praw
import pandas as pd
from collections import Counter
import base64
from urllib.parse import unquote
from googleapiclient import discovery
import json
import random

load_dotenv()

app = Flask(__name__)
app.secret_key = '1234'

reddit = praw.Reddit(
    client_id= os.getenv('CLIENT_ID'),
    client_secret=os.getenv('SECRET_KEY'),
    user_agent=os.getenv('USER_AGENT'),
)

PERSPECTIVE_API_KEY = os.getenv('PERSPECTIVE_API_KEY')

# Establish a connection to the SQLite database
conn = sqlite3.connect('./data/database.db', check_same_thread=False)
app.config['UPLOAD_FOLDER'] = './data/upload_csv'


def create_user_folder(username):
    folder_path = os.path.join("data", username)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print("User folder created successfully.")
    else:
        print("User folder already exists.")

def create_user_survey_folder(username):
    folder_path = os.path.join("data", username,"survey_response")

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print("User folder created successfully.")
    else:
        print("User folder already exists.")

def find_most_recent_file(upload_folder):
    files = [f for f in os.listdir(upload_folder) if os.path.isfile(os.path.join(upload_folder, f))]
    files = [f for f in files if re.match(r"\d{4}_\d{2}_\d{2}_\d{2}:\d{2}:\d{2}", f)]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(upload_folder, x)), reverse=True)

    if files:
        most_recent_file = files[0]
        return most_recent_file

    return None

def extract_all_comments(post_url):
    submission = reddit.submission(url=post_url)

    if len(submission.comments.list()) > 1:
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
                print('Opened all comments for post:', submission.title)
            comments = comments.list()
            break

    # Get all comments
    all_comments = [comment.body for comment in comments]
    return all_comments


def process_comments(most_recent_file):
    record = pd.read_csv(most_recent_file)
    unique_post_urls = record['reddit_post'].dropna().unique()

    all_comments = []
    for url in unique_post_urls:
        all_comments += extract_all_comments(url)

    seen_comments = record['comment_body_encoded'].tolist()

    # Decode seen comments and remove NaN values
    seen_comments = [
        unquote(base64.b64decode(comment.encode('utf-8')).decode('utf-8'))
        for comment in seen_comments
        if str(comment) != 'nan'
    ]

    unseen_comments = list((Counter(all_comments) - Counter(seen_comments)).elements())

    return all_comments, seen_comments, unseen_comments

def generate_combinations(grouped):
    combinations = [(False, False), (False, True), (True, False), (True, True)]

    random_combinations = random.sample(combinations, k=2)

    groups = []
    for combination in random_combinations:
        if combination in grouped.groups:
            group = grouped.get_group(combination)
            comments_column = group['comments']
            random_comment = random.choice(comments_column.values)
            groups.append(random_comment)
    return groups[0], groups[1]

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uuid = request.form['uuid']
        username = request.form.get('username', '') 
        error = None

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE uuid = ? AND username = ?", (uuid, username))
        user = cursor.fetchone()

        if user:
            create_user_folder(username)
            session['username'] = username
            return redirect('/dashboard')
        else:
            error = "Invalid UUID or username. Please try again."
            return render_template('login.html', error=error)

    return render_template('login.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        username = session.get('username')

        if 'csv_file' not in request.files:
            error = 'No file uploaded.'
            return render_template('dashboard.html', error=error)

        file = request.files['csv_file']

        if file.filename == '':
            error = 'No file selected.'
            return render_template('dashboard.html', error=error)

        if not file.filename.endswith('.csv'):
            error = 'Invalid file format. Please upload a CSV file.'
            return render_template('dashboard.html', error=error)

        upload_folder = os.path.join("data", username, "scraped_comments")
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        timestamp = datetime.now().strftime("%Y_%m_%d_%H:%M:%S")
        filename = f"{timestamp}.csv"

        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        success = 'File uploaded successfully.'
        return render_template('dashboard.html', success=success)

    return render_template('dashboard.html')

@app.route('/generate', methods=['GET', 'POST'])
def generate_survey():
    if request.method == 'POST':
        username = session.get('username')
        upload_folder = os.path.join("data", username, "scraped_comments")

        most_recent_file = find_most_recent_file(upload_folder)

        if most_recent_file:
            # seen and unseen
            most_recent_file_path = os.path.join(upload_folder,most_recent_file)
            all_comments, seen_comments, unseen_comments = process_comments(most_recent_file_path)
            data = {'comments': all_comments, 'seen': [comment in seen_comments for comment in all_comments]}

            df = pd.DataFrame(data)

            #toxic
            client = discovery.build(
                    "commentanalyzer",
                    "v1alpha1",
                    developerKey=PERSPECTIVE_API_KEY,
                    discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
                    static_discovery=False,
                    )

            toxicity_scores = []
            for comment in all_comments:
                analyze_request = {
                    'comment': {'text': comment},
                    'requestedAttributes': {'TOXICITY': {}}
                }
                response = client.comments().analyze(body=analyze_request).execute()
                toxicity_score = response['attributeScores']['TOXICITY']['summaryScore']['value']
                toxicity_scores.append(toxicity_score)

            toxicity_labels = [score > 0.5 for score in toxicity_scores]
            df['toxicity'] = toxicity_labels

            # save labeled comments
            folder_path = os.path.join("data", username, "labeled_comments")
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

            file_path = os.path.join(folder_path, "labeled.csv")
            df.to_csv(file_path, index=False)
           

            return render_template('survey.html')
        else:
            return "No data available for survey generation."

    return render_template('survey.html')

@app.route('/survey', methods=['GET', 'POST'])
def genSurvey():
    if request.method == 'POST':
        username = session.get('username')
        create_user_survey_folder(username)

        #call survey final data
        labeled_data = os.path.join("data", username, "labeled_comments","labeled.csv")
        labeled_data = pd.read_csv(labeled_data)

        grouped = labeled_data.groupby(['seen', 'toxicity'])
        # print(grouped.get_group((False,False))['comments'])
        option1, option2= generate_combinations(grouped)
        print('option1', option1)
        print('option2',  option2)
        

    return render_template('survey.html',option1=option1, option2=option2)
    

if __name__ == '__main__':
    app.run(debug=True, port=8080)
