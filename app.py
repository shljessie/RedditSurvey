from flask import Flask, flash, render_template, request, redirect, session
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
import csv
from django.shortcuts import render
from datetime import date

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET_KEY')

reddit = praw.Reddit(
    client_id= os.getenv('CLIENT_ID'),
    client_secret=os.getenv('SECRET_KEY'),
    user_agent=os.getenv('USER_AGENT'),
)

PERSPECTIVE_API_KEY = os.getenv('PERSPECTIVE_API_KEY')
BATCH_SIZE = 10 
# Establish a connection to the SQLite database
conn = sqlite3.connect('./data/database.db', check_same_thread=False)

# @app.before_request
# def login_check():
#     print('login checking')
#     if 'username' not in session:
#         return redirect('/')  # Redirect to the login page


def create_user_folder(username):
    folder_path = os.path.join("data", username)
    upload_path = os.path.join("data", username,"upload_data")

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        if not os.path.exists(upload_path):
             os.makedirs(upload_path)
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

    if len(submission.comments.list()) >= 1:
        while True:
            comments = submission.comments
            print('comments')
            print(comments)
            try:
                print(comments.replace_more()[-1])
                print('Opening more comments...')
            except:
                print('Opened all comments for post:', submission.title)
            comments = comments.list()
            break

    if comments:
        # Get all comments
        all_comments = [comment.body for comment in comments]
        all_comment_authors = [comment.author for comment in comments]

    # Get all comments
    if comments:
        all_comments = [comment.body for comment in comments]
        all_comment_authors = [comment.author for comment in comments]
        return all_comments , all_comment_authors
    else:
        pass

def extract_all_post_info(post_url):
    submission = reddit.submission(url=post_url)
    postauthor = submission.author.name
    postname = submission.title
    subreddit = submission.subreddit

    print('postauthor: ',postauthor)
    print('postname: ',postname)
    print('subreddit: ', subreddit)
    return postname, subreddit, postauthor

def process_comments(most_recent_file):
    record = pd.read_csv(most_recent_file)
    unique_post_urls = record['reddit_post'].dropna().unique()


    all_comments = []
    all_comment_authors =[]
    post_info = ''
    for url in unique_post_urls:
        all_comments , all_comment_authors = extract_all_comments(url)

        postname, subreddit, postauthor = extract_all_post_info(url)
        if all_comments and all_comment_authors is not None:
            all_comments += all_comments
            all_comment_authors += [author.name if author is not None else None for author in all_comment_authors]
            print("AUTHOR: ", all_comment_authors)
            post_info += str(postname) +' on r/'+ str(subreddit) +' by '+ str(postauthor)

    seen_comments = record['comment_body_encoded'].tolist()

    # Decode seen comments and remove NaN values
    seen_comments = [
        unquote(base64.b64decode(comment.encode('utf-8')).decode('utf-8'))
        for comment in seen_comments
        if str(comment) != 'nan'
    ]

    print('SEEN COMMENT:', seen_comments)

    unseen_comments = list((Counter(all_comments) - Counter(seen_comments)).elements())

    return all_comments, all_comment_authors, post_info, seen_comments, unseen_comments

def generate_combinations(grouped):
    combinations = [(False, False), (False, True), (True, False), (True, True)]

    random_combinations = random.sample(combinations, k=2)

    groups = []
    for combination in random_combinations:
        if combination in grouped.groups:
            group = grouped.get_group(combination)
            comments_column = group['comments']

            random_comment = random.choice(comments_column.values)
                    
            post_info = group['post_info'].iloc[0]  # Retrieve the post information from the group
            comment_author = group['comment_authors'].iloc[0]  # Retrieve the comment author from the group

            comment_data = {
                'comment': random_comment,
                'post_info': post_info,
                'comment_author': comment_author
            }
            groups.append(comment_data)
    return groups[0], groups[1]

def saveResults(options,selected_option, username):
    folder_path = os.path.join("data", username, "survey_response")
    current_date = date.today().strftime("%Y-%m-%d")
    file_path = os.path.join(folder_path, f"{current_date}.csv")
    
    # Check if the CSV file already exists
    if not os.path.isfile(file_path):
        # Create the file with the header
        with open(file_path, mode='w', newline='') as csvfile:
            fieldnames = ['Options','Selected Option']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    # Append the selected option to the CSV file
    with open(file_path, mode='a', newline='') as csvfile:
        fieldnames = ['Options','Selected Option']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow({'Options': options})
        writer.writerow({'Selected Option': selected_option})

    print("Results saved successfully!")

def saveSurveyResponseToCSV(response, username):
    print('Saving Demographic Survey')
    folder_path = os.path.join("data", username, "survey_response")
    file_path = os.path.join(folder_path, "demographic.csv")
    
    fieldnames = list(response.keys())

    with open(file_path, 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow(response)

@app.route('/', methods=['GET', 'POST'])
def login():
    session.clear()
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
            print('here')
            return redirect('/inform')
        else:
            error = "Invalid UUID or username. Please try again."
            return render_template('login.html', error=error)

    return render_template('login.html')

@app.route('/inform', methods=['GET', 'POST'])
def inform():
    username = session.get('username')
    print(username)
    if username:
        return render_template('inform.html')
    else:
        return redirect('/')
    


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    username = session.get('username')
    if username:
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

        success = True
        return render_template('dashboard.html', success=success)
    success = False
    return render_template('dashboard.html',success=success)

@app.route('/generate', methods=['GET', 'POST'])
def generate_survey():
    username = session.get('username')
    if username:
        upload_folder = os.path.join("data", username, "scraped_comments")

        most_recent_file = find_most_recent_file(upload_folder)

        if most_recent_file:
            # seen and unseen
            most_recent_file_path = os.path.join(upload_folder,most_recent_file)
            all_comments, all_comment_authors, post_info, seen_comments, unseen_comments = process_comments(most_recent_file_path)
            data = {'comment_authors': all_comment_authors,'post_info': post_info, 'comments': all_comments, 'seen': [comment in seen_comments for comment in all_comments]}

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
            all_scores =[]
            # https://developers.perspectiveapi.com/s/about-the-api-attributes-and-languages?language=en_US
            for comment in all_comments:
                
                analyze_request = {
                    'comment': {'text': comment},
                      "requestedAttributes": {
                                                "TOXICITY": {},
                                                "SEVERE_TOXICITY": {},
                                                "IDENTITY_ATTACK": {},
                                                "INSULT":{},
                                                "PROFANITY": {},
                                                "THREAT": {},
                                                "SEXUALLY_EXPLICIT": {},
                                                "FLIRTATION": {}
                                                }
                }

                response = client.comments().analyze(body=analyze_request).execute()
                # print(response)
                scores=[]
            
                for i in response['attributeScores'].keys():
                    score = response['attributeScores'][i]['summaryScore']['value']
                    scores.append(score)
                
                all_scores.append(scores)
                toxicity_score = response['attributeScores']['TOXICITY']['summaryScore']['value']
                toxicity_scores.append(toxicity_score)

            toxicity_labels = [score > 0.5 for score in toxicity_scores]
            df['toxicity'] = toxicity_labels
            df['all'] = all_scores

            # save labeled comments
            folder_path = os.path.join("data", username, "labeled_comments")
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

            file_path = os.path.join(folder_path, "labeled.csv")
            df.to_csv(file_path, index=False)
           

            return redirect('/survey')
        else:
            return "No data available for survey generation."
    else:
        flash('You are not logged in. Please login and try again.', 'error')
        return redirect('/')

@app.route('/survey', methods=['GET', 'POST'])
def genSurvey():
    username = session.get('username')
    # removing for now, perspective api limit reached
    if username:
        click_counter = session.get('click_counter')
        if click_counter is None:
            click_counter = 1
        else:
            click_counter += 1
        session['click_counter'] = click_counter
        username = session.get('username')
        create_user_survey_folder(username)

        #call survey final data
        labeled_data = os.path.join("data", username, "labeled_comments","labeled.csv")
        labeled_data = pd.read_csv(labeled_data)

        grouped = labeled_data.groupby(['seen', 'toxicity'])
        option1, option2= generate_combinations(grouped)

        # Call your function to save the results        
        options= [option1,option2]
        selected_option = request.form.get('option')
        saveResults(options,selected_option, username)  

        if session['click_counter'] == 11:
            session['click_counter'] = None
            return redirect('/demosurvey')

        return render_template('survey.html',option1=option1, option2=option2, click_counter = click_counter)
    else:
        flash('You are not logged in. Please login and try again.', 'error')
        return redirect('/')
        
@app.route('/demosurvey', methods=['GET','POST'])
def genDemoSurvey():

    age_options = ['18-24 years old', '25-34 years old', '35-44 years old', '45-54 years old',
                   '55-64 years old', '65-74 years old', '75 years or older', 'Prefer not to answer',
                   'Other']
    gender_options = ['Woman', 'Man', 'Non-binary', 'Prefer not to answer', 'Prefer to self-describe']
    ethnicity_options = ['White', 'Hispanic or Latino', 'Black or African American',
                         'Native American or American Indian', 'Asian/Pacific Islander',
                         'Prefer not to answer']
    education_options = ['No schooling completed', 'Nursery school to 8th grade', 'Some high school, no diploma',
                         'High school graduate, diploma, or equivalent', 'Some college but no degree',
                         'Associate degree', 'Bachelor’s degree', 'Master’s degree', 'Professional degree',
                         'Doctorate degree', 'Prefer not to answer']

    # social media use time 
    # average screen time 
    # 

    # Pass the options to the HTML template
    
    return render_template('demosurvey.html', age_options=age_options, gender_options=gender_options,
                           ethnicity_options=ethnicity_options, education_options=education_options)

@app.route('/demosubmit', methods=['GET','POST'])
def demosubmit():
    print('Submitting DEMO Survey')
    username = session.get('username')
    if username:
        # Get the submitted form data
        age = request.form.get('age')
        gender = request.form.get('gender')
        ethnicity = request.form.get('ethnicity')
        education = request.form.get('education')
        option1 = request.form.get('option1')
        option2 = request.form.get('option2')
        selected_option = request.form.get('selected_option')

        # Check if gender is 'other' and get the other_gender value
        if gender == 'other':
            gender = request.form.get('other_gender')
        else:
            gender = gender

        # Check if ethnicity is 'other' and get the other_ethnicity value
        if ethnicity == 'other':
            ethnicity = request.form.get('other_ethnicity')
        else:
            ethnicity = ethnicity

        # Create a dictionary to store the survey response
        response = {
            'Age': age,
            'Gender': gender,
            'Ethnicity': ethnicity,
            'Education': education,
            'Option1': option1,
            'Option2': option2,
            'SelectedOption': selected_option
        }

        saveSurveyResponseToCSV(response, username)

        return render_template('done.html')
    else:
        # Redirect if not logged in
        flash('You are not logged in. Please login and try again.', 'error')
        return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, port=8078)
