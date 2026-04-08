# Practical Data Mining Project

## Introduction
This project uses a real dataset of Kenyan online job advertisements stored in the NextStep PostgreSQL database. The dataset consists primarily of extracted job-post records collected from online employment sources and stored in the `career_lmi` database, with the main analytical table being `public.job_post`. The data includes identifiers such as source and URL, textual fields such as job title, job description, and requirements, and semi-structured attributes such as education, employment type, experience level, company, and location. Because it combines structured and unstructured data, it is suitable for practical data mining tasks.

The purpose of the project is to determine whether the dataset is appropriate for coursework use, clean it into a manageable analytical subset, examine its main characteristics, and recommend one suitable data mining technique together with a justified algorithm choice. The analysis was carried out directly from PostgreSQL rather than from the scraping or ingestion pipeline, so that the database itself served as the source of truth.

## Dataset Description
The dataset was taken directly from the PostgreSQL database `career_lmi`. The main table used was `public.job_post`, which contains `110,781` rows. This table stores the core extracted job-post information, including source, URL, title, timestamps, salary fields, education, experience level, employment type, and job description text. I also inspected the supporting tables `organization`, `location`, and `job_entities` in order to understand how employer names, place names, and extracted skills were represented.

The main attributes used for the project were:
- source
- URL
- raw job title
- cleaned or raw description
- requirements text
- company name
- location
- employment type
- experience level / seniority
- education
- date first seen

The dataset is drawn from online Kenyan job sources, so it reflects real labour market information rather than simulated observations. This is important for the assignment because it introduces realistic data-quality issues such as missing values, noisy labels, inconsistent text, and duplicated listing patterns, all of which are common in applied data mining.

## PostgreSQL Inspection Summary
The database contains four schemas, but the useful application data is in the `public` schema. The main relevant tables are:

- `job_post` with `110,781` rows, which stores the main job-post records
- `organization` with `2,817` rows, which stores company names and sector values
- `location` with `787` rows, which stores normalized location values
- `job_entities` with `109,392` rows, which stores extracted skills, education, and experience in JSON format
- `job_skill` with `895,494` rows, which links jobs to normalized skills
- `skill` with `41,254` rows, which stores the skill dictionary

From this inspection, I concluded that `job_post` is the correct source of truth for the assignment, while the other tables are useful only for enrichment.

## Data Cleaning and Preparation
I did not overwrite or alter any of the original source tables. Instead, I used reproducible SQL queries to define a cleaned analytical subset and then exported a sample CSV for coursework use. This approach ensured that the original PostgreSQL tables remained unchanged while the cleaning process remained transparent and repeatable.

The cleaning process involved the following steps:

1. I kept only active job posts.
2. I trimmed whitespace and converted blank strings into null values.
3. I removed duplicate rows by URL.
4. Where URL was not enough, I used title, company, and posting date as a fallback deduplication key.
5. I removed rows missing essential fields such as title, company, description, or posting date.
6. I filtered out rows with descriptions shorter than 250 characters because they would not be very useful for text mining.

Before cleaning, the main table had `110,781` rows. After light cleaning, `76,690` rows were still suitable for analysis. From this cleaned set, I exported a smaller sample of `500` rows into `analysis_outputs/cleaned_sample.csv` for coursework use.

## Data Quality Findings
The data is **suitable with light cleaning**.

This conclusion is supported by several findings. First, the most important identifying columns were complete: there were no missing values in `source`, `url`, or `title_raw`. Second, URL duplication was very low, with `0` duplicate URLs found. Third, the text fields were rich enough for analysis. In a 5% sampled description-length profile, the median description length was `3,963.5` characters, which is sufficiently large for text mining.

However, the dataset was not perfect. Some company and location values were missing because `org_id` was missing for `31,822` rows and `location_id` was missing for `31,087` rows. Salary data was also very sparse, with `109,809` rows missing both `salary_min` and `salary_max`. In addition, there were visible scrape artifacts in some company names and skills. For example, one common company value was `Read more about this company`, which is not a true employer name.

Another quality issue was the existence of `9,320` repeated title-company-date combinations involving `29,880` rows. This indicates that lightweight deduplication was necessary even though duplicate URLs were not present.

Overall, the dataset remains strong enough for a student project because the main text fields are rich and the experience-level label is mostly complete.

## Exploratory Analysis
The full dataset covers postings first seen between `2024-02-25` and `2026-03-23`. The dates are internally consistent because there were `0` cases where `last_seen` was earlier than `first_seen`.

The extracted-entity coverage was also strong:
- jobs with an entry in `job_entities`: `109,392`
- jobs with non-empty skills JSON: `107,452`
- jobs with non-empty education JSON: `104,908`
- jobs with non-empty experience JSON: `88,909`

The strongest label in the dataset was `seniority`, with the following distribution:
- Mid-Level: `40,075`
- Senior: `37,380`
- Entry: `18,766`
- Executive: `13,169`
- Missing: `1,391`

This distribution is useful because the classes are not perfectly balanced, but they are still large enough for a practical classification task.

In the exported 500-row cleaned sample, the most common experience levels were:
- Mid-Level: `199`
- Senior: `155`
- Entry: `80`
- Executive: `66`

The same sample had a median description length of `3,766` characters, which confirms that the sample remains text-rich after cleaning.

Although the dataset is useful, some exploratory outputs also show remaining noise. For example, some titles such as `Category:Careers` and some company names such as `Global South Opportunities` appear very frequently, suggesting that some sources publish listing-style pages instead of fully standardized job records.

## Chosen Data Mining Technique
The technique selected for this dataset is **classification**.

Classification was selected because the dataset already contains a usable target label in the form of `seniority`, which can be treated as an experience-level class. This label is available for almost all rows and has four meaningful categories. Because a usable target variable already exists, supervised learning is more suitable than unsupervised clustering.

Clustering would still be possible, especially if the goal were to group jobs by similarity in wording or skills. However, clustering would be harder to evaluate clearly in this assignment because the dataset already provides a better-defined labelled task.

## Justification for Algorithm Selection
The single algorithm selected for this project is **Logistic Regression**.

The model would be applied to TF-IDF features derived from the job title and description text. This choice is appropriate for several reasons. First, the dataset is text-heavy, so a linear text-classification method is a natural fit. Second, the target variable is multi-class but still interpretable. Third, Logistic Regression is simple, widely taught, computationally efficient, and easy to justify in coursework. It also provides a strong baseline for text classification and is easier to explain than more complex models.

Another reason for choosing Logistic Regression is interpretability. After training, it is possible to inspect which words or terms are associated with Entry, Mid-Level, Senior, or Executive roles. This helps connect the algorithm to labour market patterns in a meaningful way.

Clustering was not chosen as the main technique because the labelled seniority variable already provides a more direct and easier-to-evaluate objective.

## Optional Dimension Reduction
If dimensionality reduction became necessary, **TruncatedSVD** could be applied after TF-IDF vectorization. This would help reduce the size of the sparse text-feature matrix, support visualisation, and improve efficiency on a student laptop. However, this step is optional and not required for a basic Logistic Regression model.

## Conclusion
Based on direct inspection of the PostgreSQL database, the NextStep job-post dataset is suitable for a practical data mining assignment with light cleaning. The data contains enough rows, sufficiently rich text fields, and a usable target label for supervised learning. After cleaning, a large analytical subset remained, and a smaller 500-row sample was exported for coursework.

The most appropriate data mining task for this dataset is classification, using job seniority as the target variable. The most suitable single algorithm is Logistic Regression because it matches the text-heavy nature of the data, is simple to implement, and is easy to justify academically.

## Remaining Limitations or Risks
- Salary information is too sparse to be central to the analysis.
- Some company names, titles, and skills still contain scrape noise.
- Location values are incomplete for part of the data.
- The 500-row exported sample is convenient for coursework, but a larger cleaned subset would give stronger model evaluation results.

## Appendix: SQL and Python Used
- SQL inspection, quality checks, and cleaned-subset logic: `analysis_outputs/sql_used.sql`
- Exported cleaned dataset: `analysis_outputs/cleaned_sample.csv`
- Local summary script: `analysis_outputs/analysis_notebook.py`
- Example modelling script: `analysis_outputs/model_pipeline.py`
