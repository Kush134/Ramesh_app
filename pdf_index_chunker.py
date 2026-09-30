import re
from pathlib import Path
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

# ======================================================
# Azure Configuration
# ======================================================
endpoint = "https://genaidocint01.cognitiveservices.azure.com/"
key = "9f9be9dc84eb470897dbab6ffce75480"
document = r"C:\Users\rpp929424\Downloads\CAR 145_2.pdf"

from typing import Tuple, List, Optional

def process_pdf_to_markdown(document_path: str, output_file: str) -> Tuple[bool, Optional[List[dict]]]:
    """
    Analyzes a PDF document using Azure Document Intelligence Layout model,
    converts paragraphs and tables to markdown, partitions it by headings (# and ##)
    into standard chunk structure, and writes the chunked markdown output.
    """
    try:
        print(f"[Chunker] Initializing Document Intelligence client...")
        client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )
        
        print(f"[Chunker] Submitting document for analysis: {document_path}")
        with open(document_path, "rb") as f:
            poller = client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=f
            )
        result = poller.result()
        print("[Chunker] Analysis complete. Rebuilding markdown...")

        markdown = ""

        # Extract Paragraphs & Remove Header/Footers
        for para in result.paragraphs:
            skip = False
            if para.bounding_regions:
                region = para.bounding_regions[0]
                if region.polygon:
                    # Azure polygon format: [x1,y1,x2,y2,x3,y3,x4,y4]
                    y_position = region.polygon[1]

                    # Remove Header (values less than 1.0 inch)
                    if y_position < 1.0:
                        skip = True

                    # Remove Footer (values greater than 10.0 inches)
                    if y_position > 10.0:
                        skip = True

            if skip:
                continue

            text = para.content.strip()
            if not text:
                continue

            # Heading handling
            if para.role == "title":
                markdown += f"# {text}\n\n"
            elif para.role == "sectionHeading":
                markdown += f"## {text}\n\n"
            else:
                markdown += text + "\n\n"

        # Extract Tables
        for table in result.tables:
            markdown += "\n"
            rows = []
            for r in range(table.row_count):
                row = []
                for c in range(table.column_count):
                    value = ""
                    for cell in table.cells:
                        if cell.row_index == r and cell.column_index == c:
                            value = cell.content.strip()
                    row.append(value)
                rows.append(row)

            # Convert table to markdown
            for index, row in enumerate(rows):
                markdown += "| " + " | ".join(row) + " |\n"
                if index == 0:
                    markdown += "| " + " | ".join(["---"] * len(row)) + " |\n"
            markdown += "\n"

        # Create Chunks (# and ##)
        sections = re.split(r"(?=^#{1,2}\s)", markdown, flags=re.MULTILINE)
        chunks = []
        chunk_id = 1

        for section in sections:
            section = section.strip()
            if not section:
                continue

            title = re.search(r"^#{1,2}\s+(.+)", section)
            if title:
                chunks.append({
                    "chunk_id": chunk_id,
                    "clause": title.group(1),
                    "content": section
                })
                chunk_id += 1

        # Save chunks as Markdown file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write("\n")
                f.write("=" * 80)
                f.write("\n\n")

                f.write(f"CHUNK ID: {chunk['chunk_id']}\n\n")
                f.write(f"CLAUSE: {chunk['clause']}\n\n")
                f.write("-" * 80)
                f.write("\n\n")

                f.write(chunk["content"])
                f.write("\n\n")

        print(f"[Chunker] Chunk file created: {output_file}")
        print(f"[Chunker] Total chunks parsed: {len(chunks)}")
        return True, chunks
    except Exception as e:
        print(f"[Chunker] ERROR: Failed to process document {document_path}. Detail: {str(e)}")
        return False, None

if __name__ == "__main__":
    input_name = Path(document).stem
    output_tgt = f"{input_name}_chunks.md"
    success, chunks = process_pdf_to_markdown(document, output_tgt)