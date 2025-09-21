from dotenv import load_dotenv
import os
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import tempfile

# -------- NEW AI imports --------
from super_agent.agent import SuperAgent, summarize_file_tool
from openai import OpenAI
from functools import partial

# ------- ENV + AI setup ---------
load_dotenv()
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_BASE_URL = "https://e2-demo-field-eng.cloud.databricks.com/serving-endpoints"

# Demo storage path (for sample files)
DEMO_STORAGE_PATH = Path(tempfile.gettempdir()) / "databricks_drive"
DEMO_STORAGE_PATH.mkdir(exist_ok=True)

# --- AI agent setup ---
db_client = OpenAI(api_key=DATABRICKS_TOKEN, base_url=DATABRICKS_BASE_URL)
agent = SuperAgent()
agent.set_llm(db_client)
agent.register_tool("summarize_file", partial(summarize_file_tool, llm=agent.llm), "Summarize file with AI")

# ------- UI CONFIGURATION -------
st.set_page_config(
    page_title="Databricks Drive",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .main-header { background: #1a73e8; color: white; padding: 0.5rem 1rem; border-radius: 8px; margin-bottom: 1rem; display: flex; align-items: center; justify-content: space-between; }
    .drive-logo { font-size: 1.5rem; font-weight: bold; display: flex; align-items: center; gap: 0.5rem; }
    .toolbar { background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid #e0e0e0; }
    .file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0; }
    .file-card { background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem; text-align: center; transition: all 0.2s ease; cursor: pointer; }
    .file-card:hover { border-color: #1a73e8; box-shadow: 0 2px 8px rgba(26, 115, 232, 0.1); }
    .file-icon { font-size: 3rem; margin-bottom: 0.5rem; }
    .file-name { font-weight: 500; color: #202124; margin-bottom: 0.25rem; word-break: break-word; }
    .file-meta { font-size: 0.8rem; color: #5f6368; }
    .breadcrumb { background: #f8f9fa; padding: 0.5rem 1rem; border-radius: 4px; margin-bottom: 1rem; font-size: 0.9rem; }
    .upload-area { border: 2px dashed #dadce0; border-radius: 8px; padding: 2rem; text-align: center; background: #fafbfc; margin: 1rem 0; }
    .stats-bar { background: #f8f9fa; padding: 0.5rem 1rem; border-radius: 4px; margin-top: 1rem; border: 1px solid #e0e0e0; }
    .action-button { background: #1a73e8; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; margin: 0.25rem; }
    .action-button:hover { background: #1557b0; }
    .secondary-button { background: white; color: #1a73e8; border: 1px solid #dadce0; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; margin: 0.25rem; }
</style>
""", unsafe_allow_html=True)

class GoogleDriveInterface:
    def __init__(self):
        if 'current_path' not in st.session_state:
            st.session_state.current_path = "My Drive"
        if 'view_mode' not in st.session_state:
            st.session_state.view_mode = "grid"
        if 'selected_files' not in st.session_state:
            st.session_state.selected_files = []

        self.storage_path = DEMO_STORAGE_PATH

        # ----------- DEMO FILE SETUP ----------
        self.init_demo_data()

    def init_demo_data(self):
        demo_files = [
            ("📊 Sales Report Q3.xlsx", "Excel file • 2.3 MB • 3 days ago"),
            ("📝 Project Proposal.docx", "Word document • 1.1 MB • 1 week ago"),
            ("📊 Customer Data.csv", "CSV file • 850 KB • 2 weeks ago"),
            ("📄 Contract.pdf", "PDF • 4.2 MB • 3 weeks ago"),
            ("🖼️ Product Images", "Folder • 15 items • 1 month ago"),
            ("📁 Financial Reports", "Folder • 8 items • 2 months ago"),
            # -- Optional demo file for summarizer --
            ("📄 sample.txt", "Text file • 0.1 KB • Just now"),
        ]
        if 'demo_files' not in st.session_state:
            st.session_state.demo_files = demo_files

        # --- Actually create 'sample.txt' so agent can summarize it ---
        sample_path = self.storage_path / "sample.txt"
        if not sample_path.exists():
            sample_path.write_text("This is a demo file for AI summarization. You can show summaries here!", encoding="utf-8")

        # You can similarly add other sample files for fuller summarization demos.

    def get_file_icon(self, filename):
        if filename.endswith('Folder') or 'Folder' in filename:
            return "📁"
        elif any(ext in filename.lower() for ext in ['.xlsx', '.xls']):
            return "📊"
        elif any(ext in filename.lower() for ext in ['.docx', '.doc']):
            return "📝"
        elif '.csv' in filename.lower():
            return "📋"
        elif '.pdf' in filename.lower():
            return "📄"
        elif any(ext in filename.lower() for ext in ['.png', '.jpg', '.jpeg']):
            return "🖼️"
        else:
            return "📄"

    def render_header(self):
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

    def render_toolbar(self):
        col1, col2, col3, col4 = st.columns([2, 1, 1, 2])

        with col1:
            uploaded_files = st.file_uploader(
                "📤 Upload files",
                accept_multiple_files=True,
                type=['xlsx', 'xls', 'docx', 'doc', 'pdf', 'csv', 'txt', 'png', 'jpg'],
                key="file_uploader"
            )
            if uploaded_files:
                for file in uploaded_files:
                    file_path = self.storage_path / file.name
                    with open(file_path, "wb") as f:
                        f.write(file.getbuffer())
                    st.success(f"✅ Uploaded: {file.name}")

        with col2:
            if st.button("📁 New Folder"):
                st.session_state.show_new_folder = True

        with col3:
            view_mode = st.selectbox("View", ["Grid", "List"], key="view_selector")
            st.session_state.view_mode = view_mode.lower()

        with col4:
            search_term = st.text_input("🔍 Search files", placeholder="Search in Drive")
            if search_term:
                st.session_state.search_term = search_term

    def render_breadcrumb(self):
        breadcrumb_html = f"""
        <div class="breadcrumb">
            <span>📁 {st.session_state.current_path}</span>
        </div>
        """
        st.markdown(breadcrumb_html, unsafe_allow_html=True)

    def render_file_grid(self):
        files = st.session_state.demo_files
        if hasattr(st.session_state, 'search_term'):
            files = [f for f in files if st.session_state.search_term.lower() in f[0].lower()]

        cols_per_row = 4
        for i in range(0, len(files), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, file_info in enumerate(files[i:i+cols_per_row]):
                if j < len(cols):
                    with cols[j]:
                        filename, metadata = file_info
                        icon = self.get_file_icon(filename)
                        card_html = f"""
                        <div class="file-card">
                            <div class="file-icon">{icon}</div>
                            <div class="file-name">{filename}</div>
                            <div class="file-meta">{metadata}</div>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)

                        # Action buttons (original!)
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("Open", key=f"open_{i}_{j}"):
                                if "Folder" in filename:
                                    st.session_state.current_path = filename
                                    st.rerun()
                                else:
                                    # Show file preview below main area
                                    st.session_state.selected_files = [filename]

                        with col_b:
                            if st.button("⋮", key=f"menu_{i}_{j}"):
                                st.session_state.show_context_menu = f"{i}_{j}"

                        # ----------- NEW: summarize with AI if it's a real demo file ----------
                        if not "Folder" in filename and filename.endswith(('.txt', '.pdf', '.csv', '.docx')):
                            # Find the raw file name (strip emoji and space: "📄 sample.txt" -> "sample.txt")
                            clean_name = filename.split(" ", 1)[-1]
                            file_path = self.storage_path / clean_name
                            if file_path.exists():
                                if st.button("📑 Summarize with AI", key=f"summarize_{i}_{j}"):
                                    with st.spinner("Summarizing with AI..."):
                                        summary = agent.tools["summarize_file"]["func"](str(file_path))
                                        st.info(summary)

    def render_file_list(self):
        files = st.session_state.demo_files
        if hasattr(st.session_state, 'search_term'):
            files = [f for f in files if st.session_state.search_term.lower() in f[0].lower()]

        file_data = []
        for filename, metadata in files:
            icon = self.get_file_icon(filename)
            file_data.append({
                'Icon': icon,
                'Name': filename,
                'Details': metadata,
                'Actions': '⋮'
            })

        df = pd.DataFrame(file_data)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Icon": st.column_config.TextColumn("", width="small"),
                "Name": st.column_config.TextColumn("Name", width="large"),
                "Details": st.column_config.TextColumn("Details", width="medium"),
                "Actions": st.column_config.TextColumn("", width="small")
            }
        )

    def render_upload_area(self):
        st.markdown("""
        <div class="upload-area">
            <h3>📤 Drag files here to upload</h3>
            <p>Or use the upload button above</p>
            <p style="font-size: 0.8rem; color: #5f6368;">
                Supports: Excel, Word, PDF, CSV, Images and more
            </p>
        </div>
        """, unsafe_allow_html=True)

    def render_stats_bar(self):
        total_files = len([f for f in st.session_state.demo_files if not "Folder" in f[0]])
        total_folders = len([f for f in st.session_state.demo_files if "Folder" in f[0]])

        stats_html = f"""
        <div class="stats-bar">
            <span>📁 {total_folders} folders</span> • 
            <span>📄 {total_files} files</span> • 
            <span>💾 15.7 GB used of 100 GB</span>
        </div>
        """
        st.markdown(stats_html, unsafe_allow_html=True)

    def render_context_menu(self):
        if hasattr(st.session_state, 'show_context_menu'):
            with st.sidebar:
                st.subheader("File Actions")
                if st.button("📥 Download"):
                    st.success("Download started!")
                if st.button("✏️ Rename"):
                    st.info("Rename dialog would open")
                if st.button("📋 Make a copy"):
                    st.info("File copied!")
                if st.button("🗑️ Move to trash"):
                    st.warning("File moved to trash")
                if st.button("ℹ️ File information"):
                    st.info("File details would show")

    # ----------- NEW FILE PREVIEW & SUMMARIZE ---------
    def render_file_preview(self):
        selected = st.session_state.selected_files[0] if st.session_state.selected_files else None
        if not selected:
            return

        st.markdown(f"#### Preview: {selected}")
        # Only show preview/summarize on .txt and .pdf for demo
        clean_name = selected.split(" ", 1)[-1]
        file_path = self.storage_path / clean_name
        ext = clean_name.lower()
        if not file_path.exists():
            st.error("Demo preview only works for demo-sample files.")
            return
        if ext.endswith(".txt"):
            content = file_path.read_text(encoding="utf-8")
            st.text_area("Contents", content[:2000], height=200)
            if st.button("📑 Summarize this file with AI", key="preview_summarize"):
                with st.spinner("Summarizing..."):
                    summary = agent.tools["summarize_file"]["func"](str(file_path))
                    st.info(summary)
        elif ext.endswith(('.pdf', '.csv', '.docx')):
            if st.button("📑 Summarize with AI", key="preview_summarize_general"):
                with st.spinner("Summarizing..."):
                    summary = agent.tools["summarize_file"]["func"](str(file_path))
                    st.info(summary)
            st.caption("Demo summary only; preview not shown.")
        else:
            st.write("Preview not supported. Download instead.")

def main():
    drive = GoogleDriveInterface()
    drive.render_header()
    drive.render_toolbar()
    drive.render_breadcrumb()

    # Main content area with minimal change
    if st.session_state.view_mode == "grid":
        drive.render_file_grid()
    else:
        drive.render_file_list()

    # Upload area for empty state
    if len(st.session_state.demo_files) == 0:
        drive.render_upload_area()

    # Stats
    drive.render_stats_bar()

    # Context menu
    drive.render_context_menu()

    # ----------- NEW: file preview + AI summarize -----------
    if st.session_state.get("selected_files"):
        drive.render_file_preview()

    st.markdown("---")
    st.markdown("""
    ### 🎯 **Databricks Drive Prototype Demo**

    **Key Features Demonstrated:**
    - 📁 **Familiar Interface** - Google Drive-like experience
    - 📤 **File Upload** - Support for Excel, Word, PDF, CSV files
    - 🔍 **Search & Filter** - Find files quickly
    - 📊 **File Preview** - View file contents without downloading
    - 📑 **AI-powered File Summarization** - Summarize supported files with SuperAgent
    - 📁 **Folder Organization** - Organize files in folders
    - 👥 **Collaboration** - Share and collaborate on files

    **Business Impact:**
    - ✅ **Increased Adoption** - Familiar interface reduces training time
    - ✅ **Better Data Management** - Organized access to unstructured data
    - ✅ **Improved Productivity** - Easy file operations and collaboration
    - ✅ **Reduced Complexity** - No need to learn new tools
    """)

    # ----------- NEW: Assistant Q&A panel (optional) -----------
    with st.expander("🤖 SuperAgent Assistant (experimental)"):
        user_q = st.text_input("Ask a question about files/folders...")
        if user_q:
            with st.spinner("Thinking..."):
                st.success(agent.ask(user_q))

if __name__ == "__main__":
    main()