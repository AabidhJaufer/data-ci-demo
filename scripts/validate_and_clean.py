import pandas as pd
from spellchecker import SpellChecker
import difflib
import sys
import os

def clean_data(file_path):
    df = pd.read_csv(file_path, dtype=str)
    spell = SpellChecker()
    flagged_issues = []

    # 1. Strip whitespace and apply title casing to all text columns
    text_cols = [col for col in df.columns if col.lower() not in ['id', 'price']]
    for col in text_cols:
        df[col] = df[col].fillna('').astype(str).str.strip().str.title()

    # 2. Context-First Correction
    for col in text_cols:
        # Build list of existing words in this column
        existing_context = list(set(df[col].tolist()))

        for idx, val in enumerate(df[col]):
            if not val:
                continue

            # Step A: Fuzzy match against existing words in the column first
            # (Excluding exact match to avoid matching a word to itself)
            other_words = [w for w in existing_context if w.lower() != val.lower()]
            matches = difflib.get_close_matches(val, other_words, n=1, cutoff=0.55)

            if matches:
                corrected = matches[0]
                df.at[idx, col] = corrected
                flagged_issues.append(f"Row {idx + 2}: Corrected '{val}' to existing context match '{corrected}'")
            
            # Step B: If no column match exists and the word is unknown, use dictionary
            elif spell.unknown([val]):
                dict_fix = spell.correction(val)
                if dict_fix:
                    corrected = dict_fix.title()
                    df.at[idx, col] = corrected
                    flagged_issues.append(f"Row {idx + 2}: Corrected typo '{val}' to '{corrected}'")

    # 3. Format Price column
    if 'Price' in df.columns:
        for idx, val in enumerate(df['Price']):
            if val:
                try:
                    df.at[idx, 'Price'] = f"{float(val):.2f}"
                except ValueError:
                    pass

    # Save cleaned file
    cleaned_path = file_path.replace('.csv', '_cleaned.csv')
    df.to_csv(cleaned_path, index=False)

    # Output report
    with open("validation_summary.md", "w") as f:
        f.write("## Data Validation Report\n\n")
        f.write(f"Processed file: `{os.path.basename(file_path)}`\n\n")
        if flagged_issues:
            f.write("### Corrections Made\n")
            for issue in flagged_issues:
                f.write(f"- {issue}\n")
        else:
            f.write("No errors found.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        clean_data(sys.argv[1])
