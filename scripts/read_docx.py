import zipfile
import xml.etree.ElementTree as ET
import sys
import os

def read_docx(file_path):
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            xml_content = zip_ref.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            paragraphs = tree.findall('.//w:p', namespace)
            text = []
            for p in paragraphs:
                texts = p.findall('.//w:t', namespace)
                paragraph_text = "".join([t.text for t in texts if t.text])
                if paragraph_text:
                    text.append(paragraph_text)
            return "\n".join(text)
    except Exception as e:
        return f"Error reading {file_path}: {str(e)}"

if __name__ == "__main__":
    files = [f for f in os.listdir('.') if f.endswith('.docx')]
    for f in files:
        print(f"--- CONTENT OF {f} ---")
        print(read_docx(f))
        print("\n" + "="*50 + "\n")
