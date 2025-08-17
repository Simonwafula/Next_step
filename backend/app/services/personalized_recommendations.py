import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, desc, func

from ..db.models import (
    User, UserProfile, JobPost, UserJobRecommendation, 
    SavedJob, JobApplication, SearchHistory, Organization, Location
)
from .ai_service import ai_service

logger = logging.getLogger(__name__)

class PersonalizedRecommendationService:
    def __init__(self):
        self.ai_service = ai_service
    
    async def generate_recommendations_for_user(self, db: Session, user: User, limit: int = 20) -> List[Dict[str, Any]]:
        """Generate personalized job recommendations for a user."""
        try:
            # Get user profile
            profile = user.profile
            if not profile:
                logger.warning(f"No profile found for user {user.id}")
                return []
            
            # Get recent job postings (last 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # Build base query
            stmt = select(JobPost, Organization, Location).join(
                Organization, Organization.id == JobPost.org_id, isouter=True
            ).join(
                Location, Location.id == JobPost.location_id, isouter=True
            ).where(
                and_(
                    JobPost.first_seen >= cutoff_date,
                    JobPost.description_raw.is_not(None)
                )
            )
            
            # Apply user preferences
            if profile.preferred_locations:
                location_conditions = []
                for loc in profile.preferred_locations:
                    location_conditions.extend([
                        Location.city.ilike(f"%{loc}%"),
                        Location.region.ilike(f"%{loc}%"),
                        Location.country.ilike(f"%{loc}%")
                    ])
                if location_conditions:
                    stmt = stmt.where(or_(*location_conditions))
            
            # Apply experience level filter
            if profile.experience_level:
                exp_conditions = self._get_experience_conditions(profile.experience_level)
                if exp_conditions:
                    stmt = stmt.where(or_(*exp_conditions))
            
            # Apply salary filter
            if profile.salary_expectations:
                salary_conditions = self._get_salary_conditions(profile.salary_expectations)
                if salary_conditions:
                    stmt = stmt.where(and_(*salary_conditions))
            
            # Exclude already applied/saved jobs
            applied_job_ids = self._get_applied_job_ids(db, user.id)
            saved_job_ids = self._get_saved_job_ids(db, user.id)
            excluded_ids = applied_job_ids + saved_job_ids
            
            if excluded_ids:
                stmt = stmt.where(~JobPost.id.in_(excluded_ids))
            
            # Limit results for processing
            stmt = stmt.limit(100)
            
            # Execute query
            results = db.execute(stmt).all()
            
            # Calculate match scores for each job
            recommendations = []
            for job_post, org, location in results:
                try:
                    # Calculate comprehensive match score
                    match_data = self.ai_service.calculate_job_match_score(profile, job_post)
                    
                    # Skip jobs with very low match scores
                    if match_data['overall_score'] < 0.2:
                        continue
                    
                    recommendation = {
                        'job_id': job_post.id,
                        'title': job_post.title_raw,
                        'company': org.name if org else 'Unknown Company',
                        'location': self._format_location(location),
                        'url': job_post.url,
                        'salary_range': self._format_salary(job_post),
                        'seniority': job_post.seniority,
                        'first_seen': job_post.first_seen.isoformat(),
                        'match_score': round(match_data['overall_score'], 2),
                        'skill_match': round(match_data['skill_match'], 2),
                        'experience_match': round(match_data['experience_match'], 2),
                        'location_match': round(match_data['location_match'], 2),
                        'salary_match': round(match_data['salary_match'], 2),
                        'explanation': match_data['explanation'],
                        'matching_skills': match_data['matching_skills'][:5],  # Top 5
                        'missing_skills': match_data['missing_skills'][:3],    # Top 3
                        'description_preview': job_post.description_raw[:200] + "..." if job_post.description_raw else ""
                    }
                    
                    recommendations.append(recommendation)
                    
                except Exception as e:
                    logger.error(f"Error processing job {job_post.id}: {e}")
                    continue
            
            # Sort by match score
            recommendations.sort(key=lambda x: x['match_score'], reverse=True)
            
            # Store recommendations in database
            await self._store_recommendations(db, user.id, recommendations[:limit])
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error generating recommendations for user {user.id}: {e}")
            return []
    
    async def get_stored_recommendations(self, db: Session, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get stored recommendations for a user."""
        try:
            # Get recent recommendations (last 7 days)
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            stmt = select(
                UserJobRecommendation, JobPost, Organization, Location
            ).join(
                JobPost, JobPost.id == UserJobRecommendation.job_post_id
            ).join(
                Organization, Organization.id == JobPost.org_id, isouter=True
            ).join(
                Location, Location.id == JobPost.location_id, isouter=True
            ).where(
                and_(
                    UserJobRecommendation.user_id == user_id,
                    UserJobRecommendation.recommended_at >= cutoff_date,
                    UserJobRecommendation.is_active == True
                )
            ).order_by(desc(UserJobRecommendation.match_score)).limit(limit)
            
            results = db.execute(stmt).all()
            
            recommendations = []
            for rec, job_post, org, location in results:
                recommendation = {
                    'job_id': job_post.id,
                    'title': job_post.title_raw,
                    'company': org.name if org else 'Unknown Company',
                    'location': self._format_location(location),
                    'url': job_post.url,
                    'salary_range': self._format_salary(job_post),
                    'seniority': job_post.seniority,
                    'first_seen': job_post.first_seen.isoformat(),
                    'recommended_at': rec.recommended_at.isoformat(),
                    'match_score': round(rec.match_score, 2),
                    'skill_match': round(rec.skill_match_score, 2),
                    'experience_match': round(rec.experience_match_score, 2),
                    'location_match': round(rec.location_match_score, 2),
                    'salary_match': round(rec.salary_match_score, 2),
                    'explanation': rec.match_explanation,
                    'matching_skills': rec.matching_skills,
                    'missing_skills': rec.missing_skills,
                    'viewed': rec.viewed,
                    'clicked': rec.clicked,
                    'description_preview': job_post.description_raw[:200] + "..." if job_post.description_raw else ""
                }
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting stored recommendations for user {user_id}: {e}")
            return []
    
    async def mark_recommendation_interaction(self, db: Session, user_id: int, job_id: int, 
                                           interaction_type: str) -> bool:
        """Mark user interaction with a recommendation."""
        try:
            stmt = select(UserJobRecommendation).where(
                and_(
                    UserJobRecommendation.user_id == user_id,
                    UserJobRecommendation.job_post_id == job_id
                )
            )
            
            recommendation = db.execute(stmt).scalar_one_or_none()
            if not recommendation:
                return False
            
            if interaction_type == 'viewed':
                recommendation.viewed = True
            elif interaction_type == 'clicked':
                recommendation.clicked = True
                recommendation.viewed = True
            elif interaction_type == 'dismissed':
                recommendation.dismissed = True
                recommendation.is_active = False
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error marking recommendation interaction: {e}")
            return False
    
    async def get_recommendation_insights(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get insights about user's recommendation performance."""
        try:
            # Get recommendation stats
            total_stmt = select(func.count(UserJobRecommendation.id)).where(
                UserJobRecommendation.user_id == user_id
            )
            total_recommendations = db.execute(total_stmt).scalar() or 0
            
            viewed_stmt = select(func.count(UserJobRecommendation.id)).where(
                and_(
                    UserJobRecommendation.user_id == user_id,
                    UserJobRecommendation.viewed == True
                )
            )
            viewed_count = db.execute(viewed_stmt).scalar() or 0
            
            clicked_stmt = select(func.count(UserJobRecommendation.id)).where(
                and_(
                    UserJobRecommendation.user_id == user_id,
                    UserJobRecommendation.clicked == True
                )
            )
            clicked_count = db.execute(clicked_stmt).scalar() or 0
            
            # Get average match score
            avg_score_stmt = select(func.avg(UserJobRecommendation.match_score)).where(
                UserJobRecommendation.user_id == user_id
            )
            avg_match_score = db.execute(avg_score_stmt).scalar() or 0.0
            
            # Get top matching skills
            top_skills_stmt = select(UserJobRecommendation.matching_skills).where(
                and_(
                    UserJobRecommendation.user_id == user_id,
                    UserJobRecommendation.matching_skills.is_not(None)
                )
            ).limit(50)
            
            skill_results = db.execute(top_skills_stmt).scalars().all()
            all_skills = []
            for skills_list in skill_results:
                if skills_list:
                    all_skills.extend(skills_list)
            
            # Count skill frequency
            skill_counts = {}
            for skill in all_skills:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
            
            top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                'total_recommendations': total_recommendations,
                'viewed_count': viewed_count,
                'clicked_count': clicked_count,
                'view_rate': round(viewed_count / total_recommendations * 100, 1) if total_recommendations > 0 else 0,
                'click_rate': round(clicked_count / total_recommendations * 100, 1) if total_recommendations > 0 else 0,
                'average_match_score': round(avg_match_score, 2),
                'top_matching_skills': [{'skill': skill, 'frequency': count} for skill, count in top_skills],
                'recommendation_quality': self._assess_recommendation_quality(avg_match_score, viewed_count, clicked_count, total_recommendations)
            }
            
        except Exception as e:
            logger.error(f"Error getting recommendation insights for user {user_id}: {e}")
            return {}
    
    def _get_experience_conditions(self, user_experience: str):
        """Get SQL conditions for experience level matching."""
        conditions = []
        
        if user_experience.lower() in ['entry', 'junior']:
            conditions.extend([
                JobPost.seniority.ilike('%entry%'),
                JobPost.seniority.ilike('%junior%'),
                JobPost.seniority.ilike('%graduate%'),
                JobPost.seniority.ilike('%trainee%')
            ])
        elif user_experience.lower() in ['mid', 'intermediate']:
            conditions.extend([
                JobPost.seniority.ilike('%mid%'),
                JobPost.seniority.ilike('%intermediate%'),
                JobPost.seniority.ilike('%associate%')
            ])
        elif user_experience.lower() in ['senior', 'lead']:
            conditions.extend([
                JobPost.seniority.ilike('%senior%'),
                JobPost.seniority.ilike('%lead%'),
                JobPost.seniority.ilike('%principal%')
            ])
        elif user_experience.lower() in ['executive', 'director']:
            conditions.extend([
                JobPost.seniority.ilike('%executive%'),
                JobPost.seniority.ilike('%director%'),
                JobPost.seniority.ilike('%manager%'),
                JobPost.seniority.ilike('%head%')
            ])
        
        return conditions
    
    def _get_salary_conditions(self, salary_expectations: Dict):
        """Get SQL conditions for salary matching."""
        conditions = []
        
        user_min = salary_expectations.get('min')
        user_max = salary_expectations.get('max')
        
        if user_min:
            # Job max salary should be at least user minimum
            conditions.append(JobPost.salary_max >= user_min)
        
        if user_max:
            # Job min salary should not exceed user maximum
            conditions.append(JobPost.salary_min <= user_max)
        
        return conditions
    
    def _get_applied_job_ids(self, db: Session, user_id: int) -> List[int]:
        """Get job IDs that user has already applied to."""
        try:
            stmt = select(JobApplication.job_post_id).where(JobApplication.user_id == user_id)
            results = db.execute(stmt).scalars().all()
            return list(results)
        except Exception:
            return []
    
    def _get_saved_job_ids(self, db: Session, user_id: int) -> List[int]:
        """Get job IDs that user has already saved."""
        try:
            stmt = select(SavedJob.job_post_id).where(SavedJob.user_id == user_id)
            results = db.execute(stmt).scalars().all()
            return list(results)
        except Exception:
            return []
    
    def _format_location(self, location: Optional[Location]) -> str:
        """Format location for display."""
        if not location:
            return "Location not specified"
        
        parts = []
        if location.city:
            parts.append(location.city)
        if location.region and location.region != location.city:
            parts.append(location.region)
        if location.country and location.country not in parts:
            parts.append(location.country)
        
        return ", ".join(parts) if parts else location.raw or "Location not specified"
    
    def _format_salary(self, job_post: JobPost) -> str:
        """Format salary range for display."""
        if not job_post.salary_min and not job_post.salary_max:
            return "Salary not specified"
        
        currency = job_post.currency or "KSH"
        
        if job_post.salary_min and job_post.salary_max:
            return f"{currency} {job_post.salary_min:,.0f} - {job_post.salary_max:,.0f}"
        elif job_post.salary_min:
            return f"{currency} {job_post.salary_min:,.0f}+"
        elif job_post.salary_max:
            return f"Up to {currency} {job_post.salary_max:,.0f}"
        
        return "Salary not specified"
    
    async def _store_recommendations(self, db: Session, user_id: int, recommendations: List[Dict[str, Any]]):
        """Store recommendations in the database."""
        try:
            # Clear old recommendations (older than 7 days)
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            db.execute(
                select(UserJobRecommendation).where(
                    and_(
                        UserJobRecommendation.user_id == user_id,
                        UserJobRecommendation.recommended_at < cutoff_date
                    )
                )
            )
            
            # Store new recommendations
            for rec in recommendations:
                # Check if recommendation already exists
                existing_stmt = select(UserJobRecommendation).where(
                    and_(
                        UserJobRecommendation.user_id == user_id,
                        UserJobRecommendation.job_post_id == rec['job_id']
                    )
                )
                existing = db.execute(existing_stmt).scalar_one_or_none()
                
                if not existing:
                    recommendation = UserJobRecommendation(
                        user_id=user_id,
                        job_post_id=rec['job_id'],
                        match_score=rec['match_score'],
                        skill_match_score=rec['skill_match'],
                        location_match_score=rec['location_match'],
                        salary_match_score=rec['salary_match'],
                        experience_match_score=rec['experience_match'],
                        match_explanation=rec['explanation'],
                        matching_skills=rec['matching_skills'],
                        missing_skills=rec['missing_skills'],
                        recommended_at=datetime.utcnow(),
                        algorithm_version="v2.0",
                        is_active=True
                    )
                    db.add(recommendation)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error storing recommendations: {e}")
            db.rollback()
    
    def _assess_recommendation_quality(self, avg_score: float, viewed: int, clicked: int, total: int) -> str:
        """Assess the quality of recommendations."""
        if total == 0:
            return "No recommendations yet"
        
        view_rate = viewed / total if total > 0 else 0
        click_rate = clicked / total if total > 0 else 0
        
        if avg_score >= 0.7 and view_rate >= 0.6 and click_rate >= 0.2:
            return "Excellent"
        elif avg_score >= 0.5 and view_rate >= 0.4 and click_rate >= 0.1:
            return "Good"
        elif avg_score >= 0.3 and view_rate >= 0.2:
            return "Fair"
        else:
            return "Needs improvement"

# Global service instance
personalized_recommendations = PersonalizedRecommendationService()
