# LearnMate AI

**Live Project:** https://learnmate-ai-project2026.streamlit.app/

LearnMate AI is a Streamlit app that creates a personalized learning roadmap using an existing IBM watsonx.ai deployment. Learners enter their education, current skills, career goal, daily study time, and target duration; the app sends those values to the deployed prompt template and displays the generated roadmap.

## Features

- Student profile form for education, current skills, career interest, study hours, and learning duration
- Roadmap generation through an IBM watsonx.ai deployment
- IBM Cloud IAM token exchange using an API key loaded from environment configuration
- Duration checks that trim out-of-range schedule sections and reject a still-invalid roadmap
- Clear messages for missing configuration, timeouts, and API errors

## Technologies

- Python 3.10 or later
- Streamlit
- `requests`
- `python-dotenv`
- IBM watsonx.ai deployment inference API

## Setup

1. Clone or download the project and open a terminal in the project directory.

2. Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

4. Create a `.env` file in the project root and set your own IBM Cloud credentials and deployment details:

```dotenv
WATSONX_API_KEY=your_ibm_cloud_api_key
WATSONX_URL=https://your-region.ml.cloud.ibm.com/ml/v1/deployments/your-deployment-id/text/generation_stream?version=2021-05-01
WATSONX_DEPLOYMENT_ID=your-deployment-id
```

Use the URL and deployment ID for the same deployment and region. Keep real values only in `.env` or your host's environment-variable settings. Do not commit credentials or paste them into source code.

## Run

Start the app from the project root:

```powershell
python -m streamlit run app.py
```

Streamlit prints a local URL, usually `http://localhost:8501`.

## Use

1. Enter a student name and current skills.
2. Select education, career interest, daily study hours, and learning duration.
3. Select **Generate My Roadmap** and review the profile and generated roadmap.

The deployed prompt template is called with these variables: `student_name`, `education`, `current_skills`, `career_interest`, `study_hours`, and `duration`.

## Configuration and Security

The app reads `WATSONX_API_KEY`, `WATSONX_URL`, and `WATSONX_DEPLOYMENT_ID` from `.env` or the process environment. The API key is exchanged for a short-lived IBM IAM bearer token at runtime; neither credential is embedded in the application source.

The repository `.gitignore` excludes `.env` files, common secret and certificate files, Streamlit secrets, virtual environments, caches, build artifacts, and logs. Verify that `.env` is not already tracked before publishing; ignore rules do not remove files already in Git's index. If a key has been exposed, revoke or rotate it in IBM Cloud and update the local configuration.
