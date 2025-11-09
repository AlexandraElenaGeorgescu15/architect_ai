# NUCLEAR FIXES - Final Implementation

**Date:** November 9, 2025  
**Status:** CRITICAL - Immediate Action Required

---

## 🔴 CRITICAL ISSUES FROM USER OUTPUT

### Issue 1: Diagrams Full of Explanatory Text
**Example from user:**
```
flowchart TD
Here is the corrected Mermaid diagram:
```mermaid
flowchart TD
A[Start] --> B[Generate Sequence Diagram]
7. C:\Users\AGEORGE2\Desktop\Dawn-final-project\final_project\Controllers\WeatherForecastController.cs: This is another CSharp file...
Based on these files,
```

**ROOT CAUSE:** `strip_markdown_artifacts()` NOT STRONG ENOUGH

---

### Issue 2: HTML Visualizations Not Generating
**User says:** "htmls for the diagrams are not generated at all"

**ROOT CAUSE:** HTML generation using static fallback, not actual generation

---

### Issue 3: Same Model for Everything
**User says:** "ollama seems to still use the same model for everything"

**ROOT CAUSE:** Model routing not being respected

---

### Issue 4: Generic Content Everywhere
**Examples:**
- Data Flow: Shows "package-lock.json" file paths as nodes
- JIRA: Talks about Material Design and ESLint instead of project features
- Workflows: Generic analysis text instead of actual workflows

**ROOT CAUSE:** Prompts too weak, local models ignoring instructions

---

## 🎯 NUCLEAR FIX PLAN

### Fix 1: NUCLEAR Diagram Cleaning
**Make `strip_markdown_artifacts()` 10x more aggressive:**

```python
def strip_markdown_artifacts_NUCLEAR(text: str) -> str:
    """
    NUCLEAR-level cleaning - removes EVERYTHING except diagram code.
    """
    import re
    if not text:
        return ""
    
    # Step 1: Remove EVERYTHING before first valid diagram line
    diagram_starts = [
        r'erDiagram',
        r'flowchart\s+(TD|LR|TB|RL)',
        r'graph\s+(TD|LR|TB|RL)',
        r'sequenceDiagram',
        r'classDiagram',
        r'stateDiagram'
    ]
    
    for start_pattern in diagram_starts:
        match = re.search(start_pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            text = text[match.start():]
            break
    
    # Step 2: Remove ALL markdown blocks
    text = re.sub(r'```[\w\-]*\s*', '', text, flags=re.MULTILINE | re.IGNORECASE)
    
    # Step 3: Remove ALL explanatory text patterns (COMPREHENSIVE)
    kill_patterns = [
        r'Here.*?:',
        r'This.*?:',
        r'The.*?:',
        r'I\'ve.*?:',
        r'Based.*?:',
        r'From.*?:',
        r'As.*?:',
        r'\d+\.\s+[A-Z].*?:',  # Numbered lists
        r'FILE:.*',  # File paths
        r'SECTION:.*',  # Section markers
        r'RAG CONTEXT.*',  # RAG artifacts
        r'Pattern:.*',  # Pattern markers
        r'Representative:.*',  # Rep markers
        r'It seems.*',  # LLM uncertainty
        r'I recommend.*',  # LLM suggestions
        r'Please.*',  # LLM requests
        r'Note:.*',  # Notes
        r'Warning:.*',  # Warnings
        r'^\s*\d+\.\s+.*$',  # Any numbered line
    ]
    
    for pattern in kill_patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE | re.IGNORECASE)
    
    # Step 4: Remove ALL HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Step 5: Remove lines with file paths
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        if 'C:\\Users\\' in line or '/Users/' in line or 'package-lock.json' in line:
            continue
        if line.strip().startswith('FILE:') or line.strip().startswith('SECTION:'):
            continue
        cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Step 6: Remove empty lines (more than 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()
```

---

### Fix 2: Force Cloud Models for Diagrams
**Change model routing to ALWAYS use cloud (Groq) for diagrams:**

```python
# In universal_agent.py
if artifact_type in ['erd', 'architecture', 'system_overview', 'data_flow', 'user_flow', 'components_diagram', 'api_sequence']:
    # FORCE cloud models for diagrams (local models too weak)
    print(f"[MODEL_ROUTING] Forcing CLOUD model for {artifact_type} (local models inadequate)")
    # Skip local, go straight to cloud
    return await self._call_cloud_providers(prompt, system_prompt)
```

---

### Fix 3: Gemini Context Window Reduction
**Strategic reduction to fit 1M token limit:**

1. **Remove redundant RAG context** - Keep only top 5 chunks (not 18)
2. **Remove Pattern Mining context** - Not needed for generation
3. **Remove Knowledge Graph details** - Keep only entity list
4. **Truncate meeting notes** - Keep first 2000 chars

```python
# Strategic context reduction for Gemini
if provider == "gemini":
    # Reduce RAG context
    if len(self.rag_context) > 5000:
        self.rag_context = self.rag_context[:5000] + "\n... (truncated for context limit)"
    
    # Remove pattern mining
    if "DETECTED CODE PATTERNS" in full_prompt:
        full_prompt = re.sub(r'DETECTED CODE PATTERNS.*?(?=\n\n[A-Z]|\Z)', '', full_prompt, flags=re.DOTALL)
    
    # Simplify KG
    if "Knowledge Graph" in full_prompt:
        full_prompt = re.sub(r'Knowledge Graph:.*?(?=\n\n[A-Z]|\Z)', 'Knowledge Graph: Available\n', full_prompt, flags=re.DOTALL)
```

---

### Fix 4: HTML Generation Fix
**Replace static fallback with actual Groq generation:**

```python
# After diagram generation, generate HTML
if artifact_type in diagram_types:
    html_prompt = f"""
Generate a beautiful HTML visualization for this Mermaid diagram:

{diagram_content}

Requirements:
- Full HTML document
- Include Mermaid.js from CDN
- Professional styling
- Responsive design
- NO explanations, ONLY HTML code
"""
    
    html_content = await self._call_ai(html_prompt, "Generate ONLY HTML code", force_cloud=True)
    html_content = strip_markdown_artifacts_NUCLEAR(html_content)
    
    # Save HTML
    html_file = outputs_dir / "visualizations" / f"{artifact_type}_diagram.html"
    html_file.parent.mkdir(exist_ok=True)
    html_file.write_text(html_content, encoding='utf-8')
```

---

### Fix 5: NUCLEAR Prompt Strengthening
**Add these to EVERY diagram prompt:**

```python
NUCLEAR_INSTRUCTIONS = """
⚠️ ⚠️ ⚠️ CRITICAL VALIDATION REQUIREMENTS ⚠️ ⚠️ ⚠️

YOU WILL BE PENALIZED if you:
- Include ANY explanatory text
- Use markdown code blocks (```)
- Mention file paths
- Add "Here is..." or similar phrases
- Include numbered lists
- Add any text except diagram code

✅ OUTPUT FORMAT (CRITICAL):
- Start IMMEDIATELY with diagram type (erDiagram, flowchart TD, etc.)
- NO markdown blocks
- NO explanations
- NO file paths
- ONLY diagram code

❌ FAIL EXAMPLES:
"Here is the diagram:" ← NO!
"```mermaid" ← NO!
"Based on the files..." ← NO!
"1. First, we..." ← NO!

✅ PASS EXAMPLE:
erDiagram
  User {
    int id PK
  }

START YOUR RESPONSE WITH THE DIAGRAM TYPE. NOTHING ELSE.
"""
```

---

## 🚀 IMPLEMENTATION ORDER

1. ✅ Save Groq key (DONE)
2. ⏳ Replace `strip_markdown_artifacts()` with NUCLEAR version
3. ⏳ Add NUCLEAR_INSTRUCTIONS to all diagram prompts
4. ⏳ Force cloud models for diagrams
5. ⏳ Add Gemini context reduction
6. ⏳ Fix HTML generation
7. ⏳ Test everything

---

## 📊 Expected Results

| Issue | Before | After |
|-------|--------|-------|
| Explanatory text | ❌ Everywhere | ✅ Removed |
| HTML generation | ❌ Static fallback | ✅ Generated |
| Model routing | ❌ Same model | ✅ Cloud for diagrams |
| Generic content | ❌ Frequent | ✅ Project-specific |
| Quality scores | 🔴 0-70/100 | 🟢 85-95/100 |

---

## ⏱️ Estimated Time

- Implementation: 45 minutes
- Testing: 15 minutes
- **Total: 1 hour**

---

**STATUS:** Ready to implement. Proceeding with all fixes now.

