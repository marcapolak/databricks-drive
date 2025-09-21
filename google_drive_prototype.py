from dotenv import load_dotenv
import os, shutil
import streamlit as st
from pathlib import Path
import tempfile
import pandas as pd
from functools import partial
from datetime import datetime
from collections import defaultdict

from super_agent.agent import (
    SuperAgent, search_files_tool, summarize_file_tool, move_file_tool,
    load_metadata, save_metadata, create_folder
)
from openai import OpenAI

# ---- STATIC DEMO FILES/FOLDERS ----
ASSETS_DIR = Path(__file__).parent / "assets"
STATIC_DEMO_FILES = [
    {"name": "📊 Sales Report Q3.xlsx", "description": "Excel file • 2.3 MB • 3 days ago", "type": "file"},
    {"name": "📝 Project Proposal.docx", "description": "Word document • 1.1 MB • 1 week ago", "type": "file"},
    {"name": "📄 Contract.pdf", "description": "PDF • 4.2 MB • 3 weeks ago", "type": "file"},
    {"name": "📊 Customer Data.csv", "description": "CSV file • 850 KB • 2 weeks ago", "type": "file"},
    {"name": "🖼️ Product Images", "description": "Folder • 15 items • 1 month ago", "type": "folder"},
    {"name": "📁 Financial Reports", "description": "Folder • 8 items • 2 months ago", "type": "folder"},
]
STATIC_DEMO_SET = {item["name"] for item in STATIC_DEMO_FILES}
STATIC_DEMO_FOLDER_SET = {item["name"] for item in STATIC_DEMO_FILES if item["type"] == "folder"}

STORAGE_PATH = Path(tempfile.gettempdir()) / "databricks_drive_files"
STORAGE_PATH.mkdir(exist_ok=True)
os.environ["DRIVE_STORAGE_PATH"] = str(STORAGE_PATH)

# --- Agent/LLM setup ---
load_dotenv()
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_BASE_URL = "https://e2-demo-field-eng.cloud.databricks.com/serving-endpoints"
db_client = OpenAI(api_key=DATABRICKS_TOKEN, base_url=DATABRICKS_BASE_URL)
agent = SuperAgent()
agent.set_llm(db_client)
agent.register_tool("search_files", search_files_tool, "Search files")
agent.register_tool("summarize_file", partial(summarize_file_tool, llm=agent.llm), "Summarize file with AI")
agent.register_tool("move_file", move_file_tool, "Move file")

st.set_page_config(page_title="Databricks Drive", page_icon="📁", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
.main-header { background: #1a73e8; color: white; padding: 0.5rem 1rem; border-radius: 8px; margin-bottom: 1rem; display: flex; align-items: center; justify-content: space-between; }
.drive-logo { font-size: 1.5rem; font-weight: bold; display: flex; align-items: center; gap: 0.5rem; }
.file-card { background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem; text-align: center; cursor: pointer; transition: all 0.2s ease; margin-bottom: 8px;}
.file-card:hover { border-color: #1a73e8; box-shadow: 0 2px 8px rgba(26, 115, 232, 0.1);}
.file-icon { font-size: 3rem; margin-bottom: 0.5rem;}
.file-name { font-weight: 500; color: #202124; margin-bottom: 0.25rem; word-break: break-word;}
.file-meta { font-size: 0.8rem; color: #5f6368;}
.breadcrumb { background: #f8f9fa; padding: 0.5rem 1rem; border-radius: 4px; margin-bottom: 1rem; font-size: 0.9rem; }
.stats-bar { background: #f8f9fa; padding: 0.5rem 1rem; border-radius: 4px; margin-top: 1rem; border: 1px solid #e0e0e0; }
</style>
""", unsafe_allow_html=True)

def file_icon(filename):
    ext = filename.lower()
    if ext.endswith(".xlsx") or ext.endswith(".xls"):
        return "📊"
    if ext.endswith(".docx") or ext.endswith(".doc"):
        return "📝"
    if ext.endswith(".csv"):
        return "📋"
    if ext.endswith(".pdf"):
        return "📄"
    if ext.endswith(".png") or ext.endswith(".jpg") or ext.endswith(".jpeg"):
        return "🖼️"
    return "📄"

def get_current_folder():
    return st.session_state.get("current_path", "My Drive")

def set_current_folder(folder):
    st.session_state["current_path"] = folder

def list_folder_content():
    meta = load_metadata()
    children = meta["folders"].get(get_current_folder(), {}).get("children", [])
    dynamic_files, dynamic_folders = [], []
    for name in children:
        if name in meta["files"]:
            dynamic_files.append((name, meta["files"][name]))
        elif name in meta["folders"]:
            dynamic_folders.append((name, meta["folders"][name]))
    used_names = set([f for f, _ in dynamic_files] + [f for f, _ in dynamic_folders])
    result = []
    for item in STATIC_DEMO_FILES:
        if item["type"] == "folder" and item["name"] not in used_names:
            result.append({"name": item["name"], "description": item["description"], "is_demo": True, "type": "folder"})
    for f, meta in dynamic_folders:
        result.append({"name": f, "description": "User folder", "is_demo": False, "type": "folder", "meta": meta})
    for item in STATIC_DEMO_FILES:
        if item["type"] == "file" and item["name"] not in used_names:
            result.append({"name": item["name"], "description": item["description"], "is_demo": True, "type": "file"})
    for f, meta in dynamic_files:
        result.append({"name": f, "description": f"User file, {meta['size']//1024} KB", "is_demo": False, "type": "file", "meta": meta})
    return result

def upload_files(files, parent):
    meta = load_metadata()
    for file in files:
        if file.name in STATIC_DEMO_SET:
            st.warning(f"Cannot upload '{file.name}', protected demo file.")
            continue
        path = STORAGE_PATH / file.name
        with open(path, "wb") as f:
            f.write(file.getbuffer())
        size = path.stat().st_size
        upload_time = datetime.now().isoformat()
        meta["files"][file.name] = {
            "path": str(path),
            "size": size,
            "created": upload_time,
            "modified": upload_time,
            "parent": parent,
        }
        if file.name not in meta["folders"][parent]["children"]:
            meta["folders"][parent]["children"].append(file.name)
    save_metadata(meta)
    st.session_state.pop("summary_output", None)

def merged_file_folder_count_stats(folder, static_files, user_files, user_folders):
    FILETYPE_MAP = {
        ".xlsx": "Excel", ".xls": "Excel",
        ".docx": "Word", ".doc": "Word",
        ".pdf": "PDF",
        ".csv": "CSV",
    }
    files_all, folders_all = [], []
    if folder == "My Drive":
        files_all += [f for f in static_files if f["type"] == "file"]
        folders_all += [f for f in static_files if f["type"] == "folder"]
    files_all += [{"name": fname, "type": "file"} for fname, _ in user_files]
    folders_all += [{"name": fname, "type": "folder"} for fname, _ in user_folders]
    ext_counts = defaultdict(int)
    for f in files_all:
        ext = Path(f["name"]).suffix.lower()
        ftype = FILETYPE_MAP.get(ext, ext.replace(".", "").upper() if ext else "Other")
        ext_counts[ftype] += 1
    return len(files_all), dict(ext_counts), len(folders_all)

def main():
    if "current_path" not in st.session_state:
        st.session_state["current_path"] = "My Drive"
    st.markdown("""
    <div class="main-header">
        <div class="drive-logo">
            <span>📁</span>
            <span>Databricks Drive</span>
        </div>
        <div>
            <span style="font-size: 0.9rem;">Unstructured Data Management Platform</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
    with col1:
        uploaded = st.file_uploader("📤 Upload files", accept_multiple_files=True,
            type=['xlsx', 'xls', 'docx', 'doc', 'pdf', 'csv', 'txt', 'png', 'jpg'],
            key="file_uploader")
        if uploaded:
            upload_files(uploaded, get_current_folder())
            st.success("Uploaded files!")
    with col2:
        if st.button("📁 New Folder"):
            st.session_state["show_new_folder"] = True
    with col3:
        view_mode = st.selectbox("View", ["Grid", "List"], key="view_selector")
        st.session_state["view_mode"] = view_mode.lower()
    with col4:
        st.text_input("🔍 Search files", placeholder="Search in Drive", key="search_term")
    st.markdown(
        f"<div class='breadcrumb'><span>📁 {get_current_folder()}</span></div>",
        unsafe_allow_html=True
    )
    if st.session_state.get("show_new_folder"):
        folder_name = st.text_input("Folder name:")
        if st.button("Create"):
            if folder_name in STATIC_DEMO_SET:
                st.error("This folder name is reserved as a demo folder.")
            else:
                ok, msg = create_folder(folder_name, get_current_folder())
                st.success(msg) if ok else st.error(msg)
                st.session_state["show_new_folder"] = False

    file_items = list_folder_content()
    search_term = st.session_state.get("search_term")
    if search_term:
        file_items = [item for item in file_items if search_term.lower() in item["name"].lower()]

    st.divider()
    # --- File grid including Summarize AI; NO DELETE buttons ---
    if st.session_state.get("view_mode", "grid") == "grid":
        cols_per_row = 4
        for i in range(0, len(file_items), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, item in enumerate(file_items[i:i+cols_per_row]):
                name, desc, is_demo, meta = item["name"], item["description"], item.get("is_demo", False), item.get("meta", None)
                icon = file_icon(name)
                with cols[j]:
                    card_html = f"""
                    <div class="file-card">
                        <div class="file-icon">{icon}</div>
                        <div class="file-name">{name}</div>
                        <div class="file-meta">{desc}</div>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("Open", key=f"open_{i}_{j}"):
                            st.info(f"Opening {name}")
                            st.session_state["selected_file"] = name
                    with col_b:
                        if (not is_demo and item.get("type") == "file" and meta):
                            path = meta.get("path")
                            ext = name.lower()
                            if path and Path(path).exists() and ext.endswith(('.pdf', '.txt', '.csv', '.docx')):
                                if st.button("📑 Summarize with AI", key=f"summarize_{i}_{j}"):
                                    with st.spinner("Summarizing..."):
                                        summary = agent.tools["summarize_file"]["func"](name)
                                        st.session_state["summary_output"] = {"filename": name, "summary": summary}
    else:
        rows = []
        for item in file_items:
            rows.append({
                "Type": "Folder" if item.get("type") == "folder" else "File",
                "Name": item["name"],
                "Size": f"{item['meta']['size']//1024} KB" if item.get("meta") and "size" in item["meta"] else "-",
                "Date": item["meta"]["created"][:10] if item.get("meta") and "created" in item["meta"] else "-"
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()
    if st.session_state.get("selected_file"):
        name = st.session_state["selected_file"]
        filemeta = None
        for item in file_items:
            if item["name"] == name:
                filemeta = item
        st.markdown(f"#### Preview: {name}")
        if filemeta:
            if filemeta.get("is_demo"):
                st.info("AI summarization not available for demo files.")
                st.write("This file is present for demo purposes only.")
            else:
                meta = filemeta["meta"]
                path = meta["path"]
                ext = name.lower()
                if not Path(path).exists():
                    st.error("File is missing. Please re-upload.")
                elif ext.endswith(('.txt', '.csv')):
                    content = Path(path).read_text(encoding="utf-8", errors="replace")
                    st.text_area("Contents", content[:2000], height=200)
                    if st.button("📑 Summarize this file with AI"):
                        with st.spinner("Summarizing..."):
                            summary = agent.tools["summarize_file"]["func"](name)
                            st.session_state["summary_output"] = {"filename": name, "summary": summary}
                elif ext.endswith('.pdf'):
                    with open(path, "rb") as f:
                        st.download_button("⬇ Download PDF", f, name, mime="application/pdf")
                elif ext.endswith(('.png', '.jpg', '.jpeg')):
                    st.image(path)
                else:
                    st.write("Preview not supported. Download instead.")
                    with open(path, "rb") as f:
                        st.download_button("⬇ Download file", f, name)

    st.divider()
    # --- Stats bar: always live, merged type/file/folder count
    folders = [(i["name"], i.get("meta", {})) for i in file_items if i.get("type") == "folder"]
    files = [(i["name"], i.get("meta", {})) for i in file_items if i.get("type") == "file"]
    num_files, ext_counts, num_folders = merged_file_folder_count_stats(
        get_current_folder(), STATIC_DEMO_FILES, files, folders
    )
    user_storage = sum(item.get("meta", {}).get("size", 0) for item in file_items if not item.get("is_demo", False) and item.get("type") == "file")
    ext_summary = ", ".join([f"{v} {k}" for k, v in ext_counts.items()])
    stats_html = f"""
    <div class="stats-bar">
        <span>📁 {num_folders} folders</span> • 
        <span>📄 {num_files} files</span> • 
        <span>💾 User Storage: {user_storage/1024:.1f} KB</span>
    </div>
    """
    st.markdown(stats_html, unsafe_allow_html=True)

    # Sidebar: AI summary
    if "summary_output" in st.session_state:
        so = st.session_state["summary_output"]
        with st.sidebar:
            st.subheader(f"AI Summary: {so['filename']}")
            st.info(so['summary'])
            if st.button("Clear summary"):
                del st.session_state["summary_output"]

    st.markdown("---")
    st.markdown("""
    ### 🎯 **Databricks Drive Prototype Demo**
    
    **Key Features Demonstrated:**
    - 📁 **Familiar Interface** - Google Drive-like experience
    - 📤 **File Upload** - Support for Excel, Word, PDF, CSV files
    - 🔍 **Search & Filter** - Find files quickly
    - 📊 **File Preview** - View file contents without downloading
    - 📁 **Folder Organization** - Organize files in folders
    - 👥 **Collaboration** - Share and collaborate on files
    
    **Business Impact:**
    - ✅ **Increased Adoption** - Familiar interface reduces training time
    - ✅ **Better Data Management** - Organized access to unstructured data
    - ✅ **Improved Productivity** - Easy file operations and collaboration
    - ✅ **Reduced Complexity** - No need to learn new tools
    """)


    # --- Sidebar Q&A with live static+user counts
    with st.expander("🤖 SuperAgent Assistant (demo)"):
        inp = st.text_input("Ask a question about your files/folders...", key="qa_input")
        if inp:
            lower = inp.lower()
            wants_count = "how many" in lower or "count" in lower
            folder_mention = "my drive" in lower or "root" in lower or "top" in lower or get_current_folder().lower() in lower
            answered = False
            if wants_count and folder_mention:
                folders_ = [(i["name"], i.get("meta", {})) for i in file_items if i.get("type") == "folder"]
                files_ = [(i["name"], i.get("meta", {})) for i in file_items if i.get("type") == "file"]
                total_files, ext_counts, total_folders = merged_file_folder_count_stats(
                    get_current_folder(), STATIC_DEMO_FILES, files_, folders_
                )
                desc = ", ".join([f"{v} {k}" for k, v in ext_counts.items()])
                st.success(f'📁 {total_folders} folders • 📄 {total_files} files'
                           + (f' • ({desc})' if desc else '') +
                           f' • 💾 User Storage: {user_storage/1024:.1f} KB')
                answered = True
            if not answered:
                with st.spinner("Thinking..."):
                    st.success(agent.ask(inp))

if __name__ == "__main__":
    main()