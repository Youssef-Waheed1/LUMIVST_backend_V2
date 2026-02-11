"""
Batch XBRL Extraction to PostgreSQL (Clean & Fast)
==================================================
1. Extracts data from XBRL Excel files using pandas (with robust fallback).
2. Separates clean numeric values from text values.
3. Uses PostgreSQL COPY protocol for ultra-fast bulk insertion (with proper NULL handling).
4. Handles duplicates and saves in small chunks to prevent buffer overflows.
"""

import os
import sys
import pandas as pd
import argparse
import time
import io
from sqlalchemy import create_engine
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from app.core.config import settings

# Database Connection
engine = create_engine(settings.DATABASE_URL)

def clean_key(text):
    """Generates a clean snake_case key from the label."""
    if not isinstance(text, str): return f"unknown_{text}"
    text = text.split('[')[0].split('|')[0]
    clean = "".join(c if c.isalnum() else "_" for c in text)
    clean = clean.lower().strip("_")
    while "__" in clean: clean = clean.replace("__", "_")
    return clean[:100]

def parse_excel_file(file_path):
    """
    Parses a single Excel file with robust fallback for older/damaged formats.
    Returns a list of dicts: {key, label, value (numeric), text (string)}
    """
    df = None
    fname = os.path.basename(file_path)
    
    # 1. Try standard read_excel (modern XLSX)
    try:
        df = pd.read_excel(file_path, header=None, engine='openpyxl').fillna('')
    except Exception as e:
        pass

    # 2. Try read_excel with xlrd (legacy XLS)
    if df is None:
        try:
            df = pd.read_excel(file_path, header=None, engine='xlrd').fillna('')
        except Exception as e:
            pass

    # 3. Try read_html (for HTML disguised as XLS)
    if df is None:
        try:
            dfs = pd.read_html(file_path)
            if dfs:
                df = dfs[0].fillna('')
        except Exception as e:
            pass

    # 4. Try as CSV with different encodings
    if df is None:
        for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
            try:
                df = pd.read_csv(file_path, header=None, sep='\t', encoding=encoding).fillna('')
                break
            except:
                pass

    # 5. Try as CSV with comma separator
    if df is None:
        for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
            try:
                df = pd.read_csv(file_path, header=None, sep=',', encoding=encoding).fillna('')
                break
            except:
                pass

    if df is None:
        print(f"    ❌ FAILED to read {fname} (All methods failed)")
        return []
        
    try:
        data = []
        for index, row in df.iterrows():
            label = str(row[0]).strip()
            raw_value = row[1] if len(row) > 1 else ''
            
            if not label or len(label) < 2: continue
            key = clean_key(label)
            if not key: continue

            val_num = None
            val_text = None
            
            if pd.notna(raw_value) and raw_value != '':
                try:
                    clean_str = str(raw_value).replace(',', '').strip()
                    if clean_str and clean_str.replace('.', '', 1).replace('-', '', 1).isdigit():
                        val_num = float(clean_str)
                    else:
                        val_text = str(raw_value).strip()
                except:
                    val_text = str(raw_value).strip()
            
            clean_label = label[:500].replace('\t', ' ').replace('\n', ' ')
            if val_text: val_text = val_text.replace('\t', ' ').replace('\n', ' ')

            data.append({
                "key": key,
                "label": clean_label,
                "value": val_num,
                "text": val_text
            })
            
        return data
    except Exception as e:
        print(f"    ❌ Error parsing rows in {fname}: {e}")
        return []

def extract_symbol_data(symbol, base_dir):
    symbol_dir = os.path.join(base_dir, str(symbol))
    if not os.path.exists(symbol_dir): return [], None
    
    files = [f for f in os.listdir(symbol_dir) if 'XBRL' in f and (f.endswith('.xls') or f.endswith('.xlsx'))]
    symbol_metrics = []
    failed_files = []
    
    for filename in files:
        try:
            parts = os.path.splitext(filename)[0].split('_')
            year = int(parts[0])
            period = parts[-1]
            
            metrics = parse_excel_file(os.path.join(symbol_dir, filename))
            if metrics:
                for m in metrics:
                    symbol_metrics.append((str(symbol), year, period, m["key"], m["value"], m["text"], m["label"], filename))
            else:
                failed_files.append(f"{symbol}: {filename}")
        except Exception as e: 
            failed_files.append(f"{symbol}: {filename} ({str(e)[:50]})")
            continue
    
    return symbol_metrics, failed_files

def clean_text_for_db(text):
    """Ensure text is valid UTF-8 and remove control characters."""
    if not isinstance(text, str): return text
    text = text.replace('\0', '').replace('\r', '').replace('\x00', '')
    try:
        return text.encode('utf-8', 'replace').decode('utf-8')
    except:
        return ""

def save_to_db_fast(all_records):
    """
    Saves metrics to DB using CHUNKED COPY to handle large datasets safely.
    Handles 'invalid input syntax for double precision' by ensuring numeric columns get \\N not "".
    """
    if not all_records:
        print("⚠️ No records to save.")
        return 0
    
    # 0. Deduplicate
    print("🧹 Deduplicating records before insert...")
    unique_map = {}
    duplicates_count = 0
    for rec in all_records:
        unique_map[(rec[0], rec[1], rec[2], rec[3])] = rec
        
    deduplicated_records = list(unique_map.values())
    total_records = len(deduplicated_records)
    print(f"   Removed {len(all_records) - total_records:,} duplicates.")
    print(f"💾 Saving {total_records:,} unique records to Database (in chunks)...")
    
    # 1. Config: SMALL CHUNK SIZE to prevent buffer overflow
    CHUNK_SIZE = 5000 
    total_saved = 0
    
    conn = engine.raw_connection()
    try:
        for i in range(0, total_records, CHUNK_SIZE):
            # Refresh cursor per chunk
            cursor = conn.cursor()
            chunk = deduplicated_records[i : i + CHUNK_SIZE]
            
            if (i // CHUNK_SIZE) % 5 == 0:
                print(f"   ↳ Processing chunk {i//CHUNK_SIZE + 1}/{(total_records//CHUNK_SIZE)+1} ({len(chunk):,} records)...")
            
            # Prepare CSV
            output = io.StringIO()
            for row in chunk:
                line_parts = []
                # row indices: 0=sym, 1=yr, 2=pd, 3=metric, 4=VAL, 5=txt, 6=lbl, 7=file
                for idx, item in enumerate(row):
                    # Special handling for metric_value column (index 4 - DOUBLE PRECISION)
                    if idx == 4:
                        # For numeric metric_value column
                        if item is None or (isinstance(item, str) and str(item).strip() == ''):
                            line_parts.append(r"\N")
                        else:
                            try:
                                # Try to parse as float to validate
                                float_val = float(item)
                                line_parts.append(str(float_val))
                            except (ValueError, TypeError):
                                # If can't parse as float, treat as NULL for this numeric column
                                line_parts.append(r"\N")
                    else:
                        # For text columns
                        if item is None:
                            line_parts.append(r"\N")
                        else:
                            val = str(item).strip()
                            if val == "":
                                line_parts.append(r"\N")
                            else:
                                val = clean_text_for_db(val)
                                val = val.replace('\t', ' ').replace('\n', ' ').replace('\\', '\\\\')
                                line_parts.append(val)
                            
                output.write("\t".join(line_parts) + "\n")
            output.seek(0)
            
            # TEMP TABLE
            cursor.execute("CREATE TEMP TABLE IF NOT EXISTS tmp_metrics (company_symbol TEXT, year INT, period TEXT, metric_name TEXT, metric_value DOUBLE PRECISION, metric_text TEXT, label_en TEXT, source_file TEXT) ON COMMIT DELETE ROWS;")
            
            # COPY
            try:
                cursor.copy_from(
                    output, 'tmp_metrics', null='\\N', 
                    columns=('company_symbol', 'year', 'period', 'metric_name', 'metric_value', 'metric_text', 'label_en', 'source_file')
                )
            except Exception as copy_err:
                print(f"   ❌ COPY Error in chunk {i//CHUNK_SIZE + 1}: {copy_err}")
                conn.rollback()
                continue

            # UPSERT
            cursor.execute("""
                INSERT INTO company_financial_metrics 
                (company_symbol, year, period, metric_name, metric_value, metric_text, label_en, source_file)
                SELECT company_symbol, year, period, metric_name, metric_value, metric_text, label_en, source_file 
                FROM tmp_metrics
                ON CONFLICT (company_symbol, year, period, metric_name) 
                DO UPDATE SET
                    metric_value = EXCLUDED.metric_value,
                    metric_text = EXCLUDED.metric_text,
                    label_en = EXCLUDED.label_en,
                    source_file = EXCLUDED.source_file;
            """)
            
            conn.commit()
            cursor.close()
            total_saved += len(chunk)
            time.sleep(0.05) # Yield
            
        print(f"✅ Successfully saved {total_saved:,} records.")
        return total_saved
        
    except Exception as e:
        print(f"❌ Database Error: {e}")
        try: conn.rollback()
        except: pass
        return total_saved
    finally:
        try: conn.close()
        except: pass

def main():
    parser = argparse.ArgumentParser(description="Clean Batch XBRL Extraction")
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--symbols', nargs='+', help="Specific symbols (e.g. 1010)")
    args = parser.parse_args()

    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "downloads")
    
    # Get all subdirectories
    if os.path.exists(base_dir):
        all_symbols = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))])
    else:
        print(f"❌ Directory not found: {base_dir}")
        return

    if args.symbols:
        all_symbols = [s for s in all_symbols if s in args.symbols]

    if not all_symbols:
        print("❌ No symbols found.")
        return
    
    print(f"{'='*60}")
    print(f"🚀 STARTING BATCH EXTRACTION")
    print(f"📊 Symbols: {len(all_symbols)}")
    print(f"⚡ Workers: {args.workers}")
    print(f"{'='*60}")
    
    start_time = time.time()
    all_data = []
    failed_symbols = []
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(extract_symbol_data, sym, base_dir): sym for sym in all_symbols}
        completed = 0
        for future in as_completed(futures):
            res, failed = future.result()
            if res:
                all_data.extend(res)
            if failed:
                failed_symbols.extend(failed)
            completed += 1
            if completed % 20 == 0:
                print(f"   Progress: {completed}/{len(all_symbols)} processed...")

    print(f"\n✅ Extraction: {len(all_data):,} metrics found.")
    
    if failed_symbols:
        print(f"\n⚠️  Failed to read {len(failed_symbols)} files:")
        for f in failed_symbols[:20]:  # Show first 20
            print(f"   - {f}")
        if len(failed_symbols) > 20:
            print(f"   ... and {len(failed_symbols) - 20} more")
    
    save_to_db_fast(all_data)
    
    print(f"\n🏁 Finished in {time.time() - start_time:.1f}s")

if __name__ == "__main__":
    main()