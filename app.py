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
import multiprocessing as mp
from multiprocessing import Pool 
import ast


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
conn = sqlite3.connect('./data/database.db', check_same_thread=False)

def create_user_folder(uuid):
    folder_path = os.path.join("data", uuid)
    upload_path = os.path.join("data", uuid,"upload_data")

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        if not os.path.exists(upload_path):
             os.makedirs(upload_path)
        print("User folder created successfully.")
    else:
        print("User folder already exists.")

def create_user_survey_folder(uuid):
    folder_path = os.path.join("data", uuid,"survey_response")

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

    # Get all comments
    if comments:
        all_comments = [comment.body for comment in comments[:100]]
        all_comment_authors = [comment.author for comment in comments[:100]]
        return all_comments , all_comment_authors
    else:
        pass

def extract_all_post_info(post_url):
    submission = reddit.submission(url=post_url)
    postauthor = submission.author.name
    postname = submission.title
    subreddit = submission.subreddit

    print('extracted', postname, subreddit, postauthor)
    return postname, subreddit, postauthor

def is_post_deleted(url):
    post_id = url.split('/')[-2]

    try:
        submission = reddit.submission(id=post_id)
        return submission.author is not None
    except Exception as e:
        print(f"Error fetching post information: {str(e)}")
        return False

def process_comments_chunk(chunk_urls):
    all_comments = []
    all_comment_authors = []
    post_info = []

    for url in chunk_urls:
        try:
            comments, comment_authors = extract_all_comments(url)
            postname, subreddit, postauthor = extract_all_post_info(url)
            if comments and comment_authors is not None:
                all_comments += comments
                all_comment_authors += [author.name if author is not None else None for author in comment_authors]
                post_info += [str(postname) + ' on r/' + str(subreddit) + ' by ' + str(postauthor)]
        except Exception as e:
            print(f"Error processing URL: {url}")
            print(f"Error message: {str(e)}")

    return all_comments, all_comment_authors, post_info


def process_comments(most_recent_file):
    record = pd.read_csv(most_recent_file)
    unique_post_urls = record['reddit_post'].dropna().unique()
    print("UNIQUE", unique_post_urls)

    valid_urls = [url for url in unique_post_urls if reddit.submission(url=url).author is not None]

    if valid_urls == []:
        print('You do not have enough comments to do this exercise. Please browse more comments and return')
        return not_enough()
    else:
        num_processes = mp.cpu_count() 
        chunk_size = max(len(valid_urls) // num_processes, 1) 

        chunks = [valid_urls[i:i + chunk_size] for i in range(0, len(valid_urls), chunk_size)]

        pool = mp.Pool(processes=num_processes)
        results = pool.map(process_comments_chunk, chunks)
        pool.close()
        pool.join()

        all_comments = []
        all_comment_authors = []
        post_info = []
        for comments, comment_authors, info in results:
            all_comments += comments
            all_comment_authors += comment_authors
            post_info += info * len(comments)

        seen_comments = record['comment_body_encoded'].tolist()
        seen_comments = [
            unquote(base64.b64decode(comment.encode('utf-8')).decode('utf-8'))
            for comment in seen_comments
            if str(comment) != 'nan'
        ]

        unseen_comments = list((Counter(all_comments) - Counter(seen_comments)).elements())

        return all_comments, all_comment_authors, post_info, seen_comments, unseen_comments


def generate_combinations(grouped):

    # Original list of tuples
    combinations = [(False, False), (False, True), (True, False), (True, True)]

    # Ensuring one of the selected tuples has the first value as True
    random_combinations = [random.choice([t for t in combinations if t[0]]), random.choice(combinations)]

    groups = []
    for combination in random_combinations:
        if combination in grouped.groups:
            group = grouped.get_group(combination)
            if group is not None:
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
            else:
                return generate_combinations(grouped)
            pass
    
    if len(groups) >= 2:
        return groups[0], groups[1]
    else:
        return generate_combinations(grouped) 


def saveToxicResults(subreddit,rating, reason, uuid):
    folder_path = os.path.join("data", uuid, "survey_response")
    current_date = date.today().strftime("%Y-%m-%d")
    file_path = os.path.join(folder_path, f"{current_date}_toxicCat.csv")

        
    # Check if the CSV file already exists
    if not os.path.isfile(file_path):
        with open(file_path, mode='w', newline='') as csvfile:
            fieldnames = ['SubReddit','Rating', 'Reason']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    with open(file_path, mode='a', newline='') as csvfile:
        fieldnames = ['SubReddit','Rating', 'Reason']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow({'SubReddit': subreddit, 'Rating': rating, 'Reason': reason })

    print("Results saved successfully!")


def saveResults(options,selected_option, uuid, surveyType=''):
    folder_path = os.path.join("data", uuid, "survey_response")
    current_date = date.today().strftime("%Y-%m-%d")
    if surveyType == 'likert':
        file_path = os.path.join(folder_path, f"{current_date}_likert.csv")
    elif surveyType == 'toxicCat':
        file_path = os.path.join(folder_path, f"{current_date}_toxicCat.csv")
    elif surveyType == 'subRank':
        file_path = os.path.join(folder_path, f"{current_date}_subRank.csv")
    elif surveyType =='subReddit':
        file_path = os.path.join(folder_path,f"{current_date}_subReddit.csv")
    else:
        file_path = os.path.join(folder_path, f"{current_date}.csv")
    
    # Check if the CSV file already exists
    if not os.path.isfile(file_path):
        with open(file_path, mode='w', newline='') as csvfile:
            fieldnames = ['Options','Selected Option']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    with open(file_path, mode='a', newline='') as csvfile:
        fieldnames = ['Options','Selected Option']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow({'Options': options, 'Selected Option': selected_option})

    print("Results saved successfully!")

def saveSurveyResponseToCSV(response, uuid):
    print('Saving Demographic Survey')
    folder_path = os.path.join("data", uuid, "survey_response")
    file_path = os.path.join(folder_path, "demographic.csv")
    
    fieldnames = list(response.keys())

    with open(file_path, 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow(response)

@app.route('/install', methods=['GET', 'POST'])
def install():
    return render_template('extension/install.html')

@app.route('/consent', methods=['GET', 'POST'])
def consent():
    return render_template('extension/consent.html')


@app.route('/', methods=['GET', 'POST'])
def login():
    session.clear()
    if request.method == 'POST':
        uuid = request.form['uuid']
        error = None

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
        user = cursor.fetchone()

        if user:
            create_user_folder(uuid)
            session['uuid'] = uuid
            print('here')
            return redirect('/inform')
        else:
            error = "Invalid Prolific ID. Please try again."
            return render_template('login.html', error=error)

    return render_template('login.html')

@app.route('/inform', methods=['GET', 'POST'])
def inform():
    uuid = session.get('uuid')
    print(uuid)
    if uuid:
        return render_template('inform.html')
    else:
        return redirect('/')
    


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    uuid = session.get('uuid')
    if uuid:
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

        upload_folder = os.path.join("data", uuid, "scraped_comments")
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

def process_comment_toxic(comment):
    # Create Perspective API client
    client = discovery.build(
        "commentanalyzer",
        "v1alpha1",
        developerKey=PERSPECTIVE_API_KEY,
        discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
        static_discovery=False,
    )

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

    try:
        response = client.comments().analyze(body=analyze_request).execute()
    except Exception as e:
        print(f"Error processing comment: {str(e)}")
        # Return default scores and toxicity value
        return [0]*8, False

    scores = []
    for i in response['attributeScores'].keys():
        score = response['attributeScores'][i]['summaryScore']['value']
        scores.append(score)

    toxicity_score = response['attributeScores']['TOXICITY']['summaryScore']['value']

    return scores, toxicity_score > 0.5

def check_valid(most_recent_file):
    record = pd.read_csv(most_recent_file)
    unique_post_urls = record['reddit_post'].dropna().unique()
    print("UNIQUE", unique_post_urls)

    valid_urls = []
    for url in unique_post_urls:
        submission = reddit.submission(url=url)
        if submission.author is not None:
            valid_urls.append(url)


    if valid_urls == []:
        print('You do not have enough comments to do this exercise. Please browse more comments and return')
        render_template('not_enough.html')
        return False
    else: 
        return valid_urls


@app.route('/generate', methods=['GET', 'POST'])
def generate_survey():
    uuid = session.get('uuid')
    if uuid:
        upload_folder = os.path.join("data", uuid, "scraped_comments")

        most_recent_file = find_most_recent_file(upload_folder)

        if most_recent_file:
            most_recent_file_path = os.path.join(upload_folder,most_recent_file)
            if check_valid(most_recent_file_path):
                all_comments, all_comment_authors, post_info, seen_comments, unseen_comments = process_comments(most_recent_file_path)
                data = {'comment_authors': all_comment_authors,'post_info': post_info, 'comments': all_comments, 'seen': [comment in seen_comments for comment in all_comments]}

                df = pd.DataFrame(data)

                # Create a multiprocessing Pool
                pool = mp.Pool(mp.cpu_count())

                # Process comments in parallel
                results = pool.map(process_comment_toxic, all_comments)
                print('RESULTS: ', results)

                # Get toxicity scores and labels
                all_scores, toxicity_labels = zip(*results)

                df['toxicity'] = toxicity_labels
                df['all'] = all_scores

                # Save labeled comments
                folder_path = os.path.join("data", uuid, "labeled_comments")
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)

                file_path = os.path.join(folder_path, "labeled.csv")
                df.to_csv(file_path, index=False)

                return redirect('/survey')
            else:
                redirect('/notenough')
                return not_enough()
    else:
        flash('You are not logged in. Please login and try again.', 'error')
        return redirect('/')


@app.route('/notenough', methods=['GET', 'POST'])
def not_enough():
    redirect('/notenough')
    print('NOT ENOUGH')
    return render_template('not_enough.html')


@app.route('/survey', methods=['GET', 'POST'])
def genSurvey():
    uuid = session.get('uuid')
    if uuid:
        click_counter = session.get('click_counter')
        if click_counter is None:
            click_counter = 1
        else:
            click_counter += 1
        session['click_counter'] = click_counter
        uuid = session.get('uuid')
        create_user_survey_folder(uuid)

        #call survey final data
        labeled_data = os.path.join("data", uuid, "labeled_comments","labeled.csv")
        labeled_data = pd.read_csv(labeled_data)

        grouped = labeled_data.groupby(['seen', 'toxicity'])
        # Original list of tuples
        toxic_true = len(labeled_data[labeled_data['toxicity'] == True ])
        print( 'COUNT', toxic_true)

        if toxic_true <5:
            print('You dont have enough data for this survey.')
            return render_template('notenough.html', count = toxic_true)
        else:
            option1, option2= generate_combinations(grouped)

        # Call your function to save the results        
        options= [option1,option2]
        selected_option = request.form.get('option')
        option1_value = request.form.get('option1_value')
        option2_value = request.form.get('option2_value')
        saveResults([option1_value,option2_value],selected_option, uuid)  

        if session['click_counter'] == 11:
            session['click_counter'] = None

            return redirect('/likertsurvey')

        return render_template('survey.html',option1=option1, option2=option2, click_counter = click_counter)
    else:
        flash('You are not logged in. Please login and try again.', 'error')
        return redirect('/')
        
@app.route('/likertsurvey', methods=['GET','POST'])
def likertSurvey():
    uuid = session.get('uuid')
    folder_path = os.path.join("data", uuid, "survey_response")
    current_date = date.today().strftime("%Y-%m-%d")
    file_path = os.path.join(folder_path, f"{current_date}.csv")

    selected_data = pd.read_csv(file_path)
    comment = None
    valid_comments = []

    for _, row in selected_data.iterrows():
        try:
            if pd.notna(row["Selected Option"]):
                comment = ast.literal_eval(row["Selected Option"])
                valid_comments.append(comment)
        except ValueError as e:
            continue

    if uuid:
        click_counter = session.get('click_counter')
        max_click_counter = min(10, len(valid_comments))
        
        if click_counter is None:
            click_counter = 1
        else:
            click_counter += 1
        session['click_counter'] = click_counter
        
        selected_option = request.form.get('rating')
        comment_option = request.form.get('comment')
        if selected_option!=None: 
            saveResults(comment_option,selected_option, uuid, 'likert')  

        if session['click_counter'] == max_click_counter:
            session['click_counter'] = None

            return redirect('/toxiccatsurvey')

        return render_template('likertsurvey.html', data = valid_comments[click_counter], click_counter = click_counter )
    else:
        flash('You are not logged in. Please login and try again.', 'error')
        return redirect('/')

@app.route('/toxiccatsurvey', methods=['GET','POST'])    
def toxicCatSurvey():
    uuid = session.get('uuid')
    folder_path = os.path.join("data", uuid, "survey_response")
    current_date = date.today().strftime("%Y-%m-%d")
    file_path = os.path.join(folder_path, f"{current_date}.csv")

    selected_data = pd.read_csv(file_path)
    comment = None
    valid_comments = []

    for _, row in selected_data.iterrows():
        try:
            if pd.notna(row["Selected Option"]):
                comment = ast.literal_eval(row["Selected Option"])
                valid_comments.append(comment)
        except ValueError as e:
            continue

    if uuid:
        click_counter = session.get('click_counter')
        if click_counter is None:
            click_counter = 1
        else:
            click_counter += 1
        session['click_counter'] = click_counter
    
        # Retrieving the selected checkboxes
        selected_toxic_categories = request.form.getlist('toxicity')
        comment_option = request.form.get('comment')
        
        if selected_toxic_categories:
            # Assuming saveResults function can handle the list of categories
            saveResults(comment_option, selected_toxic_categories, uuid, 'toxicCat')  

        if session['click_counter'] == 11:
            session['click_counter'] = None
            return redirect('/subsurvey')

        return render_template('toxicsurvey.html', data=valid_comments[click_counter], click_counter=click_counter)
    else:
        flash('You are not logged in. Please login and try again.', 'error')
        return redirect('/')


@app.route('/subsurvey', methods=['GET','POST'])   
def subSurvey():
    uuid = session.get('uuid')
    if not uuid:
        flash('You are not logged in. Please login and try again.', 'error')
        return redirect('/')
    
    folder_path = os.path.join("data", uuid, "survey_response")
    current_date = date.today().strftime("%Y-%m-%d")
    file_path = os.path.join(folder_path, f"{current_date}.csv")
    data = pd.read_csv(file_path)
    subreddits = set()
    
    for index, row in data.iterrows():
        comment = row["Selected Option"]
        if isinstance(comment, str) and comment != 'nan':
            try:
                comment = ast.literal_eval(comment)
                if isinstance(comment, dict):  # Checking if the result is a dictionary
                    subreddit_match = re.search(r"(r/\w+)", comment.get('post_info', ''))
                    if subreddit_match:
                        subreddits.add(subreddit_match.group(1))                    
            except (ValueError, SyntaxError) as e:
                print(f"Error in row {index}: {e}")

    if request.method == 'POST':
        for subreddit in subreddits:
            toxicity_rating = request.form.get(f'toxicity_{subreddit}')
            stay_reason = request.form.get(f'stay_reason_{subreddit}')
            saveToxicResults(subreddit, toxicity_rating, stay_reason, uuid)
        return redirect('/subranksurvey')

    return render_template('subredditsurvey.html', data=list(subreddits))

@app.route('/subranksurvey', methods=['GET','POST'])    
def gensubRankSurvey():
    uuid = session.get('uuid')
    folder_path = os.path.join("data", uuid, "survey_response")
    current_date = date.today().strftime("%Y-%m-%d")
    file_path = os.path.join(folder_path, f"{current_date}.csv")
    data = pd.read_csv(file_path)
    subreddits = set()
    
    for index, row in data.iterrows():
        comment = row["Selected Option"]
        if isinstance(comment, str) and comment != 'nan':
            try:
                comment = ast.literal_eval(comment)  
                subreddit_match = re.search(r"(r/\w+)", comment['post_info'])
                if subreddit_match:
                    subreddits.add(subreddit_match.group(1)) 
                    
            except ValueError as e:
                print(f"Error in row {index}: {e}")

    if uuid:
        if request.method == 'POST':
            for subreddit in subreddits:
                toxicity_ranking = request.form.get(f'toxicity_{subreddit}')
                saveResults(subreddit, toxicity_ranking, uuid,'subRank')
            
            return redirect('/demosurvey')

        return render_template('subranksurvey.html', data=list(subreddits))
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

    return render_template('demosurvey.html', age_options=age_options, gender_options=gender_options,
                           ethnicity_options=ethnicity_options, education_options=education_options)

@app.route('/demosubmit', methods=['GET','POST'])
def demosubmit():
    print('Submitting DEMO Survey')
    uuid = session.get('uuid')
    if uuid:
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

        saveSurveyResponseToCSV(response, uuid)

        return render_template('done.html')
    else:
        # Redirect if not logged in
        flash('You are not logged in. Please login and try again.', 'error')
        return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, port=8078)
