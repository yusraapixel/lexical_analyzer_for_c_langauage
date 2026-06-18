

# C Language Lexical Analyzer

A web based lexical analyzer for C source code built with Python and Streamlit. 
Tokenizes C programs, builds a symbol table, detects lexical errors, and visualizes tokentype statistics.
Display output in interactive UI uisng Streamlit.



## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yusraapixel/lexical_analyzer_for_c_langauage.git
cd lexical_analyzer_for_c_langauage

# 2. (Optional) Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

### Running the App

```bash
streamlit run App.py
```

The app opens in your browser at `http://localhost:8501`.

---

## Usage

1. **Choose an input method** — type C code directly or upload a `.c` / `.h` / `.txt` file.
2. Use the **Load a sample program** dropdown to try a pre-loaded valid or error-containing program.
3. Click **Analyze Source Code**.
4. Browse results across four tabs:
Token Stream, Symbol Table, Lexical Errors ,Statistics

## Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web UI framework |
| `pandas` | DataFrame display and CSV export |

Install with:
```bash
pip install streamlit pandas
```

---



## License

This project is submitted as an academic project. All rights reserved by the author.
