
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

```

---

## 📋 Prerequisites

* Python 3.10+
* A **Google Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/))
* An **E2B API Key** (from [E2B.dev](https://e2b.dev/))

---

## 🚀 Quickstart

### 1. Clone the Repository

```bash
git clone [https://github.com/](https://github.com/)<your-username>/<your-repo-name>.git
cd <your-repo-name>

```

### 2. Set Up a Virtual Environment

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

```

### 3. Install Dependencies

```bash
pip install -r requirements.txt

```

### 4. Configure Environment Variables

Create a `.env` file in the root directory (or use Streamlit secrets):

```env
GEMINI_API_KEY=your_gemini_api_key_here
E2B_API_KEY=your_e2b_api_key_here

```

For Streamlit Cloud deployment, add these under **Settings > Secrets**:

```toml
GEMINI_API_KEY = "your_gemini_api_key_here"
E2B_API_KEY = "your_e2b_api_key_here"

```

### 5. Run the Application

```bash
streamlit run app.py

```

---

## 📦 `requirements.txt`

```text
streamlit
openai
e2b-code-interpreter
pandas
matplotlib
plotly

```

---

## 💡 Example Prompts to Try

1. **Trend & Time-Series Analysis:**
> *"Group total weekly sales by month and plot an interactive line chart showing seasonality."*


2. **Categorical Comparisons:**
> *"Compare average sales during holiday weeks vs non-holiday weeks in a bar chart."*


3. **Data Cleaning & Export:**
> *"Find and remove all rows with missing values in the dataset, calculate the new summary statistics, and provide a download link for the cleaned dataset."*


4. **Multi-Dataset Joins:**
> *"Merge the uploaded orders and customers files on customer ID, then show top 5 cities by total spend."*



---

## 🛡️ License

This project is licensed under the MIT License.

```

```
