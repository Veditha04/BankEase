# scripts/set_features.py
import argparse, json, pathlib, sys

def main():
    ap = argparse.ArgumentParser(description="Set 'features' in metadata.json for model versions.")
    ap.add_argument("--root", default="backend/models", help="models root directory")
    ap.add_argument("--families", nargs="*", default=["lr","rf","xgb"], help="families to update")
    ap.add_argument("--version", default="current", help="'current' or a concrete version like vYYYYMMDD_HHMMSS")
    ap.add_argument("--features", nargs="+", required=True, help="feature order to write, e.g. user_id amount location hour dayofweek")
    ap.add_argument("--dry-run", action="store_true", help="print changes without writing")
    args = ap.parse_args()

    root = pathlib.Path(args.root)
    changed = 0

    for fam in args.families:
        ptr = root / fam / "current.txt"
        ver = args.version
        if ver == "current":
            if not ptr.exists():
                print(f"[skip] {fam}: no current.txt", file=sys.stderr); continue
            ver = ptr.read_text().strip()
        meta_path = root / fam / ver / "metadata.json"
        if not meta_path.exists():
            print(f"[skip] {fam}: {meta_path} missing", file=sys.stderr); continue

        meta = json.loads(meta_path.read_text())
        old = meta.get("features")
        meta["features"] = args.features
        print(f"[ok] {fam}@{ver}: {old} -> {args.features}")
        if not args.dry_run:
            meta_path.write_text(json.dumps(meta, indent=2))
            changed += 1

    print(f"Done. Updated {changed} file(s).")

if __name__ == "__main__":
    main()
