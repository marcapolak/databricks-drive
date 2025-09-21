from dotenv import load_dotenv
import os
import streamlit as st
from functools import partial
from pathlib import Path
import tempfile
import pandas as pd
from super_agent.agent import (
    SuperAgent, search_files_tool, summarize_file_tool, move_file_tool,
    load_metadata, create_folder, delete_file
)
from openai import OpenAI
from datetime import datetime

load_dotenv()
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_BASE_URL = "https://e2-demo-field-eng.cloud.databricks.com/serving-endpoints"

STORAGE_PATH = Path(tempfile.gettempdir()) / "databricks_drive_files"
STORAGE_PATH.mkdir(exist_ok=True)
os.environ["DRIVE_STORAGE_PATH"] = str(STORAGE_PATH)

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
 .stats-bar { background: #f8f9fa; padding: 0.5rem 1rem; border-radius: 4px; margin-top: 1rem; border: 1px solid #e0e0e0; }
 .breadcrumb { background: #f8f9fa; padding: 0.5rem 1rem; border-radius: 4px; margin-bottom: 1rem; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

def list_folder_content(folder):
    meta = load_metadata()
    children = meta["folders"][folder]["children"]
    files, folders = [], []
    for name in children:
        if name in meta["files"]:
            files.append((name, meta["files"][name]))
        elif name in meta["folders"]:
            folders.append((name, meta["folders"][name]))
    return folders, files

def upload_files(files, parent):
    meta = load_metadata()
    for file in files:
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

def get_current_folder():
    return st.session_state.get("current_path", "My Drive")

def set_current_folder(folder):
    st.session_state["current_path"] = folder

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

def render_main():
    st.markdown(
        "<div class='main-header'>"
        "<div class='drive-logo'><span>📁</span> <span>Databricks Drive</span></div>"
        "<div><span style='font-size:0.9rem;'>Unstructured Data Management Platform</span></div></div>",
        unsafe_allow_html=True
    )

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
        search_term = st.text_input("🔍 Search files", placeholder="Search in Drive")
        st.session_state["search_term"] = search_term

    if st.session_state.get("show_new_folder"):
        folder_name = st.text_input("Folder name:")
        if st.button("Create"):
            ok, msg = create_folder(folder_name, get_current_folder())
            st.success(msg) if ok else st.error(msg)
            st.session_state["show_new_folder"] = False

    bc_left, bc_right = st.columns([4,1])
    with bc_left:
        st.markdown(f"<div class='breadcrumb'><span>📁 {get_current_folder()}</span></div>", unsafe_allow_html=True)
    with bc_right:
        pass  # Only per-file summaries

    folders, files = list_folder_content(get_current_folder())
    if st.session_state.get("search_term"):
        files = [(f, d) for f, d in files if st.session_state["search_term"].lower() in f.lower()]

    st.divider()
    if st.session_state.get("view_mode", "grid") == "grid":
        cols_per_row = 3
        items = folders + files
        for i in range(0, len(items), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, item in enumerate(items[i:i+cols_per_row]):
                if isinstance(item[1], dict) and "children" in item[1]:
                    with cols[j]:
                        if st.button(f"📁 {item[0]}", key=f"folder_{item[0]}"):
                            set_current_folder(item[0])
                            st.experimental_rerun()
                        st.caption("Folder")
                elif isinstance(item[1], dict):
                    with cols[j]:
                        if st.button(f"{file_icon(item[0])} {item[0]}", key=f"file_{item[0]}"):
                            st.session_state["selected_file"] = item[0]
                        st.caption(f"{item[1]['size'] / 1024:.1f} KB, {item[1]['created'][:10]}")
    else:
        data = []
        for f, d in folders:
            data.append({"Type": "Folder", "Name": f, "Size": "-", "Date": d.get("created", "-")[:10]})
        for f, d in files:
            data.append({"Type": "File", "Name": f, "Size": f"{d['size']//1024} KB", "Date": d["created"][:10]})
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    st.divider()
    # --- PDF: Single Summarize & Download Button ---
    if st.session_state.get("selected_file"):
        selected = st.session_state["selected_file"]
        meta = load_metadata()
        path = meta["files"][selected]["path"]
        st.markdown(f"#### Preview: {selected}")
        ext = selected.lower()
        if ext.endswith(('.txt', '.csv')):
            content = Path(path).read_text(encoding="utf-8")
            st.text_area("Contents", content[:2000], height=200)
        elif ext.endswith(('.png', '.jpg', '.jpeg')):
            st.image(path)
        elif ext.endswith('.pdf'):
            if st.button("📑 Summarize & Download PDF"):
                with st.spinner("Analyzing PDF and generating summary..."):
                    summary = agent.tools["summarize_file"]["func"](selected)
                    st.info(summary)
                    with open(path, "rb") as f:
                        st.download_button("⬇ Download PDF", f, selected, mime="application/pdf")
        else:
            st.write("Preview not supported. Download instead.")

    st.divider()
    st.markdown(
        "<div class='stats-bar'>"
        f"<span>📁 {len(folders)} folders</span> • "
        f"<span>📄 {len(files)} files</span> • "
        f"<span>💾 Storage: {sum([f[1]['size'] for f in files]) / 1024:.1f} KB"
        "</span></div>", unsafe_allow_html=True
    )
    st.divider()

    if st.session_state.get("show_context_menu"):
        fname = st.session_state["show_context_menu"]
        meta = load_metadata()
        folders_list = [f for f in meta["folders"].keys() if f != meta["files"][fname]["parent"]]
        st.sidebar.header(f"Actions: {fname}")
        dest = st.sidebar.selectbox("Move to folder:", folders_list)
        if st.sidebar.button("Move"):
            st.sidebar.info(move_file_tool(fname, dest))
            st.session_state.pop("show_context_menu")
            st.experimental_rerun()
    st.divider()
    with st.expander("🤖 SuperAgent Assistant"):
        inp = st.text_input("Ask a question...", placeholder="e.g. How many PDFs are in My Drive?")
        if inp:
            with st.spinner("Thinking..."):
                st.success(agent.ask(inp))

if __name__ == "__main__":
    if "current_path" not in st.session_state:
        st.session_state["current_path"] = "My Drive"
    render_main()