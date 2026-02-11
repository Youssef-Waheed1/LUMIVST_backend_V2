"""Quick diagnostic: find which XBRL files fail to parse and why."""
import os, sys, pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "downloads")

failed_files = []
total_xbrl = 0

for symbol in sorted(os.listdir(base)):
    sdir = os.path.join(base, symbol)
    if not os.path.isdir(sdir):
        continue
    for f in sorted(os.listdir(sdir)):
        if 'XBRL' not in f or not (f.endswith('.xls') or f.endswith('.xlsx')):
            continue
        total_xbrl += 1
        fpath = os.path.join(sdir, f)
        size = os.path.getsize(fpath)
        
        # Try reading
        ok = False
        err_msg = ""
        for eng in ['xlrd', None, 'openpyxl']:
            try:
                kwargs = {"header": None}
                if eng:
                    kwargs["engine"] = eng
                df = pd.read_excel(fpath, **kwargs)
                ok = True
                break
            except Exception as e:
                err_msg = str(e)
        
        if not ok:
            failed_files.append((symbol, f, size, err_msg))

print(f"Total XBRL files scanned: {total_xbrl}")
print(f"Failed files: {len(failed_files)}")
print()
for sym, fname, size, err in failed_files:
    print(f"  {sym}/{fname} ({size:,} bytes) -> {err[:80]}")
