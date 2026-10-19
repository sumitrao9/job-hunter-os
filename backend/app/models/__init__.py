from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import uuid


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, default="singleton")
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    preferred_locations = Column(JSON, nullable=True)
    education = Column(JSON, nullable=True)
    experience = Column(JSON, nullable=True)
    skills = Column(JSON, nullable=True)
    desired_roles = Column(JSON, nullable=True)
    min_salary = Column(Integer, nullable=True)
    preferred_salary = Column(Integer, nullable=True)
    remote_preference = Column(String, nullable=True)
    experience_level = Column(String, nullable=True)
    notice_period = Column(String, nullable=True)
    preferred_industries = Column(JSON, nullable=True)
    search_keywords = Column(JSON, nullable=True)
    search_exclusions = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True)
    profile_id = Column(String, ForeignKey("profiles.id"), nullable=False)
    title = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    is_default = Column(Boolean, default=False)
    parsed_sections = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile", backref="resumes")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=True)
    location = Column(String, nullable=True)
    remote = Column(Boolean, nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    source = Column(String, nullable=True)
    raw_data = Column(JSON, nullable=True)
    match_score = Column(Float, nullable=True)
    match_evidence = Column(JSON, nullable=True)
    status = Column(String, default="discovered")
    is_saved = Column(Boolean, default=False)
    is_duplicate = Column(Boolean, default=False)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    source_mappings = relationship("JobSourceMapping", back_populates="job", cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=True)
    company = Column(String, nullable=False)
    job_title = Column(String, nullable=False)
    job_url = Column(String, nullable=True)
    source = Column(String, nullable=True)
    match_score = Column(Float, nullable=True)
    status = Column(String, default="discovered")
    cover_letter = Column(Text, nullable=True)
    form_answers = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    date_discovered = Column(DateTime, default=datetime.utcnow)
    date_applied = Column(DateTime, nullable=True)
    follow_up_date = Column(DateTime, nullable=True)
    history = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship("Job")
    resume = relationship("Resume")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True)
    agent_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkflowConfig(Base):
    __tablename__ = "workflow_configs"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    purpose = Column(String, nullable=True)
    enabled = Column(Boolean, default=False)
    schedule = Column(String, nullable=True)
    config = Column(JSON, nullable=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AutoApplySettings(Base):
    __tablename__ = "auto_apply_settings"

    id = Column(String, primary_key=True, default="singleton")
    enabled = Column(Boolean, default=False)
    emergency_stop = Column(Boolean, default=False)
    mode = Column(String, default="manual")  # manual | approval | autonomous
    min_match_score = Column(Integer, default=50)
    max_per_day = Column(Integer, default=5)
    preferred_titles = Column(JSON, nullable=True)
    preferred_locations = Column(JSON, nullable=True)
    min_salary = Column(Integer, nullable=True)
    remote_only = Column(Boolean, default=False)
    experience_level = Column(String, nullable=True)
    sources = Column(JSON, nullable=True)
    default_resume_id = Column(String, ForeignKey("resumes.id"), nullable=True)
    generate_cover_letter = Column(Boolean, default=True)
    auto_submit_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TailoredResume(Base):
    __tablename__ = "tailored_resumes"

    id = Column(String, primary_key=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=True)
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=True)
    file_type = Column(String, default="docx")
    changes_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    resume = relationship("Resume")
    job = relationship("Job")
    application = relationship("Application")


class CoverLetterVersion(Base):
    __tablename__ = "cover_letter_versions"

    id = Column(String, primary_key=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application")
    job = relationship("Job")
    resume = relationship("Resume")


class FormAnswer(Base):
    __tablename__ = "form_answers"

    id = Column(String, primary_key=True)
    profile_id = Column(String, ForeignKey("profiles.id"), nullable=False)
    question_key = Column(String, nullable=False)
    question_text = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String, nullable=True)  # factual | preference | legal | unknown
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile")


class ApplicationAttempt(Base):
    __tablename__ = "application_attempts"

    id = Column(String, primary_key=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=True)
    cover_letter_id = Column(String, ForeignKey("cover_letter_versions.id"), nullable=True)
    status = Column(String, default="not_started")  # not_started | in_progress | awaiting_approval | submitted_confirmed | submitted_unconfirmed | failed | manual_required
    step = Column(String, nullable=True)  # discovered | matched | prepared | form_filled | submitted | result
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    application = relationship("Application")
    job = relationship("Job")
    resume = relationship("Resume")
    cover_letter = relationship("CoverLetterVersion")


class ApprovalRecord(Base):
    __tablename__ = "approval_records"

    id = Column(String, primary_key=True)
    attempt_id = Column(String, ForeignKey("application_attempts.id"), nullable=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=True)
    decision = Column(String, nullable=False)  # approved | rejected | pending
    reviewer = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    decided_at = Column(DateTime, default=datetime.utcnow)

    attempt = relationship("ApplicationAttempt")
    application = relationship("Application")


class BrowserLog(Base):
    __tablename__ = "browser_logs"

    id = Column(String, primary_key=True)
    attempt_id = Column(String, ForeignKey("application_attempts.id"), nullable=True)
    level = Column(String, default="info")  # info | warn | error
    message = Column(Text, nullable=False)
    url = Column(String, nullable=True)
    selector = Column(String, nullable=True)
    action = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    attempt = relationship("ApplicationAttempt")


class SubmissionConfirm(Base):
    __tablename__ = "submission_confirms"

    id = Column(String, primary_key=True)
    attempt_id = Column(String, ForeignKey("application_attempts.id"), nullable=False)
    application_id = Column(String, ForeignKey("applications.id"), nullable=True)
    confirmation_number = Column(String, nullable=True)
    confirmation_message = Column(Text, nullable=True)
    submitted_url = Column(String, nullable=True)
    screenshot_path = Column(String, nullable=True)
    confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    attempt = relationship("ApplicationAttempt")
    application = relationship("Application")


class JobSource(Base):
    __tablename__ = "job_sources"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    source_name = Column(String(255), nullable=False)
    country = Column(String(100), default="India")
    region = Column(String(100))
    category = Column(String(100))
    source_type = Column(String(50))
    adapter = Column(String(100))
    base_url = Column(String(500))
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=50)
    schedule = Column(String(50), default="1h")
    rate_limit = Column(Integer, default=10)
    requires_auth = Column(Boolean, default=False)
    requires_proxy = Column(Boolean, default=False)
    last_run = Column(DateTime)
    last_success = Column(DateTime)
    last_failure = Column(DateTime)
    jobs_found = Column(Integer, default=0)
    new_jobs = Column(Integer, default=0)
    duplicates = Column(Integer, default=0)
    failed_jobs = Column(Integer, default=0)
    health_status = Column(String(50), default="NOT_CONFIGURED")
    error_message = Column(Text)
    config = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    runs = relationship("SourceRun", back_populates="source", cascade="all, delete-orphan")


class SourceRun(Base):
    __tablename__ = "source_runs"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    source_id = Column(String(36), ForeignKey("job_sources.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    duration_seconds = Column(Integer)
    jobs_found = Column(Integer, default=0)
    new_jobs = Column(Integer, default=0)
    duplicates = Column(Integer, default=0)
    failed_jobs = Column(Integer, default=0)
    status = Column(String(50))
    error_message = Column(Text)
    queries_run = Column(JSON)
    details = Column(JSON)

    source = relationship("JobSource", back_populates="runs")


class JobSourceMapping(Base):
    __tablename__ = "job_source_mappings"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)
    source_id = Column(String(36), ForeignKey("job_sources.id"), nullable=False)
    source_job_id = Column(String(255))
    source_url = Column(String(500))
    discovered_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="source_mappings")
    source = relationship("JobSource")


class SchedulerConfig(Base):
    __tablename__ = "scheduler_config"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    enabled = Column(Boolean, default=True)
    frequency_minutes = Column(Integer, default=60)
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    running = Column(Boolean, default=False)
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    last_error = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SearchProfile(Base):
    __tablename__ = "search_profiles"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(255), nullable=False)
    is_default = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    queries = Column(JSON)
    sources = Column(JSON)
    keywords_include = Column(JSON)
    keywords_exclude = Column(JSON)
    locations = Column(JSON)
    job_types = Column(JSON)
    experience_levels = Column(JSON)
    salary_min = Column(Integer)
    remote_only = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
