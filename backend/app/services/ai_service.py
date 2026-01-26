import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from ..ml.embeddings import embed_text, generate_embeddings

try:
    from sentence_transformers import SentenceTransformer  # type: ignore

    HAS_SENTENCE_TRANSFORMERS = True
except Exception:
    SentenceTransformer = None  # type: ignore
    HAS_SENTENCE_TRANSFORMERS = False
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import openai
from sqlalchemy.orm import Session
from sqlalchemy import select, text

from ..db.models import JobPost, Skill, UserProfile, User
from ..core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        # Initialize sentence transformer for embeddings
        self.embedding_model = None
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000, stop_words="english", ngram_range=(1, 2)
        )

        # OpenAI client
        if hasattr(settings, "OPENAI_API_KEY") and settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY

        # Skills extraction patterns
        self.skill_patterns = {
            "programming": [
                "python",
                "java",
                "javascript",
                "typescript",
                "c++",
                "c#",
                "php",
                "ruby",
                "go",
                "rust",
            ],
            "web_development": [
                "html",
                "css",
                "react",
                "angular",
                "vue",
                "node.js",
                "express",
                "django",
                "flask",
            ],
            "data_science": [
                "pandas",
                "numpy",
                "scikit-learn",
                "tensorflow",
                "pytorch",
                "r",
                "stata",
                "spss",
            ],
            "databases": [
                "sql",
                "mysql",
                "postgresql",
                "mongodb",
                "redis",
                "elasticsearch",
            ],
            "cloud": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform"],
            "business": [
                "excel",
                "powerpoint",
                "project management",
                "agile",
                "scrum",
                "leadership",
            ],
            "design": [
                "photoshop",
                "illustrator",
                "figma",
                "sketch",
                "ui/ux",
                "graphic design",
            ],
        }

    def _get_embedding_model(self):
        """Lazy-load a real SentenceTransformer if available, otherwise use internal embedder."""
        if self.embedding_model is None:
            if HAS_SENTENCE_TRANSFORMERS and SentenceTransformer is not None:
                try:
                    self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                    logger.info("Loaded sentence-transformers model for embeddings")
                except Exception as e:
                    logger.warning(
                        f"Failed to load sentence-transformers model: {e}; falling back to internal embedder"
                    )
                    self.embedding_model = "internal_hash_embedder"
            else:
                self.embedding_model = "internal_hash_embedder"
        return self.embedding_model

    def generate_job_embedding(self, job_post: JobPost) -> List[float]:
        """Generate semantic embedding for a job posting."""
        try:
            # Combine job text fields
            text_parts = []
            if job_post.title_raw:
                text_parts.append(job_post.title_raw)
            if job_post.description_raw:
                text_parts.append(job_post.description_raw[:1000])  # Limit length
            if job_post.requirements_raw:
                text_parts.append(job_post.requirements_raw[:500])

            combined_text = " ".join(text_parts)

            if not combined_text.strip():
                return [0.0] * settings.EMBEDDING_DIM

            model = self._get_embedding_model()
            if model != "internal_hash_embedder":
                try:
                    emb = model.encode(combined_text, convert_to_tensor=False)
                    # sentence-transformers returns numpy array or list
                    return emb.tolist() if hasattr(emb, "tolist") else list(emb)
                except Exception as e:
                    logger.error(
                        f"Error generating embedding with sentence-transformers: {e}; falling back"
                    )
            # Fallback to internal embedding implementation
            embedding = embed_text(combined_text)
            return embedding

        except Exception as e:
            logger.error(f"Error generating job embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 384

    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for search query."""
        try:
            model = self._get_embedding_model()
            if model != "internal_hash_embedder":
                try:
                    emb = model.encode(query, convert_to_tensor=False)
                    return emb.tolist() if hasattr(emb, "tolist") else list(emb)
                except Exception as e:
                    logger.error(
                        f"Error generating query embedding with sentence-transformers: {e}; falling back"
                    )
            # Fallback
            embedding = embed_text(query)
            return embedding
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            return [0.0] * 384

    def calculate_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity between two embeddings."""
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1).reshape(1, -1)
            vec2 = np.array(embedding2).reshape(1, -1)

            # Calculate cosine similarity
            similarity = cosine_similarity(vec1, vec2)[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0

    def extract_skills_from_text(self, text: str) -> Dict[str, float]:
        """Extract skills from job description or user profile text."""
        if not text:
            return {}

        text_lower = text.lower()
        extracted_skills = {}

        # Check for known skills
        for category, skills in self.skill_patterns.items():
            for skill in skills:
                if skill.lower() in text_lower:
                    # Simple confidence based on frequency and context
                    count = text_lower.count(skill.lower())
                    confidence = min(count * 0.3 + 0.4, 1.0)
                    extracted_skills[skill] = confidence

        return extracted_skills

    def calculate_skill_match(
        self, user_skills: Dict[str, float], job_skills: Dict[str, float]
    ) -> Tuple[float, List[str], List[str]]:
        """Calculate skill match between user and job."""
        if not user_skills or not job_skills:
            return 0.0, [], []

        user_skill_set = set(user_skills.keys())
        job_skill_set = set(job_skills.keys())

        # Find matching and missing skills
        matching_skills = list(user_skill_set.intersection(job_skill_set))
        missing_skills = list(job_skill_set - user_skill_set)

        if not job_skill_set:
            return 0.0, [], []

        # Calculate match score
        match_score = len(matching_skills) / len(job_skill_set)

        # Weight by skill confidence
        weighted_match = 0.0
        total_weight = 0.0

        for skill in job_skill_set:
            job_confidence = job_skills.get(skill, 0.5)
            user_confidence = user_skills.get(skill, 0.0)

            weighted_match += job_confidence * user_confidence
            total_weight += job_confidence

        if total_weight > 0:
            match_score = weighted_match / total_weight

        # Return top 3 missing skills
        missing_skills_sorted = sorted(
            missing_skills, key=lambda x: job_skills.get(x, 0), reverse=True
        )[:3]

        return match_score, matching_skills, missing_skills_sorted

    async def generate_career_advice(
        self, user_profile: UserProfile, query: str
    ) -> str:
        """Generate AI-powered career advice."""
        try:
            if not hasattr(settings, "OPENAI_API_KEY") or not settings.OPENAI_API_KEY:
                return "AI career advice requires OpenAI API configuration."

            # Prepare context
            context = f"""
            User Profile:
            - Current Role: {user_profile.current_role or "Not specified"}
            - Experience Level: {user_profile.experience_level or "Not specified"}
            - Education: {user_profile.education or "Not specified"}
            - Skills: {", ".join(user_profile.skills.keys()) if user_profile.skills else "Not specified"}
            - Career Goals: {user_profile.career_goals or "Not specified"}
            - Preferred Locations: {", ".join(user_profile.preferred_locations) if user_profile.preferred_locations else "Not specified"}
            
            User Question: {query}
            """

            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a career advisor for the Kenyan job market. Provide practical, actionable advice based on the user's profile and question. Keep responses concise and focused on the Kenyan context.",
                    },
                    {"role": "user", "content": context},
                ],
                max_tokens=500,
                temperature=0.7,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating career advice: {e}")
            return "I'm sorry, I couldn't generate career advice at the moment. Please try again later."

    async def generate_interview_questions(
        self, job_title: str, company_name: str, job_description: str = ""
    ) -> List[str]:
        """Generate AI-powered interview questions for a specific role."""
        try:
            if not hasattr(settings, "OPENAI_API_KEY") or not settings.OPENAI_API_KEY:
                return [
                    "Tell me about yourself and your experience.",
                    "Why are you interested in this role?",
                    "What are your greatest strengths?",
                    "Where do you see yourself in 5 years?",
                    "Why do you want to work for this company?",
                ]

            prompt = f"""
            Generate 8-10 relevant interview questions for a {job_title} position at {company_name}.
            
            Job Description: {job_description[:500] if job_description else "Not provided"}
            
            Include a mix of:
            - General behavioral questions
            - Role-specific technical questions
            - Company culture fit questions
            - Situational questions
            
            Focus on questions commonly asked in the Kenyan job market.
            """

            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an HR expert who creates interview questions. Generate practical, relevant questions that help assess candidates effectively.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=800,
                temperature=0.6,
            )

            # Parse response into list of questions
            content = response.choices[0].message.content.strip()
            questions = [
                q.strip()
                for q in content.split("\n")
                if q.strip() and ("?" in q or q.strip().endswith("."))
            ]

            return questions[:10]  # Limit to 10 questions

        except Exception as e:
            logger.error(f"Error generating interview questions: {e}")
            return [
                "Tell me about yourself and your experience.",
                "Why are you interested in this role?",
                "What are your greatest strengths and weaknesses?",
                "Describe a challenging project you worked on.",
                "How do you handle pressure and deadlines?",
                "Why do you want to work for this company?",
                "Where do you see yourself in 5 years?",
                "What motivates you in your work?",
                "How do you stay updated with industry trends?",
                "Do you have any questions for us?",
            ]

    def calculate_job_match_score(
        self,
        user_profile: UserProfile,
        job_post: JobPost,
        job_embedding: List[float] = None,
        job_location_text: str | None = None,
        user_keywords: List[str] | None = None,
    ) -> Dict[str, Any]:
        """Calculate comprehensive job match score for a user."""
        try:
            scores = {
                "overall_score": 0.0,
                "skill_match": 0.0,
                "location_match": 0.0,
                "experience_match": 0.0,
                "salary_match": 0.0,
                "keyword_match": 0.0,
                "explanation": "",
                "matching_skills": [],
                "missing_skills": [],
            }

            job_text_parts = [
                job_post.title_raw or "",
                job_post.description_raw or "",
                job_post.requirements_raw or "",
            ]
            job_text = " ".join(part for part in job_text_parts if part).strip()

            # Skill matching
            if user_profile.skills and job_text:
                job_skills = self.extract_skills_from_text(job_text)
                skill_score, matching_skills, missing_skills = (
                    self.calculate_skill_match(user_profile.skills, job_skills)
                )
                scores["skill_match"] = skill_score
                scores["matching_skills"] = matching_skills
                scores["missing_skills"] = missing_skills

            # Location matching
            if user_profile.preferred_locations and (job_location_text or job_text):
                location_blob = f"{job_location_text or ''} {job_text}".lower()
                matches = [
                    loc
                    for loc in user_profile.preferred_locations
                    if loc and str(loc).lower() in location_blob
                ]
                if matches:
                    scores["location_match"] = min(
                        len(matches) / len(user_profile.preferred_locations), 1.0
                    )

            # Experience level matching
            if user_profile.experience_level and job_post.seniority:
                exp_match = self._match_experience_level(
                    user_profile.experience_level, job_post.seniority
                )
                scores["experience_match"] = exp_match

            # Salary matching
            if (
                user_profile.salary_expectations
                and job_post.salary_min
                and job_post.salary_max
            ):
                salary_match = self._match_salary_expectations(
                    user_profile.salary_expectations,
                    job_post.salary_min,
                    job_post.salary_max,
                )
                scores["salary_match"] = salary_match

            # Keyword matching (skills, goals, search history)
            keywords = user_keywords or self._extract_user_keywords(user_profile)
            if keywords and job_text:
                keyword_score, _ = self._keyword_match_score(job_text, keywords)
                scores["keyword_match"] = keyword_score

            # Calculate overall score (weighted average)
            weights = {
                "skill_match": 0.4,
                "keyword_match": 0.2,
                "location_match": 0.15,
                "experience_match": 0.15,
                "salary_match": 0.1,
            }

            weighted_sum = 0.0
            weight_total = 0.0
            for key, weight in weights.items():
                value = scores.get(key, 0.0)
                if value > 0:
                    weighted_sum += value * weight
                    weight_total += weight

            scores["overall_score"] = (
                weighted_sum / weight_total if weight_total else 0.0
            )
            scores["explanation"] = self._generate_match_explanation(scores, job_post)

            return scores

        except Exception as e:
            logger.error(f"Error calculating job match score: {e}")
            return {
                "overall_score": 0.0,
                "skill_match": 0.0,
                "location_match": 0.0,
                "experience_match": 0.0,
                "salary_match": 0.0,
                "keyword_match": 0.0,
                "explanation": "Unable to calculate match score",
                "matching_skills": [],
                "missing_skills": [],
            }

    def _match_experience_level(self, user_level: str, job_level: str) -> float:
        """Match user experience level with job requirements."""
        level_hierarchy = {
            "entry": 1,
            "junior": 1,
            "mid": 2,
            "intermediate": 2,
            "senior": 3,
            "lead": 3,
            "executive": 4,
            "director": 4,
        }

        user_score = level_hierarchy.get(user_level.lower(), 2)
        job_score = level_hierarchy.get(job_level.lower(), 2)

        # Perfect match
        if user_score == job_score:
            return 1.0
        # One level difference
        elif abs(user_score - job_score) == 1:
            return 0.7
        # Two levels difference
        elif abs(user_score - job_score) == 2:
            return 0.4
        else:
            return 0.1

    def _match_salary_expectations(
        self, expectations: Dict, job_min: float, job_max: float
    ) -> float:
        """Match salary expectations with job offer."""
        try:
            user_min = expectations.get("min", 0)
            user_max = expectations.get("max", float("inf"))

            # Check if there's overlap
            if job_max >= user_min and job_min <= user_max:
                # Calculate overlap percentage
                overlap_start = max(job_min, user_min)
                overlap_end = min(job_max, user_max)
                overlap_size = overlap_end - overlap_start

                user_range = (
                    user_max - user_min
                    if user_max != float("inf")
                    else job_max - user_min
                )
                job_range = job_max - job_min

                if user_range > 0 and job_range > 0:
                    overlap_ratio = overlap_size / min(user_range, job_range)
                    return min(overlap_ratio, 1.0)

            return 0.0

        except Exception:
            return 0.5  # Neutral score if calculation fails

    def _extract_user_keywords(self, user_profile: UserProfile) -> List[str]:
        keywords = set()
        if user_profile.skills:
            for skill in user_profile.skills.keys():
                if skill:
                    keywords.add(str(skill).strip().lower())

        for field in (
            user_profile.current_role,
            user_profile.career_goals,
            user_profile.education,
        ):
            if not field:
                continue
            for token in self._split_keywords(field):
                keywords.add(token)

        return sorted(keywords)

    def _split_keywords(self, text: str) -> List[str]:
        tokens = []
        for chunk in str(text).replace("|", ",").replace("/", ",").split(","):
            chunk = chunk.strip().lower()
            if len(chunk) < 3:
                continue
            tokens.append(chunk)
        return tokens

    def _keyword_match_score(self, text: str, keywords: List[str]):
        if not keywords or not text:
            return 0.0, []
        haystack = text.lower()
        matched = [kw for kw in keywords if kw in haystack]
        if not matched:
            return 0.0, []
        return min(len(matched) / len(keywords), 1.0), matched

    def _generate_match_explanation(self, scores: Dict, job_post: JobPost) -> str:
        """Generate human-readable explanation for job match."""
        explanations = []

        if scores["skill_match"] > 0.7:
            explanations.append("Strong skill match")
        elif scores["skill_match"] > 0.4:
            explanations.append("Good skill alignment")
        elif scores["skill_match"] > 0:
            explanations.append("Some relevant skills")

        if scores["experience_match"] > 0.8:
            explanations.append("Perfect experience level match")
        elif scores["experience_match"] > 0.5:
            explanations.append("Compatible experience level")

        if scores["location_match"] > 0.7:
            explanations.append("Preferred location")

        if scores.get("keyword_match", 0) > 0.5:
            explanations.append("Matches your interests")

        if scores["salary_match"] > 0.7:
            explanations.append("Salary expectations met")

        if not explanations:
            explanations.append("Basic compatibility")

        return ", ".join(explanations)


# Global AI service instance
ai_service = AIService()
