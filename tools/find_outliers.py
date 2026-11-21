"""
Find Outliers & Noisy Data in Leaf Datasets (PlantVillage)
==========================================================
Identifies non-leaf artifacts, misclassified fruits (e.g. bell peppers, tomatoes),
corrupted images, and visual anomalies across crop disease image datasets.

Features:
- Dual-Signal Anomaly Detection:
  1. Per-Class Embedding Distance: Compares ResNet18 visual embeddings to class centroids.
  2. Semantic Fruit & Object Filter: Uses ImageNet classification to detect non-leaf objects
     (e.g., bell peppers, strawberries, citrus fruits, screenshots).
  3. Per-Class Isolation Forest: Flags isolated density anomalies within each class.
- Safe Dataset Traversal: Automatically detects and ignores nested duplicate folders (e.g., PlantVillage/PlantVillage).
- Visual Review Outputs:
  - outlier_paths.txt: Plain list of outlier image paths.
  - outlier_report.csv: Detailed breakdown of anomaly scores and reasons.
  - outliers_gallery.html: HTML visual gallery to review suspicious images in a browser.
  - Optional quarantine mode: Copies/moves suspicious files to an isolation folder.
"""

import os
import sys
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.models as models
from torchvision import transforms
from sklearn.ensemble import IsolationForest

# Specific ImageNet classes corresponding strictly to fruits, food, or non-plant objects
# (excluding green leafy vegetables like cabbage/broccoli which visually resemble foliage)
NON_LEAF_FOOD_KEYWORDS = {
    'bell pepper', 'strawberry', 'orange', 'lemon', 'banana', 'apple', 'granny smith',
    'pomegranate', 'fig', 'jackfruit', 'pineapple', 'hip',
    'cheeseburger', 'hotdog', 'pizza', 'screen', 'monitor', 'laptop', 'television'
}

class LeafDataset(Dataset):
    """Memory-efficient PyTorch Dataset for fast batched feature extraction."""
    def __init__(self, image_paths, transform):
        self.image_paths = image_paths
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        path = self.image_paths[idx]
        try:
            with Image.open(path) as img:
                img_rgb = img.convert('RGB')
                tensor = self.transform(img_rgb)
            return tensor, str(path), True
        except Exception as e:
            # Return a zero tensor if image is corrupt
            return torch.zeros((3, 224, 224), dtype=torch.float32), str(path), False

def discover_dataset(data_dir):
    """
    Discovers valid class folders and image files, safely filtering out
    nested duplicate folders such as data/raw/PlantVillage/PlantVillage.
    """
    data_dir = Path(data_dir).resolve()
    if not data_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {data_dir}")

    # Identify potential class directories
    candidates = [d for d in data_dir.iterdir() if d.is_dir()]
    
    # Check if there is a redundant nested folder named identical to parent (e.g., PlantVillage)
    classes = []
    nested_warning = False
    for d in candidates:
        if d.name == data_dir.name or d.name == 'PlantVillage':
            # Check if it contains subdirectories
            subdirs = [s for s in d.iterdir() if s.is_dir()]
            if subdirs:
                nested_warning = True
                continue
        classes.append(d)

    if nested_warning:
        print("[WARNING] Detected redundant nested duplicate directory ('PlantVillage/PlantVillage').")
        print("          Automatically ignoring nested duplicates to prevent skewed embeddings and duplicate scanning.")

    class_to_images = {}
    valid_exts = {'.jpg', '.jpeg', '.png', '.bmp'}
    
    for c in sorted(classes, key=lambda x: x.name):
        imgs = [f for f in c.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
        if imgs:
            class_to_images[c.name] = imgs

    total_images = sum(len(v) for v in class_to_images.values())
    print(f"Discovered {len(class_to_images)} classes with a total of {total_images:,} valid images.")
    return class_to_images

def extract_features_and_predictions(image_paths, model, classifier, transform, device, batch_size=64):
    """
    Extracts 512-d normalized visual embeddings and top ImageNet predictions
    in a single efficient GPU forward pass.
    """
    dataset = LeafDataset(image_paths, transform)
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0, # Optimal & stable on Windows
        pin_memory=(device.type == 'cuda')
    )

    all_embeddings = []
    all_paths = []
    corrupted_paths = []
    top_pred_names = []
    top_pred_probs = []

    weights = models.ResNet18_Weights.DEFAULT
    categories = weights.meta['categories']

    with torch.no_grad():
        for tensors, paths_batch, valids in tqdm(loader, desc="Scanning Images", leave=False):
            tensors = tensors.to(device)
            # 1. Feature embeddings (pool layer output)
            embeddings = model(tensors) # shape: [B, 512]
            
            # 2. ImageNet classification logits
            logits = classifier(embeddings) # shape: [B, 1000]
            probs = torch.softmax(logits, dim=1)
            best_probs, best_indices = torch.max(probs, dim=1)

            embeddings_np = embeddings.cpu().numpy()
            best_probs_np = best_probs.cpu().numpy()
            best_indices_np = best_indices.cpu().numpy()

            for i in range(len(paths_batch)):
                path_str = paths_batch[i]
                is_valid = bool(valids[i])
                if not is_valid:
                    corrupted_paths.append(path_str)
                    continue

                all_embeddings.append(embeddings_np[i])
                all_paths.append(path_str)
                top_pred_names.append(categories[best_indices_np[i]])
                top_pred_probs.append(float(best_probs_np[i]))

    if not all_embeddings:
        return np.array([]), [], [], [], corrupted_paths

    embeddings_matrix = np.vstack(all_embeddings)
    return embeddings_matrix, all_paths, top_pred_names, top_pred_probs, corrupted_paths

def generate_html_gallery(outlier_df, output_html_path, max_images=None):
    """
    Generates a standalone, interactive HTML inspection gallery with:
    - Prominently displayed full absolute Windows paths on every card.
    - 1-click 'Copy Path' button for each photo.
    - Checkboxes on every photo to pick and choose files to delete.
    - Batch 'Copy Selected Paths' and 'Download PowerShell / Batch Delete Script' buttons.
    - Live search and filter by crop class, filename, and anomaly reason.
    """
    if max_images is not None:
        display_df = outlier_df.head(max_images)
    else:
        display_df = outlier_df

    output_html_path = Path(output_html_path).resolve()
    html_dir = output_html_path.parent
    unique_classes = sorted(display_df['class_name'].unique())

    cards_html = []
    for idx, row in display_df.iterrows():
        badge_class = "badge-anomaly"
        reason_str = str(row.get('outlier_reason', 'Anomaly'))
        if "Fruit/Object" in reason_str:
            badge_class = "badge-fruit"
        elif "Corrupt" in reason_str:
            badge_class = "badge-corrupt"

        abs_path = str(Path(row['image_path']).resolve())
        try:
            rel_path = os.path.relpath(abs_path, html_dir).replace('\\', '/')
        except Exception:
            rel_path = Path(abs_path).as_uri()

        img_uri = Path(abs_path).as_uri()
        img_name = Path(abs_path).name
        class_name = row['class_name']
        card_id = f"card_{idx}"
        cb_id = f"cb_{idx}"
        js_safe_path = abs_path.replace('\\', '\\\\').replace("'", "\\'")

        cards_html.append(f"""
        <div class="card" id="{card_id}" data-path="{abs_path}" data-class="{class_name}" data-reason="{reason_str.lower()}" data-name="{img_name.lower()}">
            <div class="card-header">
                <label class="checkbox-container" title="Select for deletion">
                    <input type="checkbox" id="{cb_id}" onchange="updateSelection()" />
                    <span class="checkmark"></span>
                    <span class="select-label">Select</span>
                </label>
                <span class="badge {badge_class}">{reason_str}</span>
            </div>
            <div class="img-container" onclick="toggleCard('{card_id}')">
                <img src="{rel_path}" onerror="this.src='{img_uri}'" alt="{img_name}" loading="lazy" />
            </div>
            <div class="info">
                <div class="class-tag" title="{class_name}">📁 {class_name}</div>
                <div class="file-name" title="{img_name}">{img_name}</div>
                
                <div class="meta-grid">
                    <div><span class="meta-label">Centroid Dist:</span> <span class="meta-val">{row['cosine_distance']:.4f}</span></div>
                    <div><span class="meta-label">Top Match:</span> <span class="meta-val">{row['top_imagenet_pred']} ({row['top_imagenet_prob']:.1%})</span></div>
                </div>

                <div class="path-box">
                    <div class="path-header">
                        <span class="path-title">FULL IMAGE PATH:</span>
                        <button type="button" class="btn-copy" onclick="copySinglePath('{js_safe_path}', this)" title="Copy path to clipboard">📋 Copy Path</button>
                    </div>
                    <input type="text" class="path-input" readonly value="{abs_path}" onclick="this.select()" title="Click to highlight entire path" />
                </div>
            </div>
        </div>
        """)

    cards_joined = "\n".join(cards_html)
    class_options = "\n".join([f'<option value="{c}">{c}</option>' for c in unique_classes])

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dataset Outlier & Fruit Inspection Gallery</title>
<style>
    :root {{
        --bg-main: #0b1120;
        --card-bg: #1e293b;
        --card-border: #334155;
        --card-hover: #38bdf8;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
        --accent-cyan: #38bdf8;
        --accent-red: #ef4444;
        --accent-amber: #f59e0b;
        --accent-green: #10b981;
    }}
    * {{ box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background: var(--bg-main);
        color: var(--text-primary);
        margin: 0;
        padding: 0;
        min-height: 100vh;
    }}
    
    /* Sticky Top Control Toolbar */
    .top-bar {{
        position: sticky;
        top: 0;
        z-index: 100;
        background: rgba(15, 23, 42, 0.95);
        backdrop-filter: blur(12px);
        border-bottom: 1px solid var(--card-border);
        padding: 16px 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }}
    .header-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        margin-bottom: 14px;
    }}
    h1 {{
        margin: 0;
        font-size: 22px;
        font-weight: 700;
        color: var(--accent-cyan);
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .subtitle {{
        color: var(--text-secondary);
        font-size: 13px;
        margin: 4px 0 0 0;
    }}
    
    /* Toolbar Action Controls */
    .toolbar-row {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 10px;
    }}
    .search-input, .filter-select {{
        background: #0f172a;
        border: 1px solid var(--card-border);
        color: #f1f5f9;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 13px;
        outline: none;
        transition: border-color 0.2s;
    }}
    .search-input {{ min-width: 260px; flex-grow: 1; }}
    .search-input:focus, .filter-select:focus {{
        border-color: var(--accent-cyan);
    }}
    
    .btn {{
        background: #1e293b;
        color: #f8fafc;
        border: 1px solid #475569;
        padding: 8px 14px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: all 0.2s;
        white-space: nowrap;
    }}
    .btn:hover:not(:disabled) {{
        background: #334155;
        border-color: var(--accent-cyan);
    }}
    .btn:disabled {{
        opacity: 0.4;
        cursor: not-allowed;
    }}
    .btn-primary {{
        background: #0284c7;
        border-color: #0284c7;
    }}
    .btn-primary:hover:not(:disabled) {{
        background: #0369a1;
        border-color: #38bdf8;
    }}
    .btn-danger {{
        background: #b91c1c;
        border-color: #dc2626;
    }}
    .btn-danger:hover:not(:disabled) {{
        background: #991b1b;
    }}
    .btn-fruit {{
        background: #7f1d1d;
        border-color: #ef4444;
        color: #fca5a5;
    }}
    .btn-fruit:hover:not(:disabled) {{
        background: #991b1b;
        color: #fff;
    }}
    .selection-badge {{
        background: #0369a1;
        color: #fff;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
    }}

    /* Container & Cards Grid */
    .content-area {{
        padding: 24px;
    }}
    .stats-summary {{
        display: flex;
        gap: 16px;
        margin-bottom: 20px;
        color: var(--text-secondary);
        font-size: 13px;
    }}
    .stats-item {{
        background: #1e293b;
        border: 1px solid var(--card-border);
        padding: 6px 14px;
        border-radius: 6px;
    }}
    .stats-item b {{ color: #f8fafc; }}

    .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 20px;
    }}
    
    /* Card Design */
    .card {{
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 12px;
        overflow: hidden;
        transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        display: flex;
        flex-direction: column;
    }}
    .card:hover {{
        border-color: #64748b;
        transform: translateY(-2px);
    }}
    .card.selected {{
        border: 2px solid var(--accent-cyan);
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.35);
        background: #16243b;
    }}
    
    .card-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 14px;
        background: #0f172a;
        border-bottom: 1px solid var(--card-border);
    }}
    
    /* Custom Checkbox */
    .checkbox-container {{
        display: flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
        user-select: none;
        font-size: 12px;
        font-weight: 600;
        color: #f1f5f9;
    }}
    .checkbox-container input {{
        cursor: pointer;
        width: 18px;
        height: 18px;
        accent-color: var(--accent-cyan);
    }}

    .badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        max-width: 60%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    .badge-fruit {{ background: #dc2626; color: #fff; }}
    .badge-anomaly {{ background: #d97706; color: #fff; }}
    .badge-corrupt {{ background: #991b1b; color: #fff; }}

    .img-container {{
        width: 100%;
        height: 240px;
        background: #000;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }}
    .img-container img {{
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        transition: transform 0.3s;
    }}
    .img-container:hover img {{
        transform: scale(1.05);
    }}
    
    .info {{
        padding: 14px;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
        gap: 8px;
    }}
    .class-tag {{
        font-weight: 700;
        color: var(--accent-cyan);
        font-size: 14px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .file-name {{
        color: var(--text-secondary);
        font-size: 12px;
        font-family: monospace;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    
    .meta-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 6px;
        background: #0f172a;
        padding: 8px 10px;
        border-radius: 6px;
        border: 1px solid #1e293b;
        font-size: 12px;
    }}
    .meta-label {{ color: var(--text-secondary); font-size: 11px; }}
    .meta-val {{ font-weight: 600; color: #f8fafc; }}

    /* Prominent Path Section */
    .path-box {{
        margin-top: auto;
        background: #090d16;
        border: 1px solid #263348;
        border-radius: 6px;
        padding: 8px 10px;
    }}
    .path-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }}
    .path-title {{
        font-size: 10px;
        font-weight: 700;
        color: #64748b;
        letter-spacing: 0.5px;
    }}
    .btn-copy {{
        background: #1e293b;
        color: #38bdf8;
        border: 1px solid #38bdf8;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }}
    .btn-copy:hover {{
        background: #38bdf8;
        color: #0b1120;
    }}
    .path-input {{
        width: 100%;
        background: transparent;
        border: none;
        color: #cbd5e1;
        font-family: Consolas, monospace;
        font-size: 11px;
        padding: 2px 0;
        outline: none;
        cursor: pointer;
    }}
    .path-input:focus {{
        color: #38bdf8;
    }}
    
    /* Toast Notification */
    #toast {{
        visibility: hidden;
        min-width: 250px;
        background-color: #0284c7;
        color: #fff;
        text-align: center;
        border-radius: 8px;
        padding: 12px 20px;
        position: fixed;
        z-index: 1000;
        left: 50%;
        bottom: 30px;
        transform: translateX(-50%);
        font-size: 14px;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }}
    #toast.show {{
        visibility: visible;
        animation: fadein 0.3s, fadeout 0.5s 2.5s;
    }}
    @keyframes fadein {{ from {{ bottom: 0; opacity: 0; }} to {{ bottom: 30px; opacity: 1; }} }}
    @keyframes fadeout {{ from {{ bottom: 30px; opacity: 1; }} to {{ bottom: 0; opacity: 0; }} }}
</style>
</head>
<body>

<div class="top-bar">
    <div class="header-row">
        <div>
            <h1>🌿 Dataset Outlier & Fruit Inspection Gallery</h1>
            <p class="subtitle">Review flagged images, inspect absolute paths, and select items to generate deletion scripts or copy paths.</p>
        </div>
        <div style="display:flex; align-items:center; gap:10px;">
            <span class="selection-badge" id="selectedBadge">0 Selected</span>
            <button class="btn btn-primary" id="btnCopySelected" onclick="copySelectedPaths()" disabled>📋 Copy Selected Paths</button>
            <button class="btn btn-danger" id="btnDownloadPS" onclick="downloadPowerShellScript()" disabled>💾 Download Delete Script (.ps1)</button>
            <button class="btn" id="btnDownloadBat" onclick="downloadBatchScript()" disabled>💾 Download Batch (.bat)</button>
        </div>
    </div>
    
    <div class="toolbar-row">
        <input type="text" id="searchInput" class="search-input" placeholder="🔍 Search by file name, class, or reason..." oninput="filterCards()" />
        
        <select id="classFilter" class="filter-select" onchange="filterCards()">
            <option value="">All Crop Classes</option>
            {class_options}
        </select>

        <select id="reasonFilter" class="filter-select" onchange="filterCards()">
            <option value="">All Anomaly Types</option>
            <option value="fruit">🍎 Fruits / Non-Leaf Objects</option>
            <option value="visual">📊 Visual Distance Outliers</option>
            <option value="density">🌲 Density Anomalies (IsoForest)</option>
        </select>

        <button class="btn btn-fruit" onclick="selectFruitsOnly()">🍎 Select All Fruits</button>
        <button class="btn" onclick="selectAll(true)">Select All Visible</button>
        <button class="btn" onclick="deselectAll()">Deselect All</button>
    </div>
</div>

<div class="content-area">
    <div class="stats-summary">
        <div class="stats-item">Total Outliers Flagged: <b>{len(display_df):,}</b></div>
        <div class="stats-item" id="visibleStats">Visible: <b>{len(display_df):,}</b></div>
        <div class="stats-item">Selection: <b id="selectionCountText">0 selected</b></div>
    </div>

    <div class="grid" id="cardsGrid">
        {cards_joined}
    </div>
</div>

<div id="toast">Paths copied to clipboard!</div>

<script>
    function showToast(message) {{
        const toast = document.getElementById("toast");
        toast.textContent = message;
        toast.className = "show";
        setTimeout(() => {{ toast.className = toast.className.replace("show", ""); }}, 3000);
    }}

    function copySinglePath(path, btn) {{
        navigator.clipboard.writeText(path).then(() => {{
            const originalText = btn.textContent;
            btn.textContent = "✓ Copied!";
            btn.style.background = "#10b981";
            btn.style.color = "#ffffff";
            btn.style.borderColor = "#10b981";
            showToast("Copied path to clipboard!");
            setTimeout(() => {{
                btn.textContent = originalText;
                btn.style.background = "";
                btn.style.color = "";
                btn.style.borderColor = "";
            }}, 1800);
        }}).catch(err => {{
            alert("Clipboard error: " + err);
        }});
    }}

    function toggleCard(cardId) {{
        const card = document.getElementById(cardId);
        const checkbox = card.querySelector("input[type='checkbox']");
        checkbox.checked = !checkbox.checked;
        updateSelection();
    }}

    function updateSelection() {{
        const cards = document.querySelectorAll(".card");
        let selectedCount = 0;
        cards.forEach(card => {{
            const cb = card.querySelector("input[type='checkbox']");
            if (cb.checked) {{
                card.classList.add("selected");
                selectedCount++;
            }} else {{
                card.classList.remove("selected");
            }}
        }});

        document.getElementById("selectedBadge").textContent = selectedCount + " Selected";
        document.getElementById("selectionCountText").textContent = selectedCount + " selected";
        
        const hasSelection = selectedCount > 0;
        document.getElementById("btnCopySelected").disabled = !hasSelection;
        document.getElementById("btnDownloadPS").disabled = !hasSelection;
        document.getElementById("btnDownloadBat").disabled = !hasSelection;
    }}

    function selectAll(filteredOnly) {{
        const cards = document.querySelectorAll(".card");
        cards.forEach(card => {{
            if (!filteredOnly || card.style.display !== "none") {{
                const cb = card.querySelector("input[type='checkbox']");
                cb.checked = true;
            }}
        }});
        updateSelection();
    }}

    function deselectAll() {{
        const cards = document.querySelectorAll(".card");
        cards.forEach(card => {{
            const cb = card.querySelector("input[type='checkbox']");
            cb.checked = false;
        }});
        updateSelection();
    }}

    function selectFruitsOnly() {{
        deselectAll();
        const cards = document.querySelectorAll(".card");
        cards.forEach(card => {{
            const reason = card.getAttribute("data-reason") || "";
            if (reason.includes("fruit")) {{
                card.querySelector("input[type='checkbox']").checked = true;
            }}
        }});
        updateSelection();
        showToast("Selected all fruit / non-leaf items!");
    }}

    function getSelectedPaths() {{
        const selectedCards = document.querySelectorAll(".card.selected");
        const paths = [];
        selectedCards.forEach(card => {{
            paths.push(card.getAttribute("data-path"));
        }});
        return paths;
    }}

    function copySelectedPaths() {{
        const paths = getSelectedPaths();
        if (paths.length === 0) return;
        const text = paths.join("\\n");
        navigator.clipboard.writeText(text).then(() => {{
            showToast("Copied " + paths.length + " selected file paths to clipboard!");
        }});
    }}

    function downloadPowerShellScript() {{
        const paths = getSelectedPaths();
        if (paths.length === 0) return;

        let script = "# PowerShell Outlier Deletion Script\\n";
        script += "# Generated automatically by Dataset Outlier Inspection Gallery\\n";
        script += "# Total files to remove: " + paths.length + "\\n\\n";
        script += "$outliers = @(\\n";
        paths.forEach(p => {{
            script += '    "' + p.replace(/"/g, '`"') + '",\\n';
        }});
        script += ")\\n\\n";
        script += 'Write-Host "Starting removal of ' + paths.length + ' outlier files..." -ForegroundColor Cyan\\n';
        script += "$count = 0\\n";
        script += "foreach ($f in $outliers) {{\\n";
        script += "    if (Test-Path $f) {{\\n";
        script += "        Remove-Item -Path $f -Force\\n";
        script += '        Write-Host "Removed: $f" -ForegroundColor Yellow\\n';
        script += "        $count++\\n";
        script += "    }}\\n";
        script += "}}\\n";
        script += 'Write-Host "Deletion complete! Successfully removed $count files." -ForegroundColor Green\\n';

        const blob = new Blob([script], {{ type: "text/plain;charset=utf-8" }});
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "delete_selected_outliers.ps1";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast("Downloaded delete_selected_outliers.ps1 (" + paths.length + " files)");
    }}

    function downloadBatchScript() {{
        const paths = getSelectedPaths();
        if (paths.length === 0) return;

        let bat = "@echo off\\n";
        bat += "echo Deleting " + paths.length + " selected outlier files...\\n";
        paths.forEach(p => {{
            bat += 'del /f /q "' + p + '"\\n';
        }});
        bat += "echo Outlier files removed successfully!\\n";
        bat += "pause\\n";

        const blob = new Blob([bat], {{ type: "text/plain;charset=utf-8" }});
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "delete_selected_outliers.bat";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast("Downloaded delete_selected_outliers.bat (" + paths.length + " files)");
    }}

    function filterCards() {{
        const query = document.getElementById("searchInput").value.toLowerCase().trim();
        const selectedClass = document.getElementById("classFilter").value;
        const selectedReason = document.getElementById("reasonFilter").value.toLowerCase();
        const cards = document.querySelectorAll(".card");
        let visibleCount = 0;

        cards.forEach(card => {{
            const cardClass = card.getAttribute("data-class") || "";
            const cardReason = card.getAttribute("data-reason") || "";
            const cardName = card.getAttribute("data-name") || "";
            const cardPath = (card.getAttribute("data-path") || "").toLowerCase();

            let matchesQuery = true;
            if (query) {{
                matchesQuery = cardName.includes(query) || cardPath.includes(query) || cardClass.toLowerCase().includes(query) || cardReason.includes(query);
            }}

            let matchesClass = true;
            if (selectedClass) {{
                matchesClass = (cardClass === selectedClass);
            }}

            let matchesReason = true;
            if (selectedReason) {{
                matchesReason = cardReason.includes(selectedReason);
            }}

            if (matchesQuery && matchesClass && matchesReason) {{
                card.style.display = "flex";
                visibleCount++;
            }} else {{
                card.style.display = "none";
            }}
        }});

        document.getElementById("visibleStats").innerHTML = "Visible: <b>" + visibleCount + "</b>";
    }}
</script>
</body>
</html>
"""
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

def detect_outliers(
    data_dir,
    output_dir="suspicious_outliers",
    contamination=0.005,
    threshold_sigma=3.0,
    batch_size=64,
    generate_gallery=True,
    quarantine=False,
    quarantine_action="copy"
):
    """
    Main outlier detection pipeline performing per-class visual embedding anomaly detection
    and semantic non-leaf/fruit filtering.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Executing outlier detection on device: {device}")
    if device.type == "cuda":
        print(f"GPU Accelerator: {torch.cuda.get_device_name(0)}")

    # 1. Discover data and classes
    class_to_images = discover_dataset(data_dir)

    # 2. Load pre-trained ResNet18 model
    weights = models.ResNet18_Weights.DEFAULT
    transform = weights.transforms()
    full_model = models.resnet18(weights=weights).to(device).eval()

    # Split into feature extractor (512-d) and classification head (1000-d)
    classifier_head = full_model.fc
    full_model.fc = nn.Identity()
    feature_extractor = full_model

    all_records = []
    global_corrupted = []

    print("\nAuditing classes for visual anomalies and fruits...")
    
    for class_name, img_paths in class_to_images.items():
        print(f"\nProcessing class: [{class_name}] ({len(img_paths)} images)")
        
        feats, paths, top_preds, top_probs, corrupts = extract_features_and_predictions(
            img_paths, feature_extractor, classifier_head, transform, device, batch_size=batch_size
        )
        global_corrupted.extend(corrupts)

        if len(paths) == 0:
            continue

        # L2-normalize embeddings onto unit hypersphere
        norms = np.linalg.norm(feats, axis=1, keepdims=True)
        norms[norms == 0] = 1e-8
        feats_norm = feats / norms

        # Class centroid in spherical embedding space
        centroid = np.mean(feats_norm, axis=0)
        centroid = centroid / (np.linalg.norm(centroid) + 1e-8)

        # Cosine distance to class centroid: 1 - cosine_similarity
        cosine_sims = np.dot(feats_norm, centroid)
        cosine_dists = 1.0 - cosine_sims

        # Adaptive threshold based on class distribution: mean + threshold_sigma * std
        mean_dist = np.mean(cosine_dists)
        std_dist = np.std(cosine_dists)
        sigma_threshold = mean_dist + (threshold_sigma * std_dist)

        # Per-class Isolation Forest
        n_samples = len(feats_norm)
        # Avoid fitting Isolation Forest on tiny samples
        if n_samples >= 20:
            effective_contamination = min(max(contamination, 0.001), 0.1)
            iso = IsolationForest(contamination=effective_contamination, random_state=42, n_jobs=-1)
            iso_preds = iso.fit_predict(feats_norm) # -1 is outlier
            iso_scores = iso.decision_function(feats_norm)
        else:
            iso_preds = np.ones(n_samples, dtype=int)
            iso_scores = np.zeros(n_samples, dtype=float)

        for i in range(len(paths)):
            path = paths[i]
            dist = float(cosine_dists[i])
            pred_name = top_preds[i]
            pred_prob = float(top_probs[i])
            iso_p = int(iso_preds[i])
            iso_s = float(iso_scores[i])

            # Determine anomaly flags
            is_fruit_or_non_leaf = False
            for kw in NON_LEAF_FOOD_KEYWORDS:
                if kw in pred_name.lower():
                    # Must have reasonable confidence and distance above class average
                    if pred_prob > 0.35 and dist > (mean_dist + 1.5 * std_dist):
                        is_fruit_or_non_leaf = True
                        break

            is_distance_outlier = (dist > sigma_threshold)
            is_iso_outlier = (iso_p == -1 and iso_s < -0.05 and dist > (mean_dist + 2.0 * std_dist))

            # Combined outlier determination
            is_outlier = False
            reasons = []

            if is_fruit_or_non_leaf:
                is_outlier = True
                reasons.append(f"Fruit/Object Match ({pred_name}: {pred_prob:.1%})")

            if is_distance_outlier:
                is_outlier = True
                reasons.append(f"Visual Outlier (> {threshold_sigma} std)")

            if is_iso_outlier:
                is_outlier = True
                reasons.append("Density Anomaly (IsoForest)")

            all_records.append({
                'image_path': path,
                'class_name': class_name,
                'cosine_distance': dist,
                'mean_class_distance': mean_dist,
                'iso_score': iso_s,
                'top_imagenet_pred': pred_name,
                'top_imagenet_prob': pred_prob,
                'is_outlier': is_outlier,
                'outlier_reason': " + ".join(reasons) if reasons else "Normal"
            })

    # Assemble summary DataFrame
    df = pd.DataFrame(all_records)
    
    # Add corrupt images if any
    for cp in global_corrupted:
        df = pd.concat([df, pd.DataFrame([{
            'image_path': cp,
            'class_name': Path(cp).parent.name,
            'cosine_distance': 1.0,
            'mean_class_distance': 0.0,
            'iso_score': -1.0,
            'top_imagenet_pred': 'Corrupt File',
            'top_imagenet_prob': 1.0,
            'is_outlier': True,
            'outlier_reason': 'Unreadable/Corrupt Image'
        }])], ignore_index=True)

    # Sort so top outliers appear first
    df = df.sort_values(by=['is_outlier', 'cosine_distance'], ascending=[False, False]).reset_index(drop=True)

    outlier_df = df[df['is_outlier'] == True]

    print("\n" + "=" * 60)
    print("                 OUTLIER AUDIT RESULTS")
    print("=" * 60)
    print(f"Total Images Analyzed : {len(df):,}")
    print(f"Potential Outliers    : {len(outlier_df):,} ({len(outlier_df)/max(len(df),1):.2%})")
    print(f"Corrupted Images      : {len(global_corrupted)}")
    print("=" * 60)

    # Save outlier_paths.txt (backwards-compatible with original code)
    txt_path = output_dir / "outlier_paths.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for p in outlier_df['image_path']:
            f.write(f"{p}\n")
    print(f"-> Outlier paths logged to: {txt_path}")

    # Save detailed CSV report
    csv_path = output_dir / "outlier_report.csv"
    df.to_csv(csv_path, index=False)
    print(f"-> Detailed report saved to: {csv_path}")

    # Save visual HTML gallery
    if generate_gallery and len(outlier_df) > 0:
        html_path = output_dir / "outliers_gallery.html"
        generate_html_gallery(outlier_df, html_path, max_images=None)
        print(f"-> Interactive visual gallery saved to: {html_path}")
        print("   (Open outliers_gallery.html in your browser to inspect images at a glance!)")

    # Display top 10 most anomalous items in console
    if len(outlier_df) > 0:
        print("\nTop Flagged Suspicious Samples:")
        for idx, row in outlier_df.head(10).iterrows():
            fname = Path(row['image_path']).name
            print(f" [{row['class_name']}] {fname} | Dist: {row['cosine_distance']:.3f} | Reason: {row['outlier_reason']}")

    # Quarantine handling
    if quarantine and len(outlier_df) > 0:
        import shutil
        quarantine_dir = output_dir / "quarantine"
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n-> Quarantining {len(outlier_df)} suspicious files ({quarantine_action}) to: {quarantine_dir}")
        for _, row in outlier_df.iterrows():
            src = Path(row['image_path'])
            dst_folder = quarantine_dir / row['class_name']
            dst_folder.mkdir(parents=True, exist_ok=True)
            dst = dst_folder / src.name
            if quarantine_action == 'move':
                shutil.move(src, dst)
            else:
                shutil.copy2(src, dst)
        print("   Quarantine completed successfully.")

    return df, outlier_df

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Find outliers, fruits, and noisy images in leaf datasets.")
    parser.add_argument(
        '--data_dir',
        type=str,
        default=r"C:\Users\ACER\Intern21\smart-agriculture-platform\data\raw\PlantVillage",
        help="Path to the PlantVillage dataset directory"
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        default="suspicious_outliers",
        help="Directory to save audit logs, reports, and galleries"
    )
    parser.add_argument(
        '--contamination',
        type=float,
        default=0.005,
        help="Estimated proportion of outliers for Isolation Forest (default: 0.005)"
    )
    parser.add_argument(
        '--threshold_sigma',
        type=float,
        default=3.0,
        help="Standard deviation multiplier above class mean distance to flag as outlier (default: 3.0)"
    )
    parser.add_argument(
        '--batch_size',
        type=int,
        default=64,
        help="Batch size for feature extraction (default: 64)"
    )
    parser.add_argument(
        '--no_gallery',
        action='store_true',
        help="Disable HTML visual gallery generation"
    )
    parser.add_argument(
        '--quarantine',
        action='store_true',
        help="Copy/move suspicious outlier images into a quarantine folder for isolated inspection"
    )
    parser.add_argument(
        '--quarantine_action',
        type=str,
        choices=['copy', 'move'],
        default='copy',
        help="Action for quarantine: 'copy' leaves original untouched, 'move' moves files out of dataset (default: 'copy')"
    )

    args = parser.parse_args()

    detect_outliers(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        contamination=args.contamination,
        threshold_sigma=args.threshold_sigma,
        batch_size=args.batch_size,
        generate_gallery=not args.no_gallery,
        quarantine=args.quarantine,
        quarantine_action=args.quarantine_action
    )
