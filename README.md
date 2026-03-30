# Universal Finelib B2B Scraper

## 📌 Project Overview
This repository contains a dynamic, command-line web scraping tool designed to extract structured B2B contact data from the Finelib business directory. 

Instead of hardcoding locations, the script is universally designed to accept any target state via the command line, dynamically generating localized "ground-truth" datasets used for regional market mapping and targeted lead generation.

## 🛠️ Technical Highlights & Problem Solving
Building reliable datasets from regional directories requires bypassing technical bottlenecks. This project demonstrates:
* **Command-Line Interface (CLI):** Engineered with Python's `argparse` to dynamically pass state arguments for localized searches (e.g., `python universal_scraper.py Kano`).
* **Visible Browser Automation:** Utilizing asynchronous Playwright to navigate dynamic JavaScript elements, manage page timeouts, and prevent bot-detection.
* **Regex & DOM Parsing:** Combining CSS selectors with complex Regular Expressions to extract obscured phone numbers and addresses from unstructured HTML body text.
* **Data Structuring & Resumption:** Formatting raw web text into clean `.csv` files, complete with a built-in state-saving mechanism to resume interrupted scrape jobs without duplicating data.

## 📊 Dataset Structure
The script outputs clean, structured data ready for CRM import or AI model training. The extracted CSV fields include:
* `name` (Business Name)
* `address` (Physical Address)
* `phone` (Contact Number)
* `website` (Company Website, if publicly available)
* `url` (Source Listing URL)

## 💡 Relevance to Data Quality & AI Annotation
This project serves as a practical demonstration of my ability to handle complex data collection tasks from end to end. It highlights strong analytical reasoning, an eye for data formatting, and the technical persistence required to verify real-world information—key competencies for Data Quality Specialists and AI Trainers.
