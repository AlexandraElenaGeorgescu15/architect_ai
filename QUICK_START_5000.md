# 🎯 QUICK START: 5000+ Example Fine-Tuning

## ⚡ GENERATE DATASET (5 minutes)

1. **Open app** → Sidebar → **Fine-Tuning System**
2. **Select**: "Code Prototype"
3. **Click**: "Generate Training Dataset"
4. **Wait**: 2-5 minutes
5. **Find**: `finetune_datasets/code_prototype_YYYYMMDD.jsonl`

## ✅ VERIFY DATASET

```bash
# Check file size (should be ~50-100MB for 5000 examples)
ls -lh finetune_datasets/code_prototype_*.jsonl

# Count examples
python -c "import json; print(sum(1 for line in open('finetune_datasets/code_prototype_20251106.jsonl')))"

# Should show: ~5000
```

## 🚀 FINE-TUNE MODEL

### Recommended Settings
- **Base Model**: `codellama:7b-instruct`
- **Dataset**: Your generated JSONL file
- **Steps**: 1000-2000
- **Batch Size**: 8
- **Learning Rate**: 2e-5
- **Epochs**: 2-3

### Via App
1. Fine-Tuning System → **Start Fine-Tuning**
2. Select base model: **codellama:7b-instruct**
3. Select dataset: **code_prototype_YYYYMMDD.jsonl**
4. Click **Start Training**
5. Wait 4-6 hours (CPU) or 1-2 hours (GPU)

## 🧪 TEST FINE-TUNED MODEL

### Test 1: ERD Generation
**Prompt**: `"Generate an ERD for a hotel booking system"`

**Expected Output**:
```
erDiagram
    Guest ||--o{ Reservation : makes
    Hotel ||--o{ Room : has
    Room ||--o{ Reservation : booked
    Reservation ||--o{ Payment : requires
    ...
```

### Test 2: YOUR Code Patterns
**Prompt**: `"Create a product controller with MongoDB"`

**Expected Output**:
```csharp
public class ProductController : Controller
{
    private readonly IMongoCollection<ProductDto> _products;
    
    public ProductController(IMongoDBSettings settings)
    {
        var client = new MongoClient(settings.ConnectionString);
        var database = client.GetDatabase(settings.DatabaseName);
        _products = database.GetCollection<ProductDto>("products");
    }
    ...
}
```

### Test 3: Architecture
**Prompt**: `"Show microservices architecture for e-commerce"`

**Expected Output**:
```
graph TB
    Client --> Gateway[API Gateway]
    Gateway --> Auth[Auth Service]
    Gateway --> Product[Product Service]
    Gateway --> Order[Order Service]
    Product --> ProductDB[(Product DB)]
    Order --> OrderDB[(Order DB)]
    Order --> Queue[Message Queue]
```

### Test 4: Sequence Diagram
**Prompt**: `"Sequence diagram for password reset"`

**Expected Output**:
```
sequenceDiagram
    User->>Frontend: Request Reset
    Frontend->>API: POST /forgot-password
    API->>Database: Find User
    API->>Email: Send Reset Link
    User->>Frontend: Click Link
    ...
```

## 📊 WHAT YOU GET

### Artifact Expertise
✅ 50+ ERD patterns (e-commerce, healthcare, education, CRM, etc.)  
✅ 30+ architecture styles (microservices, serverless, event-driven)  
✅ 30+ sequence flows (auth, payments, CRUD, uploads)  
✅ Professional diagram quality  

### YOUR Code Patterns
✅ IMongoDBSettings MongoDB integration  
✅ XxxDto naming convention  
✅ Controller base class inheritance  
✅ Angular HttpClient services  
✅ BSON attributes and MongoDB mapping  

### Generalization
✅ Works with ANY mother project  
✅ Adapts YOUR patterns to new features  
✅ Combines artifact expertise with YOUR style  

## 🎯 SUCCESS METRICS

### Dataset Quality
- [ ] ~5000 examples in JSONL
- [ ] Contains YOUR MongoDB/DTO/Controller code
- [ ] Contains diverse ERD domains
- [ ] Contains multiple architecture patterns
- [ ] No generic templates

### Training Quality
- [ ] Loss decreases from ~2.5 to ~0.5-1.0
- [ ] No overfitting (validation loss close to training loss)
- [ ] Completes without errors

### Output Quality
- [ ] Generates professional ERDs
- [ ] Uses YOUR IMongoDBSettings pattern
- [ ] Uses YOUR XxxDto naming
- [ ] Inherits from Controller base
- [ ] Creates correct Mermaid syntax

## 🔧 TROUBLESHOOTING

### Less than 5000 examples?
→ Check RAG index has user files (should have 49 files)  
→ Verify repo sweep is enabled  
→ Check `outputs/finetuning/chunk_selection_debug.json`

### Generic code, not YOUR patterns?
→ Stub fixes applied correctly? Run `verify_5000_system.py`  
→ Check first 10 examples in JSONL contain YOUR code  

### Training loss not decreasing?
→ Reduce learning rate to 1e-5  
→ Increase batch size to 16  
→ Verify dataset has diverse examples

### Model outputs wrong patterns?
→ Check training examples used actual code  
→ Verify fine-tuning completed (all epochs)  
→ Test with correct model name

## 📁 FILES TO CHECK

```
finetune_datasets/
└── code_prototype_20251106.jsonl  ← Your 5000+ examples

outputs/finetuning/
└── chunk_selection_debug.json  ← Verify user files selected

finetuned_models/
└── code_prototype_7b/  ← Your fine-tuned model

components/
├── expanded_artifact_examples.py  ← 100+ artifact templates
└── finetuning_dataset_builder.py  ← Updated with 5000 target
```

## 🚀 ONE-COMMAND VERIFICATION

```bash
python verify_5000_system.py
```

Should output:
```
VERIFICATION COMPLETE: ALL TESTS PASSED ✅
Target Examples: 5000
Artifact Templates: 110
Example Multiplier: 8-10× per code file
```

---

**Last Updated**: November 6, 2025  
**Status**: Production Ready ✅  
**Quick Help**: Check `5000_EXAMPLE_SYSTEM_SUMMARY.md` for details
