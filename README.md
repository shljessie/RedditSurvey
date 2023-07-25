# Reddit Survey Website

https://reddit.esrg.stanford.edu/

Survey generator website based on user viewed reddit comments.

## Server Connection
- ssh -Y esrg-scratch-22

### Data Saving Structure 
Data Saving Structure

Data
├── user
│   ├── scraped_comments
│   │   └── (2023_07_14_23:36:45.csv): uploaded comments from user (upload date)
│   └── labeled_comments
│       └── (labeled.csv): comments labeled with perspective scores
└── survey_response
    └── (2023-07-01.csv): survey responses for perceived comments

(demographic.csv)



#### Table of Contents
- [Features](#features)
- [Dependencies](#dependencies)
- [Installation](#installation)
- [Usage](#usage)
- [Database](#databse)
- [FileExplaination](#fileexplanation)

## Features
1. **UUID Login:** The website allows users to log in using a unique identifier (UUID). This login method ensures anonymous participation in the surveys.

2. **User Data Upload:** Users have the option to upload their Reddit data, including their post and comment history. This data is used to generate surveys and analyze user responses.

3. **Processing Seen Reddit Posts:** The website processes the uploaded Reddit data to identify "unseen" comments. These unseen comments are used to generate survey questions.

4. **Fetching Unseen Comments using PRAW:** The Python Reddit API Wrapper (PRAW) library is utilized to interact with the Reddit API. It enables the website to retrieve comments from Reddit posts and identify unseen comments.

   - PRAW Documentation: [https://praw.readthedocs.io/en/stable/](https://praw.readthedocs.io/en/stable/)

5. **Generating Comment Pairs:** The website generates pairs of comments to form survey questions. These pairs consist of both seen and unseen comments. The comment pairs are used to gather user opinions and insights.

6. **Toxicity Analysis:** The website incorporates the Perspective API to assign toxicity scores to both seen and unseen comments. This allows for the labeling of comments as toxic or non-toxic.

7. **Random Survey Generation:** Surveys are randomly generated based on the available data and selected criteria. Users are presented with survey questions derived from the comment pairs, allowing them to provide their feedback and opinions.


## Dependencies
To run the Reddit Survey Website, the following dependencies are required:
- Python (version 3.7 or higher)
- Flask (version 2.0.1 or higher)
- PRAW (Python Reddit API Wrapper) library
- Perspective API key & project

## Installation
To install and set up the website, follow these steps:
1. Clone the repository: `git clone https://github.com/shljessie/RedditSurvey.git`
2. Install the required dependencies: `pip install -r requirements.txt`
3. Creat a .env file with a 
  - Reddit CLIENT_ID 
  - Reddit SECRET_KEY
  - Reddit USER_AGENT
  - Perspective API_KEY


## Usage 

To rn the application: 
python3 app.py
Access the website through your preferred web browser by entering the following URL: http://localhost:8080

## File Explanation
1. /templates : contains the user login, and dashboard 
  - for login, create a UUID,username,password in the database.db
2. /process : extracting the unseen comments
3. /data: store the database.db of user info and csv files that users uploaded.


## Caddy Server
- Global options block : https://caddyserver.com/docs/caddyfile/options
- Caddy Address : https://caddyserver.com/docs/caddyfile/concepts#addresses 
- Caddy File Server: https://caddyserver.com/docs/caddyfile/directives/file_server 
