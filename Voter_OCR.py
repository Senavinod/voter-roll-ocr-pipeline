import pandas as pd
import numpy as np
import pytesseract
from pypdf import PdfReader
from pdf2image import convert_from_path
import re
import os
import glob
import matplotlib.pyplot as plt
import cv2
import sys
import traceback
import shutil

# ==========================================
# 🛑 SECURITY NOTICE: PUBLIC REPOSITORY / KAGGLE 🛑
# To protect Personally Identifiable Information (PII) of voters,
# the specific OpenCV contour coordinates and Regex extraction 
# patterns have been redacted from this public showcase.
# This script successfully batch-processed 540+ Electoral Roll PDFs.
# ==========================================

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def sort_contours(cnts, method="left-to-right"):
    """
    Sorts contours (boxes) top-to-bottom, then left-to-right 
    to handle the grid structure of an electoral roll.
    """
    boundingBoxes = [cv2.boundingRect(c) for c in cnts]
    c_boxes = list(zip(cnts, boundingBoxes))
    
    # First, sort strictly by Y-coordinate (Top to Bottom)
    c_boxes.sort(key=lambda b: b[1][1])
    
    rows = []
    current_row = []
    if c_boxes:
        last_y = c_boxes[0][1][1]
        
        for c, box in c_boxes:
            y = box[1]
            h = box[3]
            # If this box is significantly lower than the last one, start a new row
            if y > last_y + (h // 2): 
                current_row.sort(key=lambda b: b[1][0])
                rows.extend(current_row)
                current_row = []
                last_y = y
            
            current_row.append((c, box))
            
        current_row.sort(key=lambda b: b[1][0])
        rows.extend(current_row)

    return rows

def extract_voter_boxes(pdf_path):
    # Convert PDF to images
    pages = convert_from_path(pdf_path)
    
    custom_config = r'--psm 11' 
    all_extracted_text = []
    page1_text = []
    total_pages = len(pages)

    for page_num, image in enumerate(pages):
        print(f"Processing page {page_num+1}")
        
        # Convert PIL image to OpenCV format
        open_cv_image = np.array(image)
        # Convert RGB to BGR
        img = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        if (page_num+1 == 2 or page_num+1 == total_pages):
            print(f"Skipping to process this page {page_num+1} as information not useful")

        # Extract Page 1 separately 
        if page_num+1 == 1:
            text_pg1 = pytesseract.image_to_string(gray, config=r'--psm 6')
            if text_pg1.strip():
                page1_text.append(f"---- PAGE 1 START ---\n{text_pg1.strip()}\n--- PAGE 1 END ---")
                
        # extract remaining pages for voter info except page 2 and last page
        if (page_num+1 >= 3 and page_num+1 < total_pages):
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            voter_boxes = []
            for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                aspect_ratio = w / float(h)
                area = cv2.contourArea(c)
                
                # [REDACTED]: Exact Area and Aspect Ratio filters masked for PII protection
                MIN_AREA = 1000   # Redacted threshold
                MAX_AREA = 999999 # Redacted threshold
                MIN_ASPECT = 1.0  # Redacted threshold
                
                if area > MIN_AREA and area < MAX_AREA and aspect_ratio > MIN_ASPECT:
                    voter_boxes.append(c)
    
            if not voter_boxes:
                continue
    
            sorted_boxes_with_rects = sort_contours(voter_boxes)
    
            for i, (c, rect) in enumerate(sorted_boxes_with_rects):
                x, y, w, h = rect
                
                # Crop the image to the box
                roi = img[y:y+h, x:x+w]
                
                # 1. Gentle 2x upscale (instead of 3x)
                width = int(roi.shape[1] * 2)
                height = int(roi.shape[0] * 2)
                resized_roi = cv2.resize(roi, (width, height), interpolation=cv2.INTER_CUBIC)
                
                # 2. Convert to grayscale
                gray_roi = cv2.cvtColor(resized_roi, cv2.COLOR_BGR2GRAY)
                
                # 3. Median Blur: Deletes background noise and speckles without blurring letters
                final_roi = cv2.medianBlur(gray_roi, 3)
                
                # Extract text using Tesseract with PSM 11
                text = pytesseract.image_to_string(final_roi, config=custom_config)
                clean_text_str = text.strip()
                
                if clean_text_str:
                    all_extracted_text.append(clean_text_str)

    return all_extracted_text, page1_text

def clean_text(result):
    text_list = []
    for text in result:
        try:
            # [REDACTED]: Specific structural cleanup keywords masked
            pattern = r'\s*[=|!|: |;|+]+\s+'
            text = re.sub(pattern, ":", text)
            text = text.replace("REDACTED_SYMBOL", "")
            text = text.replace("REDACTED_KEYWORD", "CleanedKeyword")
            text_list.append(text)
        except Exception as e:
            print(f"Error: {e} please check function clean_text")
            continue
    return text_list

def extract_page1(page1):
    page1_list = []
    for i in page1:
        try:
            # [REDACTED]: Exact metadata targeting logic masked
            pattern1 = r"<REDACTED_REGEX_FOR_SECTION_NAME>"
            match1 = re.findall(pattern1, i)
            pattern2 = r"<REDACTED_REGEX_FOR_METADATA_LOCATIONS>"
            match2 = re.findall(pattern2, i)
            
            if match1 or match2:
                page1_list = re.split(r"\n+", match1[0] if match1 else "")
                for m in match2:
                    match = re.split(r"[:+]", m)
                    if len(match) > 1:
                        page1_list.append((match[0], match[1]))
        except Exception as e:
            tb = traceback.extract_tb(sys.exc_info()[2])
            line_no = tb[-1].line
            line_num = tb[-1].lineno
            print(f"Error: {e} please check function extract_page1")
            print(f"Line Number: {line_num}")
            print(f"Code causing error: {line_no}")

    return page1_list

def extract_name(text_list):
    name_list = []
    for text in text_list:
        try:
            pattern = r"<REDACTED_REGEX_PATTERN_FOR_NAME>"
            name = re.findall(pattern, text)
            if name: 
                name = re.split(r"[?:=+]", name[0])
                name_extract = lambda x: x[1] if len(name)>1 else name[0].replace('\nName',"")
                name = name_extract(name)
                name = re.sub(r'[^a-zA-Z ]', '', name)
                name_list.append(name)
            else:
                name_list.append("NA")
        except Exception as e:
            print(f"Error: {e} please check function extract_name")
            name_list.append("NA")
            continue
    return name_list

def extract_relation(text_list):
    relations_list = []
    for text in text_list:
        try:
            pattern = r"<REDACTED_REGEX_PATTERN_FOR_RELATION>"
            relations = re.findall(pattern, text)
            if relations: 
                relations = re.split(r"[?:]", relations[0])
                relation, name = relations[0], relations[1]
                relation = relation.removesuffix('sName')
                relations_list.append((relation, name))
            else:
                relations_list.append("NA")
        except Exception as e:
            print(f"Error: {e} please check function extract_relation")
            relations_list.append("NA")
            continue
    return relations_list

def extract_houseno(text_list):
    houseno_list = []
    for text in text_list:
        try:
            pattern = r"<REDACTED_REGEX_PATTERN_FOR_HOUSE_NO>"
            houseno = re.findall(pattern, text)
            if houseno: 
                houseno = re.sub(r"\n", "", houseno[0])
                houseno = re.sub(r"HouseNumber *:?", "", houseno)
                houseno = re.sub(r"Available*", "", houseno)
                m = re.search(r"Age.*", houseno)
                if m and m.group() in houseno:
                    houseno = houseno.replace(m.group(), "")
                houseno_list.append(houseno.strip())
            else:
                houseno_list.append("NA")
        except Exception as e:
            print(f"Error: {e} please check function extract_houseno")
            houseno_list.append("NA")
            continue
    return houseno_list

def extract_age(text_list):
    age_list = []
    for text in text_list:
        try:
            pattern = r"<REDACTED_REGEX_PATTERN_FOR_AGE>"
            age = re.findall(pattern, text)
            if age: 
                age = re.sub(r"\n", "", age[0])
                age = re.sub(r"Age ?.[^\d]?", "", age)
                age_list.append(int(age))
            else:
                age_list.append(0)
        except Exception as e:
            print(f"Error: {e} please check function extract_age")
            age_list.append("NA")
            continue
    return age_list

def extract_gender(text_list):
    gender_list = []
    for text in text_list:
        try:
            pattern = r"<REDACTED_REGEX_PATTERN_FOR_GENDER>"
            gender = re.findall(pattern, text)
            if gender: 
                gender = re.sub(r"(?:Gander|Gender)?: ?", "", gender[0])
                gender_list.append(gender)
            else:
                gender_list.append("NA")
        except Exception as e:
            print(f"Error: {e} please check function extract_gender")
            gender_list.append("NA")
            continue
    return gender_list
      
def extract_voterID(text_list):
    voterID_list = []
    for text in text_list:
        try:
            pattern = r"<REDACTED_REGEX_PATTERN_FOR_VOTER_ID>"
            voterID = re.findall(pattern, text)
            if voterID: 
                replaced_text = re.sub(r"YU0", "YUO", voterID[0])
                m = re.match(r"\w{2,5}.*[\d{3,8}]*", replaced_text)
                if m and m.end() == 11:
                    prefix, digits = m.group()[:3], m.group()[3:]
                    digits = digits.replace(" ", "")
                    if len(digits) > 7:
                        digits = digits[1:]
                    voterID_list.append(prefix + digits)
                else:
                    voterID_list.append(m.group() if m else "NA")
            else:
                voterID_list.append("NA")
        except Exception as e:
            print(f"Error: {e} please check function extract_voterID")
            voterID_list.append("NA")
            continue
    return voterID_list

def create_dataframe(result_list, page1_text_list):
    try:
        page1_list = extract_page1(page1_text_list)
        page1_data = []

        # creating df1 for page1 data
        for item in page1_list:
            if isinstance(item, tuple):
                page1_data.append(f"{item[0].strip()}:{item[1].strip()}")
            else:
                page1_data.append(item)

        df1 = pd.DataFrame(page1_data) # DataFrame 1 for page 1 data

        # Process Voter Boxes
        text = clean_text(result_list)
        name_list = extract_name(text)
        relation_list = extract_relation(text)
        houseno_list = extract_houseno(text)
        age_list = extract_age(text)
        gender_list = extract_gender(text)
        voterID_list = extract_voterID(text)
        
        structured_data = []
    
        # Loop through both lists at the same time creating df2
        for name, relation, age, gender, addr, voter in zip(name_list, relation_list, age_list, gender_list, houseno_list, voterID_list):
            rel_type, rel_name = relation
            
            structured_data.append({
                "Voter Name": name,
                "Relation": rel_type,
                "Relation Name": rel_name,            
                "House Number": addr,
                "Age": age,
                "Gender": gender,
                "Voter ID": voter
            })
        
        # Create DataFrame for voter information for remaining pages
        df2 = pd.DataFrame(structured_data)
        return df1, df2
        
    except Exception as e:
        tb = traceback.extract_tb(sys.exc_info()[2])
        line_no = tb[-1].line
        line_num = tb[-1].lineno
        
        print(f"Error: {e} please check function create_dataframe")
        print(f"Line Number: {line_num}")
        print(f"Code causing error: {line_no}")
        return pd.DataFrame(), pd.DataFrame()
    
def dataframe_toexcel(df1, df2, file_path):
    try:
        header_data = df1.iloc[:,0].values if not df1.empty else []
        df1_plain = pd.DataFrame(header_data)
        writer = pd.ExcelWriter(file_path, engine='xlsxwriter')
        
        df1_plain.to_excel(writer, index=False, header=False, startrow=0, sheet_name='Sheet1')
        df2.to_excel(writer, index=True, startrow=len(df1_plain)+1, sheet_name='Sheet1')
        
        writer.close()
        print("Excel file created successfully at the specified path.")
    except Exception as e:
        print(f"Error: {e} please check function dataframe_toexcel")

# ==========================================
# BATCH PROCESSING PIPELINE
# ==========================================
SOURCE_FOLDER = r"C:\Path\To\Your\Electoral_Rolls"
OUTPUT_FOLDER = r"C:\Path\To\Your\Electoral_Rolls\Excel_Files"
COMPLETED_FOLDER = os.path.join(SOURCE_FOLDER, "Completed")

# Create output folder if it doesn't exist
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)
if not os.path.exists(COMPLETED_FOLDER):
    os.makedirs(COMPLETED_FOLDER)

def process_all_files():
    files = [f for f in os.listdir(SOURCE_FOLDER) if f.lower().endswith('.pdf')]
    print(f"Found {len(files)} PDF files.")

    # processing single files from directory and naming as per the pdf names
    for filename in files:
        pdf_path = os.path.join(SOURCE_FOLDER, filename)
        excel_filename = os.path.splitext(filename)[0] + ".xlsx"
        output_path = os.path.join(OUTPUT_FOLDER, excel_filename)

        # path where pdf will be moved after success
        completed_path = os.path.join(COMPLETED_FOLDER, filename)

        print(f"\n--- Processing: {filename} ---")

        # 2. Extract Text
        result_list, page1_text_list = extract_voter_boxes(pdf_path)

        if not result_list:
            print(f"No voter data found in {filename}")
            continue

        # 3 Process Data and Create Dataframes
        df1, df2 = create_dataframe(result_list, page1_text_list)

        if not df2.empty:
            df2.index = np.arange(1, len(df2)+1)
            df2.index.name = "S.No"

            dataframe_toexcel(df1, df2, output_path)

            # 4. MOVE FILE ON SUCCESS
            # Check if file exists in destination (edge case handling)
            if os.path.exists(completed_path):
                os.remove(completed_path) # Overwrite existing
            
            shutil.move(pdf_path, completed_path)
            print(f"SUCCESS: PDF moved to {completed_path}") 

        else: 
            print("Extracted data was empty. PDF moved to Completed.")
            shutil.move(pdf_path, completed_path)

if __name__ == "__main__":
    process_all_files()