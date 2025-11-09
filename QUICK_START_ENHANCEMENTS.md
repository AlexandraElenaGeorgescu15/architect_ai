# Quick Start: New Prototype Enhancements

**Date:** November 9, 2025  
**Version:** 3.5.3 (with Entity Extraction)

---

## 🎉 What's New?

Your code and visual prototypes now use **YOUR actual project entities** instead of generic placeholders!

### Before:
```csharp
// ❌ Generic
public class ExtractedFeatureController { ... }
public class ExtractedFeatureDto { int Id, string Name }
```

### After:
```csharp
// ✅ Your actual entities!
public class RequestSwapController { ... }
public class RequestSwapDto { 
    int Id, string UserId, int PhoneIdOffered, 
    int PhoneIdRequested, string Status, DateTime CreatedAt 
}
```

---

## 🚀 How to Use

### Step 1: Generate ERD (Required!)
1. Enter meeting notes
2. Click **"Generate ERD"**
3. Wait for completion
4. Verify entities are correct (RequestSwap, Phone, User, not generic User/Product/Order)

### Step 2: Generate Code Prototype
1. Click **"Generate Code Prototype"**
2. Watch console for: `[CODE_GEN] ✅ Extracted N entities from ERD: RequestSwap, Phone, ...`
3. Check outputs/prototype/ for generated files

**Expected Output:**
- ✅ Controllers for EACH entity (RequestSwapController, PhoneController, UserController)
- ✅ DTOs with ALL your fields (not just Id and Name)
- ✅ Full implementations (no TODOs)
- ✅ Service layer with business logic

### Step 3: Generate Visual Prototype
1. Click **"Generate Visual Prototype"**
2. Watch console for: `[VISUAL_PROTO] ✅ Extracted N entities for UI: RequestSwap, Phone, ...`
3. Check outputs/prototype/visual_prototype_dev.html

**Expected Output:**
- ✅ Forms with your actual fields (userId, phoneIdOffered, phoneIdRequested)
- ✅ Realistic mock data (not "Sample 1", "Sample 2")
- ✅ Entity-specific UI elements

---

## 🔍 Console Messages to Look For

### ✅ Success:
```
[CODE_GEN] ✅ Extracted 4 entities from ERD: RequestSwap, Phone, User, Comment
[VISUAL_PROTO] ✅ Extracted 4 entities for UI: RequestSwap, Phone, User, Comment
```

### ⚠️ Warnings:
```
[CODE_GEN] ⚠️ No ERD file found at outputs/visualizations/erd_diagram.mmd
→ Solution: Generate ERD first!

[CODE_GEN] ⚠️ Could not extract entities from ERD: [error]
→ Solution: Check ERD file syntax
```

---

## 📊 Quality Checklist

After generation, check for these indicators of quality:

### Code Prototype:
- [ ] Controller names match your entities (not "ExtractedFeatureController")
- [ ] DTOs have 5+ fields (not just Id and Name)
- [ ] Methods have realistic names (GetUserRequests, CreateSwapRequest)
- [ ] No TODOs in the code
- [ ] Service layer included (not just controllers)

### Visual Prototype:
- [ ] Form fields match entity fields (userId, phoneIdOffered, etc.)
- [ ] Mock data includes realistic values
- [ ] Input types match field types (number for int, date for DateTime)
- [ ] No generic "Name" or "Description" fields

---

## 🎯 Example Workflow

1. **Meeting Notes:**
   ```
   Build a phone swap app where users can:
   - List their phones (brand, model, storage, price)
   - Create swap requests
   - Comment on swap requests
   - View their swap history
   ```

2. **Generate ERD** → Entities extracted:
   - `RequestSwap` (id, userId, phoneIdOffered, phoneIdRequested, status, createdAt)
   - `Phone` (id, brand, model, storage, price, condition)
   - `User` (id, email, name)
   - `Comment` (id, requestSwapId, userId, content, createdAt)

3. **Generate Code** → Files created:
   - `Controllers/RequestSwapController.cs` ✅
   - `Controllers/PhoneController.cs` ✅
   - `Controllers/UserController.cs` ✅
   - `Controllers/CommentController.cs` ✅
   - `Models/RequestSwapDto.cs` (with ALL 6 fields) ✅
   - `Services/RequestSwapService.cs` ✅

4. **Generate Visual** → UI created:
   - Form with fields: userId, phoneIdOffered, phoneIdRequested, status ✅
   - Phone table: brand, model, storage, price ✅
   - Realistic mock data ✅

---

## 🛠️ Troubleshooting

### Problem: Still seeing "ExtractedFeature" or generic code
**Causes:**
1. ERD wasn't generated first
2. ERD contains generic entities (USER, ORDER, PRODUCT)
3. Entity extraction failed silently

**Solutions:**
1. Generate ERD before code/visual prototypes
2. Regenerate ERD with more specific meeting notes
3. Check console for extraction errors

---

### Problem: DTOs only have Id and Name fields
**Cause:** Entity extraction didn't find the ERD file

**Solution:**
1. Check if `outputs/visualizations/erd_diagram.mmd` exists
2. Regenerate ERD if file is missing
3. Check console for: `[CODE_GEN] ⚠️ No ERD file found`

---

### Problem: Visual prototype has generic form fields
**Cause:** Entity extraction didn't run for visual generation

**Solution:**
1. Check console for: `[VISUAL_PROTO] ⚠️ No ERD file found`
2. Generate ERD first
3. Regenerate visual prototype

---

## 📖 Technical Details

### New Component:
- **File:** `utils/entity_extractor.py`
- **Purpose:** Extract entities and fields from ERD diagrams
- **Integration:** Auto-called during code and visual prototype generation

### How It Works:
1. Reads `outputs/visualizations/erd_diagram.mmd`
2. Parses Mermaid ERD syntax
3. Extracts entity names and fields
4. Maps types (Mermaid → C# → TypeScript)
5. Enriches RAG context with entities
6. Adds explicit instructions to prompts

### Benefits:
- ✅ Project-specific code (no generic ExtractedFeature)
- ✅ All entity fields included (not just Id and Name)
- ✅ Realistic method implementations
- ✅ Entity-specific UI elements
- ✅ Production-ready output (no TODOs)

---

## 🎓 Best Practices

### 1. Always Generate ERD First
Code and visual prototypes depend on ERD for entity extraction. Without ERD, you'll get generic output.

### 2. Review ERD for Accuracy
Entity extraction is only as good as the ERD. Make sure:
- Entities have descriptive names (RequestSwap, not Swap)
- Entities have 4+ fields (not just Id and Name)
- Field names are clear (phoneIdOffered, not offeredId)

### 3. Use Cloud Models for Prototypes
Local models (CodeLlama, Mistral) struggle with complex code generation. Use GPT-4 or Gemini for best results.

### 4. Regenerate if Generic
If you see generic names, don't use feedback buttons - just regenerate. The entity extraction system should prevent generic output.

---

## 🚀 Next Steps

1. Test the new system:
   - Generate ERD for your project
   - Generate code prototype
   - Generate visual prototype
   - Compare with previous generic output

2. Check quality:
   - Are controller names project-specific?
   - Do DTOs have all fields?
   - Is the UI entity-specific?

3. Provide feedback:
   - If output is still generic, check console logs
   - Report extraction errors if any
   - Celebrate when you see YOUR entities! 🎉

---

**Enjoy production-ready, project-specific prototypes! 🚀**

