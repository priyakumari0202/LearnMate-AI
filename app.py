
import os
import re
from urllib.parse import urlsplit, urlunsplit

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

MONTH_ORDINALS = {
    1: "First",
    2: "Second",
    3: "Third",
    4: "Fourth",
    5: "Fifth",
    6: "Sixth",
    7: "Seventh",
    8: "Eighth",
    9: "Ninth",
    10: "Tenth",
    11: "Eleventh",
    12: "Twelfth",
}


def get_config(key):
    """Read credentials from local environment or Streamlit Cloud Secrets."""
    value = os.getenv(key)

    if value:
        return value

    try:
        return st.secrets[key]
    except Exception:
        return None


def roadmap_matches_duration(roadmap, duration):
    months = int(duration.split()[0])
    max_weeks = months * 4

    scheduled_months = [
        int(match.group(2) or match.group(1))
        for match in re.finditer(
            r"\bmonths?\s+(\d+)(?:\s*[-\u2013]\s*(\d+))?",
            roadmap,
            re.IGNORECASE,
        )
    ]

    scheduled_months.extend(
        month_number
        for month_number, ordinal in MONTH_ORDINALS.items()
        if re.search(rf"\b{ordinal}\s+month\b", roadmap, re.IGNORECASE)
        or re.search(rf"\bmonth\s+{ordinal}\b", roadmap, re.IGNORECASE)
    )

    scheduled_weeks = [
        int(match.group(2) or match.group(1))
        for match in re.finditer(
            r"\bweeks?\s+(\d+)(?:\s*[-\u2013]\s*(\d+))?",
            roadmap,
            re.IGNORECASE,
        )
    ]

    return (
        max(scheduled_months, default=0) <= months
        and max(scheduled_weeks, default=0) <= max_weeks
    )


def normalize_learner_name(roadmap, name):
    learner_name_patterns = (
        r"\b([A-Z][a-z]+)(?='s\s+(?:project|journey|learning path|roadmap|skills|progress|portfolio|career)\b)",
        r"\b(?i:where|for|as)\s+([A-Z][a-z]+)\s+(?i:can|will|should|needs|could)\b",
        r"\b([A-Z][a-z]+)\s+(?i:will|can|should|needs|could|must)\s+(?i:be\s+(?:capable|ready|able)|gain|learn|start|develop|build|create|practice|understand)\b",
    )

    generated_names = {
        match.group(1)
        for pattern in learner_name_patterns
        for match in re.finditer(pattern, roadmap)
        if match.group(1).casefold() != name.casefold()
    }

    for generated_name in generated_names:
        roadmap = re.sub(
            rf"\b{re.escape(generated_name)}\b",
            name,
            roadmap,
            flags=re.IGNORECASE,
        )

    return roadmap


def trim_roadmap_to_duration(roadmap, duration):
    months = int(duration.split()[0])
    max_weeks = months * 4
    overrun_positions = []

    for match in re.finditer(
        r"\bmonths?\s+(\d+)(?:\s*[-\u2013]\s*(\d+))?",
        roadmap,
        re.IGNORECASE,
    ):
        if int(match.group(2) or match.group(1)) > months:
            overrun_positions.append(match.start())

    for month_number, ordinal in MONTH_ORDINALS.items():
        if month_number <= months:
            continue

        for match in re.finditer(
            rf"\b(?:{ordinal}\s+month|month\s+{ordinal})\b",
            roadmap,
            re.IGNORECASE,
        ):
            overrun_positions.append(match.start())

    for match in re.finditer(
        r"\bweeks?\s+(\d+)(?:\s*[-\u2013]\s*(\d+))?",
        roadmap,
        re.IGNORECASE,
    ):
        if int(match.group(2) or match.group(1)) > max_weeks:
            overrun_positions.append(match.start())

    if not overrun_positions:
        return roadmap.strip()

    return roadmap[:min(overrun_positions)].rstrip()

def generate_roadmap(name, education, skills, career, hours, duration):

    api_key = get_config("WATSONX_API_KEY")
    watsonx_url = get_config("WATSONX_URL")
    deployment_id = get_config("WATSONX_DEPLOYMENT_ID")

    if not api_key or not watsonx_url or not deployment_id:
        raise ValueError(
            "Watsonx configuration is incomplete. "
            "Check your .env or Streamlit Secrets."
        )

    configured_url = urlsplit(watsonx_url)

    if configured_url.scheme != "https" or not configured_url.netloc:
        raise ValueError("WATSONX_URL must be a valid HTTPS URL.")

    # Use non-streaming Chat API so requests.post returns JSON
    endpoint = (
        f"{configured_url.scheme}://{configured_url.netloc}"
        f"/ml/v1/deployments/{deployment_id}/text/chat"
        f"?version=2021-05-01"
    )

    # Get IBM IAM access token
    token_response = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": api_key,
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        },
        timeout=30,
    )

    token_response.raise_for_status()

    access_token = token_response.json().get("access_token")

    if not access_token:
        raise ValueError("IBM IAM did not return an access token.")

    # Prepare complete learner information for Granite
    prompt = f"""
Create a personalized learning roadmap for this student.

Student Name: {name}
Education: {education}
Current Skills: {skills}
Career Interest: {career}
Daily Study Hours: {hours}
Learning Duration: {duration}

Requirements:
1. Create a roadmap for exactly the selected duration.
2. Divide it month by month.
3. Include weekly learning goals and practical projects.
4. Include useful tools and technologies.
5. Keep the plan realistic for the student's daily study hours.
6. Do not include any months beyond the selected duration.
7. Use the student's exact name: {name}.
8. Format the roadmap clearly using headings and bullet points.
"""

    response = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        },
        timeout=120,
    )

    response.raise_for_status()

    result = response.json()

    generated_text = (
        result.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )

    if not generated_text or not generated_text.strip():
        raise ValueError(
            "IBM returned an empty roadmap. Check the deployment."
        )

    generated_text = normalize_learner_name(
        generated_text, name
    )

    generated_text = trim_roadmap_to_duration(
        generated_text, duration
    )

    if not roadmap_matches_duration(generated_text, duration):
        raise ValueError(
            f"The generated roadmap exceeds {duration}."
        )

    return generated_text.strip()



def api_error_message(error):
    response = getattr(error, "response", None)

    if response is not None:
        try:
            details = response.json()
            errors = details.get("errors", [])

            if errors:
                return errors[0].get(
                    "message", "IBM returned an API error."
                )

            return details.get(
                "errorMessage",
                details.get("message", str(error))
            )

        except (ValueError, AttributeError):
            return f"IBM returned HTTP {response.status_code}."

    return str(error)


# Streamlit application interface
st.set_page_config(
    page_title="LearnMate AI",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 LearnMate AI")

st.subheader(
    "Your Personalized Learning Pathway Generator"
)

st.write(
    "Create your own personalized learning roadmap "
    "with the power of IBM Granite AI."
)

st.divider()

st.header("Enter Your Details")

with st.form("student_form"):

    name = st.text_input("Student Name")

    education = st.selectbox(
        "Education",
        [
            "BCA 1st Year",
            "BCA 2nd Year",
            "BCA 3rd Year",
            "B.Tech",
            "Other"
        ]
    )

    skills = st.text_area("Your Current Skills")

    career = st.selectbox(
        "Career Interest",
        [
            "Data Analyst",
            "Data Scientist",
            "AI/ML Engineer",
            "Web Developer",
            "Software Developer"
        ]
    )

    hours = st.selectbox(
        "Daily Study Hours",
        [
            "1 Hour",
            "2 Hours",
            "3 Hours",
            "4 Hours"
        ]
    )

    duration = st.selectbox(
        "Learning Duration",
        [
            "3 Months",
            "6 Months",
            "9 Months",
            "12 Months"
        ]
    )

    submit = st.form_submit_button(
        "🚀 Generate My Roadmap"
    )


if submit:

    if not name or not skills:
        st.warning(
            "Please enter your name and current skills."
        )

    else:
        st.success(
            "Your profile has been submitted successfully!"
        )

        st.write("### Student Profile")
        st.write("Name:", name)
        st.write("Education:", education)
        st.write("Skills:", skills)
        st.write("Career:", career)
        st.write("Study Time:", hours)
        st.write("Duration:", duration)

        try:
            with st.spinner(
                "Generating your personalized roadmap..."
            ):
                roadmap = generate_roadmap(
                    name,
                    education,
                    skills,
                    career,
                    hours,
                    duration
                )

            st.write(
                "### Your Personalized Learning Roadmap"
            )

            st.markdown(roadmap)

        except requests.Timeout:
            st.error(
                "The request to IBM timed out. Please try again."
            )

        except requests.RequestException as error:
            st.error(
                f"IBM watsonx.ai request failed: "
                f"{api_error_message(error)}"
            )

        except (ValueError, KeyError, IndexError, TypeError) as error:
            st.error(
                f"Could not generate the roadmap: "
                f"{api_error_message(error)}"
            )