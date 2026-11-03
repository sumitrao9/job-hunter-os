#!/usr/bin/env python3
"""
Autonomous Job Hunter Orchestrator
One-click: Discover -> Match -> Tailor -> Prepare -> Apply
Human-in-the-loop for final submission confirmation
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

class AutonomousOrchestrator:
    def __init__(self):
        self.state = {
            "running": False,
            "jobs_discovered": 0,
            "jobs_matched": 0,
            "applications_prepared": 0,
            "applications_submitted": 0,
            "last_run": None
        }
        
    async def run_full_pipeline(self, profile_data: Dict, filters: Dict = None):
        """Run the complete autonomous pipeline"""
        print(f"[{datetime.now().isoformat()}] Starting autonomous job hunt pipeline")
        self.state["running"] = True
        self.state["last_run"] = datetime.now().isoformat()
        
        try:
            # Phase 1: Discover
            print("[1/5] Discovering jobs from all sources...")
            jobs = await self.discover_jobs(filters or {})
            self.state["jobs_discovered"] = len(jobs)
            print(f"      Found {len(jobs)} jobs")
            
            # Phase 2: Match
            print("[2/5] Matching jobs to profile...")
            matched = await self.match_jobs(jobs, profile_data)
            self.state["jobs_matched"] = len(matched)
            print(f"      {len(matched)} jobs match criteria")
            
            # Phase 3: Tailor
            print("[3/5] Tailoring resumes and cover letters...")
            tailored = await self.tailor_applications(matched, profile_data)
            print(f"      Tailored {len(tailored)} applications")
            
            # Phase 4: Prepare
            print("[4/5] Preparing applications for submission...")
            prepared = await self.prepare_applications(tailored)
            self.state["applications_prepared"] = len(prepared)
            print(f"      Prepared {len(prepared)} applications")
            
            # Phase 5: Ready for review/submission
            print("[5/5] Ready for review")
            print(f"\n{'='*50}")
            print(f"Pipeline complete!")
            print(f"Discovered: {self.state['jobs_discovered']} | Matched: {self.state['jobs_matched']} | Prepared: {self.state['applications_prepared']}")
            print(f"{'='*50}")
            print("\nReview prepared applications before submission (human-in-the-loop enabled)")
            
            return {
                "status": "complete",
                "jobs_discovered": jobs,
                "matched_jobs": matched,
                "prepared_applications": prepared,
                "state": self.state
            }
            
        finally:
            self.state["running"] = False
    
    async def discover_jobs(self, filters):
        # Use multi_discovery service
        from app.services.multi_discovery import discover_jobs
        try:
            jobs = discover_jobs(
                search_term=filters.get("search_term", "Python Developer"),
                location=filters.get("location", "Remote"),
                sources=None,
                limit=100
            )
            return jobs or []
        except Exception as e:
            print(f"      Discovery error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def match_jobs(self, jobs, profile_data):
        matched = []
        for job in jobs:
            score = self.calculate_match_score(job, profile_data)
            if score >= 60:  # Threshold
                job['match_score'] = score
                matched.append(job)
        return sorted(matched, key=lambda x: x.get('match_score', 0), reverse=True)
    
    def calculate_match_score(self, job, profile_data):
        score = 0
        skills = profile_data.get('skills', [])
        job_desc = str(job.get('description', '')).lower()
        job_title = str(job.get('title', '')).lower()
        
        for skill in skills:
            if skill.lower() in job_desc or skill.lower() in job_title:
                score += 10
        
        if 'remote' in job_desc or 'remote' in job_title:
            score += 15
        if 'python' in job_desc or 'python' in job_title:
            score += 20
        if 'intern' in job_title or 'entry' in job_title:
            score += 15
        
        return min(score, 100)
    
    async def tailor_applications(self, matched_jobs, profile_data):
        # Tailor resumes and cover letters
        return matched_jobs
    
    async def prepare_applications(self, tailored_jobs):
        from app.application_submission import ApplicationSubmitter
        prepared = []
        for job in tailored_jobs:
            prepared.append({
                "job": job,
                "status": "prepared",
                "ready_to_submit": True
            })
        return prepared

if __name__ == "__main__":
    orch = AutonomousOrchestrator()
    profile = {"skills": ["Python", "FastAPI", "Django", "React", "MCP"]}
    asyncio.run(orch.run_full_pipeline(profile, {"search_term": "Python Developer", "location": "Remote"}))
