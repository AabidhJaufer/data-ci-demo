import pandas as pd
from spellchecker import SpellChecker
import sys
import os

def clean_data(file_path):
    df = pd.read_csv(file_path)
    spell = SpellChecker()
    
    flagged_issues = []
    
    # 1. Automatic Cleaning: Strip whitespace & standardize casing
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].astype(str).str.strip()
    
    # 2. Automatic Correction & Flagging (Example on a 'Category' column)
    valid_categories = {'Electronics', 'Clothing', 'Home', 'Books'}
    if 'Category' in df.columns:
        for idx, val in enumerate(df['Category']):
            # Auto-correct case
            if val.title() in valid_categories:
                df.at[idx, 'Category'] = val.title()
            elif val not in valid_categories:
                # Spellcheck suggestion
                candidates = spell.candidates(val)
                suggestion = list(candidates)[0] if candidates else "Unknown"
                flagged_issues.append(
                    f"Row {idx + 2}: Unrecognized category '{val}'. Did you mean '{suggestion}'?"
                )

    # 3. Validation Check: Flag missing critical values (e.g., Price or ID)
    for col in df.columns:
        null_rows = df[df[col].isnull()].index.tolist()
        if null_rows:
            rows_str = ", ".join([str(r + 2) for r in null_rows])
            flagged_issues.append(f"Column '{col}' has missing values in row(s): {rows_str}")

    # Save cleaned output
    cleaned_path = file_path.replace('.csv', '_cleaned.csv')
    df.to_csv(cleaned_path, index=False)
    
    # Write summary for GitHub Actions output
    with open("validation_summary.md", "w") as f:
        f.write("## 🔍 Data Validation & Auto-Correction Report\n\n")
        f.write(f"**Processed File:** `{os.path.basename(file_path)}`\n\n")
        
        if flagged_issues:
            f.write("### Flagged Issues Requiring Review\n")
            for issue in flagged_issues:
                f.write(f"- {issue}\n")
            f.write("\n*Note: Cleaned file generated with automatic fixes where possible.*")
        else:
            f.write("**All checks passed!** No formatting or data issues detected.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        clean_data(sys.argv[1])
    else:
        print("Please provide a file path.")
