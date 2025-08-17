"""
Career tools service for CV building, cover letter generation, and career advice
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from ..db.database import SessionLocal
from ..db.models import JobPost, User, UserProfile, CareerDocument
import openai
import json

logger = logging.getLogger(__name__)

class CareerToolsService:
    """
    Service for providing career development tools including CV building,
    cover letter generation, and personalized career advice
    """
    
    def __init__(self):
        # Initialize OpenAI client with environment variables
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.max_tokens = int(os.getenv('OPENAI_MAX_TOKENS', '1000'))
        self.temperature = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
        
        if not openai.api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
        
    async def generate_cv_content(self, user_data: Dict, target_role: str = None) -> Dict:
        """
        Generate CV content based on user data and target role
        
        Args:
            user_data: User profile information
            target_role: Optional target role to tailor CV for
            
        Returns:
            Generated CV content with sections
        """
        try:
            # Prepare user information for CV generation
            cv_prompt = self._build_cv_prompt(user_data, target_role)
            
            # Generate CV content using AI (mock implementation for now)
            cv_content = await self._generate_ai_content(cv_prompt, "cv")
            
            # Structure the CV content
            structured_cv = self._structure_cv_content(cv_content, user_data)
            
            # Save generated CV to database
            await self._save_career_document(
                user_data.get('user_id'),
                'cv',
                structured_cv,
                target_role
            )
            
            return {
                "success": True,
                "cv_content": structured_cv,
                "target_role": target_role,
                "generated_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error generating CV content: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def generate_cover_letter(self, user_data: Dict, job_data: Dict) -> Dict:
        """
        Generate a personalized cover letter for a specific job
        
        Args:
            user_data: User profile information
            job_data: Job posting information
            
        Returns:
            Generated cover letter content
        """
        try:
            # Build cover letter prompt
            cover_letter_prompt = self._build_cover_letter_prompt(user_data, job_data)
            
            # Generate cover letter using AI
            cover_letter_content = await self._generate_ai_content(cover_letter_prompt, "cover_letter")
            
            # Structure the cover letter
            structured_letter = self._structure_cover_letter(cover_letter_content, user_data, job_data)
            
            # Save generated cover letter
            await self._save_career_document(
                user_data.get('user_id'),
                'cover_letter',
                structured_letter,
                job_data.get('title')
            )
            
            return {
                "success": True,
                "cover_letter": structured_letter,
                "job_title": job_data.get('title'),
                "company": job_data.get('company'),
                "generated_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def generate_why_work_with_statement(self, user_data: Dict, target_role: str = None) -> Dict:
        """
        Generate a "Why Work With Me" statement
        
        Args:
            user_data: User profile information
            target_role: Optional target role context
            
        Returns:
            Generated statement content
        """
        try:
            # Build statement prompt
            statement_prompt = self._build_statement_prompt(user_data, target_role)
            
            # Generate statement using AI
            statement_content = await self._generate_ai_content(statement_prompt, "statement")
            
            # Structure the statement
            structured_statement = self._structure_statement(statement_content, user_data)
            
            # Save generated statement
            await self._save_career_document(
                user_data.get('user_id'),
                'why_work_with',
                structured_statement,
                target_role
            )
            
            return {
                "success": True,
                "statement": structured_statement,
                "target_role": target_role,
                "generated_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error generating statement: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def get_career_advice(self, user_data: Dict, query: str) -> Dict:
        """
        Provide personalized career advice based on user profile and query
        
        Args:
            user_data: User profile information
            query: Specific career question or area of interest
            
        Returns:
            Personalized career advice
        """
        try:
            # Build career advice prompt
            advice_prompt = self._build_advice_prompt(user_data, query)
            
            # Generate advice using AI
            advice_content = await self._generate_ai_content(advice_prompt, "advice")
            
            # Structure the advice
            structured_advice = self._structure_advice(advice_content, query)
            
            return {
                "success": True,
                "advice": structured_advice,
                "query": query,
                "generated_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error generating career advice: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def _build_cv_prompt(self, user_data: Dict, target_role: str = None) -> str:
        """Build prompt for CV generation"""
        prompt = f"""
Generate a professional CV for the following candidate:

Personal Information:
- Name: {user_data.get('name', 'N/A')}
- Email: {user_data.get('email', 'N/A')}
- Phone: {user_data.get('phone', 'N/A')}
- Location: {user_data.get('location', 'N/A')}

Education:
{user_data.get('education', 'Not specified')}

Work Experience:
{user_data.get('experience', 'Not specified')}

Skills:
{user_data.get('skills', 'Not specified')}

{f"Target Role: {target_role}" if target_role else ""}

Please generate a professional CV with the following sections:
1. Professional Summary
2. Key Skills
3. Work Experience (with achievements)
4. Education
5. Additional sections as appropriate

Focus on quantifiable achievements and tailor content for the Kenyan job market.
"""
        return prompt
        
    def _build_cover_letter_prompt(self, user_data: Dict, job_data: Dict) -> str:
        """Build prompt for cover letter generation"""
        prompt = f"""
Generate a personalized cover letter for the following job application:

Candidate Information:
- Name: {user_data.get('name', 'N/A')}
- Background: {user_data.get('background', 'N/A')}
- Experience: {user_data.get('experience', 'N/A')}
- Skills: {user_data.get('skills', 'N/A')}

Job Information:
- Title: {job_data.get('title', 'N/A')}
- Company: {job_data.get('company', 'N/A')}
- Description: {job_data.get('description', 'N/A')}
- Requirements: {job_data.get('requirements', 'N/A')}

Please generate a compelling cover letter that:
1. Shows enthusiasm for the specific role and company
2. Highlights relevant experience and skills
3. Demonstrates understanding of the job requirements
4. Includes specific examples of achievements
5. Maintains a professional yet personable tone
6. Is appropriate for the Kenyan job market

The letter should be 3-4 paragraphs long.
"""
        return prompt
        
    def _build_statement_prompt(self, user_data: Dict, target_role: str = None) -> str:
        """Build prompt for "Why Work With Me" statement"""
        prompt = f"""
Generate a compelling "Why Work With Me" statement for the following professional:

Professional Information:
- Background: {user_data.get('background', 'N/A')}
- Experience: {user_data.get('experience', 'N/A')}
- Skills: {user_data.get('skills', 'N/A')}
- Achievements: {user_data.get('achievements', 'N/A')}
- Values: {user_data.get('values', 'N/A')}

{f"Target Role Context: {target_role}" if target_role else ""}

Please generate a powerful statement that:
1. Highlights unique value proposition
2. Showcases key strengths and differentiators
3. Includes specific examples of impact
4. Demonstrates passion and commitment
5. Shows understanding of what employers value
6. Is confident but not arrogant
7. Is relevant to the Kenyan job market

The statement should be 2-3 paragraphs long and compelling.
"""
        return prompt
        
    def _build_advice_prompt(self, user_data: Dict, query: str) -> str:
        """Build prompt for career advice"""
        prompt = f"""
Provide personalized career advice for the following professional:

Professional Profile:
- Background: {user_data.get('background', 'N/A')}
- Current Role: {user_data.get('current_role', 'N/A')}
- Experience Level: {user_data.get('experience_level', 'N/A')}
- Skills: {user_data.get('skills', 'N/A')}
- Career Goals: {user_data.get('career_goals', 'N/A')}
- Location: {user_data.get('location', 'Kenya')}

Career Question/Query:
{query}

Please provide specific, actionable career advice that:
1. Addresses the specific query
2. Considers the Kenyan job market context
3. Provides practical next steps
4. Includes relevant resources or suggestions
5. Is tailored to their experience level and background
6. Considers current market trends
7. Is encouraging and realistic

Provide structured advice with clear action items.
"""
        return prompt
        
    async def _generate_ai_content(self, prompt: str, content_type: str) -> str:
        """
        Generate content using AI (mock implementation)
        In production, this would use OpenAI API or similar
        """
        # Mock AI response - in production, replace with actual AI API call
        mock_responses = {
            "cv": """
PROFESSIONAL SUMMARY
Results-driven professional with proven track record in delivering high-quality solutions and driving business growth. Strong analytical skills combined with excellent communication abilities and a passion for continuous learning.

KEY SKILLS
• Technical Skills: Python, SQL, Data Analysis, Project Management
• Soft Skills: Leadership, Communication, Problem-solving, Team Collaboration
• Industry Knowledge: Business Analysis, Process Improvement, Strategic Planning

WORK EXPERIENCE
Senior Analyst | ABC Company | 2020 - Present
• Led data analysis projects resulting in 15% improvement in operational efficiency
• Collaborated with cross-functional teams to implement process improvements
• Mentored junior team members and contributed to team development initiatives

EDUCATION
Bachelor of Science in Business Administration
University of Nairobi | 2018
• Graduated with Second Class Honors (Upper Division)
• Relevant coursework: Statistics, Business Analytics, Strategic Management
            """,
            "cover_letter": """
Dear Hiring Manager,

I am writing to express my strong interest in the [Job Title] position at [Company Name]. With my background in [relevant field] and proven track record of [specific achievement], I am excited about the opportunity to contribute to your team's success.

In my previous role at [Previous Company], I successfully [specific example of relevant work], which directly aligns with the requirements outlined in your job posting. My experience in [relevant skill/area] has equipped me with the skills necessary to excel in this position, particularly in [specific job requirement].

What sets me apart is my ability to [unique strength/skill] combined with my passion for [relevant area]. I am particularly drawn to [Company Name] because of [specific reason related to company/role], and I believe my skills in [relevant skills] would be valuable additions to your team.

I would welcome the opportunity to discuss how my experience and enthusiasm can contribute to [Company Name]'s continued success. Thank you for considering my application.

Sincerely,
[Your Name]
            """,
            "statement": """
Why Work With Me:

I bring a unique combination of analytical expertise and creative problem-solving that drives measurable results. Throughout my career, I have consistently delivered projects that exceed expectations while building strong relationships with colleagues and stakeholders.

My approach is collaborative and results-focused. I believe in understanding the bigger picture while paying attention to crucial details. Whether leading a team or contributing as a team member, I bring energy, reliability, and a commitment to excellence that helps organizations achieve their goals.

What makes me different is my ability to translate complex ideas into actionable solutions, combined with my genuine passion for continuous learning and improvement. I thrive in dynamic environments and am always looking for ways to add value and drive positive change.
            """,
            "advice": """
Based on your profile and career goals, here's my personalized advice:

IMMEDIATE ACTIONS (Next 1-3 months):
1. Skill Development: Focus on enhancing your [specific skills] through online courses or certifications
2. Network Building: Connect with professionals in your target industry through LinkedIn and local events
3. Portfolio Enhancement: Document your achievements and create a portfolio showcasing your best work

MEDIUM-TERM STRATEGY (3-12 months):
1. Industry Research: Stay updated on trends in your field and identify emerging opportunities
2. Professional Branding: Develop a strong online presence that reflects your expertise
3. Mentorship: Seek out mentors in your desired career path and consider mentoring others

LONG-TERM PLANNING (1-3 years):
1. Career Positioning: Position yourself for leadership roles by taking on challenging projects
2. Continuous Learning: Pursue advanced certifications or additional education as needed
3. Strategic Networking: Build relationships with decision-makers in your target companies

Remember, career growth is a marathon, not a sprint. Focus on consistent progress and stay adaptable to market changes.
            """
        }
        
        return mock_responses.get(content_type, "Generated content would appear here.")
        
    def _structure_cv_content(self, content: str, user_data: Dict) -> Dict:
        """Structure CV content into organized sections"""
        return {
            "personal_info": {
                "name": user_data.get('name', ''),
                "email": user_data.get('email', ''),
                "phone": user_data.get('phone', ''),
                "location": user_data.get('location', '')
            },
            "content": content,
            "sections": [
                "Professional Summary",
                "Key Skills", 
                "Work Experience",
                "Education",
                "Additional Information"
            ],
            "format": "professional",
            "length": "2-3 pages"
        }
        
    def _structure_cover_letter(self, content: str, user_data: Dict, job_data: Dict) -> Dict:
        """Structure cover letter content"""
        return {
            "content": content,
            "job_title": job_data.get('title', ''),
            "company": job_data.get('company', ''),
            "applicant_name": user_data.get('name', ''),
            "date": datetime.utcnow().strftime("%B %d, %Y"),
            "format": "business_letter",
            "length": "3-4 paragraphs"
        }
        
    def _structure_statement(self, content: str, user_data: Dict) -> Dict:
        """Structure "Why Work With Me" statement"""
        return {
            "content": content,
            "applicant_name": user_data.get('name', ''),
            "focus_areas": [
                "Unique Value Proposition",
                "Key Strengths",
                "Professional Impact",
                "Future Potential"
            ],
            "format": "narrative",
            "length": "2-3 paragraphs"
        }
        
    def _structure_advice(self, content: str, query: str) -> Dict:
        """Structure career advice content"""
        return {
            "content": content,
            "query": query,
            "categories": [
                "Immediate Actions",
                "Medium-term Strategy", 
                "Long-term Planning"
            ],
            "format": "structured_advice",
            "actionable": True
        }
        
    async def _save_career_document(self, user_id: int, document_type: str, content: Dict, context: str = None):
        """Save generated career document to database"""
        if not user_id:
            return
            
        db = SessionLocal()
        try:
            document = CareerDocument(
                user_id=user_id,
                document_type=document_type,
                content=json.dumps(content),
                context=context,
                created_at=datetime.utcnow()
            )
            db.add(document)
            db.commit()
            logger.info(f"Saved {document_type} document for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving career document: {e}")
            db.rollback()
        finally:
            db.close()
            
    async def get_user_documents(self, user_id: int, document_type: str = None) -> List[Dict]:
        """Get saved career documents for a user"""
        db = SessionLocal()
        try:
            query = db.query(CareerDocument).filter(CareerDocument.user_id == user_id)
            
            if document_type:
                query = query.filter(CareerDocument.document_type == document_type)
                
            documents = query.order_by(CareerDocument.created_at.desc()).all()
            
            return [
                {
                    "id": doc.id,
                    "document_type": doc.document_type,
                    "content": json.loads(doc.content),
                    "context": doc.context,
                    "created_at": doc.created_at
                }
                for doc in documents
            ]
            
        except Exception as e:
            logger.error(f"Error getting user documents: {e}")
            return []
        finally:
            db.close()

# Global service instance
career_tools_service = CareerToolsService()
