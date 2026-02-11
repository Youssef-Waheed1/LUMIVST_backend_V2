"""
Fast Batch XBRL Extraction using copy_expert + failed files tracking
"""
import os, sys, pandas as pd, argparse, time, io
from sqlalchemy import create_engine
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

def clean_key(text):
    if not isinstance(text, str): return f"unknown_{text}"
    text = text.split('[')[0].split('|')[0]
    clean = "".join(c if c.isalnum() else "_" for c in text)
    clean = clean.lower().strip("_")
    while "__" in clean: clean = clean.replace("__", "_")
    return clean[:100]

def parse_excel_file(file_path):
    """Parse Excel with multiple fallback methods"""
    df = None
    fname = os.path.basename(file_path)
    
    # Try openpyxl (modern XLSX)
    try:
        df = pd.read_excel(file_path, header=None, engine='openpyxl').fillna('')
    except:
        pass
    
    # Try xlrd (legacy XLS)
    if df is None:
        try:
            df = pd.read_excel(file_path, header=None, engine='xlrd').fillna('')
        except:
            pass
    
    # Try HTML
    if df is None:
        try:
            dfs = pd.read_html(file_path)
            if dfs:
                df = dfs[0].fillna('')
        except:
            pass
    
    # Try CSV formats
    if df is None:
        for enc in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
            try:
                df = pd.read_csv(file_path, header=None, sep='\t', encoding=enc).fillna('')
                break
            except:
                pass
    
    if df is None:
        return []
    
    try:
        data = []
        for _, row in df.iterrows():
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
    except:
        return []

def extract_symbol_data(symbol, base_dir):
    """Extract with failure tracking"""
    symbol_dir = os.path.join(base_dir, str(symbol))
    if not os.path.exists(symbol_dir): return [], None
    
    files = [f for f in os.listdir(symbol_dir) if 'XBRL' in f and (f.endswith('.xls') or f.endswith('.xlsx'))]
    metrics = []
    failed = []
    
    for filename in files:
        try:
            parts = os.path.splitext(filename)[0].split('_')
            year = int(parts[0])
            period = parts[-1]
            
            parsed = parse_excel_file(os.path.join(symbol_dir, filename))
            if parsed:
                for m in parsed:
                    metrics.append((str(symbol), year, period, m["key"], m["value"], m["text"], m["label"], filename))
            else:
                failed.append(f"{symbol}: {filename}")
        except Exception as e:
            failed.append(f"{symbol}: {filename}")
    
    return metrics, failed

def clean_text_for_db(text):
    if not isinstance(text, str): return text
    text = text.replace('\0', '').replace('\r', '').replace('\x00', '')
    try:
        return text.encode('utf-8', 'replace').decode('utf-8')
    except:
        return ""

def save_to_db_fast(all_records):
    """Save using copy_expert (faster)"""
    if not all_records:
        print("⚠️ No records to save.")
        return 0
    
    print("🧹 Deduplicating...")
    unique_map = {}
    for rec in all_records:
        unique_map[(rec[0], rec[1], rec[2], rec[3])] = rec
    
    dedup = list(unique_map.values())
    print(f"   Removed {len(all_records) - len(dedup):,} duplicates.")
    print(f"💾 Saving {len(dedup):,} records...")
    
    CHUNK_SIZE = 10000
    total_saved = 0
    conn = engine.raw_connection()
    
    try:
        for i in range(0, len(dedup), CHUNK_SIZE):
            chunk = dedup[i : i + CHUNK_SIZE]
            chunk_num = (i // CHUNK_SIZE) + 1
            total_chunks = ((len(dedup) - 1) // CHUNK_SIZE) + 1
            
            if chunk_num % 10 == 0 or chunk_num == 1:
                print(f"   Chunk {chunk_num}/{total_chunks}")
            
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TEMP TABLE tmp_metrics (
                    company_symbol TEXT,
                    year INT,
                    period TEXT,
                    metric_name TEXT,
                    metric_value DOUBLE PRECISION,
                    metric_text TEXT,
                    label_en TEXT,
                    source_file TEXT
                );
            """)
            
            csv_buf = io.StringIO()
            for row in chunk:
                parts = []
                for idx, item in enumerate(row):
                    if idx == 4:  # metric_value
                        if item is None or str(item).strip() == '':
                            parts.append('')
                        else:
                            try:
                                parts.append(str(float(item)))
                            except:
                                parts.append('')
                    else:  # text
                        if item is None or str(item).strip() == '':
                            parts.append('')
                        else:
                            val = str(item).strip()
                            val = clean_text_for_db(val)
                            val = val.replace('\\', '\\\\').replace('"', '""')
                            if any(c in val for c in [',', '"', '\n']):
                                val = f'"{val}"'
                            parts.append(val)
                csv_buf.write(','.join(parts) + '\n')
            
            csv_buf.seek(0)
            
            copy_sql = "COPY tmp_metrics FROM STDIN WITH (FORMAT CSV, DELIMITER ',', NULL '')"
            try:
                cursor.copy_expert(copy_sql, csv_buf)
            except Exception as e:
                print(f"   ❌ COPY Error: {str(e)[:100]}")
                conn.rollback()
                cursor.close()
                continue
            
            cursor.execute("""
                INSERT INTO company_financial_metrics 
                (company_symbol, year, period, metric_name, metric_value, metric_text, label_en, source_file)
                SELECT * FROM tmp_metrics
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
        
        print(f"✅ Saved {total_saved:,} records.")
        return total_saved
        
    except Exception as e:
        print(f"❌ Error: {e}")
        try: conn.rollback()
        except: pass
        return total_saved
    finally:
        try: conn.close()
        except: pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--symbols', nargs='+')
    args = parser.parse_args()
    
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "downloads")
    
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
    print(f"🚀 BATCH XBRL EXTRACTION (FAST)")
    print(f"📊 Symbols: {len(all_symbols)}")
    print(f"⚡ Workers: {args.workers}")
    print(f"{'='*60}")
    
    start = time.time()
    all_data = []
    failed_symbols = []
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(extract_symbol_data, sym, base_dir): sym for sym in all_symbols}
        done = 0
        for future in as_completed(futures):
            res, failed = future.result()
            if res:
                all_data.extend(res)
            if failed:
                failed_symbols.extend(failed)
            done += 1
            if done % 20 == 0:
                print(f"   Progress: {done}/{len(all_symbols)}")
    
    print(f"\n✅ Extracted: {len(all_data):,} metrics")
    
    if failed_symbols:
        print(f"\n⚠️  Failed to read {len(failed_symbols)} files:")
        for f in failed_symbols[:10]:
            print(f"   - {f}")
        if len(failed_symbols) > 10:
            print(f"   ... and {len(failed_symbols) - 10} more")
    
    save_to_db_fast(all_data)
    
    print(f"\n⏱️  Total: {time.time() - start:.1f}s")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
