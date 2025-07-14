from serpapi import GoogleSearch
from google.generativeai import GenerativeModel
import google.generativeai as genai
import os

# === SETUP ===
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")              # Set via environment variable
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")        # Set via environment variable

genai.configure(api_key=GEMINI_API_KEY)
model = GenerativeModel("gemini-2.0-flash-lite")

# # === 1. Extract Text from Resume (DOCX) ===
# def extract_text_from_docx(file_path):
#     doc = Document(file_path)
#     return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

# === 2. Fetch Job Descriptions from Online ===
def fetch_job_descriptions(job_title):
    params = {
        "engine": "google_jobs",
        "q": f"{job_title} job description site:linkedin.com",
        "location": "India",
        "api_key": SERPAPI_KEY
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    return [job["description"] for job in results.get("jobs_results", [])[:3]]

# === 3. Extract Keywords from JD using Gemini ===
def extract_keywords_from_jd(jd_text):
    prompt = f"""
Here is a job description for analysis:

---
{jd_text}
---

Extract the most important keywords a resume should include to match this job.
Group them under:
- Hard Skills
- Soft Skills
- Tools & Technologies
- Certifications
- Domain Keywords

Respond in bullet-point format under each heading.
"""
    response = model.generate_content(prompt)
    return response.text

# === 4. Parse Keyword Output into Dictionary ===
def parse_keywords_into_dict(keyword_output):
    categories = ["Hard Skills", "Soft Skills", "Tools & Technologies", "Certifications", "Domain Keywords"]
    parsed = {}
    current = None
    for line in keyword_output.splitlines():
        line = line.strip()
        if any(cat in line for cat in categories):
            current = line.replace(":", "").strip()
            parsed[current] = []
        elif line.startswith("-") and current:
            parsed[current].append(line[1:].strip())
    return parsed

# === 5. Compare Resume Text with Keywords ===
def compare_keywords(resume_text, keyword_dict):
    missing = {}
    for category, keywords in keyword_dict.items():
        missing[category] = [kw for kw in keywords if kw.lower() not in resume_text.lower()]
    return missing

# === 6. Generate Resume Feedback with Gemini ===
def generate_resume_feedback(resume_text, job_title, missing_keywords):
    prompt = f"""
You are an expert resume coach.

Given the resume and job title below, and the missing keywords, provide concise feedback:
1. List only the most important keywords to include (grouped)
2. Suggest 1-2 resume bullet rewrites (keep it brief)
3. Suggest 1 certification or project idea (if relevant)
4. Give 1-2 short formatting or structure tips

Be brief and to the point. Avoid lengthy explanations.

Resume:
{resume_text}

Job Title:
{job_title}

Missing Keywords:
{missing_keywords}
"""
    response = model.generate_content(prompt)
    return response.text

# === MAIN FUNCTION ===
def strengthen_resume(resume_text, job_title):
    print("🔍 Fetching job descriptions...")
    jd_list = fetch_job_descriptions(job_title)
    combined_jd_text = "\n\n".join(jd_list)

    print("🧠 Extracting keywords with Gemini...")
    keyword_output = extract_keywords_from_jd(combined_jd_text)
    keyword_dict = parse_keywords_into_dict(keyword_output)

    print("📊 Comparing with resume...")
    missing = compare_keywords(resume_text, keyword_dict)

    print("✍️ Generating feedback with Gemini...")
    feedback = generate_resume_feedback(resume_text, job_title, missing)

    return feedback

