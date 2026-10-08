# 📈 Autonomous Data Analyst Pro

An autonomous, multi-turn AI Data Analyst agent built with **Streamlit**, **Google Gemini** (via OpenAI-compatible endpoint), and **E2B Code Interpreter**. 

Upload one or multiple CSV/ZIP datasets, ask complex business questions in natural language, and the agent writes, tests, self-heals, and executes Python code inside an isolated cloud sandbox to generate data summaries, interactive Plotly visualizations, and downloadable exports.

---

## 🌟 Key Features

* **Multi-Turn Conversational Memory:** Ask follow-up questions naturally without losing context across the chat session.
* **Self-Healing Code Execution Loop:** If generated Python code throws an error (e.g., column mismatches, data type errors), the agent reads the traceback, debugs itself, and retries up to 3 times automatically.
* **Interactive Visualizations (Plotly):** Generates interactive graphs (zoom, pan, hover tooltips) exported as JSON and rendered natively in the UI.
* **Multi-File & Archive Support:** Upload multiple `.csv` files or `.zip` archives simultaneously; the agent inspects all available schemas and joins datasets with `pandas.merge()`.
* **Data Transformation & Export:** Ask the agent to clean, filter, or transform data, and receive an instant download button for the modified CSV.
* **Isolated Cloud Execution:** Python execution runs inside secure, ephemeral [E2B sandboxes](https://e2b.dev/), ensuring complete safety from untrusted code execution.

---

## 🏗️ Architecture & Workflow

```text
User Prompt + Datasets
         │
         ▼
[Streamlit Frontend] ───> Uploads files to [E2B Sandbox]
                                   │
                                   ▼
                            Schema Extracted
                                   │
                                   ▼
                       [Gemini 2.5 Flash LLM]
                         (Forced Tool Choice)
                                   │
                                   ▼
                        Generated Python Script
                                   │
                                   ▼
                       [E2B Sandbox Execution]
                        ├── Error? ──> Feedback Loop (Retry up to 3x)
                        └── Success ──> Returns Output, Plotly JSON, CSV
                                   │
                                   ▼
                     Rendered in Streamlit Chat UI
