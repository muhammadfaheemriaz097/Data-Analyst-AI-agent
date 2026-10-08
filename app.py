import base64
import json
import os
import streamlit as st
from openai import OpenAI
from e2b_code_interpreter import Sandbox

st.set_page_config(page_title="Gemini Data Analyst", layout="wide")

st.title("📊 Gemini Data Analyst Agent")
st.markdown("Powered by Google Gemini 1.5 Flash and E2B Cloud Sandboxes.")

# 1. Retrieve API Keys securely from Streamlit Secrets
# In Hugging Face Spaces, you set these in the "Settings -> Variables and secrets" tab
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
E2B_API_KEY = os.environ.get("E2B_API_KEY") or st.secrets.get("E2B_API_KEY")

if not GEMINI_API_KEY or not E2B_API_KEY:
    st.warning("Please configure your GEMINI_API_KEY and E2B_API_KEY in the environment or secrets.")
    st.stop()

# 2. Initialize the OpenAI SDK pointing to Google's Gemini endpoint
client = OpenAI(
    api_key=GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# UI Elements
with st.sidebar:
    st.header("Dataset Input")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

query = st.text_area("What would you like to know?", placeholder="e.g., Show me revenue by region as a bar chart.")

if st.button("Run Analysis", type="primary"):
    if not uploaded_file:
        st.error("Please upload a CSV file first.")
    elif not query.strip():
        st.error("Please enter a question.")
    else:
        with st.spinner("Spinning up secure cloud sandbox and analyzing..."):
            
            file_bytes = uploaded_file.getvalue()
            filename = uploaded_file.name
            
            # Spin up the E2B micro-VM
            with Sandbox.create() as sandbox:
                sandbox.files.write(filename, file_bytes)
                
                # Extract schema
                inspect_script = f"""
import pandas as pd
df = pd.read_csv('{filename}')
print("COLUMNS:", list(df.columns))
print("TYPES:\\n", df.dtypes.to_dict())
"""
                schema_info = sandbox.run_code(inspect_script).text

                # Define the execution tool
                tools = [{
                    "type": "function",
                    "function": {
                        "name": "run_python",
                        "description": "Executes Python code. The CSV is saved locally. Save charts as 'chart.png'.",
                        "parameters": {
                            "type": "object",
                            "properties": {"code": {"type": "string"}},
                            "required": ["code"],
                        }
                    }
                }]

                messages = [
                    {"role": "system", "content": "You are a Data Analyst. Write python code to analyze data. ALWAYS use the run_python tool to execute it."},
                    {"role": "user", "content": f"Dataset: {filename}\nSchema:\n{schema_info}\nTask: {query}"}
                ]

                # Phase 1: Gemini writes code
                response = client.chat.completions.create(
                    model="gemini-1.5-flash", # Using the fast, free Gemini model
                    messages=messages, 
                    tools=tools, 
                    tool_choice="auto"
                )
                
                msg = response.choices[0].message
                messages.append(msg)
                
                executed_code = None
                
                # If Gemini decides to write code, execute it
                if msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        executed_code = json.loads(tool_call.function.arguments)["code"]
                        execution = sandbox.run_code(executed_code)
                        
                        output = execution.text if not execution.error else f"Error: {execution.error.value}"
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": output
                        })
                    
                    # Phase 2: Gemini synthesizes the output
                    final_response = client.chat.completions.create(
                        model="gemini-1.5-flash", 
                        messages=messages
                    )
                    summary = final_response.choices[0].message.content
                else:
                    summary = msg.content
                
                # Check for a generated chart
                chart_base64 = None
                try:
                    chart_bytes = sandbox.files.read("chart.png", format="bytes")
                    chart_base64 = base64.b64encode(chart_bytes).decode("utf-8")
                except:
                    pass

            # Render Results
            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader("Insights")
                st.markdown(summary)
                if executed_code:
                    with st.expander("View Code Executed"):
                        st.code(executed_code, language="python")
            with col2:
                st.subheader("Visualization")
                if chart_base64:
                    image_data = base64.b64decode(chart_base64)
                    st.image(image_data, use_container_width=True)
                else:
                    st.info("No visualization was generated.")
