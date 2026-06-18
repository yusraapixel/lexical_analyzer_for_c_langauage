
import streamlit as st
import pandas as pd

from lexer.lexer import analyze_source

st.set_page_config(
    page_title="C Lexical Analyzer",
   
    layout="wide",
)

# Sidebar - sample programs for quick demonstration
SAMPLES = {
    "-- Select a sample --": "",
    "Valid: Simple Program": """#include <stdio.h>

int main() {
    int a = 10;
    int b = 20;
    int sum = a + b;
    printf("Sum = %d\\n", sum);
    return 0;
}
""",
    "Valid: Loop with Float": """int main() {
    float total = 0.0;
    int i;
    for (i = 1; i <= 10; i++) {
        total += i * 1.5;
    }
    return 0;
}
""",
    "With Errors: Mixed Issues": """#include <stdio.h>

int main() {
    int x = 10;
    int y@ = 5;          // illegal character '@'
    char c = 'AB';        // invalid character constant
    char *s = "unterminated string; // invalid
    int z = 12abc;        
    /* this comment never closes
    return 0;
}
""",
}

st.title(" C Language Lexical Analyzer")



# Input section

st.subheader("1. Provide Source Code")

input_mode = st.radio(
    "Input method",
    ["Manual Entry", "Upload File"],
    horizontal=True,
)

source_code = ""

if input_mode == "Manual Entry":
    sample_choice = st.selectbox("Load a sample program", list(SAMPLES.keys()))
    default_text = SAMPLES.get(sample_choice, "") if sample_choice != "-- Select a sample --" else ""
    source_code = st.text_area(
        "Enter C source code below:",
        value=default_text,
        height=300,
        placeholder="int main() {\n    int x = 10;\n    return 0;\n}",
    )
else:
    uploaded_file = st.file_uploader("Upload a .c source file", type=["c", "h", "txt"])
    if uploaded_file is not None:
        source_code = uploaded_file.read().decode("utf-8", errors="replace")
        st.text_area("File contents (preview):", value=source_code, height=250, disabled=True)

analyze_clicked = st.button(" Analyze Source Code", type="primary", use_container_width=False)

st.markdown("---")


# Analysis and results display
if analyze_clicked:
    if not source_code or not source_code.strip():
        st.warning("Please enter or upload some C source code to analyze.")
    else:
        tokens, errors, symtab, lex = analyze_source(source_code)
        summary = lex.summary()

        st.subheader("2. Analysis Results")

        #  Top metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Tokens", len(tokens))
        m2.metric("Unique Identifiers", len(symtab))
        m3.metric("Lexical Errors", len(errors))
        m4.metric(
            "Status",
            " Clean" if len(errors) == 0 else "⚠️ Errors Found",
        )

        tab_tokens, tab_symtab, tab_errors, tab_stats = st.tabs(
            [" Token Stream", "Symbol Table", " Lexical Errors", " Statistics"]
        )

        #  Token stream tab 
        with tab_tokens:
            st.markdown("Step-by-step recognized tokens, in source order:")
            if tokens:
                df_tokens = pd.DataFrame(
                    [
                        {
                            "Index": i + 1,
                            "Lexeme": t.lexeme if t.type != "COMMENT" else (
                                t.lexeme if len(t.lexeme) <= 40 else t.lexeme[:40] + " ..."
                            ),
                            "Token Type": t.type,
                            "Line": t.line,
                            "Column": t.column,
                        }
                        for i, t in enumerate(tokens)
                    ]
                )

                def highlight_errors(row):
                    if row["Token Type"] == "ERROR":
                        return ["background-color: #ffe1e1"] * len(row)
                    return [""] * len(row)

                st.dataframe(
                    df_tokens.style.apply(highlight_errors, axis=1),
                    use_container_width=True,
                    height=420,
                )

                csv_tokens = df_tokens.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download Token Stream (CSV)",
                    csv_tokens,
                    file_name="token_stream.csv",
                    mime="text/csv",
                )
            else:
                st.info("No tokens generated.")

        # Symbol table tab 
        with tab_symtab:
            st.markdown("Identifiers encountered, their inferred type (if declared with a "
                        "basic type keyword), first line of appearance, and occurrence count:")
            if symtab:
                df_sym = pd.DataFrame(
                    [
                        {
                            "Name": entry.name,
                            "Category": entry.category,
                            "Inferred Type": entry.data_type or "—",
                            "First Line": entry.first_line,
                            "Occurrences": entry.occurrences,
                        }
                        for entry in symtab.values()
                    ]
                )
                st.dataframe(df_sym, use_container_width=True, height=350)

                csv_sym = df_sym.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download Symbol Table (CSV)",
                    csv_sym,
                    file_name="symbol_table.csv",
                    mime="text/csv",
                )
            else:
                st.info("No symbols (identifiers) found.")

        #  Errors tab 
        with tab_errors:
            if errors:
                st.error(f"{len(errors)} lexical error(s) detected:")
                df_err = pd.DataFrame(
                    [
                        {
                            "Line": e.line,
                            "Column": e.column,
                            "Offending Text": e.lexeme if len(e.lexeme) <= 50 else e.lexeme[:50] + " ...",
                            "Message": e.message,
                        }
                        for e in errors
                    ]
                )
                st.dataframe(df_err, use_container_width=True, height=300)
                for e in errors:
                    st.markdown(f"- **Line {e.line}, Col {e.column}:** {e.message} → `{e.lexeme[:30]}`")
            else:
                st.success("No lexical errors detected. The source is lexically well formed.")

        #  Stats tab
        with tab_stats:
            st.markdown("Distribution of token types:")
            stat_rows = [{"Token Type": k, "Count": v} for k, v in summary.items() if v > 0]
            df_stats = pd.DataFrame(stat_rows).sort_values("Count", ascending=False)
            c1, c2 = st.columns([1, 1])
            with c1:
                st.dataframe(df_stats, use_container_width=True, hide_index=True)
            with c2:
                st.bar_chart(df_stats.set_index("Token Type"))

else:
    st.info("Enter or upload C source code above, then click **Analyze Source Code**.")
