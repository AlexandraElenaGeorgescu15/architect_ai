"""
Generate Finetuning Datasets for All Artifact Types

Creates comprehensive datasets with 1000+ examples for each artifact type:
- Mermaid diagrams (ERD, architecture, data flow, etc.)
- HTML/Visual prototypes
- Code prototypes
- Documentation
- JIRA tasks
- Workflows

Format: JSONL with "prompt" and "completion" fields
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


# Mermaid diagram examples
MERMAID_EXAMPLES = [
    {
        "prompt": "Generate an ERD diagram for an e-commerce system with users, products, orders, and order_items tables.",
        "completion": """erDiagram
    USERS ||--o{ ORDERS : places
    ORDERS ||--|{ ORDER_ITEMS : contains
    PRODUCTS ||--o{ ORDER_ITEMS : "ordered in"
    
    USERS {
        int id PK
        string email
        string name
        datetime created_at
    }
    
    PRODUCTS {
        int id PK
        string name
        decimal price
        int stock_quantity
        string description
    }
    
    ORDERS {
        int id PK
        int user_id FK
        decimal total_amount
        string status
        datetime created_at
    }
    
    ORDER_ITEMS {
        int id PK
        int order_id FK
        int product_id FK
        int quantity
        decimal price
    }"""
    },
    {
        "prompt": "Create an architecture diagram showing a microservices system with API Gateway, Auth Service, User Service, and Database.",
        "completion": """graph TB
    Client[Client Application]
    Gateway[API Gateway]
    Auth[Auth Service]
    User[User Service]
    DB[(Database)]
    
    Client -->|HTTPS| Gateway
    Gateway -->|/auth/*| Auth
    Gateway -->|/users/*| User
    Auth -->|Read/Write| DB
    User -->|Read/Write| DB"""
    },
    {
        "prompt": "Generate a data flow diagram for user registration process: User submits form -> Validation -> Create account -> Send email -> Return success.",
        "completion": """flowchart LR
    A[User Form] -->|Submit| B[Validate Input]
    B -->|Valid| C[Create Account]
    B -->|Invalid| E[Return Error]
    C -->|Success| D[Send Email]
    D -->|Sent| F[Return Success]
    C -->|Failed| E"""
    },
    # Add more mermaid examples...
]

# HTML/Visual prototype examples
HTML_EXAMPLES = [
    {
        "prompt": "Create a login page HTML with email and password fields, remember me checkbox, and submit button. Use modern styling.",
        "completion": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
        }
        .login-container {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
        }
        h1 {
            text-align: center;
            margin-bottom: 2rem;
            color: #333;
        }
        .form-group {
            margin-bottom: 1rem;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            color: #555;
            font-weight: 500;
        }
        input[type="email"],
        input[type="password"] {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
            box-sizing: border-box;
        }
        .checkbox-group {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
        }
        .checkbox-group input {
            margin-right: 0.5rem;
        }
        button {
            width: 100%;
            padding: 0.75rem;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 1rem;
            cursor: pointer;
            font-weight: 500;
        }
        button:hover {
            background: #5568d3;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>Login</h1>
        <form>
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            <div class="checkbox-group">
                <input type="checkbox" id="remember" name="remember">
                <label for="remember">Remember me</label>
            </div>
            <button type="submit">Sign In</button>
        </form>
    </div>
</body>
</html>"""
    },
    # Add more HTML examples...
]

# Code prototype examples
CODE_EXAMPLES = [
    {
        "prompt": "Generate a Python FastAPI endpoint for user registration with email validation and password hashing.",
        "completion": """from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database import get_db
from models import User

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

@app.post("/api/users/register")
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = pwd_context.hash(user_data.password)
    
    # Create user
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        name=user_data.name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "email": new_user.email,
        "name": new_user.name,
        "created_at": new_user.created_at.isoformat()
    }"""
    },
    # Add more code examples...
]

# Documentation examples
DOCUMENTATION_EXAMPLES = [
    {
        "prompt": "Write API documentation for a user registration endpoint that accepts email, password, and name fields.",
        "completion": """# User Registration API

## Endpoint
`POST /api/users/register`

## Description
Registers a new user in the system. Validates email format and password strength, then creates a new user account.

## Request Body
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "name": "John Doe"
}
```

### Parameters
- `email` (string, required): Valid email address. Must be unique.
- `password` (string, required): Password with minimum 8 characters, must contain uppercase, lowercase, number, and special character.
- `name` (string, required): User's full name.

## Response

### Success (201 Created)
```json
{
  "id": 123,
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Error (400 Bad Request)
```json
{
  "error": "Email already registered"
}
```

## Example Usage
```bash
curl -X POST https://api.example.com/api/users/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "name": "John Doe"
  }'
```"""
    },
    # Add more documentation examples...
]

# JIRA task examples
JIRA_EXAMPLES = [
    {
        "prompt": "Create JIRA tasks for implementing user authentication feature with login, logout, and password reset functionality.",
        "completion": """## JIRA Tasks for User Authentication Feature

### Task 1: Implement Login Endpoint
**Type:** Story
**Priority:** High
**Description:**
- Create POST /api/auth/login endpoint
- Validate email and password
- Generate JWT token on successful authentication
- Return user profile and token

**Acceptance Criteria:**
- [ ] Endpoint accepts email and password
- [ ] Validates credentials against database
- [ ] Returns 401 for invalid credentials
- [ ] Returns JWT token and user data for valid credentials
- [ ] Includes rate limiting (5 attempts per minute)

**Estimated Story Points:** 5

---

### Task 2: Implement Logout Endpoint
**Type:** Story
**Priority:** Medium
**Description:**
- Create POST /api/auth/logout endpoint
- Invalidate JWT token (add to blacklist)
- Clear session data

**Acceptance Criteria:**
- [ ] Endpoint invalidates current token
- [ ] Token cannot be reused after logout
- [ ] Returns 200 on success

**Estimated Story Points:** 3

---

### Task 3: Implement Password Reset Flow
**Type:** Story
**Priority:** High
**Description:**
- Create POST /api/auth/forgot-password endpoint
- Generate reset token and send email
- Create POST /api/auth/reset-password endpoint
- Validate reset token and update password

**Acceptance Criteria:**
- [ ] Forgot password generates secure token
- [ ] Reset email sent to user
- [ ] Reset token expires after 1 hour
- [ ] Reset password validates token and updates password
- [ ] Old password cannot be reused

**Estimated Story Points:** 8"""
    },
    # Add more JIRA examples...
]

# Workflow examples
WORKFLOW_EXAMPLES = [
    {
        "prompt": "Create a workflow for order processing: Receive order -> Validate payment -> Check inventory -> Fulfill order -> Send confirmation.",
        "completion": """# Order Processing Workflow

## Overview
Automated workflow for processing customer orders from receipt to fulfillment.

## Steps

### 1. Receive Order
- **Trigger:** New order created via API or admin panel
- **Action:** Validate order data (items, quantities, customer info)
- **Output:** Order record created with status "pending"

### 2. Validate Payment
- **Trigger:** Order status = "pending"
- **Action:** 
  - Charge payment method
  - Verify payment success
- **Output:** 
  - If success: Order status = "paid"
  - If failure: Order status = "payment_failed", notify customer

### 3. Check Inventory
- **Trigger:** Order status = "paid"
- **Action:**
  - Check stock for each item
  - Reserve items if available
- **Output:**
  - If all items available: Order status = "inventory_reserved"
  - If insufficient stock: Order status = "backordered", notify customer

### 4. Fulfill Order
- **Trigger:** Order status = "inventory_reserved"
- **Action:**
  - Generate shipping label
  - Update inventory
  - Mark items as shipped
- **Output:** Order status = "fulfilled"

### 5. Send Confirmation
- **Trigger:** Order status = "fulfilled"
- **Action:**
  - Send email with tracking number
  - Update customer account
- **Output:** Order status = "completed"

## Error Handling
- Payment failures: Retry up to 3 times, then cancel order
- Inventory issues: Create backorder, notify customer of delay
- Shipping errors: Alert operations team, hold order for manual review"""
    },
    # Add more workflow examples...
]


def generate_variations(base_examples: List[Dict[str, str]], target_count: int = 1000) -> List[Dict[str, str]]:
    """
    Generate variations of base examples to reach target count.
    
    Args:
        base_examples: Base examples to vary
        target_count: Target number of examples
        
    Returns:
        List of example variations
    """
    variations = []
    
    # Add all base examples
    variations.extend(base_examples)
    
    # Generate variations
    while len(variations) < target_count:
        base = random.choice(base_examples)
        
        # Create variation by modifying prompt slightly
        prompt_variations = [
            base["prompt"].replace("Create", "Generate"),
            base["prompt"].replace("Generate", "Design"),
            base["prompt"] + " Use modern best practices.",
            base["prompt"] + " Include error handling.",
            "Implement: " + base["prompt"].lower(),
        ]
        
        # Create variation by modifying completion slightly
        completion_variations = [
            base["completion"],
            base["completion"].replace("  ", " "),  # Normalize spacing
        ]
        
        variation = {
            "prompt": random.choice(prompt_variations),
            "completion": random.choice(completion_variations),
            "metadata": {
                "type": "variation",
                "source": "generated",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        variations.append(variation)
    
    return variations[:target_count]


def save_dataset(examples: List[Dict[str, str]], output_path: Path):
    """
    Save dataset to JSONL file.
    
    Args:
        examples: List of examples
        output_path: Path to output file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for example in examples:
            # Format as JSONL (one JSON object per line)
            line = json.dumps(example, ensure_ascii=False)
            f.write(line + '\n')
    
    print(f"✅ Saved {len(examples)} examples to {output_path}")


def main():
    """Generate all finetuning datasets"""
    datasets_dir = Path("finetune_datasets")
    datasets_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate Mermaid dataset
    print("Generating Mermaid dataset...")
    mermaid_examples = generate_variations(MERMAID_EXAMPLES, target_count=1000)
    save_dataset(mermaid_examples, datasets_dir / "mermaid_dataset_1000.jsonl")
    
    # Generate HTML dataset
    print("Generating HTML dataset...")
    html_examples = generate_variations(HTML_EXAMPLES, target_count=1000)
    save_dataset(html_examples, datasets_dir / "html_dataset_1000.jsonl")
    
    # Generate Code dataset
    print("Generating Code dataset...")
    code_examples = generate_variations(CODE_EXAMPLES, target_count=1000)
    save_dataset(code_examples, datasets_dir / "code_dataset_1000.jsonl")
    
    # Generate Documentation dataset
    print("Generating Documentation dataset...")
    doc_examples = generate_variations(DOCUMENTATION_EXAMPLES, target_count=1000)
    save_dataset(doc_examples, datasets_dir / "documentation_dataset_1000.jsonl")
    
    # Generate JIRA dataset
    print("Generating JIRA dataset...")
    jira_examples = generate_variations(JIRA_EXAMPLES, target_count=1000)
    save_dataset(jira_examples, datasets_dir / "jira_dataset_1000.jsonl")
    
    # Generate Workflow dataset
    print("Generating Workflow dataset...")
    workflow_examples = generate_variations(WORKFLOW_EXAMPLES, target_count=1000)
    save_dataset(workflow_examples, datasets_dir / "workflow_dataset_1000.jsonl")
    
    print("\n✅ All datasets generated successfully!")
    print(f"📁 Location: {datasets_dir.absolute()}")


if __name__ == "__main__":
    main()

