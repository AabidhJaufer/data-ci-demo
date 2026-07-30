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
    
    # 1. Strip whitespace across all cells
    for col in df.columns:
        df[col] = df[col].fillna('').astype(str).str.strip()

    # 2. Capitalize the first letter of every word across all text columns
    # (Excludes purely numeric columns like ID or Price)
    text_cols = [col for col in df.columns if col.lower() not in ['id', 'price']]
    
    for col in text_cols:
        for idx, val in enumerate(df[col]):
            if val:
                # title() capitalizes the first letter of every word
                capitalized_val = val.title()
                if capitalized_val != val:
                    df.at[idx, col] = capitalized_val

    # 3. Context-Aware Correction for Category/Type columns
    category_cols = [col for col in df.columns if col.lower() in ['category', 'type', 'status', 'department']]
    
    for col in category_cols:
        # Build trusted pool of existing values in this column
        all_values = df[col].tolist()
        unique_existing = list(set([v.title() for v in all_values if len(v) > 2]))

        for idx, val in enumerate(df[col]):
            if not val:
                continue

            val_title = val.title()

            # Check A: Exact match in context pool
            if val_title in unique_existing:
                df.at[idx, col] = val_title
                continue

            # Check B: Fuzzy match against column context (cutoff=0.5 catches missing letters like 'cloting')
            column_matches = difflib.get_close_matches(val_title, unique_existing, n=1, cutoff=0.5)

            if column_matches:
                best_match = column_matches[0]
                df.at[idx, col] = best_match
                flagged_issues.append(
                    f"Row {idx + 2}: Auto-corrected '{val}' to match existing column context '{best_match}'"
                )
            else:
                # Check C: Flag unverified dictionary suggestion without auto-applying
                dict_suggestion = spell.correction(val)
                if dict_suggestion and dict_suggestion.lower() != val.lower():
                    flagged_issues.append(
                        f"Row {idx + 2}: Unrecognized entry '{val}' in column '{col}'. Recommended suggestion: '{dict_suggestion.title()}' (Unverified - left unchanged)."
                    )
                else:
                    flagged_issues.append(
                        f"Row {idx + 2}: Unrecognized entry '{val}' in column '{col}'. Manual review required."
                    )

    # 4. Format Price column to standard 2 decimal places
    if 'Price' in df.columns:
        for idx, val in enumerate(df['Price']):
            if val:
                try:
                    formatted_price = f"{float(val):.2f}"
                    df.at[idx, 'Price'] = formatted_price
                except ValueError:
                    flagged_issues.append(f"Row {idx + 2}: Invalid price value '{val}'")

    # 5. Check for missing required values
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
