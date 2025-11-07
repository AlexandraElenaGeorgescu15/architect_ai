# 🚀 5000+ TRAINING EXAMPLE STRATEGY

**Goal**: Generate 5000+ high-quality training examples teaching BOTH artifact generation expertise AND your specific code patterns.

---

## 📊 STRATEGY BREAKDOWN

### 1. **Artifact Generation Mastery (100+ Builtin Examples)**

Created `expanded_artifact_examples.py` with **100+ comprehensive examples** covering:

#### ERD Examples (50+)
- **E-commerce**: Multi-vendor platforms, shopping carts, wishlists
- **Healthcare**: Hospital management, patient records, appointments
- **Education**: LMS, students, courses, assignments, grading
- **Social Media**: Posts, comments, likes, followers, messages
- **CRM**: Leads, contacts, accounts, opportunities, sales
- **Booking**: Hotels, reservations, payments, amenities
- **Inventory**: Warehouses, stock, suppliers, purchase orders

#### Architecture Diagrams (30+)
- **Microservices**: API gateway, service mesh, message queues
- **Serverless**: AWS Lambda, API Gateway, DynamoDB, S3
- **Event-Driven**: CQRS, event sourcing, event bus patterns
- **Three-Tier**: Presentation, Application, Data layers
- **CI/CD**: GitHub Actions, Docker, Kubernetes pipelines
- **Real-Time**: WebSocket servers, presence, chat systems

#### Sequence Diagrams (30+)
- **Authentication**: Registration, login, password reset, OAuth 2.0
- **CRUD Operations**: Create, read, update, delete flows
- **E-commerce**: Checkout, payment processing, order confirmation
- **File Management**: Upload with virus scanning, cloud storage
- **Notifications**: Email, SMS, push notification flows

#### Code Generation Examples (30+)
- **.NET Controllers**: MongoDB integration with IMongoDBSettings
- **DTOs**: Following XxxDto naming convention with BSON attributes
- **Angular Services**: HttpClient patterns, Observable handling
- **Validation**: Input validation, error handling patterns

**Result**: 100+ professional artifact examples teaching model to be an expert generator

---

### 2. **YOUR Code Patterns (Multiple Variations)**

Modified `_generate_examples_for_chunk()` to create **8-10 variations** per code file instead of 2:

#### Base Variations (All Files)
1. "Generate code for {component} following patterns in {file}"
2. "Implement {component} based on repository structure"
3. "Create a {file_type} component similar to {file}"
4. "Adapt this {component} pattern for a new feature"
5. "Write {component} following coding standards in codebase"
6. "Replicate the structure and patterns from {file}"

#### Type-Specific Additions

**Angular Components** (+2 examples):
- "Update Angular component to match project styling"
- "Build Angular component like {component} with same structure"

**Angular Services** (+2 examples):
- "Produce Angular service methods for backend API"
- "Implement service similar to {component} for API communication"

**.NET Controllers/DTOs** (+3 examples):
- "Generate .NET API docs with DTO naming/validation patterns"
- "Create .NET {type} following MongoDB integration pattern"
- "Build {component} with same dependency injection pattern"

**Result**: 49 user files × 8-10 variations = **~450 examples** of YOUR actual patterns

---

### 3. **Scale-Up Configuration**

```python
# BEFORE
MIN_DATASET_SIZE = 200
DEFAULT_TARGET_EXAMPLES = 800
MAX_DATASET_SIZE = 1500

# AFTER
MIN_DATASET_SIZE = 500
DEFAULT_TARGET_EXAMPLES = 5000  # ✅ Target 5000+
MAX_DATASET_SIZE = 6000  # ✅ Allow up to 6000
```

---

## 🎯 WHAT THE MODEL WILL LEARN

### Artifact Generation Expertise
✅ **50+ ERD patterns** across all industries  
✅ **30+ architecture styles** (microservices, serverless, event-driven)  
✅ **30+ sequence flows** (auth, payments, uploads, notifications)  
✅ **Professional diagram quality** - correct Mermaid syntax  
✅ **Domain knowledge** - e-commerce, healthcare, education, CRM

### YOUR Specific Patterns
✅ **IMongoDBSettings injection** - your MongoDB connection pattern  
✅ **XxxDto naming convention** - your DTO structure  
✅ **Controller base class** - your .NET controller inheritance  
✅ **MongoDB collections** - your data access patterns  
✅ **Angular services** - your HttpClient and Observable patterns  
✅ **BSON attributes** - your MongoDB document mapping  

---

## 📈 TRAINING DATASET COMPOSITION

```
TOTAL: 5000+ Examples

├── Artifact Examples: ~100
│   ├── ERDs: 50+
│   ├── Architecture: 30+
│   ├── Sequence: 30+
│   └── Code Templates: 30+
│
├── User Code Patterns: ~450
│   ├── .NET Controllers: ~120 (15 files × 8 variations)
│   ├── DTOs: ~80 (10 files × 8 variations)
│   ├── Angular Components: ~100 (12 files × 8 variations)
│   ├── Angular Services: ~80 (10 files × 8 variations)
│   └── Other: ~70
│
└── Repo-Wide Sweep: ~4450
    ├── Additional code files
    ├── Meeting context variations
    ├── Pattern combinations
    └── Cross-file examples
```

---

## 🔥 HOW TO GENERATE

### Step 1: Open Architect AI App
Navigate to sidebar → **Fine-Tuning System**

### Step 2: Select Artifact Type
Choose **"Code Prototype"** (generates all artifact types + code)

### Step 3: Configure
- **Target Examples**: 5000
- **Max Examples**: 6000
- Let the system auto-generate

### Step 4: Verify Quality
Open generated JSONL file in `finetune_datasets/`, check:
- ✅ Contains YOUR MongoDB/DTO/Controller code
- ✅ Contains diverse ERD examples (e-commerce, healthcare, etc.)
- ✅ Contains architecture diagrams (microservices, serverless)
- ✅ Contains sequence flows (auth, payments, CRUD)

---

## ✅ SUCCESS CRITERIA

### Quantity
- ✅ **5000+ total examples** in JSONL file
- ✅ **100+ artifact templates** (ERD, architecture, sequence)
- ✅ **450+ your code variations**
- ✅ **~4450 repo sweep examples**

### Quality
- ✅ Examples show IMongoDBSettings pattern
- ✅ Examples show XxxDto naming
- ✅ Examples show Controller inheritance
- ✅ ERDs cover multiple domains (not just user management)
- ✅ Architecture diagrams show different patterns
- ✅ Sequence diagrams cover different flows

### Diversity
- ✅ E-commerce ERDs
- ✅ Healthcare ERDs
- ✅ Social media ERDs
- ✅ Microservices architectures
- ✅ Serverless architectures
- ✅ Auth sequence flows
- ✅ Payment sequence flows

---

## 🚀 FINE-TUNING RECOMMENDATIONS

### Model Selection
**Recommended**: `codellama:7b-instruct` or `codellama:13b-instruct`
- Good balance of size and performance
- Fast training on 5000 examples
- Excellent code generation quality

### Training Parameters
```yaml
Base Model: codellama:7b-instruct
Dataset: code_prototype_5000.jsonl (5000+ examples)
Steps: 1000-2000
Batch Size: 8
Learning Rate: 2e-5
Epochs: 2-3
```

### Expected Training Time
- **7B model**: ~4-6 hours (CPU) / ~1-2 hours (GPU)
- **13B model**: ~8-12 hours (CPU) / ~2-4 hours (GPU)

### Validation
After fine-tuning, test with:
1. **"Create a registration controller with MongoDB"**  
   → Should output YOUR IMongoDBSettings pattern

2. **"Generate an ERD for an e-commerce system"**  
   → Should output professional multi-entity ERD

3. **"Show the architecture for a microservices app"**  
   → Should output service mesh diagram

4. **"Sequence diagram for user authentication"**  
   → Should output detailed auth flow

---

## 🎓 LEARNING PROGRESSION

### What Happens During Training

**Epochs 1-2**: Basic pattern recognition
- Learns Mermaid syntax
- Learns your MongoDB patterns
- Learns DTO structures

**Epochs 3-5**: Pattern application
- Can generate ERDs for new domains
- Can adapt your code patterns to new features
- Can create correct architecture diagrams

**Epochs 5+**: Generalization
- Creates artifacts matching your style
- Generates code with YOUR naming conventions
- Combines patterns intelligently

---

## 💡 PRO TIPS

### 1. **Review First 100 Examples**
Before training, inspect the JSONL file to verify:
- Mix of artifacts and code
- YOUR patterns in code examples
- Diverse artifact domains

### 2. **Incremental Training**
Start with 1000 examples, test, then expand:
- 1000 examples → Test quality
- 3000 examples → Test diversity
- 5000+ examples → Maximum performance

### 3. **Monitor Loss**
During training, loss should:
- Start high (~2.5-3.0)
- Decrease steadily
- Converge around 0.5-1.0

### 4. **Test After Each Epoch**
Generate sample outputs after each epoch to see improvement

---

## 🔄 MAINTENANCE

### Adding More Examples
To expand beyond 5000:
1. Add more examples to `expanded_artifact_examples.py`
2. Increase `MAX_DATASET_SIZE` to 10000
3. Regenerate dataset

### Domain-Specific Training
To focus on specific domains:
1. Add more ERD examples for that domain
2. Add sequence flows for that workflow
3. Weight those examples higher in dataset

---

## 📝 SUMMARY

**You now have a system that generates 5000+ training examples teaching:**

✅ **100+ artifact patterns** (ERD, architecture, sequence, flowchart)  
✅ **YOUR specific code patterns** (MongoDB, DTOs, Controllers, Services)  
✅ **Professional quality** (correct syntax, realistic examples)  
✅ **Domain diversity** (e-commerce, healthcare, education, social media)  
✅ **Generalization ability** (works with ANY mother project)

**Result**: A fine-tuned model that's an **expert artifact generator** AND **knows your specific coding style** 🎯
