import json
import os
import sys
from datetime import date
from pathlib import Path

REQUIRED_CONFIG_FIELDS = ["id", "name", "version", "best_for", "theme", "pptx_bg", "css_variables", "includes"]
REQUIRED_CSS_FILES = ["base.css", "components.css"]
OPTIONAL_CSS_FILES = ["effects.css"]
VALID_THEMES = ["light", "dark"]


def validate_config(config, folder_name):
    warnings = []
    for field in REQUIRED_CONFIG_FIELDS:
        if field not in config:
            warnings.append(f"[{folder_name}] config.json missing required field: {field}")

    if "theme" in config and config["theme"] not in VALID_THEMES:
        warnings.append(f"[{folder_name}] Invalid theme: {config['theme']}, must be light/dark")

    if "pptx_bg" in config:
        bg = config["pptx_bg"]
        if not isinstance(bg, str) or len(bg) != 6:
            warnings.append(f"[{folder_name}] Invalid pptx_bg: {bg}, must be 6-char hex without #")

    return warnings


def sync_styles_index(styles_dir=None):
    if styles_dir is None:
        styles_dir = Path(__file__).parent.parent / "templates" / "styles"
    else:
        styles_dir = Path(styles_dir)

    if not styles_dir.exists():
        print(f"Error: styles directory not found: {styles_dir}")
        sys.exit(1)

    all_warnings = []
    styles = {}
    light_styles = []
    dark_styles = []
    quick_lookup = {
        "tech": [],
        "business": [],
        "creative": [],
        "education": [],
    }

    keyword_map = {
        "tech": ["Security", "Tech", "Cyberpunk", "AI", "Programming", "SaaS", "Dashboards", "Product launch", "Data reports", "Tech talks", "Architecture", "Engineering"],
        "business": ["Enterprise", "Investment", "Premium brand", "Product showcase"],
        "creative": ["Fashion", "Art", "Culture", "Creative", "Fun science", "Web3"],
        "education": ["Education", "Personal blog", "Handmade", "Kids education"],
    }

    for folder in sorted(styles_dir.iterdir()):
        if not folder.is_dir():
            continue
        if folder.name.startswith(".") or folder.name == "__pycache__":
            continue

        config_path = folder / "config.json"
        if not config_path.exists():
            all_warnings.append(f"[{folder.name}] config.json not found, skipping")
            continue

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            all_warnings.append(f"[{folder.name}] config.json parse error: {e}")
            continue

        warnings = validate_config(config, folder.name)
        all_warnings.extend(warnings)

        style_id = config.get("id", "")
        if not style_id:
            continue

        for css_file in REQUIRED_CSS_FILES:
            if not (folder / css_file).exists():
                all_warnings.append(f"[{folder.name}] Missing required CSS: {css_file}")

        if not (folder / "preview.png").exists():
            all_warnings.append(f"[{folder.name}] preview.png not found (recommended)")

        theme = config.get("theme", "light")
        if theme == "light":
            light_styles.append(style_id)
        else:
            dark_styles.append(style_id)

        best_for = config.get("best_for", [])
        for category, keywords in keyword_map.items():
            if any(kw in " ".join(best_for) for kw in keywords):
                quick_lookup[category].append(style_id)

        styles[style_id] = {
            "id": style_id,
            "name": config.get("name", ""),
            "name_cn": config.get("name_cn", ""),
            "best_for": best_for,
            "theme": theme,
            "pptx_bg": config.get("pptx_bg", ""),
            "preview": f"{folder.name}/preview.png",
            "config": f"{folder.name}/config.json",
        }

    index = {
        "meta": {
            "total": len(styles),
            "updated": str(date.today()),
            "generator": "sync_styles_index.py",
        },
        "categories": {
            "light": light_styles,
            "dark": dark_styles,
        },
        "quickLookup": quick_lookup,
        "styles": styles,
    }

    output_path = styles_dir / "styles_index.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"Generated styles_index.json with {len(styles)} styles")
    print(f"  Light: {len(light_styles)} | Dark: {len(dark_styles)}")

    if all_warnings:
        print(f"\nWarnings ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"  ⚠ {w}")
    else:
        print("\nNo warnings - all styles valid!")

    return index


if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else None
    sync_styles_index(target_dir)
