# voter-roll-ocr-pipeline
🗳️ Electoral Roll OCR Pipeline & Mobile App (Full-Stack AI)
Note: This repository is a sanitized showcase. To comply with data privacy standards and protect Personally Identifiable Information (PII), the specific OpenCV contour coordinates, regex extraction patterns, and live server endpoints have been redacted. The sample files provided contain dummy data.

📖 Project Overview
This project began as a data engineering challenge and evolved into a full-stack mobile AI application. The core objective was to automate the extraction of complex, grid-locked tabular data from official government PDF records and convert it into structured, highly searchable relational data (Excel/CSV).

The project was executed in two major phases:

Phase 1: Enterprise-Scale Batch Processing (Data Engineering)
I sourced official Electoral Roll PDFs directly from the Election Commission of India (ECI) website (https://www.eci.gov.in/). These documents are notoriously difficult to parse due to their varied grid structures, mixed languages, and dense formatting.

To solve this, I built an automated local Python pipeline that successfully processed an entire district's dataset:

The Scale: Automatically processed 540 individual PDF files.

The Volume: Each file contained 30 to 40 pages, resulting in roughly 16,000 to 20,000 pages of processed data.

The Pipeline: The script handled dynamic page skipping (ignoring non-data cover pages), error handling for corrupted files, and automated file-moving upon successful extraction.

Phase 2: Cloud Deployment & Mobile Accessibility (Full-Stack)
Once the core extraction logic was perfected, I wanted to make the tool accessible on the go without requiring a local Python environment.

The Backend: I wrapped the computer vision and OCR logic into a Flask API and deployed it to a Dockerized Linux container hosted on Hugging Face Spaces.

The Frontend: I built an Android Application using Kivy. The app uses native Android Scoped Storage to allow the user to select a PDF on their phone, securely transmits it to the Flask backend for processing, and downloads the resulting .xlsx file directly back to the mobile device.

🛠️ System Architecture & Tech Stack
Computer Vision & OCR
pdf2image: Converts multi-page PDFs into high-resolution images.

OpenCV (cv2): Handles grayscale conversion, binary thresholding, and contour mapping to isolate individual voter grid boxes. Features custom top-to-bottom/left-to-right sorting algorithms.

PyTesseract: Extracts raw string data from the isolated image crops.

Data Structuring
Regex (re): Complex pattern matching to separate Names, Relative Names, Ages, House Numbers, and Voter IDs from the noisy raw OCR text.

Pandas: Structures the cleaned text into multi-sheet DataFrames.

XlsxWriter: Exports the final DataFrames into formatted Excel spreadsheets.

Application & Deployment
Python 3.9+

Flask & Werkzeug: REST API development and secure file handling.

Kivy & Buildozer: Mobile UI development and APK compilation.

Hugging Face Spaces: Cloud hosting via custom Dockerfile to handle heavy system-level dependencies (Tesseract-OCR, Poppler).

📁 Repository Structure
/data_pipeline.py - The batch-processing script used to process the 540 files locally.

/server.py - The Flask API backend deployed to the cloud.

/main.py - The Kivy mobile app source code.

/Example_Files - Redacted sample inputs and outputs to demonstrate the pipeline's capability without exposing PII.
