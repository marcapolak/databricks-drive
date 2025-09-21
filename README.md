# Databricks Drive – Google Drive-style File Manager (with AI Summarization)

This repository contains a **Streamlit application** that offers a familiar, Google Drive-inspired workflow for file organization, unstructured data management, and AI-powered insight—all in a single business demo UI.

---

## 📽️ Demo Screencast

> **Screencast:**
![Databricks Drive Demo](./streamlit-google_drive_prototype.gif)


---

## 🎯 Databricks Drive Prototype Demo

### Key Features Demonstrated:
- 📁 **Familiar Interface** - Google Drive-like experience  
- 📤 **File Upload** - Support for Excel, Word, PDF, CSV files  
- 🔍 **Search & Filter** - Find files quickly  
- 📊 **File Preview** - View file contents without downloading  
- 📁 **Folder Organization** - Organize files in folders  
- 👥 **Collaboration** - Share and collaborate on files  

### Business Impact:
- ✅ **Increased Adoption** - Familiar interface reduces training time  
- ✅ **Better Data Management** - Organized access to unstructured data  
- ✅ **Improved Productivity** - Easy file operations and collaboration  
- ✅ **Reduced Complexity** - No need to learn new tools  

---

## 🗂️ App Highlights

- **Demo Files/Folders Always Present:**  
  A fixed set of demo Excel, Word, PDF, CSV, and folder entries are *always visible* for onboarding or demo—even if no user upload occurs. These static samples cannot be overwritten, deleted, or summarized.

- **User File Upload, Folder Creation & Organization:**  
  Upload any supported file (Excel, Word, PDF, CSV, text, image) to "My Drive" and create user folders. Uploaded files persist, are previewable, and may be deleted—but demo content is always protected.

- **Merged UI for Real + Demo Content:**  
  All display (grid/list), stats, and sidebar Q&A **merge user and static demo items** at runtime, so users see a seamless Drive-like experience.

- **AI File Summarization:**  
  Any user-uploaded file (if supported: PDF, TXT, CSV, DOCX, etc. and present on disk) can be summarized via SuperAgent with a dedicated sidebar summary panel.  
  - Summaries are auto-cleared when uploading/deleting or when the file is missing.  
  - Demo/static ("business sample") files **cannot be summarized** for extra safety.

- **Business-Grade Stats & Assistant:** - TO DO -
  - The bottom stats bar **and** sidebar assistant Q&A always display *live, merged* file/folder type and count (e.g. “📁 4 folders • 📄 9 files • 💾 User Storage: 281.6 KB”)—updating instantly as files are added/removed.  
  - Q&A queries like "How many files?", "How many PDFs?" etc. **always return accurate results** reflecting both all demo + user files/folders, never hallucinated.

- **Classic UX:**  
  - Robust search and filtering (case-insensitive).  
  - Grid/list switcher, Drive-style cards, and readable menu/actions.  
  - Sidebar and stats always match visible Drive state, with session-robust upload/delete handling and error-free reruns.


---

## 🏗️ Repo Structure - TO DO -


```plaintext
├── .env                  
├── .gitignore
├── google_drive_prototype.py
├── requirements.txt
├── super_agent/
│   └── agent.py          ← GPT-based agent logic
```

## Authors and Contributors
---
**Lead Author:**  
- Daniel Velasquez Dahlin (Field Engineering, Senior Solutions Engineer)

**Co-Authors / Contributors:**  
- Karanveer Singh (Field Engineering, Senior Solutions Engineer)  
- Marcelina Polak (Field Engineering, Senior Solutions Engineer)

