"""Knowledge Base with TF-IDF scoring.

Based on the AutoApply project's approach: users upload career documents once,
entries are parsed and categorized, then TF-IDF ranks entries by relevance to
each job description. Relevant entries are injected into AI prompts for
tailored resume/cover letter generation.
"""
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.resume_parser import parse_resume_file
from app.config import settings

SECTION_MARKERS = {
    "experience": ["experience", "work experience", "employment", "career"],
    "skills": ["skills", "technical skills", "core competencies", "expertise"],
    "education": ["education", "academic", "degrees", "credentials"],
    "projects": ["projects", "portfolio", "key projects"],
    "achievements": ["achievements", "accomplishments", "results", "highlights"],
    "summary": ["summary", "profile", "overview", "objective"],
}


@dataclass
class KBCategory:
    name: str
    entries: List[str] = field(default_factory=list)
    tfidf_scores: List[float] = field(default_factory=list)


@dataclass
class KBDocument:
    id: str
    filename: str
    categories: Dict[str, KBCategory] = field(default_factory=dict)
    raw_text: str = ""


class KnowledgeBase:
    """Manages career knowledge entries with TF-IDF relevance scoring."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or os.path.join(settings.upload_dir, "knowledge_base")
        os.makedirs(self.storage_dir, exist_ok=True)
        self._tfidf_vectorizer: Optional["TfidfVectorizer"] = None

    def add_document(self, file_path: str, doc_id: Optional[str] = None) -> str:
        """Add a career document to the knowledge base."""
        import uuid

        doc_id = doc_id or uuid.uuid4().hex
        parsed = parse_resume_file(file_path)
        raw_text = parsed.get("raw_text", "")
        sections = parsed.get("sections", {})

        doc = KBDocument(id=doc_id, filename=os.path.basename(file_path), raw_text=raw_text)

        # Use parsed sections if available, otherwise chunk by section markers.
        for sec_name, entries in sections.items():
            if sec_name in ("email", "phone", "linkedin", "github"):
                continue
            if isinstance(entries, list):
                doc.categories[sec_name] = KBCategory(name=sec_name, entries=[str(e) for e in entries])
            elif isinstance(entries, str):
                doc.categories[sec_name] = KBCategory(name=sec_name, entries=[entries])

        # Fallback: chunk raw text by section markers.
        if not doc.categories:
            doc.categories = self._chunk_by_sections(raw_text)

        # Save to disk.
        doc_path = os.path.join(self.storage_dir, f"{doc_id}.txt")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(raw_text)

        return doc_id

    def _chunk_by_sections(self, text: str) -> Dict[str, KBCategory]:
        """Split text into categories based on section header markers."""
        categories: Dict[str, KBCategory] = {}
        lines = text.split("\n")
        current_category = "general"
        current_lines: List[str] = []

        for line in lines:
            line_lower = line.strip().lower()
            matched = False
            for cat_name, markers in SECTION_MARKERS.items():
                if any(marker in line_lower for marker in markers):
                    if current_lines:
                        categories.setdefault(
                            current_category, KBCategory(name=current_category)
                        ).entries.append("\n".join(current_lines).strip())
                    current_category = cat_name
                    current_lines = []
                    matched = True
                    break
            if not matched:
                current_lines.append(line)

        if current_lines:
            categories.setdefault(
                current_category, KBCategory(name=current_category)
            ).entries.append("\n".join(current_lines).strip())

        return categories

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents in the knowledge base."""
        docs = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".txt"):
                doc_id = filename.replace(".txt", "")
                doc_path = os.path.join(self.storage_dir, filename)
                docs.append({
                    "id": doc_id,
                    "filename": filename,
                    "size_bytes": os.path.getsize(doc_path),
                })
        return docs

    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the knowledge base."""
        doc_path = os.path.join(self.storage_dir, f"{doc_id}.txt")
        if os.path.exists(doc_path):
            os.remove(doc_path)
            return True
        return False

    def score_entries(
        self,
        job_title: str,
        job_description: str,
        category: str = "experience",
        top_n: int = 10,
    ) -> List[Dict[str, Any]]:
        """Score knowledge base entries against a job using TF-IDF cosine similarity.

        Returns the top_n most relevant entries from all documents,
        ranked by similarity to the job title + description.
        """
        # Lazy import sklearn only when needed
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            return self._fallback_scoring(job_title, job_description, category, top_n)

        # Gather all entries across all documents in the storage dir.
        entries: List[str] = []
        sources: List[str] = []

        for doc_file in os.listdir(self.storage_dir):
            if doc_file.endswith(".txt"):
                doc_path = os.path.join(self.storage_dir, doc_file)
                with open(doc_path, "r", encoding="utf-8") as f:
                    text = f.read()
                # Simple chunking by paragraphs.
                paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 20]
                for para in paragraphs:
                    entries.append(para)
                    sources.append(doc_file)

        if not entries:
            return []

        # Build TF-IDF matrix.
        corpus = [f"{job_title}. {job_description}"] + entries
        try:
            self._tfidf_vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 3),
                max_features=1000,
            )
            tfidf_matrix = self._tfidf_vectorizer.fit_transform(corpus)
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
        except Exception:
            return self._fallback_scoring(job_title, job_description, category, top_n)

        # Rank and return top_n.
        ranked = sorted(
            enumerate(similarities), key=lambda x: x[1], reverse=True
        )
        results = []
        for idx, score in ranked[:top_n]:
            if score > 0:
                results.append({
                    "entry": entries[idx],
                    "score": round(float(score), 4),
                    "source": sources[idx],
                })

        return results

    def _fallback_scoring(
        self, job_title: str, job_description: str, category: str, top_n: int
    ) -> List[Dict[str, Any]]:
        """Simple keyword-based fallback when sklearn is unavailable."""
        job_text = f"{job_title} {job_description}".lower()
        job_tokens = set(re.split(r"\W+", job_text)) - {""}

        results: List[Dict[str, Any]] = []
        for doc_file in os.listdir(self.storage_dir):
            if not doc_file.endswith(".txt"):
                continue
            doc_path = os.path.join(self.storage_dir, doc_file)
            with open(doc_path, "r", encoding="utf-8") as f:
                text = f.read()
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 20]
            for para in paragraphs:
                para_tokens = set(re.split(r"\W+", para.lower())) - {""}
                overlap = len(job_tokens & para_tokens)
                if overlap > 0:
                    score = overlap / max(len(job_tokens), 1)
                    results.append({
                        "entry": para,
                        "score": round(score, 4),
                        "source": doc_file,
                    })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_n]


knowledge_base = KnowledgeBase()
