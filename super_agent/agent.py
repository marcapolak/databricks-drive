import os
import json
from pathlib import Path
import mimetypes
from openai import OpenAI

METADATA_PATH = Path(os.environ.get("DRIVE_STORAGE_PATH", "/tmp/databricks_drive")) / "metadata.json"

def load_metadata():
    if METADATA_PATH.exists():
        with open(METADATA_PATH, "r") as f:
            return json.load(f)
    return {"folders": {"My Drive": {"parent": None, "children": []}}, "files": {}}

def save_metadata(meta):
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_PATH, "w") as f:
        json.dump(meta, f, indent=2)

def _search_files(keyword, meta):
    return [
        (fname, fdata)
        for fname, fdata in meta["files"].items()
        if keyword.lower() in fname.lower() or keyword.lower() in fdata.get("description", "")
    ]

def search_files_tool(keyword):
    meta = load_metadata()
    files = _search_files(keyword, meta)
    if not files:
        return f"No files found matching: '{keyword}'"
    return "\n".join(f"- {fname} (size: {fdata['size']} bytes, in: {fdata['parent']})" for fname, fdata in files)

def summarize_file_tool(filename, llm=None, num_pages=2, max_chars=4000):
    meta = load_metadata()
    fdata = meta["files"].get(filename)
    if not fdata:
        return f"File '{filename}' not found."
    path = Path(fdata["path"])
    mime, _ = mimetypes.guess_type(str(path))
    try:
        if mime in ["text/plain", "text/csv"]:
            text = path.read_text(encoding="utf-8", errors="replace")
            head = "\n".join(text.splitlines()[:10])
            return f"**{filename}**\n\n> Preview first 10 lines:\n{head}"
        elif mime and mime.startswith("image/"):
            return f"**{filename}**\n\n(Image preview available in UI)"
        elif mime == "application/pdf":
            text = ""
            try:
                import pdfplumber
                with pdfplumber.open(str(path)) as pdf:
                    for i, page in enumerate(pdf.pages[:num_pages]):
                        page_txt = page.extract_text() or ""
                        text += page_txt + "\n"
            except Exception:
                try:
                    import PyPDF2
                    with open(str(path), "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        for i, page in enumerate(reader.pages[:num_pages]):
                            page_txt = page.extract_text() or ""
                            text += page_txt + "\n"
                except Exception as e2:
                    return f"**{filename}**\n\n(Could not extract text from PDF: {e2})"
            trimmed = text[:max_chars].strip()
            if not trimmed:
                return f"**{filename}**\n\n(Could not extract text from PDF. It may be scanned or encrypted.)"
            if llm:
                prompt = (
                    f"You are an executive assistant for Databricks field engineers.\n"
                    f"Given this extracted snippet from '{filename}':\n\n"
                    f"{trimmed}\n"
                    "---\n"
                    "Write a concise executive summary with key customers/projects, main topics, business outcomes, and actionable findings. "
                    "Use headings/bullets when suitable. Do not repeat raw text—synthesize for a product manager, architect, or field leader."
                )
                try:
                    response = llm.chat.completions.create(
                        model="drive_superagent",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=600,
                    )
                    content = response.choices[0].message.content
                    return f"**{filename}**\n\n{content}"
                except Exception as e:
                    return f"**{filename}**\n\n(LLM summarization failed: {e})"
            else:
                return f"**{filename}**\n\n> **PDF Preview (first {num_pages} pages):**\n{trimmed}\n"
        else:
            return f"**{filename}**\n\nUnsupported file type for summary."
    except Exception as e:
        return f"**{filename}**\n\nError reading file: {e}"

def move_file_tool(filename, folder):
    meta = load_metadata()
    if filename not in meta["files"]:
        return f"File '{filename}' not found."
    if folder not in meta["folders"]:
        return f"Destination folder '{folder}' doesn't exist."
    cur_folder = meta["files"][filename]["parent"]
    if cur_folder == folder:
        return f"File '{filename}' already in '{folder}'."
    meta["folders"][cur_folder]["children"].remove(filename)
    meta["folders"][folder]["children"].append(filename)
    meta["files"][filename]["parent"] = folder
    save_metadata(meta)
    return f"Moved '{filename}' to '{folder}'."

def create_folder(name, parent="My Drive"):
    meta = load_metadata()
    if name in meta["folders"]:
        return False, "Folder already exists"
    meta["folders"][name] = {"parent": parent, "children": []}
    meta["folders"][parent]["children"].append(name)
    save_metadata(meta)
    return True, "Folder created"

def delete_file(filename):
    meta = load_metadata()
    if filename in meta["files"]:
        folder = meta["files"][filename]["parent"]
        meta["folders"][folder]["children"].remove(filename)
        path = meta["files"][filename]["path"]
        try:
            Path(path).unlink()
        except FileNotFoundError:
            pass
        del meta["files"][filename]
        save_metadata(meta)

class SuperAgent:
    def __init__(self, databricks_token=None, base_url=None):
        self.tools = {}
        self.llm = None
        token = databricks_token or os.environ.get('DATABRICKS_TOKEN')
        endpoint = base_url or "https://e2-demo-field-eng.cloud.databricks.com/serving-endpoints/drive_superagent/invocations"
        if token:
            self.llm = OpenAI(api_key=token, base_url=endpoint)
        else:
            print("Warning: No Databricks token found; LLM won't be initialized.")

    def set_llm(self, llm_client):
        self.llm = llm_client

    def register_tool(self, name, func, description=""):
        self.tools[name] = {"func": func, "description": description}

    def ask(self, query):
        query_lower = query.lower()
        if query_lower.startswith("search "):
            keyword = query[7:]
            return self.tools.get("search_files", {}).get("func", lambda k: "Tool not registered")(keyword)
        elif query_lower.startswith("summarize "):
            filename = query[10:]
            return self.tools.get("summarize_file", {}).get("func", lambda f: "Tool not registered")(filename)
        elif query_lower.startswith("move "):
            parts = query.split()
            if len(parts) >= 4 and parts[-2] == "to":
                filename = " ".join(parts[1:-2])
                folder = parts[-1]
                return self.tools.get("move_file", {}).get("func", lambda f, fol: "Tool not registered")(filename, folder)
            else:
                return "Please specify: move <filename> to <folder>"
        if self.llm:
            try:
                meta = load_metadata()
                ws = f"[FOLDERS]: {list(meta['folders'].keys())}\n[FILES]: {list(meta['files'].keys())}"
                response = self.llm.chat.completions.create(
                    model="drive_superagent",
                    messages=[
                        {"role": "system", "content": "Workspace structure:\n" + ws},
                        {"role": "user", "content": query}
                    ],
                    max_tokens=500
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"LLM call failed: {str(e)}"
        else:
            return "No LLM backend configured."