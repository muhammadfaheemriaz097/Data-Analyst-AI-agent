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
    # UPDATED: Now accepts both CSV and ZIP files
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
                    
                    # UPDATED: Logic to handle ZIP files vs standard CSV files
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

                    # UPDATED: The prompt now tells the AI to read the ACTIVE_FILE path printed by our script
                    messages = [
                        {"role": "system", "content": "You are a Senior Data Analyst. Write python code using pandas and matplotlib to analyze data. ALWAYS use the run_python tool to execute it. Always save charts as 'chart.png'. Ensure you load the correct CSV path indicated by ACTIVE_FILE."},
                        {"role": "user", "content": f"Schema Info:\n{schema_info}\nTask: {query}"}
                    ]

                    st.write("🧠 AI is planning the analysis...")
                    response = client.chat.completions.create(
                        model="gemini-2.5-flash", 
                        messages=messages, 
                        tools=tools, 
                        tool_choice="auto"
                    )
                    
                    msg = response.choices[0].message
                    messages.append(msg)
                    
                    executed_code = None
                    
                    if msg.tool_calls:
                        st.write("💻 Executing AI-generated Python code...")
                        for tool_call in msg.tool_calls:
                            executed_code = json.loads(tool_call.function.arguments)["code"]
                            execution = sandbox.run_code(executed_code)
                            
                            output = execution.text if not execution.error else f"Error: {execution.error.value}"
                            
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": output
                            })
                        
                        st.write("📝 Synthesizing final insights...")
                        final_response = client.chat.completions.create(
                            model="gemini-2.5-flash", 
                            messages=messages
                        )
                        summary = final_response.choices[0].message.content
                    else:
                        summary = msg.content
                    
                    chart_base64 = None
                    try:
                        chart_bytes = sandbox.files.read("chart.png", format="bytes")
                        if chart_bytes:
                            chart_base64 = base64.b64encode(chart_bytes).decode("utf-8")
                    except Exception:
                        pass
                
                status.update(label="Analysis Complete!", state="complete", expanded=False)
                
            except Exception as e:
                status.update(label="An error occurred", state="error", expanded=True)
                st.error(f"Error details: {str(e)}")
                st.stop()

        # --- BEAUTIFUL RESULTS RENDERING (TABS) ---
        st.divider()
        st.markdown('<p class="main-header" style="font-size: 2rem;">Analysis Results</p>', unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["📊 Executive Summary", "📈 Visualization", "💻 Execution Logs"])
        
        with tab1:
            st.markdown(summary)
            
        with tab2:
            if chart_base64:
                image_data = base64.b64decode(chart_base64)
                st.image(image_data, use_container_width=True, caption="AI-Generated Visualization")
            else:
                st.info("No visualization was generated for this specific query. Try asking the AI to 'plot' or 'chart' the data.")
                
        with tab3:
            if executed_code:
                st.markdown("### Python Code Written by AI")
                st.code(executed_code, language="python")
            else:
                st.info("The AI answered the question directly without needing to execute Python code.")
