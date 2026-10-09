import os
import hashlib
import json

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    pipeline_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(pipeline_dir, ".."))
    
    manifest = {}
    checksum_lines = []
    
    # Target files to include in manifest
    target_dirs = [
        os.path.join(project_root, "ml_pipeline"),
        os.path.join(project_root, "backend", "app", "ml"),
    ]
    
    extensions = {".py", ".db", ".pkl", ".json", ".csv", ".tex", ".pdf"}
    
    for tdir in target_dirs:
        if not os.path.exists(tdir):
            continue
        for root, dirs, files in os.walk(tdir):
            # Skip cache dirs
            dirs[:] = [d for d in dirs if d not in {"__pycache__", ".pytest_cache", "mlruns"}]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in extensions or fname in {"requirements.txt", "Dockerfile"}:
                    full_path = os.path.join(root, fname)
                    rel_path = os.path.relpath(full_path, project_root).replace("\\", "/")
                    file_hash = compute_sha256(full_path)
                    file_size = os.path.getsize(full_path)
                    
                    manifest[rel_path] = {
                        "sha256": file_hash,
                        "size_bytes": file_size
                    }
                    checksum_lines.append(f"{file_hash}  {rel_path}")
    
    # Sort checksum lines
    checksum_lines.sort()
    
    # Save checksums.sha256
    checksums_path = os.path.join(pipeline_dir, "checksums.sha256")
    with open(checksums_path, "w", encoding="utf-8") as f:
        f.write("\n".join(checksum_lines) + "\n")
    print(f"Wrote SHA-256 checksums to {checksums_path} ({len(checksum_lines)} files)")
    
    # Save manifest.json
    manifest_path = os.path.join(pipeline_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote manifest JSON to {manifest_path}")

if __name__ == "__main__":
    main()
