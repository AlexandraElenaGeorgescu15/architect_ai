"""
Prototype Generator
- Detect repo stack (Angular, React, Vue, .NET API, WPF, Blazor, FastAPI, Flask, Django, Express, Spring)
- Parse LLM multi-file output and save files
- Deterministic scaffold fallback when LLM is unavailable/insufficient
"""

import re
from pathlib import Path
from typing import List, Tuple, Dict


def detect_stack(base: Path) -> Dict[str, bool]:
    has_angular = (base / "final_project" / "angular.json").exists() or (base / "final_project" / "src" / "app").exists()
    has_react = False
    has_vue = False
    pkg = base / "final_project" / "package.json"
    if pkg.exists():
        try:
            txt = pkg.read_text(encoding='utf-8')
            has_react = '"react"' in txt
            has_vue = '"vue"' in txt
        except Exception:
            pass
    has_dotnet = (base / "final-proj-sln").exists()
    # Blazor: .razor files
    has_blazor = any(True for _ in base.glob("**/*.razor"))
    # WPF detection: any .xaml, or csproj containing <UseWPF>true</UseWPF>
    has_wpf = False
    for csproj in base.glob("**/*.csproj"):
        try:
            txt = csproj.read_text(encoding='utf-8')
            if "<UseWPF>true</UseWPF>" in txt:
                has_wpf = True
                break
        except Exception:
            continue
    if not has_wpf:
        for _ in base.glob("**/*.xaml"):
            has_wpf = True
            break
    has_fastapi = any((p.exists() and 'fastapi' in p.read_text(encoding='utf-8')) for p in base.glob("**/*.py"))
    has_flask = any((p.exists() and 'from flask' in p.read_text(encoding='utf-8')) for p in base.glob("**/*.py"))
    has_django = (base / "manage.py").exists() or any('django' in p.read_text(encoding='utf-8') for p in base.glob("**/settings.py"))
    has_express = (pkg.exists() and ('"express"' in pkg.read_text(encoding='utf-8'))) or any((p.exists() and 'express()' in p.read_text(encoding='utf-8')) for p in base.glob("**/*.js"))
    has_spring = (base / "pom.xml").exists() or any((p.exists() and 'spring-boot-starter' in p.read_text(encoding='utf-8')) for p in base.glob("**/pom.xml"))
    has_streamlit = (base / "architect_ai_cursor_poc" / "app").exists()
    return {
        "has_angular": has_angular,
        "has_react": has_react,
        "has_vue": has_vue,
        "has_dotnet": has_dotnet,
        "has_blazor": has_blazor,
        "has_wpf": has_wpf,
        "has_fastapi": has_fastapi,
        "has_flask": has_flask,
        "has_django": has_django,
        "has_express": has_express,
        "has_spring": has_spring,
        "has_streamlit": has_streamlit,
    }


def parse_llm_files(response: str) -> List[Tuple[str, str]]:
    files: List[Tuple[str, str]] = []
    # Matches blocks like === FILE: path === ... === END FILE ===
    pattern = re.compile(r"===\s*FILE:\s*(.*?)\s*===\s*([\s\S]*?)\s*===\s*END FILE\s*===", re.MULTILINE)
    for m in pattern.finditer(response):
        path = m.group(1).strip()
        content = m.group(2)
        if path:
            files.append((path, content))
    return files


def save_llm_files(response: str, out_root: Path) -> List[Path]:
    saved: List[Path] = []
    for rel, content in parse_llm_files(response):
        target = out_root / "prototypes" / "llm" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        saved.append(target)
    return saved


def _sanitize(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-") or "feature"

# ---------------- UI/API SCAFFOLDS ----------------

def scaffold_angular(feature_name: str, out_root: Path) -> List[Path]:
    saved: List[Path] = []
    feat = _sanitize(feature_name)
    ang_root = out_root / "prototype" / "angular" / "src" / "app"
    pages = ang_root / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    comp_base = pages / f"{feat}.component"
    comp_ts = comp_base.with_suffix(".ts")
    comp_html = comp_base.with_suffix(".html")
    comp_scss = comp_base.with_suffix(".scss")
    comp_ts.write_text(f"""
import {{ Component }} from '@angular/core';

@Component({{
  selector: 'app-{feat}',
  standalone: true,
  templateUrl: './{feat}.component.html',
  styleUrls: ['./{feat}.component.scss']
}})
export class {feat.capitalize()}Component {{
  title = '{feat.capitalize()} Prototype';
}}
""".strip(), encoding='utf-8')
    comp_html.write_text(f"""
<div class="container">
  <h1>{{{{ title }}}}</h1>
  <p>Generated prototype for {feat}.</p>
  <button class="btn">Primary Action</button>
</div>
""".strip(), encoding='utf-8')
    comp_scss.write_text("""
.container { padding: 1rem; }
.btn { background: #667eea; color: #fff; border: 0; padding: .5rem 1rem; border-radius: .5rem; }
""".strip(), encoding='utf-8')
    saved += [comp_ts, comp_html, comp_scss]
    readme = out_root / "prototype" / "angular" / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text(f"""
# Angular Prototype

Standalone component for {feat}. Copy under your Angular app and add a lazy route.
""".strip(), encoding='utf-8')
    saved.append(readme)
    return saved


def scaffold_dotnet_api(feature_name: str, out_root: Path) -> List[Path]:
    saved: List[Path] = []
    feat = _sanitize(feature_name)
    api_root = out_root / "prototype" / "api"
    ctrl = api_root / "Controllers" / f"{feat.capitalize()}Controller.cs"
    dto = api_root / "Dtos" / f"{feat.capitalize()}Dto.cs"
    ctrl.parent.mkdir(parents=True, exist_ok=True)
    dto.parent.mkdir(parents=True, exist_ok=True)
    ctrl.write_text(f"""
using Microsoft.AspNetCore.Mvc;

namespace Prototype.Controllers {{
    [ApiController]
    [Route("api/[controller]")]
    public class {feat.capitalize()}Controller : ControllerBase {{
        [HttpGet]
        public IActionResult Get() => Ok(new [] {{ "ok" }});
    }}
}}
""".strip(), encoding='utf-8')
    dto.write_text(f"""
namespace Prototype.Dtos {{
    public class {feat.capitalize()}Dto {{
        public int Id {{ get; set; }}
        public string Name {{ get; set; }} = string.Empty;
    }}
}}
""".strip(), encoding='utf-8')
    saved += [ctrl, dto]
    api_readme = api_root / "README.md"
    api_readme.write_text("# API Prototype\nAdd to your .NET project and wire Program.cs.", encoding='utf-8')
    saved.append(api_readme)
    return saved


def scaffold_react(feature_name: str, out_root: Path) -> List[Path]:
    feat = _sanitize(feature_name)
    root = out_root / "prototype" / "react" / "src"
    root.mkdir(parents=True, exist_ok=True)
    comp = root / f"{feat.capitalize()}Page.tsx"
    comp.write_text(f"""
import React from 'react';

export const {feat.capitalize()}Page: React.FC = () => {{
  return (
    <div style={{ padding: 16 }}>
      <h1>{feat.capitalize()} Prototype</h1>
      <button style={{ background:'#667eea', color:'#fff', border:0, padding:'8px 16px', borderRadius:8 }}>Primary Action</button>
    </div>
  );
}};
""".strip(), encoding='utf-8')
    readme = out_root / "prototype" / "react" / "README.md"
    readme.write_text("# React Prototype\nCopy component to your app and add route.", encoding='utf-8')
    return [comp, readme]


def scaffold_vue(feature_name: str, out_root: Path) -> List[Path]:
    feat = _sanitize(feature_name)
    root = out_root / "prototype" / "vue" / "src"
    root.mkdir(parents=True, exist_ok=True)
    comp = root / f"{feat.capitalize()}Page.vue"
    comp.write_text(f"""
<template>
  <div class="container">
    <h1>{feat.capitalize()} Prototype</h1>
    <button class="btn">Primary Action</button>
  </div>
</template>
<script setup lang="ts">
</script>
<style>
.container {{ padding: 1rem; }}
.btn {{ background:#667eea; color:#fff; border:0; padding:.5rem 1rem; border-radius:.5rem; }}
</style>
""".strip(), encoding='utf-8')
    readme = out_root / "prototype" / "vue" / "README.md"
    readme.write_text("# Vue Prototype\nCopy component and add route.", encoding='utf-8')
    return [comp, readme]


def scaffold_blazor(feature_name: str, out_root: Path) -> List[Path]:
    feat = _sanitize(feature_name)
    root = out_root / "prototype" / "blazor"
    root.mkdir(parents=True, exist_ok=True)
    razor = root / f"{feat}.razor"
    razor.write_text(f"""
@page "/{feat}"
<h3>{feat.capitalize()} Prototype</h3>
<button class="btn">Primary Action</button>
""".strip(), encoding='utf-8')
    readme = root / "README.md"
    readme.write_text("# Blazor Prototype\nCopy .razor into your project and add route.", encoding='utf-8')
    return [razor, readme]


def scaffold_wpf(feature_name: str, out_root: Path) -> List[Path]:
    saved: List[Path] = []
    feat = _sanitize(feature_name)
    wpf_root = out_root / "prototype" / "wpf"
    wpf_root.mkdir(parents=True, exist_ok=True)
    main_xaml = wpf_root / "MainWindow.xaml"
    main_cs = wpf_root / "MainWindow.xaml.cs"
    app_xaml = wpf_root / "App.xaml"
    app_cs = wpf_root / "App.xaml.cs"
    main_xaml.write_text(f"""
<Window x:Class="Prototype.MainWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="{feat.capitalize()} Prototype" Height="450" Width="800">
    <Grid>
        <StackPanel Margin="16">
            <TextBlock Text="{feat.capitalize()} Prototype" FontSize="24" FontWeight="Bold"/>
            <Button Content="Primary Action" Width="160" Height="36" Margin="0,12,0,0"/>
        </StackPanel>
    </Grid>
</Window>
""".strip(), encoding='utf-8')
    main_cs.write_text("""
using System.Windows;

namespace Prototype {
    public partial class MainWindow : Window {
        public MainWindow() {
            InitializeComponent();
        }
    }
}
""".strip(), encoding='utf-8')
    app_xaml.write_text("""
<Application x:Class="Prototype.App"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             StartupUri="MainWindow.xaml">
    <Application.Resources>
    </Application.Resources>
</Application>
""".strip(), encoding='utf-8')
    app_cs.write_text("""
using System.Windows;

namespace Prototype {
    public partial class App : Application {
    }
}
""".strip(), encoding='utf-8')
    saved += [main_xaml, main_cs, app_xaml, app_cs]
    readme = wpf_root / "README.md"
    readme.write_text(f"""
# WPF Prototype
Generated basic WPF window for {feat}. Add to your WPF project or create a new csproj with <UseWPF>true</UseWPF>.
""".strip(), encoding='utf-8')
    saved.append(readme)
    return saved


def scaffold_fastapi(feature_name: str, out_root: Path) -> List[Path]:
    feat = _sanitize(feature_name)
    root = out_root / "prototype" / "fastapi"
    root.mkdir(parents=True, exist_ok=True)
    main = root / "main.py"
    main.write_text(f"""
from fastapi import FastAPI

app = FastAPI(title="{feat.capitalize()} API")

@app.get("/health")
def health():
    return {{"status":"ok"}}
""".strip(), encoding='utf-8')
    return [main]


def scaffold_flask(feature_name: str, out_root: Path) -> List[Path]:
    feat = _sanitize(feature_name)
    root = out_root / "prototype" / "flask"
    root.mkdir(parents=True, exist_ok=True)
    app_py = root / "app.py"
    app_py.write_text(f"""
from flask import Flask
app = Flask(__name__)

@app.route('/health')
def health():
    return {{'status':'ok'}}

if __name__ == '__main__':
    app.run()
""".strip(), encoding='utf-8')
    return [app_py]


def scaffold_django(feature_name: str, out_root: Path) -> List[Path]:
    root = out_root / "prototype" / "django"
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    readme.write_text("""
# Django Prototype
Run `django-admin startproject app` then add an app with views and urls.
""".strip(), encoding='utf-8')
    return [readme]


def scaffold_express(feature_name: str, out_root: Path) -> List[Path]:
    feat = _sanitize(feature_name)
    root = out_root / "prototype" / "express"
    root.mkdir(parents=True, exist_ok=True)
    app_js = root / "app.js"
    app_js.write_text(f"""
const express = require('express');
const app = express();
app.get('/health', (req, res) => res.json({{ status: 'ok' }}));
app.listen(3000, () => console.log('{feat} API running on 3000'));
""".strip(), encoding='utf-8')
    return [app_js]


def scaffold_spring(feature_name: str, out_root: Path) -> List[Path]:
    feat = _sanitize(feature_name)
    root = out_root / "prototype" / "spring"
    pkg = "com.prototype"
    ctrl = root / f"{feat.capitalize()}Controller.java"
    root.mkdir(parents=True, exist_ok=True)
    ctrl.write_text(f"""
package {pkg};
import org.springframework.web.bind.annotation.*;
@RestController
@RequestMapping("/api/{feat}")
public class {feat.capitalize()}Controller {{
    @GetMapping("/health")
    public String health() {{ return "ok"; }}
}}
""".strip(), encoding='utf-8')
    return [ctrl]

# ---------------- SELECTION ----------------

def generate_best_effort(feature_name: str, base: Path, out_root: Path, llm_response: str = "") -> List[Path]:
    saved: List[Path] = []
    # Try to save LLM files first
    if llm_response and "=== FILE:" in llm_response:
        saved = save_llm_files(llm_response, out_root)
        if saved:
            return saved
    stack = detect_stack(base)
    # UI-first decision
    if stack["has_angular"]:
        ui = scaffold_angular(feature_name, out_root)
        api = scaffold_dotnet_api(feature_name, out_root) if stack["has_dotnet"] else []
        return ui + api
    if stack["has_react"]:
        ui = scaffold_react(feature_name, out_root)
        api = scaffold_dotnet_api(feature_name, out_root) if stack["has_dotnet"] else []
        return ui + api
    if stack["has_vue"]:
        ui = scaffold_vue(feature_name, out_root)
        api = scaffold_dotnet_api(feature_name, out_root) if stack["has_dotnet"] else []
        return ui + api
    if stack["has_blazor"]:
        return scaffold_blazor(feature_name, out_root)
    if stack["has_wpf"]:
        return scaffold_wpf(feature_name, out_root)
    # Backend-first decision
    if stack["has_spring"]:
        return scaffold_spring(feature_name, out_root)
    if stack["has_dotnet"]:
        return scaffold_dotnet_api(feature_name, out_root)
    if stack["has_fastapi"]:
        return scaffold_fastapi(feature_name, out_root)
    if stack["has_django"]:
        return scaffold_django(feature_name, out_root)
    if stack["has_flask"]:
        return scaffold_flask(feature_name, out_root)
    if stack["has_express"]:
        return scaffold_express(feature_name, out_root)
    # Last resort
    return scaffold_streamlit(feature_name, out_root)
