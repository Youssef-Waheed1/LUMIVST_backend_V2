#!/usr/bin/env python3
"""
Collect parameters from Excel files for many companies and write them sequentially
into a single Excel file for comparison.

Usage:
    python collect_company_parameters.py --input-dir /path/to/excels --output-file params_summary.xlsx

Behavior:
 - If `--input-dir` contains subdirectories, each subdirectory is treated as one company
   and the script picks the first Excel file found inside it.
 - Otherwise, all Excel files in `--input-dir` are processed; company name is the file stem.
 - For each Excel file, the script scans each sheet and extracts parameter/value pairs:
     * If a sheet has exactly 2 columns, treat them as (parameter, value).
     * Otherwise, use column headers as parameter names and take the first non-empty cell
       in that column as the value.
 - The output Excel contains sequential blocks: a header row with the company name,
   then parameter rows, then a blank separator row, repeated for each company.
"""

import argparse
import os
from pathlib import Path
from typing import List, Tuple
import pandas as pd


def find_excel_in_dir(dirpath: Path) -> List[Path]:
    exts = {'.xls', '.xlsx', '.xlsm'}
    files = [p for p in sorted(dirpath.iterdir()) if p.suffix.lower() in exts and p.is_file()]
    return files


def extract_params_from_file(path: Path) -> List[Tuple[str, str, str]]:
    """Return list of tuples (sheet, parameter, value)"""
    results = []
    try:
        xls = pd.ExcelFile(path)
    except Exception as e:
        print(f"Failed to open {path}: {e}")
        return results

    for sheet in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet, header=0)
        except Exception:
            # fallback: read without header
            try:
                df = pd.read_excel(xls, sheet_name=sheet, header=None)
            except Exception:
                continue

        if df.shape[1] == 2:
            # treat as key-value
            left = df.columns[0]
            right = df.columns[1]
            for idx, row in df.iterrows():
                k = row.iloc[0]
                v = row.iloc[1]
                if pd.isna(k) and pd.isna(v):
                    continue
                results.append((sheet, str(k) if not pd.isna(k) else '', str(v) if not pd.isna(v) else ''))
        else:
            # use headers as parameter names and take first non-null value in the column
            for col in df.columns:
                col_series = df[col].dropna()
                val = col_series.iloc[0] if not col_series.empty else ''
                results.append((sheet, str(col), str(val) if val != '' else ''))

    return results


def collect(input_dir: Path) -> List[List[str]]:
    rows: List[List[str]] = []
    entries = sorted([p for p in input_dir.iterdir()])

    # decide if there are subdirectories that look like company folders
    subdirs = [p for p in entries if p.is_dir()]
    if subdirs:
        targets = []
        for d in subdirs:
            files = find_excel_in_dir(d)
            if files:
                targets.append((d.name, files[0]))
    else:
        # take files in input_dir
        exts = {'.xls', '.xlsx', '.xlsm'}
        targets = [(p.stem, p) for p in entries if p.is_file() and p.suffix.lower() in exts]

    if not targets:
        print("No Excel files found in input directory.")
        return rows

    for company, filepath in targets:
        print(f"Processing {company} -> {filepath}")
        rows.append([f"Company: {company}", '', ''])
        params = extract_params_from_file(filepath)
        if not params:
            rows.append(['', 'No parameters extracted', ''])
        else:
            for sheet, key, val in params:
                rows.append(['', key, val])
        rows.append(['', '', ''])

    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', '-i', required=True, help='Directory containing company Excel files or company subfolders')
    parser.add_argument('--output-file', '-o', default='collected_parameters.xlsx', help='Output Excel file')
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print('Input directory does not exist:', input_dir)
        return

    rows = collect(input_dir)
    if not rows:
        print('No rows collected, exiting.')
        return

    df = pd.DataFrame(rows, columns=['Company', 'Parameter', 'Value'])
    out_path = Path(args.output_file)
    try:
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='parameters')
        print(f'Wrote {len(rows)} rows to {out_path}')
    except Exception as e:
        print(f'Failed to write output file: {e}')


if __name__ == '__main__':
    main()
