import pandas as pd
from spellchecker import SpellChecker
import difflib
import sys
import os


def smart_title(text):
    """Title-case a string without butchering apostrophes/contractions.
    str.title() turns "don't" into "Don'T" -- this avoids that."""
    return ' '.join(
        word[0].upper() + word[1:] if word else word
        for word in text.split(' ')
    ).replace("'S", "'s").replace("'T", "'t").replace("'D", "'d").replace("'Ll", "'ll").replace("'Re", "'re").replace("'Ve", "'ve")


def clean_data(file_path):
    df = pd.read_csv(file_path, dtype=str)
    spell = SpellChecker()

    flagged_issues = []

    # 1. Strip whitespace across all cells
    for col in df.columns:
        df[col] = df[col].fillna('').astype(str).str.strip()

    # 2. Capitalize the first letter of every word across all text columns
    text_cols = [col for col in df.columns if col.lower() not in ['id', 'price']]

    for col in text_cols:
        for idx, val in enumerate(df[col]):
            if val:
                capitalized_val = smart_title(val)
                if capitalized_val != val:
                    df.at[idx, col] = capitalized_val

    # 3. Context-aware correction for Category/Type columns
    category_cols = [col for col in df.columns if col.lower() in ['category', 'type', 'status', 'department']]

    for col in category_cols:
        all_values = [v for v in df[col].tolist() if len(v) > 2]

        # KEY FIX: only values that appear MORE THAN ONCE count as "trusted".
        # A value that only shows up a single time (e.g. a one-off typo) is
        # never allowed to validate itself.
        value_counts = pd.Series(all_values).value_counts()
        trusted_pool = list(value_counts[value_counts > 1].index)

        for idx, val in enumerate(df[col]):
            if not val:
                continue

            val_title = val  # already smart_title'd in step 2

            # Check A: exact match against the TRUSTED pool only (not itself)
            if val_title in trusted_pool:
                continue  # already a recognized, frequently-used value

            # Check B: fuzzy match against trusted pool only
            column_matches = difflib.get_close_matches(val_title, trusted_pool, n=1, cutoff=0.5)

            if column_matches:
                best_match = column_matches[0]
                df.at[idx, col] = best_match
                flagged_issues.append(
                    f"Row {idx + 2}: Auto-corrected '{val}' to match existing column context '{best_match}'"
                )
            else:
                # Check C: dictionary suggestion, word-by-word (spellchecker
                # only handles single words, not "Home Goods" as one string)
                words = val_title.split(' ')
                corrected_words = []
                any_diff = False
                for w in words:
                    suggestion = spell.correction(w)
                    if suggestion and suggestion.lower() != w.lower():
                        any_diff = True
                        corrected_words.append(suggestion.capitalize())
                    else:
                        corrected_words.append(w)
                dict_suggestion = ' '.join(corrected_words)

                if any_diff:
                    flagged_issues.append(
                        f"Row {idx + 2}: Unrecognized entry '{val}' in column '{col}'. "
                        f"Recommended suggestion: '{dict_suggestion}' (Unverified - left unchanged)."
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

    cleaned_path = file_path.replace('.csv', '_cleaned.csv')
    df.to_csv(cleaned_path, index=False)

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
