import os
import re
import cv2
import sys
import traceback
import numpy as np
import pandas as pd
import pytesseract
from pdf2image import convert_from_path
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename

# --- Initialize the Server ---
app = Flask(__name__)

# ==========================================
# 🛑 SECURITY NOTICE: PUBLIC REPOSITORY 🛑
# To protect Personally Identifiable Information (PII) of voters,
# the specific OpenCV contour coordinates and Regex extraction 
# patterns have been redacted from this public showcase.
# ==========================================

# Create temporary folders for incoming Android files
UPLOAD_FOLDER = 'temp_uploads'
OUTPUT_FOLDER = 'temp_outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ==========================================
# MY OCR WORKING FUNCTIONS
# ==========================================
def sort_contours(cnts, method="left-to-right"):
    boundingBoxes = [cv2.boundingRect(c) for c in cnts]
    c_boxes = list(zip(cnts, boundingBoxes))
    c_boxes.sort(key=lambda b: b[1][1])
    
    rows = []
    current_row = []
    if c_boxes:
        last_y = c_boxes[0][1][1]
        for c, box in c_boxes:
            y = box[1]
            h = box[3]
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
    # ==========================================
    # Converts PDF to images and uses OpenCV to draw bounding boxes around individual voter cards.
    # ==========================================
    pages = convert_from_path(pdf_path)
    all_voter_boxes = []

    for image in pages: # FIXED: Changed 'images' to 'pages'
        # Convert PIL image to OpenCV format
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Apply binary thresholding
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        
        # Find contours of the voter boxes
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            
            # [REDACTED]: Specific width and height ratios that identify a valid voter box
            valid_box_width = w > 0  # Redacted threshold
            valid_box_height = h > 0 # Redacted threshold
            
            if valid_box_width and valid_box_height:
                # [REDACTED]: Specific cropping coordinates
                cropped_box = img_cv[y:y+h, x:x+w] 
                all_voter_boxes.append(cropped_box)
                
    return all_voter_boxes

def clean_text(result):
    text_list = []
    for text in result:
        try:
           """Cleans raw Tesseract OCR output."""
           # [REDACTED]: Specific character replacement and noise reduction logic
           text_list.append(str(text)) # Added so the try block isn't empty
        except Exception as e:
            continue
    return text_list

def extract_page1(page1):
    page1_list = []
    for i in page1:
        try:
            """Extracts metadata from the cover page of the electoral roll."""
            # [REDACTED]: Logic to extract Assembly Constituency, Part Number, etc.
            page1_list.append(("Demo State", "Demo District")) # Added so the try block isn't empty
        except Exception as e:
            continue
    return page1_list

def extract_name(text_list):
    name_list = []
    for text in text_list:
        try:
            """Extracts voter name using Regex."""
            # [REDACTED]: The exact Regex pattern for Hindi/English name matching
            pattern = r"<REDACTED_REGEX_PATTERN_FOR_NAME>"
            match = re.search(pattern, text) # FIXED: Changed text_list to text
            name_list.append(match.group(1) if match else "John Doe (Demo)")
        except Exception as e: 
            name_list.append("NA")
    return name_list

def extract_relation(text_list):
    relations_list = []
    for text in text_list:
        try:
            """Extracts Father's/Husband's name using Regex."""
            pattern = r"<REDACTED_REGEX_PATTERN_FOR_RELATION>"
            match = re.search(pattern, text) # FIXED: Changed text_list to text
            relations_list.append(("Father", "Richard Doe (Demo)")) # Mocking tuple return
        except: relations_list.append(("NA", "NA"))
    return relations_list

def extract_houseno(text_list):
    houseno_list = []
    for text in text_list:
        try:
            pattern = r"<REDACTED_REGEX_PATTERN_FOR_HOUSE_NO>"
            match = re.search(pattern, text) # FIXED: Changed text_list to text
            houseno_list.append(match.group(1) if match else "123-B (Demo)")
        except: houseno_list.append("NA")
    return houseno_list

def extract_age(text_list):
    age_list = []
    for text in text_list:
        pattern = r"<REDACTED_REGEX_PATTERN_FOR_AGE>"
        match = re.search(pattern, text) # FIXED: Changed text_list to text
        age_list.append(match.group(1) if match else "35")
    return age_list

def extract_gender(text_list):
    gender_list = []
    for text in text_list:
        try:
            pattern = r"<REDACTED_REGEX_PATTERN_FOR_GENDER>"
            match = re.search(pattern, text) # FIXED: Changed text_list to text
            gender_list.append(match.group(1) if match else "M")
        except: gender_list.append("NA")
    return gender_list
      
def extract_voterID(text_list):
    voterID_list = []
    for text in text_list:
        try:
            pattern = r"<REDACTED_REGEX_PATTERN_FOR_VOTER_ID>"
            match = re.search(pattern, text) # FIXED: Changed text_list to text
            voterID_list.append(match.group(1) if match else "XYZ9876543")
        except: voterID_list.append("NA")
    return voterID_list

def create_dataframe(result_list,page1_text_list):
    try:
        page1_list = extract_page1(page1_text_list)
        page1_data = []
        for item in page1_list:
            if isinstance(item,tuple):
                page1_data.append(f"{item[0].strip()}:{item[1].strip()}")
            else:
                page1_data.append(item)

        df1 = pd.DataFrame(page1_data)

        text = clean_text(result_list)
        name_list = extract_name(text)
        relation_list = extract_relation(text)
        houseno_list = extract_houseno(text)
        age_list = extract_age(text)
        gender_list = extract_gender(text)
        voterID_list = extract_voterID(text)
        
        structured_data = []
        for name, relation, age, gender, addr, voter in zip(name_list, relation_list, age_list, gender_list, houseno_list, voterID_list):
            rel_type, rel_name = relation
            structured_data.append({
                "Voter Name": name, "Relation": rel_type, "Relation Name": rel_name,            
                "House Number": addr, "Age": age, "Gender": gender, "Voter ID": voter
            })
        
        df2 = pd.DataFrame(structured_data)
        return df1,df2
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame(), pd.DataFrame()
    
def dataframe_toexcel(df1,df2,file_path):
    try:
        header_data = df1.iloc[:,0].values if not df1.empty else [] # Added empty check
        df1_plain = pd.DataFrame(header_data)
        writer = pd.ExcelWriter(file_path, engine = 'xlsxwriter')
        df1_plain.to_excel(writer, index=False, header=False, startrow=0, sheet_name='Sheet1')
        df2.to_excel(writer, index=True, startrow = len(df1_plain)+1, sheet_name = 'Sheet1')
        writer.close()
    except Exception as e:
        print(f"Error: {e}")

# ==========================================
# THE FLASK API ENDPOINT
# ==========================================
@app.route('/process_pdf', methods=['POST'])
def process_api():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(pdf_path)
        
        print(f"\n---> Received PDF from Phone: {filename}. Starting OCR...")

        result_list = extract_voter_boxes(pdf_path)
        
        # --- DEMO FALLBACK ---
        # If the redacted OpenCV logic yields no boxes, inject mock data to keep the demo running
        if not result_list:
            result_list = ["Mock Voter Box 1", "Mock Voter Box 2"]
            
        page1_text_list = ["Mock Cover Page Text"] # FIXED: Added missing variable

        df1, df2 = create_dataframe(result_list, page1_text_list)
        
        if not df2.empty:
            df2.index = np.arange(1, len(df2)+1)
            df2.index.name = "S.No"
        
        excel_filename = os.path.splitext(filename)[0] + "_Mobile_Extracted.xlsx"
        excel_path = os.path.join(OUTPUT_FOLDER, excel_filename)
        dataframe_toexcel(df1, df2, excel_path)

        print(f"---> Processing Complete! Sending {excel_filename} back to Phone.")
        return send_file(excel_path, as_attachment=True, download_name=excel_filename)

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("==================================================")
    print("Demo SERVER IS RUNNING!")
    print("==================================================")

    app.run(host='0.0.0.0', port=0000, debug=False)