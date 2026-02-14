"""
Career Visualization Service

Generates visual summaries of career insights:
- Word clouds for responsibilities and skills
- Bar charts for skill frequency
- Pie charts for education/experience distribution
- Heatmaps for career comparisons

Uses matplotlib, wordcloud, and other visualization libraries.
Outputs can be saved as images or returned as base64 for API responses.
"""

import io
import base64
import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None

try:
    from wordcloud import WordCloud

    HAS_WORDCLOUD = True
except ImportError:
    HAS_WORDCLOUD = False
    WordCloud = None

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None


class CareerVisualizer:
    """Generates visual representations of career insights"""

    def __init__(self):
        self.figsize = (10, 6)
        self.colors = {
            "primary": "#2563eb",
            "secondary": "#10b981",
            "accent": "#f59e0b",
            "background": "#f8fafc",
            "text": "#1e293b",
        }

    def generate_wordcloud(
        self,
        text: str,
        title: str = "Key Terms",
        max_words: int = 100,
        width: int = 800,
        height: int = 400,
    ) -> dict[str, Any]:
        """
        Generate a word cloud from text.
        Returns base64-encoded image and word frequencies.
        """
        if not HAS_WORDCLOUD or not HAS_MATPLOTLIB:
            return self._fallback_word_data(text, title)

        try:
            word_freq = self._extract_word_frequencies(text, max_words)

            if not word_freq:
                return {"success": False, "error": "No words to visualize"}

            wc = WordCloud(
                width=width,
                height=height,
                background_color="white",
                max_words=max_words,
                colormap="viridis",
                prefer_horizontal=0.7,
                min_font_size=10,
            )

            wc.generate_from_frequencies(word_freq)

            fig, ax = plt.subplots(figsize=(width / 100, height / 100))
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format="png", bbox_inches="tight", dpi=100)
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.read()).decode("utf-8")
            plt.close(fig)

            return {
                "success": True,
                "image_base64": img_base64,
                "image_format": "png",
                "word_frequencies": dict(word_freq.most_common(20)),
                "total_words": len(word_freq),
            }

        except Exception as e:
            logger.error(f"Error generating wordcloud: {e}")
            return self._fallback_word_data(text, title)

    def generate_skills_bar_chart(
        self,
        skills_data: dict[str, Any],
        title: str = "Top Skills Required",
        top_n: int = 10,
    ) -> dict[str, Any]:
        """
        Generate a horizontal bar chart for skills frequency.
        """
        if not HAS_MATPLOTLIB:
            return self._fallback_skills_data(skills_data, title)

        try:
            top_skills = skills_data.get("top_10", [])[:top_n]

            if not top_skills:
                return {"success": False, "error": "No skills data to visualize"}

            skills = [s["skill"] for s in top_skills]
            frequencies = [s["frequency"] for s in top_skills]

            fig, ax = plt.subplots(figsize=(10, 6))

            colors = plt.cm.viridis([i / len(skills) for i in range(len(skills))])

            bars = ax.barh(range(len(skills)), frequencies, color=colors)
            ax.set_yticks(range(len(skills)))
            ax.set_yticklabels([s.title() for s in skills])
            ax.invert_yaxis()

            ax.set_xlabel("Frequency in Job Postings", fontsize=11)
            ax.set_title(title, fontsize=14, fontweight="bold", pad=15)

            for i, (bar, freq) in enumerate(zip(bars, frequencies)):
                ax.text(
                    bar.get_width() + 0.5,
                    bar.get_y() + bar.get_height() / 2,
                    str(freq),
                    va="center",
                    fontsize=9,
                )

            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            plt.tight_layout()

            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format="png", bbox_inches="tight", dpi=100)
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.read()).decode("utf-8")
            plt.close(fig)

            return {
                "success": True,
                "image_base64": img_base64,
                "image_format": "png",
                "skills_shown": skills,
                "frequencies": frequencies,
            }

        except Exception as e:
            logger.error(f"Error generating skills bar chart: {e}")
            return self._fallback_skills_data(skills_data, title)

    def generate_education_pie_chart(
        self,
        education_data: dict[str, Any],
        title: str = "Education Requirements",
    ) -> dict[str, Any]:
        """
        Generate a pie chart for education level distribution.
        """
        if not HAS_MATPLOTLIB:
            return self._fallback_education_data(education_data, title)

        try:
            levels = education_data.get("levels", {})

            if not levels:
                return {"success": False, "error": "No education data to visualize"}

            labels = []
            sizes = []

            level_labels = {
                "phd": "PhD/Doctorate",
                "masters": "Master's Degree",
                "bachelors": "Bachelor's Degree",
                "diploma": "Diploma",
                "certificate": "Certificate",
            }

            for level, count in levels.items():
                labels.append(level_labels.get(level, level.title()))
                sizes.append(count)

            fig, ax = plt.subplots(figsize=(8, 8))

            colors = plt.cm.Set3(range(len(labels)))

            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                autopct="%1.1f%%",
                colors=colors,
                startangle=90,
                explode=[0.02] * len(sizes),
            )

            for text in texts:
                text.set_fontsize(11)
            for autotext in autotexts:
                autotext.set_fontsize(9)

            ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

            plt.tight_layout()

            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format="png", bbox_inches="tight", dpi=100)
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.read()).decode("utf-8")
            plt.close(fig)

            return {
                "success": True,
                "image_base64": img_base64,
                "image_format": "png",
                "distribution": dict(zip(labels, sizes)),
            }

        except Exception as e:
            logger.error(f"Error generating education pie chart: {e}")
            return self._fallback_education_data(education_data, title)

    def generate_experience_distribution(
        self,
        experience_data: dict[str, Any],
        title: str = "Experience Requirements",
    ) -> dict[str, Any]:
        """
        Generate a bar chart for experience years distribution.
        """
        if not HAS_MATPLOTLIB:
            return self._fallback_experience_data(experience_data, title)

        try:
            distribution = experience_data.get("distribution", {})

            if not distribution:
                summary = {
                    "min": experience_data.get("min_years"),
                    "max": experience_data.get("max_years"),
                    "average": experience_data.get("average"),
                }
                return {
                    "success": False,
                    "summary": summary,
                    "error": "No distribution data",
                }

            years = sorted([int(y) for y in distribution.keys()])
            counts = [distribution[str(y)] for y in years]

            fig, ax = plt.subplots(figsize=(10, 5))

            ax.bar(years, counts, color=self.colors["primary"], edgecolor="white")

            ax.set_xlabel("Years of Experience", fontsize=11)
            ax.set_ylabel("Number of Job Postings", fontsize=11)
            ax.set_title(title, fontsize=14, fontweight="bold", pad=15)

            ax.set_xticks(years)
            ax.set_xticklabels([f"{y} yr{'s' if y != 1 else ''}" for y in years])

            avg = experience_data.get("average")
            if avg:
                ax.axvline(
                    x=avg,
                    color=self.colors["accent"],
                    linestyle="--",
                    linewidth=2,
                    label=f"Average: {avg} years",
                )
                ax.legend()

            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            plt.tight_layout()

            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format="png", bbox_inches="tight", dpi=100)
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.read()).decode("utf-8")
            plt.close(fig)

            return {
                "success": True,
                "image_base64": img_base64,
                "image_format": "png",
                "distribution": distribution,
                "statistics": {
                    "min": min(years) if years else 0,
                    "max": max(years) if years else 0,
                    "average": avg,
                },
            }

        except Exception as e:
            logger.error(f"Error generating experience distribution: {e}")
            return self._fallback_experience_data(experience_data, title)

    def generate_career_dashboard(
        self,
        collated_data: dict[str, Any],
        title: str = "Career Overview",
    ) -> dict[str, Any]:
        """
        Generate a combined dashboard with multiple visualizations.
        Returns all visualizations in a single response.
        """
        dashboard = {
            "title": title,
            "job_count": collated_data.get("job_count", 0),
            "visualizations": {},
        }

        responsibilities = collated_data.get("responsibilities", {})
        if responsibilities.get("example_tasks"):
            tasks_text = " ".join(responsibilities["example_tasks"])
            dashboard["visualizations"]["responsibilities_wordcloud"] = (
                self.generate_wordcloud(
                    tasks_text,
                    title="Key Responsibilities",
                )
            )

        skills = collated_data.get("skills", {})
        if skills.get("top_10"):
            dashboard["visualizations"]["skills_chart"] = (
                self.generate_skills_bar_chart(
                    skills,
                    title="Top Skills Required",
                )
            )

        education = collated_data.get("education", {})
        if education.get("levels"):
            dashboard["visualizations"]["education_chart"] = (
                self.generate_education_pie_chart(
                    education,
                    title="Education Requirements",
                )
            )

        experience = collated_data.get("experience", {})
        if experience.get("distribution"):
            dashboard["visualizations"]["experience_chart"] = (
                self.generate_experience_distribution(
                    experience,
                    title="Experience Requirements",
                )
            )

        return dashboard

    def generate_text_summary_visual(
        self,
        summary_data: dict[str, Any],
        title: str,
    ) -> dict[str, Any]:
        """
        Generate a text-based visual summary (infographic-style).
        """
        if not HAS_MATPLOTLIB:
            return {"success": False, "error": "matplotlib not available"}

        try:
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.axis("off")

            ax.set_xlim(0, 10)
            ax.set_ylim(0, 10)

            ax.text(
                5,
                9.5,
                title,
                fontsize=18,
                fontweight="bold",
                ha="center",
                va="top",
                color=self.colors["text"],
            )

            y_pos = 8.5

            sections = [
                ("What You'll Do", summary_data.get("what_you_do", "")),
                (
                    "Skills Needed",
                    ", ".join(
                        summary_data.get("skills_needed", {}).get("top_skills", [])
                    ),
                ),
                (
                    "Education",
                    str(
                        summary_data.get("education_required", {}).get(
                            "minimum", "Not specified"
                        )
                    ),
                ),
                (
                    "Experience",
                    str(
                        summary_data.get("experience_needed", {}).get(
                            "level", "Not specified"
                        )
                    ),
                ),
                (
                    "Salary Range",
                    str(
                        summary_data.get("salary_range", {}).get(
                            "range", "Not specified"
                        )
                    ),
                ),
                ("Career Outlook", summary_data.get("career_outlook", "")),
            ]

            for section_title, content in sections:
                if content:
                    ax.text(
                        0.5,
                        y_pos,
                        section_title,
                        fontsize=12,
                        fontweight="bold",
                        color=self.colors["primary"],
                    )
                    y_pos -= 0.4

                    ax.text(
                        0.5,
                        y_pos,
                        str(content)[:100],
                        fontsize=10,
                        color=self.colors["text"],
                        wrap=True,
                    )
                    y_pos -= 1.2

            plt.tight_layout()

            img_buffer = io.BytesIO()
            fig.savefig(
                img_buffer,
                format="png",
                bbox_inches="tight",
                dpi=100,
                facecolor=self.colors["background"],
            )
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.read()).decode("utf-8")
            plt.close(fig)

            return {
                "success": True,
                "image_base64": img_base64,
                "image_format": "png",
            }

        except Exception as e:
            logger.error(f"Error generating text summary visual: {e}")
            return {"success": False, "error": str(e)}

    def _extract_word_frequencies(self, text: str, max_words: int) -> Counter:
        """Extract word frequencies from text, filtering common words."""
        import re

        text_lower = text.lower()
        words = re.findall(r"\b[a-z]{3,}\b", text_lower)

        stopwords = {
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "can",
            "her",
            "was",
            "one",
            "our",
            "out",
            "has",
            "have",
            "had",
            "been",
            "will",
            "your",
            "from",
            "they",
            "this",
            "that",
            "with",
            "which",
            "what",
            "when",
            "where",
            "who",
            "whom",
            "how",
            "why",
            "than",
            "then",
            "them",
            "these",
            "those",
            "being",
            "about",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "again",
            "further",
            "once",
            "here",
            "there",
            "should",
            "would",
            "could",
            "might",
            "must",
            "shall",
            "experience",
            "required",
            "requirements",
            "responsibilities",
            "including",
            "preferred",
            "minimum",
            "qualifications",
            "skills",
            "ability",
            "strong",
            "excellent",
            "good",
            "years",
            "year",
            "application",
            "apply",
            "job",
            "work",
            "working",
            "works",
            "related",
            "field",
            "position",
            "role",
            "roles",
            "duties",
            "tasks",
            "task",
            "ensure",
            "ensure",
            "support",
            "support",
        }

        filtered_words = [w for w in words if w not in stopwords and len(w) > 3]

        return Counter(filtered_words)

    def _fallback_word_data(self, text: str, title: str) -> dict[str, Any]:
        """Return word frequency data without image when libraries unavailable."""
        word_freq = self._extract_word_frequencies(text, 100)
        return {
            "success": True,
            "image_base64": None,
            "image_format": None,
            "word_frequencies": dict(word_freq.most_common(20)),
            "total_words": len(word_freq),
            "note": "Install matplotlib and wordcloud for image generation",
        }

    def _fallback_skills_data(self, skills_data: dict, title: str) -> dict[str, Any]:
        """Return skills data without image when libraries unavailable."""
        top_skills = skills_data.get("top_10", [])[:10]
        return {
            "success": True,
            "image_base64": None,
            "skills_shown": [s["skill"] for s in top_skills],
            "frequencies": [s["frequency"] for s in top_skills],
            "note": "Install matplotlib for chart generation",
        }

    def _fallback_education_data(
        self, education_data: dict, title: str
    ) -> dict[str, Any]:
        """Return education data without image when libraries unavailable."""
        levels = education_data.get("levels", {})
        return {
            "success": True,
            "image_base64": None,
            "distribution": levels,
            "note": "Install matplotlib for chart generation",
        }

    def _fallback_experience_data(
        self, experience_data: dict, title: str
    ) -> dict[str, Any]:
        """Return experience data without image when libraries unavailable."""
        return {
            "success": True,
            "image_base64": None,
            "distribution": experience_data.get("distribution", {}),
            "summary": {
                "min": experience_data.get("min_years"),
                "max": experience_data.get("max_years"),
                "average": experience_data.get("average"),
            },
            "note": "Install matplotlib for chart generation",
        }


career_visualizer = CareerVisualizer()
