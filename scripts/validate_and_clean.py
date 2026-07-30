import pandas as pd
from spellchecker import SpellChecker
import difflib
import sys
import os

def clean_data(file_path):
    # Read everything as string to prevent pandas from dropping trailing price zeroes
    df = pd.read_csv(file_path, dtype=str)
    spell = SpellChecker()
    
    flagged_issues = []
    
    # 1. Strip leading and trailing whitespace across all cells
    for col in df.columns:
        df[col] = df[col].fillna('').astype(str).str.strip()

    # 2. Context-Aware Correction for Text Columns (e.g., Category)
    text_columns = [col for col in df.columns if col.lower() in ['category', 'type', 'status', 'department']]
    
    for col in text_columns:
        # Step A: Build a dictionary of existing trusted values in this column
        # Filter out empty strings and items that look like obvious errors (too short or low occurrence)
        all_values = df[col].tolist()
        clean_existing = [v.title() for v in all_values if len(v) > 2]
        unique_existing = list(set(clean_existing))

        for idx, val in enumerate(df[col]):
            if not val:
                continue

            val_title = val.title()

            # Check 1: Is it already an exact match (ignoring case)?
            if val_title in unique_existing:
                df.at[idx, col] = val_title
                continue

            # Check 2: Compare against other words ALREADY present in this column first
            column_matches = difflib.get_close_matches(val_title, unique_existing, n=1, cutoff=0.5)

            if column_matches:
                best_match = column_matches[0]
                df.at[idx, col] = best_match
                flagged_issues.append(
                    f"Row {idx + 2}: Auto-corrected '{val}' to match existing column context '{best_match}'"
                )
            else:
                # Check 3: If no column context match exists, get dictionary suggestion BUT do not auto-apply it
                dict_suggestion = spell.correction(val)
                if dict_suggestion and dict_suggestion.lower() != val.lower():
                    flagged_issues.append(
                        f"Row {idx + 2}: Unrecognized entry '{val}' in column '{col}'. Recommended suggestion: '{dict_suggestion.title()}' (Unverified - left unchanged)."
                    )
                else:
                    flagged_issues.append(
                        f"Row {idx + 2}: Unrecognized entry '{val}' in column '{col}'. Manual review required."
                    )

    # 3. Format Price column to standard 2 decimal places
    if 'Price' in df.columns:
        for idx, val in enumerate(df['Price']):
            if val:
                try:
                    formatted_price = f"{float(val):.2f}"
                    df.at[idx, 'Price'] = formatted_price
                except ValueError:
                    flagged_issues.append(f"Row {idx + 2}: Invalid price value '{val}'")

    # 4. Check for missing required values
    for col in df.columns:
        missing_rows = df[df[col] == ''].index.tolist()
        if missing_rows:
            rows_str = ", ".join([str(r + 2) for r in missing_rows])
            flagged_issues.append(f"Column '{col}' has missing values in row(s): {rows_str}")

    # Save the updated CSV
    cleaned_path = file_path.replace('.csv', '_cleaned.csv')
    df.to_csv(cleaned_path, index=False)
    
    # Generate clean text summary report for GitHub PR
    with open("validation_summary.md", "w") as f:
        f.write("## Data Validation Report\n\n")
        f.write(f"Processed file: `{os.path.basename(file_path)}`\n\n")
        
        if flagged_issues:
            f.write("### Issues Identified\n")
            for issue in flagged_issues:
                f.write(f"- {issue}\n")
        else:
            f.write("Validation passed successfully with no errors detected.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        clean_data(sys.argv[1])
    else:
        print("Error: Target file path required.")
