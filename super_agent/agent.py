from openai import OpenAI
import os

class SuperAgent:
    def __init__(self, databricks_token=None, base_url=None):
        self.tools = {}
        self.llm = None

        # Initialize OpenAI client for Databricks LLM
        token = databricks_token or os.environ.get('DATABRICKS_TOKEN')
        endpoint = base_url or "https://e2-demo-field-eng.cloud.databricks.com/serving-endpoints/drive_superagent"  # Update if needed

        if token:
            self.llm = OpenAI(api_key=token, base_url=endpoint)
        else:
            print("Warning: No Databricks token found; LLM won't be initialized.")

    def set_llm(self, llm_client):
        """Set or update the LLM client."""
        self.llm = llm_client

    def register_tool(self, name, func, description=""):
        self.tools[name] = {
            "func": func,
            "description": description
        }

    def ask(self, query):
        # Handle custom tools
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
                return "Please specify the move command as: move <filename> to <folder>"

        # Otherwise, call the LLM chat completion
        if self.llm:
            try:
                response = self.llm.chat.completions.create(
                    model="drive_superagent",  # make sure this matches your deployed model name
                    messages=[{"role": "user", "content": query}],
                    max_tokens=500
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"LLM call failed: {str(e)}"
        else:
            return "No LLM backend configured."


# -- Tool implementations --

def search_files_tool(keyword):
    # Replace with your actual file search logic
    return f"🔍 Searching for files containing: '{keyword}'"

def summarize_file_tool(filename):
    # Replace with your actual file summarization logic
    return f"📝 Summary of file '{filename}': This is a placeholder summary."

def move_file_tool(filename, folder):
    # Replace with your actual file moving logic
    return f"📂 Moving file '{filename}' to folder '{folder}' successfully."

