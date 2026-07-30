import pandas as pd
from spellchecker import SpellChecker
import sys
import os

def clean_data(file_path):
    # Read everything as strings so pandas doesn't truncate floats (e.g. 120.00 -> 120.0)
    df = pd.read_csv(file_path, dtype=str)
    spell = SpellChecker()
    
    flagged_issues = []
    
    # 1. Trim whitespace across all string values
    for col in df.columns:
        df[col] = df[col].fillna('').astype(str).str.strip()

    # 2. Fix Categories (Auto-correct typos AND write changes back to the DataFrame)
    if 'Category' in df.columns:
        for idx, val in enumerate(df['Category']):
            if not val:
                continue
            
            # Step A: Standardize casing
            title_val = val.title()
            
            # Step B: Get best spellcheck suggestion
            corrected = spell.correction(val)
            
            # Pick the corrected word if available, otherwise fall back to title casing
            final_val = corrected.title() if corrected else title_val
            
            # ACTUALLY overwrite the cell in the dataframe
            df.at[idx, 'Category'] = final_val
            
            # Flag if an actual edit was made
            if final_val != val:
                flagged_issues.append(
                    f"Row {idx + 2}: Corrected category typo '{val}' -> '{final_val}'"
                )

    # 3. Preserve 2-decimal place formatting for Price
    if 'Price' in df.columns:
        for idx, val in enumerate(df['Price']):
            if val:
                try:
                    formatted_price = f"{float(val):.2f}"
                    df.at[idx, 'Price'] = formatted_price
                except ValueError:
                    flagged_issues.append(f"Row {idx + 2}: Invalid price value '{val}'")

    # 4. Check for missing values in required fields
    for col in df.columns:
        missing_rows = df[df[col] == ''].index.tolist()
        if missing_rows:
            rows_str = ", ".join([str(r + 2) for r in missing_rows])
            flagged_issues.append(f"Column '{col}' has missing values in row(s): {rows_str}")

    # Save cleaned CSV file
    cleaned_path = file_path.replace('.csv', '_cleaned.csv')
    df.to_csv(cleaned_path, index=False)
    
    # Generate GitHub PR Markdown report
    with open("validation_summary.md", "w") as f:
        f.write("## 🔍 Data Validation & Auto-Correction Report\n\n")
        f.write(f"**Processed File:** `{os.path.basename(file_path)}`\n\n")
        
        if flagged_issues:
            f.write("###  Actions Taken & Flagged Issues\n")
            for issue in flagged_issues:
                f.write(f"- {issue}\n")
        else:
            f.write(" **All checks passed with no issues!**")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        clean_data(sys.argv[1])
    else:
        print("Please provide a target CSV file path.")
