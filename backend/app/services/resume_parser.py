import os
import re
from typing import Any

import pdfplumber
from docx import Document


def _extract_text_from_pdf(path: str) -> str:
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text()
            if txt:
                pages.append(txt)
    return "\n".join(pages)


def _extract_text_from_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text)


def parse_resume_file(path: str) -> dict[str, Any]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        text = _extract_text_from_pdf(path)
    elif ext == ".docx":
        text = _extract_text_from_docx(path)
    elif ext == ".txt":
        with open(path, encoding="utf-8") as f:
            text = f.read()
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    return {
        "raw_text": text,
        "sections": _extract_sections(text),
    }


def _extract_sections(text: str) -> dict[str, Any]:
    lower = text.lower()
    sections: dict[str, Any] = {"raw_text": text}

    email_match = re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", text)
    sections["email"] = email_match.group(0) if email_match else None

    phone_match = re.search(r"(?:(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", text)
    sections["phone"] = phone_match.group(0) if phone_match else None

    linkedin_match = re.search(r"https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9\-_]+", text)
    sections["linkedin"] = linkedin_match.group(0) if linkedin_match else None

    github_match = re.search(r"https?://(?:www\.)?github\.com/[A-Za-z0-9\-_]+", text)
    sections["github"] = github_match.group(0) if github_match else None

    skills_keywords = [
        "javascript", "typescript", "python", "java", "react", "node", "express",
        "mongodb", "sql", "postgres", "docker", "aws", "azure", "gcp", "kubernetes",
        "git", "graphql", "rest", "next", "vue", "angular", "svelte", "tailwind",
        "css", "html", "sass", "webpack", "vite", "jest", "cypress", "playwright",
        "figma", "photoshop", "illustrator", "ui", "ux", "figma", "swift", "kotlin",
        "flutter", "dart", "go", "golang", "rust", "c++", "c#", ".net", "php",
        "laravel", "ruby", "rails", "redis", "elasticsearch", "kafka", "spark",
        "tensorflow", "pytorch", "ml", "ai", "machine learning", "data science",
        "agile", "scrum", "jira", "confluence", "ci/cd", "terraform", "ansible",
        "linux", "nginx", "apache", "mysql", "oracle", "cassandra", "dynamodb",
        "firebase", "supabase", "vercel", "netlify", "heroku", "digitalocean",
    ]
    found_skills = []
    for skill in skills_keywords:
        if re.search(rf"\b{re.escape(skill)}\b", lower):
            found_skills.append(skill)
    sections["skills"] = found_skills

    # Experience: look for company names, job titles, dates.
    experience: list[dict[str, str]] = []
    exp_pattern = re.findall(
        r"(?P<title>[A-Z][A-Za-z\s/]+?)\s+(?:at|@|,)\s+(?P<company>[A-Z][A-Za-z0-9\s&]+?)[\s,]+(?P<period>\d{4}\s*[-–]\s*(?:\d{4}|Present))",
        text,
    )
    for title, company, period in exp_pattern[:10]:
        experience.append(
            {
                "title": title.strip(),
                "company": company.strip(),
                "period": period.strip(),
            }
        )
    sections["experience"] = experience

    education: list[dict[str, str]] = []
    edu_pattern = re.findall(
        r"(?P<degree>[A-Z][A-Za-z\s]+(?:in\s+[A-Za-z\s]+)?)\s+(?:from|at|,)\s+(?P<school>[A-Z][A-Za-z0-9\s&]+?)[\s,]+(?P<period>\d{4}\s*[-–]\s*(?:\d{4}|Present))",
        text,
    )
    for degree, school, period in edu_pattern[:5]:
        education.append(
            {
                "degree": degree.strip(),
                "school": school.strip(),
                "period": period.strip(),
            }
        )
    sections["education"] = education

    return sections
