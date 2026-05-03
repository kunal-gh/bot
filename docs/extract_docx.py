import zipfile
import xml.etree.ElementTree as ET
import sys

def extract_text_from_docx(docx_path):
    try:
        with zipfile.ZipFile(docx_path) as docx:
            xml_content = docx.read('word/document.xml')
        
        tree = ET.fromstring(xml_content)
        # XML namespace for Word docx
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        
        paragraphs = []
        for p in tree.findall('.//w:p', ns):
            texts = [node.text for node in p.findall('.//w:t', ns) if node.text]
            if texts:
                paragraphs.append(''.join(texts))
                
        return '\n'.join(paragraphs)
    except Exception as e:
        return f"Error reading docx: {e}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = extract_text_from_docx(sys.argv[1])
        with open("extracted_text.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print("Done")
    else:
        print("Please provide a path to a docx file.")
