import base64
import json
import os
import streamlit as st
from openai import OpenAI
from e2b_code_interpreter import Sandbox

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="AI Data Analyst", page_icon="📈", layout="wide")

# --- CUSTOM CSS STYLING ---
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: 700; margin-bottom: 0px; }
    .sub-header { font-size: 1.1rem; color: #6B7280; margin-bottom: 30px; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; height: 3rem; }
</style>
""", unsafe_allow_html=True)

# --- API KEY MANAGEMENT ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
E2B_API_KEY = os.environ.get("E2B_API_KEY") or st.secrets.get("E2B_API_KEY")

client = OpenAI(
    api_key=GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# --- SIDEBAR: SETTINGS & UPLOADS ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2103/2103254.png", width=60)
    st.title("Settings & Data")
    
    st.markdown("### System Status")
    if GEMINI_API_KEY:
        st.markdown("✅ **Gemini API:** Connected")
    else:
        st.error("❌ Gemini API Key Missing")
        
    if E2B_API_KEY:
        st.markdown("✅ **E2B Sandbox:** Connected")
    else:
        st.error("❌ E2B API Key Missing")
        
    st.divider()
    
    st.markdown("### Upload Dataset")
    uploaded_file = st.file_uploader("Upload your CSV or ZIP file here", type=["csv", "zip"], help="Maximum file size is 200MB.")

# --- MAIN DASHBOARD INTERFACE ---
st.markdown('<p class="main-header">📈 Autonomous Data Analyst Agent</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Upload a dataset, ask a question in plain English, and watch the AI write code to analyze and visualize your data.</p>', unsafe_allow_html=True)

query = st.text_area(
    "What would you like to know about this data?", 
    placeholder="e.g., Which product category generated the most revenue? Please create a bar chart.",
    height=100
)

# --- EXECUTION LOGIC ---
if st.button("🚀 Run Analysis", type="primary"):
    if not GEMINI_API_KEY or not E2B_API_KEY:
        st.error("Cannot run: Missing API Keys. Please check your Streamlit Secrets.")
    elif not uploaded_file:
        st.warning("Please upload a dataset from the sidebar first.")
    elif not query.strip():
        st.warning("Please enter a question for the AI.")
    else:
        with st.status("Initializing AI Agent...", expanded=True) as status:
            file_bytes = uploaded_file.getvalue()
            filename = uploaded_file.name
            
            try:
                st.write("🔒 Spinning up isolated E2B cloud sandbox...")
                with Sandbox.create() as sandbox:
                    
                    st.write("📂 Uploading dataset to sandbox...")
                    sandbox.files.write(filename, file_bytes)
                    
                    st.write("🔍 Inspecting dataset schema...")
                    
                    if filename.endswith(".zip"):
                        st.write("📦 Extracting ZIP archive...")
                        inspect_script = f"""
import zipfile, os, glob
import pandas as pd

with zipfile.ZipFile('{filename}', 'r') as zip_ref:
    zip_ref.extractall('extracted_data')

csv_files = glob.glob('extracted_data/**/*.csv', recursive=True)
if not csv_files:
    raise FileNotFoundError("No CSV file found inside the uploaded ZIP archive.")

target_csv = csv_files[0]
df = pd.read_csv(target_csv)
print("ACTIVE_FILE:", target_csv)
print("COLUMNS:", list(df.columns))
print("TYPES:\\n", df.dtypes.to_dict())
"""
                    else:
                        inspect_script = f"""
import pandas as pd
df = pd.read_csv('{filename}')
print("ACTIVE_FILE:", '{filename}')
print("COLUMNS:", list(df.columns))
print("TYPES:\\n", df.dtypes.to_dict())
"""

                    schema_info = sandbox.run_code(inspect_script).text

                    tools = [{
                        "type": "function",
                        "function": {
                            "name": "run_python",
                            "description": "Executes Python code. ALWAYS save charts as 'chart.png' via plt.savefig('chart.png').",
                            "parameters": {
                                "type": "object",
                                "properties": {"code": {"type": "string"}},
                                "required": ["code"],
                            }
                        }
                    }]

                    messages = [
                        {"role": "system", "content": "You are a Senior Data Analyst. Write python code using pandas and matplotlib to analyze data. ALWAYS use the run_python tool to execute it. Always save charts as 'chart.png'. Ensure you load the correct CSV path indicated by ACTIVE_FILE."},
                        {"role": "user", "content": f"Schema Info:\n{schema_info}\nTask: {query}"}
                    ]

                    st.write("🧠 AI is planning the analysis...")
                    
                    # FIX: Explicitly forcing the AI to call the 'run_python' tool
                    response = client.chat.completions.create(
                        model="gemini-2.5-flash", 
                        messages=messages, 
                        tools=tools, 
                        tool_choice={"type": "function", "function": {"name": "run_python"}}
                    )
                    
                    msg = response.choices[0].message
                    
                    assistant_message = {
                        "role": "assistant",
                        "content": msg.content or "" 
                    }
                    
                    executed_
