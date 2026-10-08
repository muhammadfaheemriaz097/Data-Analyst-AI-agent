import json
import os
import streamlit as st
from openai import OpenAI
from e2b_code_interpreter import Sandbox
import plotly.io as pio

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="AI Data Analyst Pro", page_icon="📈", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; margin-bottom: 0px; }
    .sub-header { font-size: 1rem; color: #6B7280; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE (MEMORY) ---
if "messages" not in st.session_state:
    st.session_state.messages = [] # Stores full API history
if "chat_ui" not in st.session_state:
    st.session_state.chat_ui = [] # Stores UI elements (text, charts, data)

# --- API KEY MANAGEMENT ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
E2B_API_KEY = os.environ.get("E2B_API_KEY") or st.secrets.get("E2B_API_KEY")

client = OpenAI(
    api_key=GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# --- SIDEBAR: SETTINGS & UPLOADS ---
with st.sidebar:
    st.title("⚙️ Workspace")
    
    # MULTI-FILE UPLOAD
    uploaded_files = st.file_uploader(
        "Upload Datasets (CSV/ZIP)", 
        type=["csv", "zip"], 
        accept_multiple_files=True,
        help="Upload multiple files to join them."
    )
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_ui = []
        st.rerun()

    st.divider()
    st.markdown("### System Status")
    st.markdown("✅ Gemini API" if GEMINI_API_KEY else "❌ Gemini API Missing")
    st.markdown("✅ E2B Sandbox" if E2B_API_KEY else "❌ E2B API Missing")

# --- MAIN DASHBOARD INTERFACE ---
st.markdown('<p class="main-header">📈 Autonomous Data Analyst Pro</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Upload data, ask complex questions, and watch the AI write self-healing code to analyze it.</p>', unsafe_allow_html=True)

# --- RENDER CHAT HISTORY ---
for ui_msg in st.session_state.chat_ui:
    with st.chat_message(ui_msg["role"]):
        if ui_msg.get("text"): st.markdown(ui_msg["text"])
        if ui_msg.get("chart"): st.plotly_chart(pio.from_json(ui_msg["chart"]), use_container_width=True)
        if ui_msg.get("csv_bytes") and ui_msg.get("csv_name"):
            st.download_button(
                label=f"⬇️ Download {ui_msg['csv_name']}",
                data=ui_msg["csv_bytes"],
                file_name=ui_msg["csv_name"],
                mime="text/csv"
            )
        if ui_msg.get("code"):
            with st.expander("💻 View Executed Python Code"):
                st.code(ui_msg["code"], language="python")

# --- CHAT INPUT & EXECUTION ---
if query := st.chat_input("E.g., Merge these datasets and plot revenue by region..."):
    if not GEMINI_API_KEY or not E2B_API_KEY:
        st.error("Missing API Keys.")
        st.stop()
    if not uploaded_files:
        st.warning("Please upload at least one dataset in the sidebar.")
        st.stop()

    # 1. Add User Query to UI and API Memory
    st.session_state.chat_ui.append({"role": "user", "text": query})
    with st.chat_message("user"):
        st.markdown(query)
        
    with st.chat_message("assistant"):
        with st.status("Analyzing...", expanded=True) as status:
            try:
                # 2. Spin up Sandbox & Process Files
                with Sandbox.create() as sandbox:
                    status.write("📂 Uploading files to isolated cloud sandbox...")
                    for f in uploaded_files:
                        sandbox.files.write(f.name, f.getvalue())
                        if f.name.endswith(".zip"):
                            sandbox.run_code(f"import zipfile\nwith zipfile.ZipFile('{f.name}', 'r') as zip_ref:\n    zip_ref.extractall('.')")
                    
                    status.write("🔍 Inspecting schema across all files...")
                    inspect_code = """
import os, glob, pandas as pd
csvs = glob.glob('**/*.csv', recursive=True)
for c in csvs:
    try:
        df = pd.read_csv(c, nrows=5)
        print(f"\\nFILE: {c}")
        print("COLUMNS:", list(df.columns))
        print("TYPES:\\n", df.dtypes.to_dict())
    except: pass
"""
                    schema_info = sandbox.run_code(inspect_code).text

                    # 3. Formulate System Prompt
                    sys_prompt = f"""You are an elite Data Analyst. You write Python code using pandas and plotly.
1. ALWAYS use the `run_python` tool to execute code.
2. The current available CSV files and their schemas are: {schema_info}
3. INTERACTIVE CHARTS: If asked for a chart, ALWAYS use `plotly.express` or `plotly.graph_objects` and save it as a JSON file exactly named `chart.json` using `fig.write_json('chart.json')`.
4. DATA EXPORT: If asked to clean, filter, or export data, ALWAYS save the final dataframe exactly as `output.csv` using `df.to_csv('output.csv', index=False)`.
"""
                    # Overwrite system prompt in memory to ensure updated schema
                    api_messages = [{"role": "system", "content": sys_prompt}] + st.session_state.messages
                    api_messages.append({"role": "user", "content": query})
                    
                    tools = [{
                        "type": "function",
                        "function": {
                            "name": "run_python",
                            "description": "Executes Python code in a secure sandbox.",
                            "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}
                        }
                    }]

                    # 4. Self-Healing Execution Loop
                    max_retries = 3
                    retries = 0
                    final_summary = ""
                    executed_code = ""
                    
                    while retries < max_retries:
                        status.update(label=f"🧠 Planning & Coding (Attempt {retries+1}/{max_retries})...")
                        response = client.chat.completions.create(
                            model="gemini-2.5-flash",
                            messages=api_messages,
                            tools=tools,
                            tool_choice={"type": "function", "function": {"name": "run_python"}} if retries == 0 else "auto"
                        )
                        
                        msg = response.choices[0].message
                        api_messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": getattr(msg, 'tool_calls', None)})
                        
                        if msg.tool_calls:
                            for tool_call in msg.tool_calls:
                                code = json.loads(tool_call.function.arguments)["code"]
                                executed_code = code # Save for UI
                                status.write("💻 Executing Python code...")
                                execution = sandbox.run_code(code)
                                
                                if execution.error:
                                    status.write(f"⚠️ Code error detected. Self-healing... ({execution.error.value})")
                                    api_messages.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call.id,
                                        "content": f"ERROR: {execution.error.value}\nPlease fix the code and try again."
                                    })
                                    retries += 1
                                    break # Break tool loop to trigger next LLM call
                                else:
                                    api_messages.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call.id,
                                        "content": execution.text or "Success"
                                    })
                            else:
                                # If loop completes without errors, get final text summary
                                status.write("📝 Synthesizing insights...")
                                final_response = client.chat.completions.create(model="gemini-2.5-flash", messages=api_messages)
                                final_summary = final_response.choices[0].message.content
                                break
                        else:
                            final_summary = msg.content
                            break
                    
                    if retries >= max_retries:
                        final_summary = "⚠️ The agent repeatedly failed to execute the code correctly. Please review the code logs."

                    # 5. Extract Outputs (Chart / CSV)
                    chart_json = None
                    try:
                        chart_bytes = sandbox.files.read("chart.json", format="bytes")
                        chart_json = chart_bytes.decode("utf-8")
                    except: pass
                    
                    csv_export_bytes = None
                    try:
                        csv_export_bytes = sandbox.files.read("output.csv", format="bytes")
                    except: pass
                    
            except Exception as e:
                status.update(label="System Error", state="error", expanded=True)
                st.error(str(e))
                st.stop()

            # 6. Final UI Rendering & Memory Save
            status.update(label="Task Complete!", state="complete", expanded=False)
            
            ui_element = {
                "role": "assistant", 
                "text": final_summary, 
                "code": executed_code,
                "chart": chart_json,
                "csv_bytes": csv_export_bytes,
                "csv_name": "cleaned_data.csv" if csv_export_bytes else None
            }
            
            st.session_state.chat_ui.append(ui_element)
            st.session_state.messages.extend([
                {"role": "user", "content": query},
                {"role": "assistant", "content": final_summary}
            ]) # Save text history for context
            
            st.rerun() # Refresh app to render new messages
