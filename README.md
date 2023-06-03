# Reddit Survey Website

<img width="307" alt="Screenshot 2023-06-03 at 3 08 30 PM" src="https://github.com/shljessie/RedditSurvey/assets/59305253/6d050e57-d1cb-4eb2-8d0d-06dc59741622">
<img width="300" alt="Screenshot 2023-06-03 at 3 11 16 PM" src="https://github.com/shljessie/RedditSurvey/assets/59305253/9cbb6238-7484-4b32-a329-7cbacb99e1ae">
<img width="300" alt="Screenshot 2023-06-03 at 3 12 14 PM" src="https://github.com/shljessie/RedditSurvey/assets/59305253/55a79603-2e9a-4864-a7d4-f78c7ebde955">

Survey generator website based on user viewed reddit comments.

Miro Board: https://miro.com/app/board/uXjVMCWibLw=/ 

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
  - Reddit ClIENT_ID 
  - Reddit SECRET_KEY
  - Reddit USER_AGENT
  - Perspective API_KEY


## Usage 
To use the Reddit Survey Website, follow these steps:
Run the application: python app.py
Access the website through your preferred web browser by entering the following URL: http://localhost:8080

## Database
**1. database.db :** user database (id,UUID,username,password)

**2. data/{username}/scraped_comments:** user uploaded csv comments
> YYYY_MM_DD_HH:MM:SS.csv

**3. data/{username}/labeled_comments :** processed comments with Toxicity/Seen labeled
> labeled_comments.csv

**3. data/{username}/survey_response :** user survey response data
> YYYY_MM_DD_HH:MM:SS_repsonse.csv


## File Explanation
1. /templates : contains the user login, and dashboard 
  - for login, create a UUID,username,password in the database.db
2. /process : extracting the unseen comments
3. /data: store the database.db of user info and csv files that users uploaded.


## Note to self
https://stackoverflow.com/questions/13716658/how-to-delete-all-commit-history-in-github 
