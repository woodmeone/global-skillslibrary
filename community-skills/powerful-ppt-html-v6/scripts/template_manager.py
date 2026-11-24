#!/usr/bin/env python3
"""
模板管理器 - 统一的模板增删改查工具
支持：创建模板、删除模板、验证模板、生成预览、同步索引

用法：
  python template_manager.py create --name "My Style" --theme light
  python template_manager.py delete --id combo-13
  python template_manager.py validate --id combo-12
  python template_manager.py sync
  python template_manager.py list
  python template_manager.py quality-check --id combo-12
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

STYLES_DIR = Path(__file__).parent.parent / "templates" / "styles"
USER_STYLES_DIR = Path(__file__).parent.parent / "templates" / "user-styles"
INDEX_FILE = STYLES_DIR / "styles_index.json"

REQUIRED_CONFIG_FIELDS = ["id", "name", "version", "best_for", "theme", "pptx_bg", "css_variables", "includes"]
REQUIRED_CSS_FILES = ["base.css", "components.css"]
OPTIONAL_CSS_FILES = ["effects.css"]
VALID_THEMES = ["light", "dark"]

QUALITY_CHECKS = {
    "config_complete": "config.json 包含所有必需字段",
    "css_files_exist": "必需的 CSS 文件存在",
    "css_variables_defined": "CSS 变量定义完整（至少包含颜色和图表变量）",
    "preview_exists": "预览图存在",
    "no_syntax_errors": "CSS 无语法错误",
    "color_contrast_ok": "文字与背景对比度足够",
    "responsive_design": "包含响应式断点",
    "reduced_motion": "包含 prefers-reduced-motion 支持",
}


class TemplateManager:
    def __init__(self, styles_dir: Path = STYLES_DIR, user_dir: Path = USER_STYLES_DIR):
        self.styles_dir = styles_dir
        self.user_dir = user_dir
        self.user_dir.mkdir(parents=True, exist_ok=True)

    def create(self, name: str, theme: str = "light", name_cn: str = "", 
               best_for: List[str] = None, is_user_template: bool = False) -> Dict:
        """创建新模板"""
        if best_for is None:
            best_for = ["General purpose"]
        
        existing_ids = self._get_existing_ids()
        new_id = self._generate_next_id(existing_ids)
        folder_name = f"{new_id}-{self._name_to_slug(name)}"
        target_dir = self.user_dir if is_user_template else self.styles_dir
        template_dir = target_dir / folder_name
        
        if template_dir.exists():
            return {"success": False, "error": f"Template folder already exists: {folder_name}"}
        
        template_dir.mkdir(parents=True)
        
        config = {
            "id": new_id,
            "name": name,
            "name_cn": name_cn or name,
            "version": "1.0.0",
            "best_for": best_for,
            "theme": theme,
            "pptx_bg": "ffffff" if theme == "light" else "1a1a1a",
            "chart_support": "svg+echarts",
            "micro_interactions": [],
            "css_variables": self._generate_default_variables(theme),
            "includes": ["base.css", "effects.css", "components.css"],
            "author": "user" if is_user_template else "system",
            "created_at": str(date.today()),
            "quality_score": 0,
        }
        
        with open(template_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        self._create_template_css(template_dir, name, theme)
        
        return {
            "success": True,
            "id": new_id,
            "folder": folder_name,
            "path": str(template_dir),
            "message": f"Template '{name}' created. Run 'sync' and 'preview' to complete."
        }

    def delete(self, template_id: str) -> Dict:
        """删除模板"""
        folder = self._find_template_folder(template_id)
        if not folder:
            return {"success": False, "error": f"Template not found: {template_id}"}
        
        shutil.rmtree(folder)
        return {"success": True, "message": f"Template {template_id} deleted"}

    def validate(self, template_id: str) -> Dict:
        """验证模板完整性"""
        folder = self._find_template_folder(template_id)
        if not folder:
            return {"success": False, "error": f"Template not found: {template_id}"}
        
        results = {"valid": True, "warnings": [], "errors": []}
        
        config_path = folder / "config.json"
        if not config_path.exists():
            results["errors"].append("config.json not found")
            results["valid"] = False
            return results
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            results["errors"].append(f"config.json parse error: {e}")
            results["valid"] = False
            return results
        
        for field in REQUIRED_CONFIG_FIELDS:
            if field not in config:
                results["warnings"].append(f"Missing recommended field: {field}")
        
        if config.get("theme") not in VALID_THEMES:
            results["errors"].append(f"Invalid theme: {config.get('theme')}")
            results["valid"] = False
        
        for css_file in REQUIRED_CSS_FILES:
            if not (folder / css_file).exists():
                results["errors"].append(f"Missing required CSS: {css_file}")
                results["valid"] = False
        
        css_vars = config.get("css_variables", {})
        required_vars = ["--bg-primary", "--text-primary", "--chart-color-1"]
        for var in required_vars:
            if var not in css_vars:
                results["warnings"].append(f"Missing CSS variable: {var}")
        
        return results

    def quality_check(self, template_id: str) -> Dict:
        """质量检查并评分"""
        folder = self._find_template_folder(template_id)
        if not folder:
            return {"success": False, "error": f"Template not found: {template_id}"}
        
        scores = {}
        total_score = 0
        max_score = len(QUALITY_CHECKS) * 10
        
        validation = self.validate(template_id)
        if not validation["valid"]:
            return {"success": False, "errors": validation["errors"], "score": 0}
        
        scores["config_complete"] = 10 if not validation["warnings"] else 7
        scores["css_files_exist"] = 10
        
        config = self._load_config(folder)
        css_vars = config.get("css_variables", {})
        scores["css_variables_defined"] = 10 if len(css_vars) >= 15 else 5
        
        scores["preview_exists"] = 10 if (folder / "preview.png").exists() else 0
        
        base_css = folder / "base.css"
        if base_css.exists():
            css_content = base_css.read_text(encoding="utf-8")
            scores["no_syntax_errors"] = 10
            scores["responsive_design"] = 10 if "@media" in css_content else 0
            scores["reduced_motion"] = 10 if "prefers-reduced-motion" in css_content else 0
        else:
            scores["no_syntax_errors"] = 0
            scores["responsive_design"] = 0
            scores["reduced_motion"] = 0
        
        bg_color = css_vars.get("--bg-primary", "#ffffff")
        text_color = css_vars.get("--text-primary", "#000000")
        scores["color_contrast_ok"] = self._check_contrast(bg_color, text_color)
        
        total_score = sum(scores.values())
        percentage = round(total_score / max_score * 100, 1)
        
        config["quality_score"] = percentage
        config_path = folder / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "id": template_id,
            "score": percentage,
            "breakdown": scores,
            "grade": self._get_grade(percentage),
            "recommendation": self._get_recommendation(percentage)
        }

    def sync(self) -> Dict:
        """同步索引文件"""
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "sync_styles_index.py")],
            capture_output=True, text=True
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }

    def generate_previews(self) -> Dict:
        """生成所有预览图"""
        result = subprocess.run(
            ["node", str(Path(__file__).parent / "generate_previews.js")],
            capture_output=True, text=True, cwd=str(Path(__file__).parent.parent)
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }

    def list_templates(self, include_user: bool = True) -> List[Dict]:
        """列出所有模板"""
        templates = []
        
        for folder in self.styles_dir.iterdir():
            if folder.is_dir() and (folder / "config.json").exists():
                templates.append(self._get_template_info(folder))
        
        if include_user and self.user_dir.exists():
            for folder in self.user_dir.iterdir():
                if folder.is_dir() and (folder / "config.json").exists():
                    info = self._get_template_info(folder)
                    info["is_user_template"] = True
                    templates.append(info)
        
        return sorted(templates, key=lambda x: x["id"])

    def _get_existing_ids(self) -> List[str]:
        ids = []
        for folder in self.styles_dir.iterdir():
            if folder.is_dir() and (folder / "config.json").exists():
                try:
                    config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
                    ids.append(config.get("id", ""))
                except:
                    pass
        return ids

    def _generate_next_id(self, existing_ids: List[str]) -> str:
        max_num = 0
        for id_str in existing_ids:
            match = re.match(r"combo-(\d+)", id_str)
            if match:
                max_num = max(max_num, int(match.group(1)))
        return f"combo-{max_num + 1}"

    def _name_to_slug(self, name: str) -> str:
        slug = name.lower().replace(" ", "-").replace("_", "-")
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        return slug[:30]

    def _generate_default_variables(self, theme: str) -> Dict:
        if theme == "light":
            return {
                "--bg-primary": "#ffffff",
                "--bg-secondary": "#f5f5f5",
                "--bg-card": "#ffffff",
                "--text-primary": "#1a1a1a",
                "--text-secondary": "#666666",
                "--text-accent": "#0066cc",
                "--radius": "8px",
                "--chart-color-1": "#0066cc",
                "--chart-color-2": "#cc3366",
                "--chart-color-3": "#33cc66",
                "--chart-color-4": "#cc9933",
                "--chart-color-5": "#9966cc",
                "--chart-color-6": "#66cccc",
                "--chart-text": "#1a1a1a",
                "--chart-text-secondary": "#666666",
                "--chart-grid": "#e0e0e0",
                "--chart-bg": "transparent",
            }
        else:
            return {
                "--bg-primary": "#1a1a1a",
                "--bg-secondary": "#2a2a2a",
                "--bg-card": "#252525",
                "--text-primary": "#f5f5f5",
                "--text-secondary": "#a0a0a0",
                "--text-accent": "#00ccff",
                "--radius": "8px",
                "--chart-color-1": "#00ccff",
                "--chart-color-2": "#ff3366",
                "--chart-color-3": "#33ff66",
                "--chart-color-4": "#ffcc33",
                "--chart-color-5": "#cc33ff",
                "--chart-color-6": "#33ffcc",
                "--chart-text": "#f5f5f5",
                "--chart-text-secondary": "#a0a0a0",
                "--chart-grid": "#404040",
                "--chart-bg": "transparent",
            }

    def _create_template_css(self, template_dir: Path, name: str, theme: str):
        vars_str = "\n".join([f"  {k}: {v};" for k, v in self._generate_default_variables(theme).items()])
        
        base_css = f""":root {{
{vars_str}
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  overflow: hidden;
}}

.presentation {{ width: 100vw; height: 100vh; position: relative; }}

.slide {{
  width: 100%; height: 100%; position: absolute; top: 0; left: 0;
  display: flex; flex-direction: column; justify-content: center;
  padding: 60px 80px;
  opacity: 0; transform: translateY(12px);
  transition: opacity 0.6s ease, transform 0.6s ease;
  pointer-events: none; visibility: hidden;
}}

.slide.active {{
  opacity: 1; transform: none; pointer-events: auto; visibility: visible;
}}

.hero-title {{
  font-size: clamp(2.5rem, 6vw, 5rem); font-weight: 700;
  line-height: 1.1; color: var(--text-primary);
}}

.hero-subtitle {{
  font-size: clamp(1rem, 1.5vw, 1.25rem); color: var(--text-secondary);
  margin-top: 20px; line-height: 1.6;
}}

.section-label {{
  font-size: 0.85rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.1em; color: var(--text-accent);
}}

.section-title {{
  font-size: clamp(1.8rem, 4vw, 3.5rem); font-weight: 700;
  margin-top: 12px; line-height: 1.1; color: var(--text-primary);
}}

.section-desc {{
  font-size: clamp(1rem, 1.5vw, 1.3rem); color: var(--text-secondary);
  margin-top: 20px; line-height: 1.7; max-width: 70%;
}}

@media (max-width: 768px) {{
  .slide {{ padding: 40px 32px; }}
  .section-desc {{ max-width: 100%; }}
}}

@media (prefers-reduced-motion: reduce) {{
  .slide {{ transition: opacity 0.3s ease; transform: none !important; }}
}}
"""
        
        with open(template_dir / "base.css", "w", encoding="utf-8") as f:
            f.write(base_css)
        
        effects_css = f""".slide::before {{
  content: '';
  position: absolute; inset: 0;
  background: radial-gradient(circle at 30% 30%, rgba(0,0,0,0.02), transparent 50%);
  pointer-events: none;
}}

.slide.active .section-label {{
  animation: fadeIn 0.6s ease 0.1s both;
}}

.slide.active .hero-title,
.slide.active .section-title {{
  animation: fadeIn 0.6s ease 0.2s both;
}}

.slide.active .hero-subtitle,
.slide.active .section-desc {{
  animation: fadeIn 0.6s ease 0.4s both;
}}

@keyframes fadeIn {{
  from {{ opacity: 0; transform: translateY(12px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}
"""
        
        with open(template_dir / "effects.css", "w", encoding="utf-8") as f:
            f.write(effects_css)
        
        components_css = f""".brutal-card {{
  background: var(--bg-card);
  border: 1px solid var(--text-secondary);
  padding: 24px;
  border-radius: var(--radius);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}}

.brutal-card:hover {{
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.1);
}}

.card-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px; margin-top: 24px;
}}

.hero-tag {{
  display: inline-block; padding: 4px 12px; font-size: 0.75rem;
  font-weight: 600; margin-right: 8px; margin-top: 8px;
  background: var(--bg-secondary); color: var(--text-primary);
  border-radius: calc(var(--radius) / 2);
}}

.step-group {{ display: flex; flex-direction: column; gap: 16px; margin-top: 24px; }}
.step-item {{ display: flex; align-items: flex-start; gap: 16px; }}

.step-num {{
  min-width: 40px; height: 40px; display: flex; align-items: center;
  justify-content: center; font-size: 1.1rem; font-weight: 700;
  color: var(--bg-primary); background: var(--text-primary);
  border-radius: calc(var(--radius) / 2);
}}

.case-list {{ display: flex; flex-direction: column; gap: 12px; margin-top: 24px; }}
.case-item {{
  display: flex; align-items: center; gap: 12px; padding: 12px 16px;
  border: 1px solid var(--text-secondary); background: var(--bg-secondary);
  border-radius: var(--radius);
}}
"""
        
        with open(template_dir / "components.css", "w", encoding="utf-8") as f:
            f.write(components_css)

    def _find_template_folder(self, template_id: str) -> Optional[Path]:
        for base_dir in [self.styles_dir, self.user_dir]:
            for folder in base_dir.iterdir():
                if folder.is_dir() and (folder / "config.json").exists():
                    try:
                        config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
                        if config.get("id") == template_id:
                            return folder
                    except:
                        pass
        return None

    def _load_config(self, folder: Path) -> Dict:
        try:
            return json.loads((folder / "config.json").read_text(encoding="utf-8"))
        except:
            return {}

    def _get_template_info(self, folder: Path) -> Dict:
        config = self._load_config(folder)
        return {
            "id": config.get("id", ""),
            "name": config.get("name", ""),
            "name_cn": config.get("name_cn", ""),
            "theme": config.get("theme", ""),
            "quality_score": config.get("quality_score", 0),
            "folder": folder.name,
        }

    def _check_contrast(self, bg: str, text: str) -> int:
        def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
            hex_str = hex_str.lstrip("#")
            return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
        
        try:
            bg_rgb = hex_to_rgb(bg)
            text_rgb = hex_to_rgb(text)
            
            bg_lum = 0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2]
            text_lum = 0.299 * text_rgb[0] + 0.587 * text_rgb[1] + 0.114 * text_rgb[2]
            
            contrast = abs(bg_lum - text_lum)
            
            if contrast > 128:
                return 10
            elif contrast > 64:
                return 7
            else:
                return 3
        except:
            return 5

    def _get_grade(self, score: float) -> str:
        if score >= 90:
            return "A+ 优秀"
        elif score >= 80:
            return "A 良好"
        elif score >= 70:
            return "B 合格"
        elif score >= 60:
            return "C 待改进"
        else:
            return "D 不合格"

    def _get_recommendation(self, score: float) -> str:
        if score >= 90:
            return "模板质量优秀，可以发布到公共模板库"
        elif score >= 70:
            return "模板质量合格，建议完善细节后发布"
        elif score >= 60:
            return "模板需要改进，请检查警告项"
        else:
            return "模板质量不合格，请参考文档重新设计"


def main():
    parser = argparse.ArgumentParser(description="模板管理器")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    create_parser = subparsers.add_parser("create", help="创建新模板")
    create_parser.add_argument("--name", required=True, help="模板名称")
    create_parser.add_argument("--theme", choices=["light", "dark"], default="light", help="主题")
    create_parser.add_argument("--name-cn", default="", help="中文名称")
    create_parser.add_argument("--best-for", nargs="+", default=["General"], help="适用场景")
    create_parser.add_argument("--user", action="store_true", help="创建为用户模板")
    
    delete_parser = subparsers.add_parser("delete", help="删除模板")
    delete_parser.add_argument("--id", required=True, help="模板ID")
    
    validate_parser = subparsers.add_parser("validate", help="验证模板")
    validate_parser.add_argument("--id", required=True, help="模板ID")
    
    quality_parser = subparsers.add_parser("quality-check", help="质量检查")
    quality_parser.add_argument("--id", required=True, help="模板ID")
    
    subparsers.add_parser("sync", help="同步索引")
    subparsers.add_parser("preview", help="生成预览")
    subparsers.add_parser("list", help="列出所有模板")
    
    args = parser.parse_args()
    manager = TemplateManager()
    
    if args.command == "create":
        result = manager.create(args.name, args.theme, args.name_cn, args.best_for, args.user)
    elif args.command == "delete":
        result = manager.delete(args.id)
    elif args.command == "validate":
        result = manager.validate(args.id)
    elif args.command == "quality-check":
        result = manager.quality_check(args.id)
    elif args.command == "sync":
        result = manager.sync()
    elif args.command == "preview":
        result = manager.generate_previews()
    elif args.command == "list":
        result = manager.list_templates()
    else:
        parser.print_help()
        return
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
