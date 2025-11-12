"""Dataset builder tailored for fine-tuning local models on project context."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .finetuning_feedback import feedback_store
from .finetuning_settings import load_finetuning_settings
from ._tool_detector import (
    get_user_project_directories,
    get_user_project_root,
    should_exclude_path,
)

# Import additional training examples from separate modules
try:
    from .training_examples_ruby import RUBY_EXAMPLES
except ImportError:
    RUBY_EXAMPLES = []

try:
    from .training_examples_php import LARAVEL_EXAMPLES
except ImportError:
    LARAVEL_EXAMPLES = []

try:
    from .training_examples_mobile import MOBILE_EXAMPLES
except ImportError:
    MOBILE_EXAMPLES = []

try:
    from .training_examples_testing import TESTING_EXAMPLES
except ImportError:
    TESTING_EXAMPLES = []

# Import expanded artifact examples (100+ examples)
try:
    from .expanded_artifact_examples import ALL_EXPANDED_EXAMPLES
except ImportError:
    ALL_EXPANDED_EXAMPLES = []

# Deferred imports to avoid heavy dependencies at module import time


ANGULAR_COMPONENT_SUFFIX = ".component.ts"
ANGULAR_TEMPLATE_SUFFIX = ".component.html"
ANGULAR_STYLE_SUFFIX = ".component.scss"
ANGULAR_SERVICE_SUFFIX = ".service.ts"
DOTNET_CONTROLLER_SUFFIX = "controller.cs"
DOTNET_DTO_SUFFIX = "dto.cs"
DOTNET_SERVICE_SUFFIX = "service.cs"

MIN_DATASET_SIZE = 3  # Lowered for testing (comprehensive generation happens during training)
DEFAULT_TARGET_EXAMPLES = 1000  # Target 1000+ examples  
MAX_DATASET_SIZE = 6000  # Allow up to 6000 examples
MAX_FILE_BYTES = 200_000

SUPPORTED_DATASET_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".cs",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".html",
    ".scss",
    ".css",
    ".md",
    ".sql",
}

BUILTIN_MERMAID_ARTIFACTS: List[Dict[str, str]] = [
    # === ERD EXAMPLES ===
    {
        "instruction": "Generate a clean ERD diagram for the following entities.",
        "input": "Entities: User (id, email, name), Post (id, title, content, userId), Comment (id, text, postId, userId)",
        "output": (
            "erDiagram\n"
            "    User ||--o{ Post : creates\n"
            "    User ||--o{ Comment : writes\n"
            "    Post ||--o{ Comment : has\n"
            "\n"
            "    User {\n"
            "        int id PK\n"
            "        string email\n"
            "        string name\n"
            "    }\n"
            "\n"
            "    Post {\n"
            "        int id PK\n"
            "        string title\n"
            "        string content\n"
            "        int userId FK\n"
            "    }\n"
            "\n"
            "    Comment {\n"
            "        int id PK\n"
            "        string text\n"
            "        int postId FK\n"
            "        int userId FK\n"
            "    }"
        ),
    },
    {
        "instruction": "Generate an ERD for an e-commerce system.",
        "input": "Requirements: Track customers, orders, products, and order items with proper relationships.",
        "output": (
            "erDiagram\n"
            "    Customer ||--o{ Order : places\n"
            "    Order ||--o{ OrderItem : contains\n"
            "    Product ||--o{ OrderItem : orderedAs\n"
            "\n"
            "    Customer {\n"
            "        int id PK\n"
            "        string email\n"
            "        string name\n"
            "        string address\n"
            "    }\n"
            "\n"
            "    Order {\n"
            "        int id PK\n"
            "        int customerId FK\n"
            "        date orderDate\n"
            "        string status\n"
            "        decimal total\n"
            "    }\n"
            "\n"
            "    Product {\n"
            "        int id PK\n"
            "        string name\n"
            "        string description\n"
            "        decimal price\n"
            "        int stock\n"
            "    }\n"
            "\n"
            "    OrderItem {\n"
            "        int id PK\n"
            "        int orderId FK\n"
            "        int productId FK\n"
            "        int quantity\n"
            "        decimal price\n"
            "    }"
        ),
    },
    # === FLOWCHART EXAMPLES ===
    {
        "instruction": "Create a flowchart for user authentication flow.",
        "input": "System: Login form -> Validate credentials -> Success: Dashboard, Failure: Error message",
        "output": (
            "flowchart TD\n"
            "    A[User Opens App] --> B[Login Form]\n"
            "    B --> C{Valid Credentials?}\n"
            "    C -->|Yes| D[Load User Data]\n"
            "    C -->|No| E[Show Error Message]\n"
            "    D --> F[Navigate to Dashboard]\n"
            "    E --> B"
        ),
    },
    {
        "instruction": "Generate a system architecture flowchart.",
        "input": "Components: Angular Frontend, .NET API, MongoDB Database, Redis Cache",
        "output": (
            "flowchart LR\n"
            "    A[Angular Frontend] --> B[.NET API]\n"
            "    B --> C[MongoDB]\n"
            "    B --> D[Redis Cache]\n"
            "    B --> E[Auth Service]\n"
            "    E --> F[JWT Tokens]"
        ),
    },
    {
        "instruction": "Create a data flow diagram for order processing.",
        "input": "Flow: Customer places order -> Validate inventory -> Process payment -> Confirm order -> Ship",
        "output": (
            "flowchart TD\n"
            "    A[Customer Places Order] --> B{Check Inventory}\n"
            "    B -->|In Stock| C[Process Payment]\n"
            "    B -->|Out of Stock| D[Notify Customer]\n"
            "    C --> E{Payment Success?}\n"
            "    E -->|Yes| F[Confirm Order]\n"
            "    E -->|No| G[Cancel Order]\n"
            "    F --> H[Ship Products]\n"
            "    H --> I[Send Tracking Info]"
        ),
    },
    # === SEQUENCE DIAGRAM EXAMPLES ===
    {
        "instruction": "Generate a sequence diagram for API authentication.",
        "input": "Flow: Client -> API -> Auth Service -> Database, then return JWT token",
        "output": (
            "sequenceDiagram\n"
            "    participant C as Client\n"
            "    participant A as API\n"
            "    participant Auth as Auth Service\n"
            "    participant DB as Database\n"
            "\n"
            "    C->>A: POST /login\n"
            "    A->>Auth: Validate Credentials\n"
            "    Auth->>DB: Query User\n"
            "    DB-->>Auth: User Data\n"
            "    Auth-->>A: Valid\n"
            "    A->>A: Generate JWT\n"
            "    A-->>C: 200 OK + Token"
        ),
    },
    {
        "instruction": "Create a sequence diagram for creating a resource.",
        "input": "Flow: User creates post -> API validates -> Save to DB -> Return success",
        "output": (
            "sequenceDiagram\n"
            "    participant U as User\n"
            "    participant UI as Frontend\n"
            "    participant API as Backend API\n"
            "    participant DB as Database\n"
            "\n"
            "    U->>UI: Fill Post Form\n"
            "    U->>UI: Click Submit\n"
            "    UI->>API: POST /api/posts\n"
            "    API->>API: Validate Data\n"
            "    API->>DB: INSERT INTO posts\n"
            "    DB-->>API: Success\n"
            "    API-->>UI: 201 Created\n"
            "    UI-->>U: Show Success Message"
        ),
    },
    # === API DOCUMENTATION EXAMPLES ===
    {
        "instruction": "Generate API documentation for a REST endpoint.",
        "input": "Endpoint: GET /api/users/{id} - Returns user by ID",
        "output": (
            "## GET /api/users/{id}\n\n"
            "**Description**: Retrieve a user by their ID.\n\n"
            "**Parameters**:\n"
            "- `id` (path, required): User ID (integer)\n\n"
            "**Response**: `200 OK`\n"
            "```json\n"
            "{\n"
            '  "id": 1,\n'
            '  "email": "user@example.com",\n'
            '  "name": "John Doe",\n'
            '  "createdAt": "2024-01-01T00:00:00Z"\n'
            "}\n"
            "```\n\n"
            "**Errors**:\n"
            "- `404 Not Found`: User does not exist\n"
            "- `401 Unauthorized`: Missing or invalid token"
        ),
    },
    {
        "instruction": "Document a POST endpoint with request body.",
        "input": "Endpoint: POST /api/products - Create a new product",
        "output": (
            "## POST /api/products\n\n"
            "**Description**: Create a new product in the catalog.\n\n"
            "**Request Body**:\n"
            "```json\n"
            "{\n"
            '  "name": "Product Name",\n'
            '  "description": "Product description",\n'
            '  "price": 29.99,\n'
            '  "stock": 100\n'
            "}\n"
            "```\n\n"
            "**Response**: `201 Created`\n"
            "```json\n"
            "{\n"
            '  "id": 42,\n'
            '  "name": "Product Name",\n'
            '  "description": "Product description",\n'
            '  "price": 29.99,\n'
            '  "stock": 100,\n'
            '  "createdAt": "2024-01-01T00:00:00Z"\n'
            "}\n"
            "```\n\n"
            "**Validation**:\n"
            "- `name`: Required, 3-100 characters\n"
            "- `price`: Required, must be positive\n"
            "- `stock`: Required, must be >= 0"
        ),
    },
    # === CODE GENERATION EXAMPLES ===
    {
        "instruction": "Generate an Angular service for API calls.",
        "input": "Service: ProductService with methods to get all products and create a product",
        "output": (
            "import { Injectable } from '@angular/core';\n"
            "import { HttpClient } from '@angular/common/http';\n"
            "import { Observable } from 'rxjs';\n"
            "import { Product } from '../models/product';\n"
            "\n"
            "@Injectable({\n"
            "  providedIn: 'root'\n"
            "})\n"
            "export class ProductService {\n"
            "  private apiUrl = '/api/products';\n"
            "\n"
            "  constructor(private http: HttpClient) {}\n"
            "\n"
            "  getProducts(): Observable<Product[]> {\n"
            "    return this.http.get<Product[]>(this.apiUrl);\n"
            "  }\n"
            "\n"
            "  createProduct(product: Product): Observable<Product> {\n"
            "    return this.http.post<Product>(this.apiUrl, product);\n"
            "  }\n"
            "\n"
            "  getProductById(id: number): Observable<Product> {\n"
            "    return this.http.get<Product>(`${this.apiUrl}/${id}`);\n"
            "  }\n"
            "}"
        ),
    },
    {
        "instruction": "Generate a .NET API controller.",
        "input": "Controller: UsersController with GET and POST endpoints",
        "output": (
            "using Microsoft.AspNetCore.Mvc;\n"
            "using MyApp.Models;\n"
            "using MyApp.Services;\n"
            "\n"
            "namespace MyApp.Controllers\n"
            "{\n"
            "    [ApiController]\n"
            '    [Route("api/[controller]")]\n'
            "    public class UsersController : ControllerBase\n"
            "    {\n"
            "        private readonly IUserService _userService;\n"
            "\n"
            "        public UsersController(IUserService userService)\n"
            "        {\n"
            "            _userService = userService;\n"
            "        }\n"
            "\n"
            "        [HttpGet]\n"
            "        public async Task<ActionResult<List<User>>> GetUsers()\n"
            "        {\n"
            "            var users = await _userService.GetAllUsersAsync();\n"
            "            return Ok(users);\n"
            "        }\n"
            "\n"
            '        [HttpGet("{id}")]\n'
            "        public async Task<ActionResult<User>> GetUser(int id)\n"
            "        {\n"
            "            var user = await _userService.GetUserByIdAsync(id);\n"
            "            if (user == null)\n"
            "                return NotFound();\n"
            "            return Ok(user);\n"
            "        }\n"
            "\n"
            "        [HttpPost]\n"
            "        public async Task<ActionResult<User>> CreateUser(UserDto userDto)\n"
            "        {\n"
            "            var user = await _userService.CreateUserAsync(userDto);\n"
            "            return CreatedAtAction(nameof(GetUser), new { id = user.Id }, user);\n"
            "        }\n"
            "    }\n"
            "}"
        ),
    },
    # === JIRA/TASK EXAMPLES ===
    {
        "instruction": "Generate JIRA user stories from requirements.",
        "input": "Feature: User can request a phone swap by selecting phones from a list",
        "output": (
            "## User Story\n\n"
            "**As a** user  \n"
            "**I want** to request a phone swap  \n"
            "**So that** I can exchange my current phone for another available phone  \n\n"
            "### Acceptance Criteria\n\n"
            "**Given** I am logged in  \n"
            "**When** I click \"Request Phone Swap\"  \n"
            "**Then** I should see a modal with:\n"
            "- Dropdown of available phones\n"
            "- Dropdown of my owned phones\n"
            "- Optional comment field\n"
            "- Submit and Cancel buttons\n\n"
            "**Given** I submit a valid swap request  \n"
            "**When** the request is processed  \n"
            "**Then** the request should be saved with status \"Pending\"  \n"
            "**And** I should see a confirmation message\n\n"
            "### Technical Notes\n\n"
            "- Frontend: Angular modal component\n"
            "- Backend: POST /api/phone-swaps endpoint\n"
            "- Validate user owns the offered phone\n"
            "- Store in MongoDB with status field"
        ),
    },
    {
        "instruction": "Create subtasks for a feature implementation.",
        "input": "Feature: Product catalog with search and filter functionality",
        "output": (
            "## Epic: Product Catalog\n\n"
            "### Subtask 1: Create Product Model\n"
            "- Define Product interface/class\n"
            "- Add fields: id, name, description, price, stock, category\n"
            "- Implement validation\n\n"
            "### Subtask 2: Build Product Service\n"
            "- Create ProductService class\n"
            "- Implement CRUD methods\n"
            "- Add search functionality\n"
            "- Add filter by category\n\n"
            "### Subtask 3: Create API Endpoints\n"
            "- GET /api/products (with query params)\n"
            "- GET /api/products/{id}\n"
            "- POST /api/products\n"
            "- PUT /api/products/{id}\n"
            "- DELETE /api/products/{id}\n\n"
            "### Subtask 4: Build Frontend Component\n"
            "- Product list component\n"
            "- Search input with debounce\n"
            "- Category filter dropdown\n"
            "- Product card display\n\n"
            "### Subtask 5: Add Unit Tests\n"
            "- Service layer tests\n"
            "- API endpoint tests\n"
            "- Component tests\n"
            "- Integration tests"
        ),
    },
    # === ARCHITECTURE EXAMPLES ===
    {
        "instruction": "Describe the system architecture.",
        "input": "System: Full-stack web application with Angular, .NET API, and MongoDB",
        "output": (
            "# System Architecture\n\n"
            "## Overview\n"
            "Three-tier architecture with clear separation of concerns.\n\n"
            "## Layers\n\n"
            "### Presentation Layer (Frontend)\n"
            "- **Technology**: Angular 16+\n"
            "- **Responsibilities**: \n"
            "  - User interface rendering\n"
            "  - Form validation\n"
            "  - State management (RxJS)\n"
            "  - HTTP communication with API\n\n"
            "### Application Layer (Backend)\n"
            "- **Technology**: .NET 7 Web API\n"
            "- **Responsibilities**:\n"
            "  - Business logic\n"
            "  - Data validation\n"
            "  - Authentication/Authorization (JWT)\n"
            "  - API endpoint handling\n\n"
            "### Data Layer\n"
            "- **Technology**: MongoDB\n"
            "- **Responsibilities**:\n"
            "  - Data persistence\n"
            "  - Query optimization\n"
            "  - Data integrity\n\n"
            "## Communication Flow\n"
            "1. User interacts with Angular UI\n"
            "2. HTTP request sent to .NET API\n"
            "3. API validates and processes request\n"
            "4. API queries/updates MongoDB\n"
            "5. Response returned to frontend\n"
            "6. UI updated with new data"
        ),
    },
    # === VALIDATION & ERROR HANDLING ===
    {
        "instruction": "Generate input validation code.",
        "input": "Validate user registration form: email, password (8+ chars), name (required)",
        "output": (
            "public class UserRegistrationValidator\n"
            "{\n"
            "    public ValidationResult Validate(UserRegistrationDto dto)\n"
            "    {\n"
            "        var errors = new List<string>();\n"
            "\n"
            "        // Email validation\n"
            "        if (string.IsNullOrWhiteSpace(dto.Email))\n"
            '            errors.Add("Email is required");\n'
            "        else if (!IsValidEmail(dto.Email))\n"
            '            errors.Add("Email format is invalid");\n'
            "\n"
            "        // Password validation\n"
            "        if (string.IsNullOrWhiteSpace(dto.Password))\n"
            '            errors.Add("Password is required");\n'
            "        else if (dto.Password.Length < 8)\n"
            '            errors.Add("Password must be at least 8 characters");\n'
            "\n"
            "        // Name validation\n"
            "        if (string.IsNullOrWhiteSpace(dto.Name))\n"
            '            errors.Add("Name is required");\n'
            "\n"
            "        return new ValidationResult\n"
            "        {\n"
            "            IsValid = errors.Count == 0,\n"
            "            Errors = errors\n"
            "        };\n"
            "    }\n"
            "\n"
            "    private bool IsValidEmail(string email)\n"
            "    {\n"
            "        try\n"
            "        {\n"
            "            var addr = new System.Net.Mail.MailAddress(email);\n"
            "            return addr.Address == email;\n"
            "        }\n"
            "        catch\n"
            "        {\n"
            "            return false;\n"
            "        }\n"
            "    }\n"
            "}"
        ),
    },
    # === MERMAID/HTML CONVERSION ===
    {
        "instruction": "Convert the Mermaid ERD into relational table documentation.",
        "input": (
            "erDiagram\n"
            "  Customer ||--o{ Order : places\n"
            "  Order ||--o{ OrderLine : contains\n"
            "  Product ||--o{ OrderLine : featuredIn\n"
        ),
        "output": (
            "# Tables\n"
            "## Customer\n"
            "- id (UUID, PK)\n"
            "- name (TEXT)\n"
            "## Order\n"
            "- id (UUID, PK)\n"
            "- customer_id (UUID, FK -> Customer.id)\n"
            "## OrderLine\n"
            "- id (UUID, PK)\n"
            "- order_id (UUID, FK -> Order.id)\n"
            "- product_id (UUID, FK -> Product.id)\n"
        ),
    },
    {
        "instruction": "Generate HTML that renders the provided Mermaid flowchart with light and dark theme toggles.",
        "input": (
            "flowchart TD\n"
            "  Start --> Login\n"
            "  Login -->|Success| Dashboard\n"
            "  Login -->|Failure| Error\n"
        ),
        "output": (
            "<section class=\"diagram-wrapper\">\n"
            "  <div class=\"toolbar\">\n"
            "    <button data-theme=\"light\">Light</button>\n"
            "    <button data-theme=\"dark\">Dark</button>\n"
            "  </div>\n"
            "  <div class=\"mermaid\">\n"
            "flowchart TD\n"
            "  Start --> Login\n"
            "  Login -->|Success| Dashboard\n"
            "  Login -->|Failure| Error\n"
            "  </div>\n"
            "</section>"
        ),
    },
    {
        "instruction": "Summarise the following Mermaid sequence diagram into acceptance criteria.",
        "input": (
            "sequenceDiagram\n"
            "  participant U as User\n"
            "  participant A as API\n"
            "  participant DB as Database\n"
            "  U->>A: Submit phone swap\n"
            "  A->>DB: Validate ownership\n"
            "  DB-->>A: Ownership confirmed\n"
            "  A-->>U: Request accepted\n"
        ),
        "output": (
            "- The API must validate that the requester owns the offered phone.\n"
            "- Upon successful validation the service returns HTTP 202.\n"
            "- Failed ownership checks return HTTP 403 with a descriptive message.\n"
        ),
    },
    {
        "instruction": "Given this Mermaid graph, produce a narrative architecture description in markdown.",
        "input": (
            "graph TD\n"
            "  ClientUI --> Gateway\n"
            "  Gateway --> SwapService\n"
            "  SwapService --> MongoDB[(MongoDB)]\n"
            "  SwapService --> NotificationQueue\n"
        ),
        "output": (
            "## Architecture Overview\n"
            "1. ClientUI calls the Gateway to initiate a phone swap.\n"
            "2. Gateway routes the request to SwapService.\n"
            "3. SwapService persists swap requests in MongoDB and enqueues notifications.\n"
        ),
    },
    # === ANGULAR/TYPESCRIPT EXAMPLES ===
    {
        "instruction": "Generate an Angular component for displaying a list of items.",
        "input": "Component: ProductListComponent that fetches and displays products",
        "output": (
            "import { Component, OnInit } from '@angular/core';\n"
            "import { ProductService } from '../../services/product.service';\n"
            "import { Product } from '../../models/product';\n"
            "\n"
            "@Component({\n"
            "  selector: 'app-product-list',\n"
            "  templateUrl: './product-list.component.html',\n"
            "  styleUrls: ['./product-list.component.scss']\n"
            "})\n"
            "export class ProductListComponent implements OnInit {\n"
            "  products: Product[] = [];\n"
            "  loading = false;\n"
            "  error: string | null = null;\n"
            "\n"
            "  constructor(private productService: ProductService) {}\n"
            "\n"
            "  ngOnInit(): void {\n"
            "    this.loadProducts();\n"
            "  }\n"
            "\n"
            "  loadProducts(): void {\n"
            "    this.loading = true;\n"
            "    this.error = null;\n"
            "    this.productService.getProducts().subscribe({\n"
            "      next: (data) => {\n"
            "        this.products = data;\n"
            "        this.loading = false;\n"
            "      },\n"
            "      error: (err) => {\n"
            "        this.error = 'Failed to load products';\n"
            "        this.loading = false;\n"
            "        console.error(err);\n"
            "      }\n"
            "    });\n"
            "  }\n"
            "\n"
            "  deleteProduct(id: number): void {\n"
            "    if (confirm('Delete this product?')) {\n"
            "      this.productService.deleteProduct(id).subscribe(() => {\n"
            "        this.loadProducts();\n"
            "      });\n"
            "    }\n"
            "  }\n"
            "}"
        ),
    },
    {
        "instruction": "Create an Angular modal component for editing data.",
        "input": "Modal: EditUserModal with form fields and submit/cancel buttons",
        "output": (
            "import { Component, Input, Output, EventEmitter } from '@angular/core';\n"
            "import { FormBuilder, FormGroup, Validators } from '@angular/forms';\n"
            "import { User } from '../../models/user';\n"
            "\n"
            "@Component({\n"
            "  selector: 'app-edit-user-modal',\n"
            "  templateUrl: './edit-user-modal.component.html'\n"
            "})\n"
            "export class EditUserModalComponent {\n"
            "  @Input() user: User | null = null;\n"
            "  @Output() save = new EventEmitter<User>();\n"
            "  @Output() cancel = new EventEmitter<void>();\n"
            "\n"
            "  userForm: FormGroup;\n"
            "\n"
            "  constructor(private fb: FormBuilder) {\n"
            "    this.userForm = this.fb.group({\n"
            "      name: ['', [Validators.required, Validators.minLength(2)]],\n"
            "      email: ['', [Validators.required, Validators.email]],\n"
            "      role: ['user', Validators.required]\n"
            "    });\n"
            "  }\n"
            "\n"
            "  ngOnChanges(): void {\n"
            "    if (this.user) {\n"
            "      this.userForm.patchValue(this.user);\n"
            "    }\n"
            "  }\n"
            "\n"
            "  onSubmit(): void {\n"
            "    if (this.userForm.valid) {\n"
            "      this.save.emit(this.userForm.value);\n"
            "    }\n"
            "  }\n"
            "\n"
            "  onCancel(): void {\n"
            "    this.cancel.emit();\n"
            "  }\n"
            "}"
        ),
    },
    # === C#/.NET EXAMPLES ===
    {
        "instruction": "Generate a .NET service class with dependency injection.",
        "input": "Service: ProductService with CRUD operations using repository pattern",
        "output": (
            "using MyApp.Models;\n"
            "using MyApp.Repositories;\n"
            "\n"
            "namespace MyApp.Services\n"
            "{\n"
            "    public interface IProductService\n"
            "    {\n"
            "        Task<List<Product>> GetAllProductsAsync();\n"
            "        Task<Product?> GetProductByIdAsync(int id);\n"
            "        Task<Product> CreateProductAsync(ProductDto dto);\n"
            "        Task<bool> UpdateProductAsync(int id, ProductDto dto);\n"
            "        Task<bool> DeleteProductAsync(int id);\n"
            "    }\n"
            "\n"
            "    public class ProductService : IProductService\n"
            "    {\n"
            "        private readonly IProductRepository _repository;\n"
            "        private readonly ILogger<ProductService> _logger;\n"
            "\n"
            "        public ProductService(IProductRepository repository, ILogger<ProductService> logger)\n"
            "        {\n"
            "            _repository = repository;\n"
            "            _logger = logger;\n"
            "        }\n"
            "\n"
            "        public async Task<List<Product>> GetAllProductsAsync()\n"
            "        {\n"
            "            return await _repository.GetAllAsync();\n"
            "        }\n"
            "\n"
            "        public async Task<Product?> GetProductByIdAsync(int id)\n"
            "        {\n"
            "            return await _repository.GetByIdAsync(id);\n"
            "        }\n"
            "\n"
            "        public async Task<Product> CreateProductAsync(ProductDto dto)\n"
            "        {\n"
            "            var product = new Product\n"
            "            {\n"
            "                Name = dto.Name,\n"
            "                Description = dto.Description,\n"
            "                Price = dto.Price,\n"
            "                Stock = dto.Stock\n"
            "            };\n"
            "\n"
            "            await _repository.AddAsync(product);\n"
            "            _logger.LogInformation($\"Product {product.Id} created\");\n"
            "            return product;\n"
            "        }\n"
            "\n"
            "        public async Task<bool> UpdateProductAsync(int id, ProductDto dto)\n"
            "        {\n"
            "            var product = await _repository.GetByIdAsync(id);\n"
            "            if (product == null) return false;\n"
            "\n"
            "            product.Name = dto.Name;\n"
            "            product.Description = dto.Description;\n"
            "            product.Price = dto.Price;\n"
            "            product.Stock = dto.Stock;\n"
            "\n"
            "            await _repository.UpdateAsync(product);\n"
            "            return true;\n"
            "        }\n"
            "\n"
            "        public async Task<bool> DeleteProductAsync(int id)\n"
            "        {\n"
            "            return await _repository.DeleteAsync(id);\n"
            "        }\n"
            "    }\n"
            "}"
        ),
    },
    {
        "instruction": "Create a .NET DTO with validation attributes.",
        "input": "DTO: UserRegistrationDto with email, password, and name validation",
        "output": (
            "using System.ComponentModel.DataAnnotations;\n"
            "\n"
            "namespace MyApp.Models\n"
            "{\n"
            "    public class UserRegistrationDto\n"
            "    {\n"
            "        [Required(ErrorMessage = \"Email is required\")]\n"
            "        [EmailAddress(ErrorMessage = \"Invalid email format\")]\n"
            "        public string Email { get; set; } = string.Empty;\n"
            "\n"
            "        [Required(ErrorMessage = \"Password is required\")]\n"
            "        [MinLength(8, ErrorMessage = \"Password must be at least 8 characters\")]\n"
            "        [RegularExpression(@\"^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).+$\",\n"
            "            ErrorMessage = \"Password must contain uppercase, lowercase, and number\")]\n"
            "        public string Password { get; set; } = string.Empty;\n"
            "\n"
            "        [Required(ErrorMessage = \"Name is required\")]\n"
            "        [StringLength(100, MinimumLength = 2, ErrorMessage = \"Name must be 2-100 characters\")]\n"
            "        public string Name { get; set; } = string.Empty;\n"
            "\n"
            "        [Phone(ErrorMessage = \"Invalid phone number\")]\n"
            "        public string? PhoneNumber { get; set; }\n"
            "    }\n"
            "}"
        ),
    },
    # === PROTOTYPE GENERATION EXAMPLES ===
    {
        "instruction": "Generate a complete Angular component with HTML and CSS.",
        "input": "Feature: Phone swap request modal with dropdowns for selecting phones",
        "output": (
            "// phone-swap-modal.component.ts\n"
            "import { Component, OnInit } from '@angular/core';\n"
            "import { PhoneService } from '../../services/phone.service';\n"
            "import { Phone } from '../../models/phone';\n"
            "\n"
            "@Component({\n"
            "  selector: 'app-phone-swap-modal',\n"
            "  templateUrl: './phone-swap-modal.component.html',\n"
            "  styleUrls: ['./phone-swap-modal.component.scss']\n"
            "})\n"
            "export class PhoneSwapModalComponent implements OnInit {\n"
            "  availablePhones: Phone[] = [];\n"
            "  myPhones: Phone[] = [];\n"
            "  selectedAvailablePhone: number | null = null;\n"
            "  selectedMyPhone: number | null = null;\n"
            "  comment = '';\n"
            "\n"
            "  constructor(private phoneService: PhoneService) {}\n"
            "\n"
            "  ngOnInit(): void {\n"
            "    this.loadPhones();\n"
            "  }\n"
            "\n"
            "  loadPhones(): void {\n"
            "    this.phoneService.getAvailablePhones().subscribe(phones => {\n"
            "      this.availablePhones = phones;\n"
            "    });\n"
            "    this.phoneService.getMyPhones().subscribe(phones => {\n"
            "      this.myPhones = phones;\n"
            "    });\n"
            "  }\n"
            "\n"
            "  submitRequest(): void {\n"
            "    if (this.selectedAvailablePhone && this.selectedMyPhone) {\n"
            "      const request = {\n"
            "        requestedPhoneId: this.selectedAvailablePhone,\n"
            "        offeredPhoneId: this.selectedMyPhone,\n"
            "        comment: this.comment\n"
            "      };\n"
            "      this.phoneService.createSwapRequest(request).subscribe(() => {\n"
            "        alert('Swap request submitted!');\n"
            "        this.close();\n"
            "      });\n"
            "    }\n"
            "  }\n"
            "\n"
            "  close(): void {\n"
            "    // Close modal logic\n"
            "  }\n"
            "}\n"
            "\n"
            "<!-- phone-swap-modal.component.html -->\n"
            "<div class=\"modal-overlay\">\n"
            "  <div class=\"modal-content\">\n"
            "    <h2>Request Phone Swap</h2>\n"
            "    <div class=\"form-group\">\n"
            "      <label>Phone to Request:</label>\n"
            "      <select [(ngModel)]=\"selectedAvailablePhone\">\n"
            "        <option [value]=\"null\">Select a phone</option>\n"
            "        <option *ngFor=\"let phone of availablePhones\" [value]=\"phone.id\">\n"
            "          {{phone.brand}} {{phone.model}}\n"
            "        </option>\n"
            "      </select>\n"
            "    </div>\n"
            "    <div class=\"form-group\">\n"
            "      <label>Phone to Exchange:</label>\n"
            "      <select [(ngModel)]=\"selectedMyPhone\">\n"
            "        <option [value]=\"null\">Select your phone</option>\n"
            "        <option *ngFor=\"let phone of myPhones\" [value]=\"phone.id\">\n"
            "          {{phone.brand}} {{phone.model}}\n"
            "        </option>\n"
            "      </select>\n"
            "    </div>\n"
            "    <div class=\"form-group\">\n"
            "      <label>Comment (optional):</label>\n"
            "      <textarea [(ngModel)]=\"comment\"></textarea>\n"
            "    </div>\n"
            "    <div class=\"actions\">\n"
            "      <button (click)=\"submitRequest()\" [disabled]=\"!selectedAvailablePhone || !selectedMyPhone\">\n"
            "        Submit Request\n"
            "      </button>\n"
            "      <button (click)=\"close()\">Cancel</button>\n"
            "    </div>\n"
            "  </div>\n"
            "</div>\n"
            "\n"
            "/* phone-swap-modal.component.scss */\n"
            ".modal-overlay {\n"
            "  position: fixed;\n"
            "  top: 0;\n"
            "  left: 0;\n"
            "  right: 0;\n"
            "  bottom: 0;\n"
            "  background: rgba(0, 0, 0, 0.5);\n"
            "  display: flex;\n"
            "  align-items: center;\n"
            "  justify-content: center;\n"
            "}\n"
            "\n"
            ".modal-content {\n"
            "  background: white;\n"
            "  padding: 2rem;\n"
            "  border-radius: 8px;\n"
            "  max-width: 500px;\n"
            "  width: 100%;\n"
            "}\n"
            "\n"
            ".form-group {\n"
            "  margin-bottom: 1rem;\n"
            "}\n"
            "\n"
            "label {\n"
            "  display: block;\n"
            "  margin-bottom: 0.5rem;\n"
            "  font-weight: 600;\n"
            "}\n"
            "\n"
            "select, textarea {\n"
            "  width: 100%;\n"
            "  padding: 0.5rem;\n"
            "  border: 1px solid #ccc;\n"
            "  border-radius: 4px;\n"
            "}\n"
            "\n"
            ".actions {\n"
            "  display: flex;\n"
            "  gap: 1rem;\n"
            "  margin-top: 1.5rem;\n"
            "}\n"
            "\n"
            "button {\n"
            "  padding: 0.5rem 1rem;\n"
            "  border-radius: 4px;\n"
            "  cursor: pointer;\n"
            "}\n"
            "\n"
            "button:first-child {\n"
            "  background: #007bff;\n"
            "  color: white;\n"
            "  border: none;\n"
            "}\n"
            "\n"
            "button:disabled {\n"
            "  opacity: 0.5;\n"
            "  cursor: not-allowed;\n"
            "}"
        ),
    },
    {
        "instruction": "Generate a complete .NET API endpoint with controller and DTO.",
        "input": "Feature: API endpoint to create a phone swap request",
        "output": (
            "// Controllers/PhoneSwapController.cs\n"
            "using Microsoft.AspNetCore.Mvc;\n"
            "using Microsoft.AspNetCore.Authorization;\n"
            "using MyApp.Models;\n"
            "using MyApp.Services;\n"
            "\n"
            "namespace MyApp.Controllers\n"
            "{\n"
            "    [ApiController]\n"
            "    [Route(\"api/[controller]\")]\n"
            "    [Authorize]\n"
            "    public class PhoneSwapController : ControllerBase\n"
            "    {\n"
            "        private readonly IPhoneSwapService _swapService;\n"
            "        private readonly ILogger<PhoneSwapController> _logger;\n"
            "\n"
            "        public PhoneSwapController(IPhoneSwapService swapService, ILogger<PhoneSwapController> logger)\n"
            "        {\n"
            "            _swapService = swapService;\n"
            "            _logger = logger;\n"
            "        }\n"
            "\n"
            "        [HttpPost]\n"
            "        public async Task<ActionResult<PhoneSwapRequest>> CreateSwapRequest(PhoneSwapRequestDto dto)\n"
            "        {\n"
            "            var userId = int.Parse(User.FindFirst(\"userId\")?.Value ?? \"0\");\n"
            "            \n"
            "            // Validate ownership\n"
            "            var ownsPhone = await _swapService.ValidateOwnership(userId, dto.OfferedPhoneId);\n"
            "            if (!ownsPhone)\n"
            "            {\n"
            "                return Forbid(\"You don't own this phone\");\n"
            "            }\n"
            "\n"
            "            var request = await _swapService.CreateSwapRequestAsync(userId, dto);\n"
            "            _logger.LogInformation($\"Swap request {request.Id} created by user {userId}\");\n"
            "            \n"
            "            return CreatedAtAction(nameof(GetSwapRequest), new { id = request.Id }, request);\n"
            "        }\n"
            "\n"
            "        [HttpGet(\"{id}\")]\n"
            "        public async Task<ActionResult<PhoneSwapRequest>> GetSwapRequest(int id)\n"
            "        {\n"
            "            var request = await _swapService.GetSwapRequestAsync(id);\n"
            "            if (request == null)\n"
            "                return NotFound();\n"
            "            return Ok(request);\n"
            "        }\n"
            "    }\n"
            "}\n"
            "\n"
            "// Models/PhoneSwapRequestDto.cs\n"
            "using System.ComponentModel.DataAnnotations;\n"
            "\n"
            "namespace MyApp.Models\n"
            "{\n"
            "    public class PhoneSwapRequestDto\n"
            "    {\n"
            "        [Required]\n"
            "        public int RequestedPhoneId { get; set; }\n"
            "\n"
            "        [Required]\n"
            "        public int OfferedPhoneId { get; set; }\n"
            "\n"
            "        [MaxLength(500)]\n"
            "        public string? Comment { get; set; }\n"
            "    }\n"
            "\n"
            "    public class PhoneSwapRequest\n"
            "    {\n"
            "        public int Id { get; set; }\n"
            "        public int RequesterId { get; set; }\n"
            "        public int RequestedPhoneId { get; set; }\n"
            "        public int OfferedPhoneId { get; set; }\n"
            "        public string Status { get; set; } = \"Pending\";\n"
            "        public string? Comment { get; set; }\n"
            "        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;\n"
            "    }\n"
            "}"
        ),
    },
    # === PYTHON/FLASK EXAMPLES ===
    {
        "instruction": "Generate a Flask API endpoint with validation.",
        "input": "Endpoint: POST /api/users - Create a new user",
        "output": (
            "from flask import Blueprint, request, jsonify\n"
            "from flask_jwt_extended import jwt_required, get_jwt_identity\n"
            "from marshmallow import Schema, fields, validate, ValidationError\n"
            "from models import User, db\n"
            "import logging\n"
            "\n"
            "users_bp = Blueprint('users', __name__)\n"
            "logger = logging.getLogger(__name__)\n"
            "\n"
            "class UserSchema(Schema):\n"
            "    email = fields.Email(required=True)\n"
            "    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))\n"
            "    password = fields.Str(required=True, validate=validate.Length(min=8))\n"
            "    role = fields.Str(validate=validate.OneOf(['user', 'admin']), missing='user')\n"
            "\n"
            "@users_bp.route('/api/users', methods=['POST'])\n"
            "@jwt_required()\n"
            "def create_user():\n"
            "    schema = UserSchema()\n"
            "    try:\n"
            "        data = schema.load(request.json)\n"
            "    except ValidationError as err:\n"
            "        return jsonify({'errors': err.messages}), 400\n"
            "    \n"
            "    # Check if user exists\n"
            "    if User.query.filter_by(email=data['email']).first():\n"
            "        return jsonify({'error': 'Email already exists'}), 409\n"
            "    \n"
            "    user = User(\n"
            "        email=data['email'],\n"
            "        name=data['name'],\n"
            "        role=data['role']\n"
            "    )\n"
            "    user.set_password(data['password'])\n"
            "    \n"
            "    db.session.add(user)\n"
            "    db.session.commit()\n"
            "    \n"
            "    logger.info(f'User {user.id} created by {get_jwt_identity()}')\n"
            "    \n"
            "    return jsonify({\n"
            "        'id': user.id,\n"
            "        'email': user.email,\n"
            "        'name': user.name,\n"
            "        'role': user.role\n"
            "    }), 201"
        ),
    },
    {
        "instruction": "Generate a Python FastAPI endpoint with Pydantic models.",
        "input": "Endpoint: POST /api/products - Create a product with validation",
        "output": (
            "from fastapi import APIRouter, Depends, HTTPException, status\n"
            "from fastapi.security import HTTPBearer\n"
            "from pydantic import BaseModel, Field, validator\n"
            "from typing import Optional\n"
            "from datetime import datetime\n"
            "from sqlalchemy.orm import Session\n"
            "from database import get_db\n"
            "from models import Product\n"
            "import logging\n"
            "\n"
            "router = APIRouter(prefix='/api/products', tags=['products'])\n"
            "security = HTTPBearer()\n"
            "logger = logging.getLogger(__name__)\n"
            "\n"
            "class ProductCreate(BaseModel):\n"
            "    name: str = Field(..., min_length=3, max_length=100)\n"
            "    description: Optional[str] = Field(None, max_length=500)\n"
            "    price: float = Field(..., gt=0)\n"
            "    stock: int = Field(..., ge=0)\n"
            "    category: str\n"
            "    \n"
            "    @validator('price')\n"
            "    def validate_price(cls, v):\n"
            "        if v > 1000000:\n"
            "            raise ValueError('Price too high')\n"
            "        return round(v, 2)\n"
            "\n"
            "class ProductResponse(BaseModel):\n"
            "    id: int\n"
            "    name: str\n"
            "    description: Optional[str]\n"
            "    price: float\n"
            "    stock: int\n"
            "    category: str\n"
            "    created_at: datetime\n"
            "    \n"
            "    class Config:\n"
            "        orm_mode = True\n"
            "\n"
            "@router.post('/', response_model=ProductResponse, status_code=status.HTTP_201_CREATED)\n"
            "async def create_product(\n"
            "    product: ProductCreate,\n"
            "    db: Session = Depends(get_db),\n"
            "    token: str = Depends(security)\n"
            "):\n"
            "    # Check for duplicate\n"
            "    existing = db.query(Product).filter(Product.name == product.name).first()\n"
            "    if existing:\n"
            "        raise HTTPException(\n"
            "            status_code=status.HTTP_409_CONFLICT,\n"
            "            detail='Product with this name already exists'\n"
            "        )\n"
            "    \n"
            "    db_product = Product(**product.dict())\n"
            "    db.add(db_product)\n"
            "    db.commit()\n"
            "    db.refresh(db_product)\n"
            "    \n"
            "    logger.info(f'Product {db_product.id} created')\n"
            "    return db_product"
        ),
    },
    # === NODE.JS/EXPRESS EXAMPLES ===
    {
        "instruction": "Generate an Express.js REST API route with middleware.",
        "input": "Endpoint: POST /api/orders - Create an order with auth and validation",
        "output": (
            "const express = require('express');\n"
            "const { body, validationResult } = require('express-validator');\n"
            "const jwt = require('jsonwebtoken');\n"
            "const Order = require('../models/Order');\n"
            "const logger = require('../utils/logger');\n"
            "\n"
            "const router = express.Router();\n"
            "\n"
            "// Auth middleware\n"
            "const authenticate = (req, res, next) => {\n"
            "  const token = req.headers.authorization?.split(' ')[1];\n"
            "  if (!token) {\n"
            "    return res.status(401).json({ error: 'No token provided' });\n"
            "  }\n"
            "  \n"
            "  try {\n"
            "    const decoded = jwt.verify(token, process.env.JWT_SECRET);\n"
            "    req.user = decoded;\n"
            "    next();\n"
            "  } catch (err) {\n"
            "    return res.status(401).json({ error: 'Invalid token' });\n"
            "  }\n"
            "};\n"
            "\n"
            "// Validation rules\n"
            "const orderValidation = [\n"
            "  body('items').isArray({ min: 1 }).withMessage('Items must be a non-empty array'),\n"
            "  body('items.*.productId').isInt({ gt: 0 }).withMessage('Invalid product ID'),\n"
            "  body('items.*.quantity').isInt({ gt: 0 }).withMessage('Quantity must be positive'),\n"
            "  body('shippingAddress').notEmpty().withMessage('Shipping address required')\n"
            "];\n"
            "\n"
            "router.post('/api/orders', authenticate, orderValidation, async (req, res) => {\n"
            "  const errors = validationResult(req);\n"
            "  if (!errors.isEmpty()) {\n"
            "    return res.status(400).json({ errors: errors.array() });\n"
            "  }\n"
            "  \n"
            "  try {\n"
            "    const { items, shippingAddress } = req.body;\n"
            "    \n"
            "    // Calculate total\n"
            "    const total = await calculateOrderTotal(items);\n"
            "    \n"
            "    const order = new Order({\n"
            "      userId: req.user.id,\n"
            "      items,\n"
            "      shippingAddress,\n"
            "      total,\n"
            "      status: 'pending'\n"
            "    });\n"
            "    \n"
            "    await order.save();\n"
            "    logger.info(`Order ${order._id} created by user ${req.user.id}`);\n"
            "    \n"
            "    res.status(201).json(order);\n"
            "  } catch (err) {\n"
            "    logger.error('Order creation failed:', err);\n"
            "    res.status(500).json({ error: 'Failed to create order' });\n"
            "  }\n"
            "});\n"
            "\n"
            "module.exports = router;"
        ),
    },
    # === REACT EXAMPLES ===
    {
        "instruction": "Generate a React component with hooks and API integration.",
        "input": "Component: UserList with search, pagination, and error handling",
        "output": (
            "import React, { useState, useEffect, useCallback } from 'react';\n"
            "import axios from 'axios';\n"
            "import { useDebounce } from '../hooks/useDebounce';\n"
            "\n"
            "interface User {\n"
            "  id: number;\n"
            "  name: string;\n"
            "  email: string;\n"
            "  role: string;\n"
            "}\n"
            "\n"
            "const UserList: React.FC = () => {\n"
            "  const [users, setUsers] = useState<User[]>([]);\n"
            "  const [loading, setLoading] = useState(false);\n"
            "  const [error, setError] = useState<string | null>(null);\n"
            "  const [searchTerm, setSearchTerm] = useState('');\n"
            "  const [page, setPage] = useState(1);\n"
            "  const [totalPages, setTotalPages] = useState(1);\n"
            "  \n"
            "  const debouncedSearch = useDebounce(searchTerm, 500);\n"
            "  \n"
            "  const fetchUsers = useCallback(async () => {\n"
            "    setLoading(true);\n"
            "    setError(null);\n"
            "    \n"
            "    try {\n"
            "      const response = await axios.get('/api/users', {\n"
            "        params: {\n"
            "          search: debouncedSearch,\n"
            "          page,\n"
            "          limit: 10\n"
            "        }\n"
            "      });\n"
            "      \n"
            "      setUsers(response.data.users);\n"
            "      setTotalPages(response.data.totalPages);\n"
            "    } catch (err) {\n"
            "      setError(err.response?.data?.message || 'Failed to fetch users');\n"
            "    } finally {\n"
            "      setLoading(false);\n"
            "    }\n"
            "  }, [debouncedSearch, page]);\n"
            "  \n"
            "  useEffect(() => {\n"
            "    fetchUsers();\n"
            "  }, [fetchUsers]);\n"
            "  \n"
            "  const handleDelete = async (id: number) => {\n"
            "    if (!confirm('Delete this user?')) return;\n"
            "    \n"
            "    try {\n"
            "      await axios.delete(`/api/users/${id}`);\n"
            "      fetchUsers();\n"
            "    } catch (err) {\n"
            "      alert('Failed to delete user');\n"
            "    }\n"
            "  };\n"
            "  \n"
            "  if (loading) return <div className=\"spinner\">Loading...</div>;\n"
            "  if (error) return <div className=\"error\">{error}</div>;\n"
            "  \n"
            "  return (\n"
            "    <div className=\"user-list\">\n"
            "      <input\n"
            "        type=\"text\"\n"
            "        placeholder=\"Search users...\"\n"
            "        value={searchTerm}\n"
            "        onChange={(e) => setSearchTerm(e.target.value)}\n"
            "        className=\"search-input\"\n"
            "      />\n"
            "      \n"
            "      <table>\n"
            "        <thead>\n"
            "          <tr>\n"
            "            <th>Name</th>\n"
            "            <th>Email</th>\n"
            "            <th>Role</th>\n"
            "            <th>Actions</th>\n"
            "          </tr>\n"
            "        </thead>\n"
            "        <tbody>\n"
            "          {users.map(user => (\n"
            "            <tr key={user.id}>\n"
            "              <td>{user.name}</td>\n"
            "              <td>{user.email}</td>\n"
            "              <td>{user.role}</td>\n"
            "              <td>\n"
            "                <button onClick={() => handleDelete(user.id)}>Delete</button>\n"
            "              </td>\n"
            "            </tr>\n"
            "          ))}\n"
            "        </tbody>\n"
            "      </table>\n"
            "      \n"
            "      <div className=\"pagination\">\n"
            "        <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>\n"
            "          Previous\n"
            "        </button>\n"
            "        <span>Page {page} of {totalPages}</span>\n"
            "        <button onClick={() => setPage(p => p + 1)} disabled={page === totalPages}>\n"
            "          Next\n"
            "        </button>\n"
            "      </div>\n"
            "    </div>\n"
            "  );\n"
            "};\n"
            "\n"
            "export default UserList;"
        ),
    },
    # === VUE EXAMPLES ===
    {
        "instruction": "Generate a Vue 3 component with Composition API.",
        "input": "Component: ProductForm with validation and API submission",
        "output": (
            "<template>\n"
            "  <form @submit.prevent=\"handleSubmit\" class=\"product-form\">\n"
            "    <div class=\"form-group\">\n"
            "      <label for=\"name\">Product Name</label>\n"
            "      <input\n"
            "        id=\"name\"\n"
            "        v-model=\"form.name\"\n"
            "        type=\"text\"\n"
            "        :class=\"{ 'error': errors.name }\"\n"
            "        @blur=\"validateField('name')\"\n"
            "      />\n"
            "      <span v-if=\"errors.name\" class=\"error-message\">{{ errors.name }}</span>\n"
            "    </div>\n"
            "    \n"
            "    <div class=\"form-group\">\n"
            "      <label for=\"price\">Price</label>\n"
            "      <input\n"
            "        id=\"price\"\n"
            "        v-model.number=\"form.price\"\n"
            "        type=\"number\"\n"
            "        step=\"0.01\"\n"
            "        :class=\"{ 'error': errors.price }\"\n"
            "        @blur=\"validateField('price')\"\n"
            "      />\n"
            "      <span v-if=\"errors.price\" class=\"error-message\">{{ errors.price }}</span>\n"
            "    </div>\n"
            "    \n"
            "    <div class=\"form-group\">\n"
            "      <label for=\"description\">Description</label>\n"
            "      <textarea\n"
            "        id=\"description\"\n"
            "        v-model=\"form.description\"\n"
            "        rows=\"4\"\n"
            "      ></textarea>\n"
            "    </div>\n"
            "    \n"
            "    <button type=\"submit\" :disabled=\"loading || !isValid\">\n"
            "      {{ loading ? 'Submitting...' : 'Create Product' }}\n"
            "    </button>\n"
            "    \n"
            "    <div v-if=\"apiError\" class=\"error-message\">{{ apiError }}</div>\n"
            "  </form>\n"
            "</template>\n"
            "\n"
            "<script setup lang=\"ts\">\n"
            "import { ref, computed, reactive } from 'vue';\n"
            "import { useRouter } from 'vue-router';\n"
            "import axios from 'axios';\n"
            "\n"
            "const router = useRouter();\n"
            "\n"
            "const form = reactive({\n"
            "  name: '',\n"
            "  price: 0,\n"
            "  description: ''\n"
            "});\n"
            "\n"
            "const errors = reactive({\n"
            "  name: '',\n"
            "  price: ''\n"
            "});\n"
            "\n"
            "const loading = ref(false);\n"
            "const apiError = ref('');\n"
            "\n"
            "const isValid = computed(() => {\n"
            "  return form.name.length >= 3 && form.price > 0;\n"
            "});\n"
            "\n"
            "const validateField = (field: string) => {\n"
            "  if (field === 'name') {\n"
            "    errors.name = form.name.length < 3 ? 'Name must be at least 3 characters' : '';\n"
            "  } else if (field === 'price') {\n"
            "    errors.price = form.price <= 0 ? 'Price must be positive' : '';\n"
            "  }\n"
            "};\n"
            "\n"
            "const handleSubmit = async () => {\n"
            "  validateField('name');\n"
            "  validateField('price');\n"
            "  \n"
            "  if (!isValid.value) return;\n"
            "  \n"
            "  loading.value = true;\n"
            "  apiError.value = '';\n"
            "  \n"
            "  try {\n"
            "    const response = await axios.post('/api/products', form);\n"
            "    router.push(`/products/${response.data.id}`);\n"
            "  } catch (err: any) {\n"
            "    apiError.value = err.response?.data?.message || 'Failed to create product';\n"
            "  } finally {\n"
            "    loading.value = false;\n"
            "  }\n"
            "};\n"
            "</script>\n"
            "\n"
            "<style scoped>\n"
            ".product-form {\n"
            "  max-width: 500px;\n"
            "  margin: 2rem auto;\n"
            "}\n"
            "\n"
            ".form-group {\n"
            "  margin-bottom: 1rem;\n"
            "}\n"
            "\n"
            "label {\n"
            "  display: block;\n"
            "  margin-bottom: 0.5rem;\n"
            "  font-weight: 600;\n"
            "}\n"
            "\n"
            "input, textarea {\n"
            "  width: 100%;\n"
            "  padding: 0.5rem;\n"
            "  border: 1px solid #ccc;\n"
            "  border-radius: 4px;\n"
            "}\n"
            "\n"
            "input.error, textarea.error {\n"
            "  border-color: #dc3545;\n"
            "}\n"
            "\n"
            ".error-message {\n"
            "  color: #dc3545;\n"
            "  font-size: 0.875rem;\n"
            "  margin-top: 0.25rem;\n"
            "}\n"
            "\n"
            "button {\n"
            "  background: #007bff;\n"
            "  color: white;\n"
            "  padding: 0.75rem 1.5rem;\n"
            "  border: none;\n"
            "  border-radius: 4px;\n"
            "  cursor: pointer;\n"
            "}\n"
            "\n"
            "button:disabled {\n"
            "  opacity: 0.5;\n"
            "  cursor: not-allowed;\n"
            "}\n"
            "</style>"
        ),
    },
    # === JAVA/SPRING BOOT EXAMPLES ===
    {
        "instruction": "Generate a Spring Boot REST controller with validation.",
        "input": "Controller: BookController with CRUD operations",
        "output": (
            "package com.example.library.controller;\n"
            "\n"
            "import com.example.library.dto.BookDTO;\n"
            "import com.example.library.model.Book;\n"
            "import com.example.library.service.BookService;\n"
            "import org.springframework.beans.factory.annotation.Autowired;\n"
            "import org.springframework.http.HttpStatus;\n"
            "import org.springframework.http.ResponseEntity;\n"
            "import org.springframework.validation.annotation.Validated;\n"
            "import org.springframework.web.bind.annotation.*;\n"
            "import javax.validation.Valid;\n"
            "import java.util.List;\n"
            "\n"
            "@RestController\n"
            '@RequestMapping("/api/books")\n'
            "@Validated\n"
            "public class BookController {\n"
            "\n"
            "    @Autowired\n"
            "    private BookService bookService;\n"
            "\n"
            "    @GetMapping\n"
            "    public ResponseEntity<List<Book>> getAllBooks() {\n"
            "        List<Book> books = bookService.findAll();\n"
            "        return ResponseEntity.ok(books);\n"
            "    }\n"
            "\n"
            '    @GetMapping("/{id}")\n'
            "    public ResponseEntity<Book> getBookById(@PathVariable Long id) {\n"
            "        return bookService.findById(id)\n"
            "            .map(ResponseEntity::ok)\n"
            "            .orElse(ResponseEntity.notFound().build());\n"
            "    }\n"
            "\n"
            "    @PostMapping\n"
            "    public ResponseEntity<Book> createBook(@Valid @RequestBody BookDTO bookDTO) {\n"
            "        Book created = bookService.create(bookDTO);\n"
            "        return ResponseEntity.status(HttpStatus.CREATED).body(created);\n"
            "    }\n"
            "\n"
            '    @PutMapping("/{id}")\n'
            "    public ResponseEntity<Book> updateBook(\n"
            "        @PathVariable Long id,\n"
            "        @Valid @RequestBody BookDTO bookDTO\n"
            "    ) {\n"
            "        return bookService.update(id, bookDTO)\n"
            "            .map(ResponseEntity::ok)\n"
            "            .orElse(ResponseEntity.notFound().build());\n"
            "    }\n"
            "\n"
            '    @DeleteMapping("/{id}")\n'
            "    public ResponseEntity<Void> deleteBook(@PathVariable Long id) {\n"
            "        boolean deleted = bookService.delete(id);\n"
            "        return deleted ? ResponseEntity.noContent().build()\n"
            "                       : ResponseEntity.notFound().build();\n"
            "    }\n"
            "}"
        ),
    },
    # === GO EXAMPLES ===
    {
        "instruction": "Generate a Go HTTP handler with validation.",
        "input": "Handler: CreateUser with JSON binding and error handling",
        "output": (
            "package handlers\n"
            "\n"
            "import (\n"
            '    "encoding/json"\n'
            '    "net/http"\n'
            '    "github.com/go-playground/validator/v10"\n'
            '    "myapp/models"\n'
            '    "myapp/services"\n'
            ")\n"
            "\n"
            "type UserHandler struct {\n"
            "    service  *services.UserService\n"
            "    validate *validator.Validate\n"
            "}\n"
            "\n"
            "func NewUserHandler(service *services.UserService) *UserHandler {\n"
            "    return &UserHandler{\n"
            "        service:  service,\n"
            "        validate: validator.New(),\n"
            "    }\n"
            "}\n"
            "\n"
            "type CreateUserRequest struct {\n"
            '    Email    string `json:"email" validate:"required,email"`\n'
            '    Name     string `json:"name" validate:"required,min=2,max=100"`\n'
            '    Password string `json:"password" validate:"required,min=8"`\n'
            "}\n"
            "\n"
            "func (h *UserHandler) CreateUser(w http.ResponseWriter, r *http.Request) {\n"
            "    var req CreateUserRequest\n"
            "    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {\n"
            "        http.Error(w, err.Error(), http.StatusBadRequest)\n"
            "        return\n"
            "    }\n"
            "\n"
            "    if err := h.validate.Struct(req); err != nil {\n"
            "        http.Error(w, err.Error(), http.StatusBadRequest)\n"
            "        return\n"
            "    }\n"
            "\n"
            "    user, err := h.service.Create(r.Context(), &models.User{\n"
            "        Email:    req.Email,\n"
            "        Name:     req.Name,\n"
            "        Password: req.Password,\n"
            "    })\n"
            "\n"
            "    if err != nil {\n"
            '        if err == services.ErrUserExists {\n'
            '            http.Error(w, "User already exists", http.StatusConflict)\n'
            "            return\n"
            "        }\n"
            '        http.Error(w, "Internal server error", http.StatusInternalServerError)\n'
            "        return\n"
            "    }\n"
            "\n"
            '    w.Header().Set("Content-Type", "application/json")\n'
            "    w.WriteStatus(http.StatusCreated)\n"
            "    json.NewEncoder(w).Encode(user)\n"
            "}"
        ),
    },
    # === RUST EXAMPLES ===
    {
        "instruction": "Generate a Rust Actix-web handler with validation.",
        "input": "Handler: POST /api/products with struct validation",
        "output": (
            "use actix_web::{web, HttpResponse, Result};\n"
            "use serde::{Deserialize, Serialize};\n"
            "use validator::Validate;\n"
            "\n"
            "#[derive(Debug, Deserialize, Validate)]\n"
            "pub struct CreateProductRequest {\n"
            '    #[validate(length(min = 3, max = 100))]\n'
            "    pub name: String,\n"
            "    \n"
            '    #[validate(length(max = 500))]\n'
            "    pub description: Option<String>,\n"
            "    \n"
            '    #[validate(range(min = 0.01))]\n'
            "    pub price: f64,\n"
            "    \n"
            '    #[validate(range(min = 0))]\n'
            "    pub stock: i32,\n"
            "}\n"
            "\n"
            "#[derive(Debug, Serialize)]\n"
            "pub struct Product {\n"
            "    pub id: i32,\n"
            "    pub name: String,\n"
            "    pub description: Option<String>,\n"
            "    pub price: f64,\n"
            "    pub stock: i32,\n"
            "}\n"
            "\n"
            "pub async fn create_product(\n"
            "    req: web::Json<CreateProductRequest>,\n"
            "    pool: web::Data<sqlx::PgPool>,\n"
            ") -> Result<HttpResponse> {\n"
            "    // Validate request\n"
            "    req.validate()\n"
            '        .map_err(|e| actix_web::error::ErrorBadRequest(e))?;\n'
            "    \n"
            "    // Insert into database\n"
            "    let product = sqlx::query_as::<_, Product>(\n"
            "        \"INSERT INTO products (name, description, price, stock) \"\n"
            "        \"VALUES ($1, $2, $3, $4) RETURNING *\"\n"
            "    )\n"
            "    .bind(&req.name)\n"
            "    .bind(&req.description)\n"
            "    .bind(req.price)\n"
            "    .bind(req.stock)\n"
            "    .fetch_one(pool.get_ref())\n"
            "    .await\n"
            "    .map_err(|e| {\n"
            '        log::error!("Database error: {:?}", e);\n'
            "        actix_web::error::ErrorInternalServerError(e)\n"
            "    })?;\n"
            "    \n"
            "    Ok(HttpResponse::Created().json(product))\n"
            "}"
        ),
    },
    # === SQL/DATABASE EXAMPLES ===
    {
        "instruction": "Generate SQL schema for a blog system.",
        "input": "Tables: users, posts, comments with proper relationships and indexes",
        "output": (
            "-- Users table\n"
            "CREATE TABLE users (\n"
            "    id SERIAL PRIMARY KEY,\n"
            "    email VARCHAR(255) UNIQUE NOT NULL,\n"
            "    name VARCHAR(100) NOT NULL,\n"
            "    password_hash VARCHAR(255) NOT NULL,\n"
            "    role VARCHAR(20) DEFAULT 'user',\n"
            "    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n"
            "    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
            ");\n"
            "\n"
            "-- Posts table\n"
            "CREATE TABLE posts (\n"
            "    id SERIAL PRIMARY KEY,\n"
            "    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,\n"
            "    title VARCHAR(200) NOT NULL,\n"
            "    content TEXT NOT NULL,\n"
            "    slug VARCHAR(200) UNIQUE NOT NULL,\n"
            "    status VARCHAR(20) DEFAULT 'draft',\n"
            "    published_at TIMESTAMP,\n"
            "    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n"
            "    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
            ");\n"
            "\n"
            "-- Comments table\n"
            "CREATE TABLE comments (\n"
            "    id SERIAL PRIMARY KEY,\n"
            "    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,\n"
            "    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,\n"
            "    content TEXT NOT NULL,\n"
            "    parent_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,\n"
            "    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n"
            "    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
            ");\n"
            "\n"
            "-- Indexes for performance\n"
            "CREATE INDEX idx_posts_user_id ON posts(user_id);\n"
            "CREATE INDEX idx_posts_status ON posts(status);\n"
            "CREATE INDEX idx_posts_published_at ON posts(published_at);\n"
            "CREATE INDEX idx_comments_post_id ON comments(post_id);\n"
            "CREATE INDEX idx_comments_user_id ON comments(user_id);\n"
            "CREATE INDEX idx_comments_parent_id ON comments(parent_id);\n"
            "\n"
            "-- Trigger for updated_at\n"
            "CREATE OR REPLACE FUNCTION update_updated_at_column()\n"
            "RETURNS TRIGGER AS $$\n"
            "BEGIN\n"
            "    NEW.updated_at = CURRENT_TIMESTAMP;\n"
            "    RETURN NEW;\n"
            "END;\n"
            "$$ language 'plpgsql';\n"
            "\n"
            "CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users\n"
            "FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();\n"
            "\n"
            "CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts\n"
            "FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();\n"
            "\n"
            "CREATE TRIGGER update_comments_updated_at BEFORE UPDATE ON comments\n"
            "FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();"
        ),
    },
    # === DOCKER EXAMPLES ===
    {
        "instruction": "Generate a Dockerfile for a Node.js application.",
        "input": "Multi-stage build with production optimization",
        "output": (
            "# Build stage\n"
            "FROM node:18-alpine AS builder\n"
            "\n"
            "WORKDIR /app\n"
            "\n"
            "# Copy package files\n"
            "COPY package*.json ./\n"
            "\n"
            "# Install dependencies\n"
            "RUN npm ci --only=production && \\\n"
            "    npm cache clean --force\n"
            "\n"
            "# Copy source code\n"
            "COPY . .\n"
            "\n"
            "# Build application\n"
            "RUN npm run build\n"
            "\n"
            "# Production stage\n"
            "FROM node:18-alpine\n"
            "\n"
            "# Add non-root user\n"
            "RUN addgroup -g 1001 -S nodejs && \\\n"
            "    adduser -S nodejs -u 1001\n"
            "\n"
            "WORKDIR /app\n"
            "\n"
            "# Copy from builder\n"
            "COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist\n"
            "COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules\n"
            "COPY --from=builder --chown=nodejs:nodejs /app/package*.json ./\n"
            "\n"
            "# Switch to non-root user\n"
            "USER nodejs\n"
            "\n"
            "# Expose port\n"
            "EXPOSE 3000\n"
            "\n"
            "# Health check\n"
            'HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \\\n'
            '  CMD node -e "require(\'http\').get(\'http://localhost:3000/health\', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"\n'
            "\n"
            "# Start application\n"
            'CMD ["node", "dist/server.js"]'
        ),
    },
    # === KUBERNETES EXAMPLES ===
    {
        "instruction": "Generate Kubernetes deployment and service manifests.",
        "input": "Deployment: web-app with 3 replicas, health checks, and ConfigMap",
        "output": (
            "apiVersion: v1\n"
            "kind: ConfigMap\n"
            "metadata:\n"
            "  name: web-app-config\n"
            "data:\n"
            "  API_URL: https://api.example.com\n"
            "  LOG_LEVEL: info\n"
            "---\n"
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            "  name: web-app\n"
            "  labels:\n"
            "    app: web-app\n"
            "spec:\n"
            "  replicas: 3\n"
            "  selector:\n"
            "    matchLabels:\n"
            "      app: web-app\n"
            "  template:\n"
            "    metadata:\n"
            "      labels:\n"
            "        app: web-app\n"
            "    spec:\n"
            "      containers:\n"
            "      - name: web-app\n"
            "        image: myorg/web-app:1.0.0\n"
            "        ports:\n"
            "        - containerPort: 3000\n"
            "          name: http\n"
            "        envFrom:\n"
            "        - configMapRef:\n"
            "            name: web-app-config\n"
            "        resources:\n"
            "          requests:\n"
            "            memory: \"128Mi\"\n"
            "            cpu: \"100m\"\n"
            "          limits:\n"
            "            memory: \"256Mi\"\n"
            "            cpu: \"200m\"\n"
            "        livenessProbe:\n"
            "          httpGet:\n"
            "            path: /health\n"
            "            port: 3000\n"
            "          initialDelaySeconds: 30\n"
            "          periodSeconds: 10\n"
            "        readinessProbe:\n"
            "          httpGet:\n"
            "            path: /ready\n"
            "            port: 3000\n"
            "          initialDelaySeconds: 5\n"
            "          periodSeconds: 5\n"
            "---\n"
            "apiVersion: v1\n"
            "kind: Service\n"
            "metadata:\n"
            "  name: web-app-service\n"
            "spec:\n"
            "  selector:\n"
            "    app: web-app\n"
            "  ports:\n"
            "  - protocol: TCP\n"
            "    port: 80\n"
            "    targetPort: 3000\n"
            "  type: LoadBalancer"
        ),
    },
    # === TESTING EXAMPLES ===
    {
        "instruction": "Generate unit tests for a Python service.",
        "input": "Tests: UserService with mocked database",
        "output": (
            "import pytest\n"
            "from unittest.mock import Mock, patch\n"
            "from services.user_service import UserService\n"
            "from models.user import User\n"
            "\n"
            "@pytest.fixture\n"
            "def mock_db():\n"
            "    return Mock()\n"
            "\n"
            "@pytest.fixture\n"
            "def user_service(mock_db):\n"
            "    return UserService(mock_db)\n"
            "\n"
            "class TestUserService:\n"
            "    def test_create_user_success(self, user_service, mock_db):\n"
            "        # Arrange\n"
            "        user_data = {\n"
            "            'email': 'test@example.com',\n"
            "            'name': 'Test User',\n"
            "            'password': 'password123'\n"
            "        }\n"
            "        mock_db.query.return_value.filter_by.return_value.first.return_value = None\n"
            "        \n"
            "        # Act\n"
            "        result = user_service.create_user(user_data)\n"
            "        \n"
            "        # Assert\n"
            "        assert result.email == user_data['email']\n"
            "        assert result.name == user_data['name']\n"
            "        mock_db.session.add.assert_called_once()\n"
            "        mock_db.session.commit.assert_called_once()\n"
            "    \n"
            "    def test_create_user_duplicate_email(self, user_service, mock_db):\n"
            "        # Arrange\n"
            "        user_data = {'email': 'test@example.com', 'name': 'Test', 'password': 'pass'}\n"
            "        existing_user = User(email='test@example.com')\n"
            "        mock_db.query.return_value.filter_by.return_value.first.return_value = existing_user\n"
            "        \n"
            "        # Act & Assert\n"
            "        with pytest.raises(ValueError, match='Email already exists'):\n"
            "            user_service.create_user(user_data)\n"
            "    \n"
            "    def test_get_user_by_id(self, user_service, mock_db):\n"
            "        # Arrange\n"
            "        user_id = 1\n"
            "        expected_user = User(id=user_id, email='test@example.com', name='Test')\n"
            "        mock_db.query.return_value.filter_by.return_value.first.return_value = expected_user\n"
            "        \n"
            "        # Act\n"
            "        result = user_service.get_user_by_id(user_id)\n"
            "        \n"
            "        # Assert\n"
            "        assert result == expected_user\n"
            "        mock_db.query.assert_called_with(User)\n"
            "    \n"
            "    @patch('services.user_service.hash_password')\n"
            "    def test_password_hashing(self, mock_hash, user_service, mock_db):\n"
            "        # Arrange\n"
            "        mock_hash.return_value = 'hashed_password'\n"
            "        user_data = {'email': 'test@example.com', 'name': 'Test', 'password': 'plaintext'}\n"
            "        mock_db.query.return_value.filter_by.return_value.first.return_value = None\n"
            "        \n"
            "        # Act\n"
            "        user_service.create_user(user_data)\n"
            "        \n"
            "        # Assert\n"
            "        mock_hash.assert_called_once_with('plaintext')"
        ),
    },
    # === MORE DIAGRAM EXAMPLES ===
    {
        "instruction": "Generate a class diagram for a library system.",
        "input": "Classes: Book, Author, Member, Loan with relationships",
        "output": (
            "classDiagram\n"
            "    class Book {\n"
            "        +int id\n"
            "        +string title\n"
            "        +string isbn\n"
            "        +int authorId\n"
            "        +boolean available\n"
            "        +checkOut()\n"
            "        +checkIn()\n"
            "    }\n"
            "    \n"
            "    class Author {\n"
            "        +int id\n"
            "        +string name\n"
            "        +string bio\n"
            "        +getBooks()\n"
            "    }\n"
            "    \n"
            "    class Member {\n"
            "        +int id\n"
            "        +string name\n"
            "        +string email\n"
            "        +date joinDate\n"
            "        +borrowBook(Book book)\n"
            "        +returnBook(Book book)\n"
            "    }\n"
            "    \n"
            "    class Loan {\n"
            "        +int id\n"
            "        +int bookId\n"
            "        +int memberId\n"
            "        +date loanDate\n"
            "        +date dueDate\n"
            "        +date returnDate\n"
            "        +calculateFine()\n"
            "    }\n"
            "    \n"
            "    Author \"1\" --> \"*\" Book : writes\n"
            "    Member \"1\" --> \"*\" Loan : has\n"
            "    Book \"1\" --> \"*\" Loan : borrowed_as\n"
        ),
    },
    {
        "instruction": "Generate a state diagram for order processing.",
        "input": "States: pending, processing, shipped, delivered, cancelled",
        "output": (
            "stateDiagram-v2\n"
            "    [*] --> Pending\n"
            "    \n"
            "    Pending --> Processing : confirm_payment\n"
            "    Pending --> Cancelled : payment_failed\n"
            "    Pending --> Cancelled : user_cancelled\n"
            "    \n"
            "    Processing --> Shipped : items_packed\n"
            "    Processing --> Cancelled : out_of_stock\n"
            "    \n"
            "    Shipped --> Delivered : delivery_confirmed\n"
            "    Shipped --> Processing : returned\n"
            "    \n"
            "    Delivered --> [*]\n"
            "    Cancelled --> [*]\n"
            "    \n"
            "    note right of Processing\n"
            "        Inventory is reserved\n"
            "        Payment is captured\n"
            "    end note\n"
            "    \n"
            "    note right of Shipped\n"
            "        Tracking number assigned\n"
            "        Customer notified\n"
            "    end note"
        ),
    },
    {
        "instruction": "Generate a Gantt chart for project timeline.",
        "input": "Project: Web app development with phases",
        "output": (
            "gantt\n"
            "    title Web Application Development Timeline\n"
            "    dateFormat YYYY-MM-DD\n"
            "    \n"
            "    section Planning\n"
            "    Requirements Gathering       :done, req, 2024-01-01, 2w\n"
            "    System Design               :done, design, after req, 2w\n"
            "    \n"
            "    section Development\n"
            "    Backend API                 :active, backend, 2024-02-01, 4w\n"
            "    Frontend UI                 :frontend, after backend, 4w\n"
            "    Database Setup              :db, 2024-02-01, 1w\n"
            "    \n"
            "    section Testing\n"
            "    Unit Tests                  :test1, after frontend, 1w\n"
            "    Integration Tests           :test2, after test1, 1w\n"
            "    User Acceptance Testing     :uat, after test2, 1w\n"
            "    \n"
            "    section Deployment\n"
            "    Production Setup            :deploy, after uat, 3d\n"
            "    Go Live                     :milestone, after deploy, 1d"
        ),
    },
    # === GENERIC CRUD PATTERNS (Universal) ===
    {
        "instruction": "Generate a generic REST API controller with full CRUD operations.",
        "input": "Entity: Item with standard CRUD endpoints",
        "output": (
            "// Generic CRUD Controller Pattern\n"
            "@RestController\n"
            '@RequestMapping("/api/items")\n'
            "public class ItemController {\n"
            "    private final ItemService service;\n"
            "\n"
            "    public ItemController(ItemService service) {\n"
            "        this.service = service;\n"
            "    }\n"
            "\n"
            "    @GetMapping\n"
            "    public List<Item> getAll() {\n"
            "        return service.findAll();\n"
            "    }\n"
            "\n"
            '    @GetMapping("/{id}")\n'
            "    public Item getById(@PathVariable Long id) {\n"
            "        return service.findById(id)\n"
            "            .orElseThrow(() -> new NotFoundException(\"Item not found\"));\n"
            "    }\n"
            "\n"
            "    @PostMapping\n"
            "    public Item create(@Valid @RequestBody ItemDto dto) {\n"
            "        return service.create(dto);\n"
            "    }\n"
            "\n"
            '    @PutMapping("/{id}")\n'
            "    public Item update(@PathVariable Long id, @Valid @RequestBody ItemDto dto) {\n"
            "        return service.update(id, dto);\n"
            "    }\n"
            "\n"
            '    @DeleteMapping("/{id}")\n'
            "    public void delete(@PathVariable Long id) {\n"
            "        service.delete(id);\n"
            "    }\n"
            "}"
        ),
    },
    {
        "instruction": "Generate pagination and filtering utilities.",
        "input": "Generic pagination with page, size, and sort parameters",
        "output": (
            "// Pagination Utility\n"
            "export interface PaginationParams {\n"
            "  page: number;\n"
            "  size: number;\n"
            "  sort?: string;\n"
            "  order?: 'asc' | 'desc';\n"
            "}\n"
            "\n"
            "export interface PaginatedResponse<T> {\n"
            "  data: T[];\n"
            "  total: number;\n"
            "  page: number;\n"
            "  totalPages: number;\n"
            "}\n"
            "\n"
            "export class PaginationService {\n"
            "  static paginate<T>(\n"
            "    items: T[],\n"
            "    params: PaginationParams\n"
            "  ): PaginatedResponse<T> {\n"
            "    const { page, size, sort, order } = params;\n"
            "    \n"
            "    // Sort if requested\n"
            "    let sortedItems = [...items];\n"
            "    if (sort) {\n"
            "      sortedItems.sort((a, b) => {\n"
            "        const aVal = a[sort];\n"
            "        const bVal = b[sort];\n"
            "        const comparison = aVal > bVal ? 1 : aVal < bVal ? -1 : 0;\n"
            "        return order === 'desc' ? -comparison : comparison;\n"
            "      });\n"
            "    }\n"
            "    \n"
            "    // Paginate\n"
            "    const start = (page - 1) * size;\n"
            "    const end = start + size;\n"
            "    const data = sortedItems.slice(start, end);\n"
            "    \n"
            "    return {\n"
            "      data,\n"
            "      total: items.length,\n"
            "      page,\n"
            "      totalPages: Math.ceil(items.length / size)\n"
            "    };\n"
            "  }\n"
            "}"
        ),
    },
    # === ERROR HANDLING PATTERNS ===
    {
        "instruction": "Generate a global error handler for web applications.",
        "input": "Error handler: Catch all errors, log them, and return user-friendly messages",
        "output": (
            "// Global Error Handler\n"
            "@ControllerAdvice\n"
            "public class GlobalExceptionHandler {\n"
            "\n"
            "    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);\n"
            "\n"
            "    @ExceptionHandler(NotFoundException.class)\n"
            "    public ResponseEntity<ErrorResponse> handleNotFound(NotFoundException ex) {\n"
            "        log.warn(\"Resource not found: {}\", ex.getMessage());\n"
            "        return ResponseEntity\n"
            "            .status(HttpStatus.NOT_FOUND)\n"
            "            .body(new ErrorResponse(\"NOT_FOUND\", ex.getMessage()));\n"
            "    }\n"
            "\n"
            "    @ExceptionHandler(ValidationException.class)\n"
            "    public ResponseEntity<ErrorResponse> handleValidation(ValidationException ex) {\n"
            "        log.warn(\"Validation error: {}\", ex.getMessage());\n"
            "        return ResponseEntity\n"
            "            .status(HttpStatus.BAD_REQUEST)\n"
            "            .body(new ErrorResponse(\"VALIDATION_ERROR\", ex.getMessage()));\n"
            "    }\n"
            "\n"
            "    @ExceptionHandler(Exception.class)\n"
            "    public ResponseEntity<ErrorResponse> handleGeneral(Exception ex) {\n"
            "        log.error(\"Unexpected error\", ex);\n"
            "        return ResponseEntity\n"
            "            .status(HttpStatus.INTERNAL_SERVER_ERROR)\n"
            "            .body(new ErrorResponse(\"INTERNAL_ERROR\", \"An unexpected error occurred\"));\n"
            "    }\n"
            "\n"
            "    @Data\n"
            "    public static class ErrorResponse {\n"
            "        private final String code;\n"
            "        private final String message;\n"
            "        private final long timestamp = System.currentTimeMillis();\n"
            "    }\n"
            "}"
        ),
    },
    # === AUTHENTICATION/AUTHORIZATION PATTERNS ===
    {
        "instruction": "Generate JWT authentication middleware.",
        "input": "Middleware: Validate JWT tokens on protected routes",
        "output": (
            "// JWT Authentication Middleware\n"
            "import jwt from 'jsonwebtoken';\n"
            "\n"
            "export const authenticateToken = (req, res, next) => {\n"
            "  const authHeader = req.headers['authorization'];\n"
            "  const token = authHeader && authHeader.split(' ')[1];\n"
            "\n"
            "  if (!token) {\n"
            "    return res.status(401).json({ error: 'Access token required' });\n"
            "  }\n"
            "\n"
            "  try {\n"
            "    const user = jwt.verify(token, process.env.JWT_SECRET);\n"
            "    req.user = user;\n"
            "    next();\n"
            "  } catch (err) {\n"
            "    return res.status(403).json({ error: 'Invalid or expired token' });\n"
            "  }\n"
            "};\n"
            "\n"
            "export const authorize = (...roles) => {\n"
            "  return (req, res, next) => {\n"
            "    if (!req.user) {\n"
            "      return res.status(401).json({ error: 'Not authenticated' });\n"
            "    }\n"
            "\n"
            "    if (!roles.includes(req.user.role)) {\n"
            "      return res.status(403).json({ error: 'Insufficient permissions' });\n"
            "    }\n"
            "\n"
            "    next();\n"
            "  };\n"
            "};"
        ),
    },
    # === CACHING PATTERNS ===
    {
        "instruction": "Generate a caching service with TTL and invalidation.",
        "input": "Service: In-memory cache with time-to-live and manual invalidation",
        "output": (
            "// Generic Caching Service\n"
            "export class CacheService<T> {\n"
            "  private cache: Map<string, { data: T; expiry: number }> = new Map();\n"
            "  private defaultTTL: number;\n"
            "\n"
            "  constructor(defaultTTLSeconds: number = 300) {\n"
            "    this.defaultTTL = defaultTTLSeconds * 1000;\n"
            "  }\n"
            "\n"
            "  set(key: string, value: T, ttl?: number): void {\n"
            "    const expiry = Date.now() + (ttl ? ttl * 1000 : this.defaultTTL);\n"
            "    this.cache.set(key, { data: value, expiry });\n"
            "  }\n"
            "\n"
            "  get(key: string): T | null {\n"
            "    const entry = this.cache.get(key);\n"
            "    \n"
            "    if (!entry) return null;\n"
            "    \n"
            "    if (Date.now() > entry.expiry) {\n"
            "      this.cache.delete(key);\n"
            "      return null;\n"
            "    }\n"
            "    \n"
            "    return entry.data;\n"
            "  }\n"
            "\n"
            "  invalidate(key: string): void {\n"
            "    this.cache.delete(key);\n"
            "  }\n"
            "\n"
            "  invalidatePattern(pattern: string): void {\n"
            "    const regex = new RegExp(pattern);\n"
            "    for (const key of this.cache.keys()) {\n"
            "      if (regex.test(key)) {\n"
            "        this.cache.delete(key);\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "\n"
            "  clear(): void {\n"
            "    this.cache.clear();\n"
            "  }\n"
            "\n"
            "  size(): number {\n"
            "    return this.cache.size;\n"
            "  }\n"
            "}"
        ),
    },
    # === LOGGING PATTERNS ===
    {
        "instruction": "Generate a structured logging utility.",
        "input": "Logger: Structured logs with levels, context, and metadata",
        "output": (
            "// Structured Logger\n"
            "export enum LogLevel {\n"
            "  DEBUG = 'DEBUG',\n"
            "  INFO = 'INFO',\n"
            "  WARN = 'WARN',\n"
            "  ERROR = 'ERROR'\n"
            "}\n"
            "\n"
            "export class Logger {\n"
            "  private context: string;\n"
            "\n"
            "  constructor(context: string) {\n"
            "    this.context = context;\n"
            "  }\n"
            "\n"
            "  private log(level: LogLevel, message: string, metadata?: any): void {\n"
            "    const logEntry = {\n"
            "      timestamp: new Date().toISOString(),\n"
            "      level,\n"
            "      context: this.context,\n"
            "      message,\n"
            "      ...metadata\n"
            "    };\n"
            "\n"
            "    const output = JSON.stringify(logEntry);\n"
            "\n"
            "    switch (level) {\n"
            "      case LogLevel.DEBUG:\n"
            "        console.debug(output);\n"
            "        break;\n"
            "      case LogLevel.INFO:\n"
            "        console.info(output);\n"
            "        break;\n"
            "      case LogLevel.WARN:\n"
            "        console.warn(output);\n"
            "        break;\n"
            "      case LogLevel.ERROR:\n"
            "        console.error(output);\n"
            "        break;\n"
            "    }\n"
            "  }\n"
            "\n"
            "  debug(message: string, metadata?: any): void {\n"
            "    this.log(LogLevel.DEBUG, message, metadata);\n"
            "  }\n"
            "\n"
            "  info(message: string, metadata?: any): void {\n"
            "    this.log(LogLevel.INFO, message, metadata);\n"
            "  }\n"
            "\n"
            "  warn(message: string, metadata?: any): void {\n"
            "    this.log(LogLevel.WARN, message, metadata);\n"
            "  }\n"
            "\n"
            "  error(message: string, error?: Error, metadata?: any): void {\n"
            "    this.log(LogLevel.ERROR, message, {\n"
            "      ...metadata,\n"
            "      error: error ? {\n"
            "        message: error.message,\n"
            "        stack: error.stack\n"
            "      } : undefined\n"
            "    });\n"
            "  }\n"
            "}"
        ),
    },
    # === REPOSITORY PATTERN ===
    {
        "instruction": "Generate a generic repository pattern implementation.",
        "input": "Repository: Base repository with common database operations",
        "output": (
            "// Generic Repository Pattern\n"
            "public interface IRepository<T, ID> {\n"
            "    Task<T?> FindByIdAsync(ID id);\n"
            "    Task<IEnumerable<T>> FindAllAsync();\n"
            "    Task<T> CreateAsync(T entity);\n"
            "    Task<T> UpdateAsync(T entity);\n"
            "    Task<bool> DeleteAsync(ID id);\n"
            "    Task<bool> ExistsAsync(ID id);\n"
            "}\n"
            "\n"
            "public abstract class BaseRepository<T, ID> : IRepository<T, ID> where T : class {\n"
            "    protected readonly DbContext _context;\n"
            "    protected readonly DbSet<T> _dbSet;\n"
            "    protected readonly ILogger<BaseRepository<T, ID>> _logger;\n"
            "\n"
            "    protected BaseRepository(DbContext context, ILogger<BaseRepository<T, ID>> logger) {\n"
            "        _context = context;\n"
            "        _dbSet = context.Set<T>();\n"
            "        _logger = logger;\n"
            "    }\n"
            "\n"
            "    public virtual async Task<T?> FindByIdAsync(ID id) {\n"
            "        return await _dbSet.FindAsync(id);\n"
            "    }\n"
            "\n"
            "    public virtual async Task<IEnumerable<T>> FindAllAsync() {\n"
            "        return await _dbSet.ToListAsync();\n"
            "    }\n"
            "\n"
            "    public virtual async Task<T> CreateAsync(T entity) {\n"
            "        await _dbSet.AddAsync(entity);\n"
            "        await _context.SaveChangesAsync();\n"
            "        _logger.LogInformation(\"Entity created: {Entity}\", entity);\n"
            "        return entity;\n"
            "    }\n"
            "\n"
            "    public virtual async Task<T> UpdateAsync(T entity) {\n"
            "        _dbSet.Update(entity);\n"
            "        await _context.SaveChangesAsync();\n"
            "        _logger.LogInformation(\"Entity updated: {Entity}\", entity);\n"
            "        return entity;\n"
            "    }\n"
            "\n"
            "    public virtual async Task<bool> DeleteAsync(ID id) {\n"
            "        var entity = await FindByIdAsync(id);\n"
            "        if (entity == null) return false;\n"
            "        _dbSet.Remove(entity);\n"
            "        await _context.SaveChangesAsync();\n"
            "        _logger.LogInformation(\"Entity deleted: ID {Id}\", id);\n"
            "        return true;\n"
            "    }\n"
            "\n"
            "    public virtual async Task<bool> ExistsAsync(ID id) {\n"
            "        return await FindByIdAsync(id) != null;\n"
            "    }\n"
            "}"
        ),
    },
    # === API CLIENT PATTERNS ===
    {
        "instruction": "Generate a generic HTTP client wrapper with retry logic.",
        "input": "Client: Reusable HTTP client with automatic retries and error handling",
        "output": (
            "// Generic API Client\n"
            "export class ApiClient {\n"
            "  private baseURL: string;\n"
            "  private maxRetries: number;\n"
            "  private retryDelay: number;\n"
            "\n"
            "  constructor(baseURL: string, maxRetries = 3, retryDelay = 1000) {\n"
            "    this.baseURL = baseURL;\n"
            "    this.maxRetries = maxRetries;\n"
            "    this.retryDelay = retryDelay;\n"
            "  }\n"
            "\n"
            "  private async request<T>(\n"
            "    endpoint: string,\n"
            "    options: RequestInit,\n"
            "    attempt = 1\n"
            "  ): Promise<T> {\n"
            "    try {\n"
            "      const response = await fetch(`${this.baseURL}${endpoint}`, options);\n"
            "\n"
            "      if (!response.ok) {\n"
            "        if (response.status >= 500 && attempt < this.maxRetries) {\n"
            "          await this.delay(this.retryDelay * attempt);\n"
            "          return this.request<T>(endpoint, options, attempt + 1);\n"
            "        }\n"
            "        throw new Error(`HTTP ${response.status}: ${response.statusText}`);\n"
            "      }\n"
            "\n"
            "      return await response.json();\n"
            "    } catch (error) {\n"
            "      if (attempt < this.maxRetries) {\n"
            "        await this.delay(this.retryDelay * attempt);\n"
            "        return this.request<T>(endpoint, options, attempt + 1);\n"
            "      }\n"
            "      throw error;\n"
            "    }\n"
            "  }\n"
            "\n"
            "  private delay(ms: number): Promise<void> {\n"
            "    return new Promise(resolve => setTimeout(resolve, ms));\n"
            "  }\n"
            "\n"
            "  async get<T>(endpoint: string): Promise<T> {\n"
            "    return this.request<T>(endpoint, { method: 'GET' });\n"
            "  }\n"
            "\n"
            "  async post<T>(endpoint: string, data: any): Promise<T> {\n"
            "    return this.request<T>(endpoint, {\n"
            "      method: 'POST',\n"
            "      headers: { 'Content-Type': 'application/json' },\n"
            "      body: JSON.stringify(data)\n"
            "    });\n"
            "  }\n"
            "\n"
            "  async put<T>(endpoint: string, data: any): Promise<T> {\n"
            "    return this.request<T>(endpoint, {\n"
            "      method: 'PUT',\n"
            "      headers: { 'Content-Type': 'application/json' },\n"
            "      body: JSON.stringify(data)\n"
            "    });\n"
            "  }\n"
            "\n"
            "  async delete<T>(endpoint: string): Promise<T> {\n"
            "    return this.request<T>(endpoint, { method: 'DELETE' });\n"
            "  }\n"
            "}"
        ),
    },
    # === EVENT EMITTER PATTERN ===
    {
        "instruction": "Generate an event emitter for pub/sub patterns.",
        "input": "EventEmitter: Type-safe event bus for decoupled communication",
        "output": (
            "// Type-Safe Event Emitter\n"
            "type EventCallback<T = any> = (data: T) => void;\n"
            "\n"
            "export class EventEmitter {\n"
            "  private events: Map<string, EventCallback[]> = new Map();\n"
            "\n"
            "  on<T = any>(event: string, callback: EventCallback<T>): void {\n"
            "    if (!this.events.has(event)) {\n"
            "      this.events.set(event, []);\n"
            "    }\n"
            "    this.events.get(event)!.push(callback);\n"
            "  }\n"
            "\n"
            "  off<T = any>(event: string, callback: EventCallback<T>): void {\n"
            "    const callbacks = this.events.get(event);\n"
            "    if (callbacks) {\n"
            "      const index = callbacks.indexOf(callback);\n"
            "      if (index > -1) {\n"
            "        callbacks.splice(index, 1);\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "\n"
            "  emit<T = any>(event: string, data?: T): void {\n"
            "    const callbacks = this.events.get(event);\n"
            "    if (callbacks) {\n"
            "      callbacks.forEach(callback => callback(data));\n"
            "    }\n"
            "  }\n"
            "\n"
            "  once<T = any>(event: string, callback: EventCallback<T>): void {\n"
            "    const wrapper: EventCallback<T> = (data) => {\n"
            "      callback(data);\n"
            "      this.off(event, wrapper);\n"
            "    };\n"
            "    this.on(event, wrapper);\n"
            "  }\n"
            "\n"
            "  clear(event?: string): void {\n"
            "    if (event) {\n"
            "      this.events.delete(event);\n"
            "    } else {\n"
            "      this.events.clear();\n"
            "    }\n"
            "  }\n"
            "}"
        ),
    },
    # === CONFIGURATION MANAGEMENT ===
    {
        "instruction": "Generate a configuration loader with environment variable support.",
        "input": "Config: Load configuration from files and environment variables with validation",
        "output": (
            "// Configuration Loader\n"
            "import fs from 'fs';\n"
            "import path from 'path';\n"
            "\n"
            "export interface AppConfig {\n"
            "  port: number;\n"
            "  database: {\n"
            "    host: string;\n"
            "    port: number;\n"
            "    name: string;\n"
            "    user: string;\n"
            "    password: string;\n"
            "  };\n"
            "  jwt: {\n"
            "    secret: string;\n"
            "    expiresIn: string;\n"
            "  };\n"
            "  logging: {\n"
            "    level: string;\n"
            "  };\n"
            "}\n"
            "\n"
            "export class ConfigLoader {\n"
            "  private config: AppConfig;\n"
            "\n"
            "  constructor() {\n"
            "    this.config = this.load();\n"
            "    this.validate();\n"
            "  }\n"
            "\n"
            "  private load(): AppConfig {\n"
            "    const env = process.env.NODE_ENV || 'development';\n"
            "    const configPath = path.join(process.cwd(), `config/${env}.json`);\n"
            "\n"
            "    let fileConfig = {};\n"
            "    if (fs.existsSync(configPath)) {\n"
            "      fileConfig = JSON.parse(fs.readFileSync(configPath, 'utf-8'));\n"
            "    }\n"
            "\n"
            "    // Merge file config with environment variables\n"
            "    return {\n"
            "      port: parseInt(process.env.PORT || fileConfig.port || '3000'),\n"
            "      database: {\n"
            "        host: process.env.DB_HOST || fileConfig.database?.host || 'localhost',\n"
            "        port: parseInt(process.env.DB_PORT || fileConfig.database?.port || '5432'),\n"
            "        name: process.env.DB_NAME || fileConfig.database?.name || 'app',\n"
            "        user: process.env.DB_USER || fileConfig.database?.user || 'user',\n"
            "        password: process.env.DB_PASSWORD || fileConfig.database?.password || ''\n"
            "      },\n"
            "      jwt: {\n"
            "        secret: process.env.JWT_SECRET || fileConfig.jwt?.secret || '',\n"
            "        expiresIn: process.env.JWT_EXPIRES_IN || fileConfig.jwt?.expiresIn || '24h'\n"
            "      },\n"
            "      logging: {\n"
            "        level: process.env.LOG_LEVEL || fileConfig.logging?.level || 'info'\n"
            "      }\n"
            "    };\n"
            "  }\n"
            "\n"
            "  private validate(): void {\n"
            "    if (!this.config.jwt.secret) {\n"
            "      throw new Error('JWT_SECRET is required');\n"
            "    }\n"
            "    if (!this.config.database.password) {\n"
            "      throw new Error('DB_PASSWORD is required');\n"
            "    }\n"
            "  }\n"
            "\n"
            "  get(): AppConfig {\n"
            "    return this.config;\n"
            "  }\n"
            "}"
        ),
    },
    # === ERROR SCENARIOS & EDGE CASES ===
    {
        "instruction": "Handle null pointer exceptions and defensive programming.",
        "input": "Function: Process user data with null safety checks",
        "output": (
            "// Defensive Programming Pattern\n"
            "public class UserProcessor {\n"
            "    public ProcessResult ProcessUser(UserDto? userDto) {\n"
            "        // Guard clause: null check\n"
            "        if (userDto == null) {\n"
            "            return ProcessResult.Error(\"User data cannot be null\");\n"
            "        }\n"
            "\n"
            "        // Guard clause: validate required fields\n"
            "        if (string.IsNullOrWhiteSpace(userDto.Email)) {\n"
            "            return ProcessResult.Error(\"Email is required\");\n"
            "        }\n"
            "\n"
            "        // Guard clause: validate format\n"
            "        if (!IsValidEmail(userDto.Email)) {\n"
            "            return ProcessResult.Error($\"Invalid email format: {userDto.Email}\");\n"
            "        }\n"
            "\n"
            "        // Safe navigation for nested objects\n"
            "        var address = userDto.Address?.Street ?? \"No address provided\";\n"
            "        \n"
            "        // Safe collection access\n"
            "        var phoneCount = userDto.PhoneNumbers?.Count ?? 0;\n"
            "        if (phoneCount == 0) {\n"
            "            _logger.LogWarning(\"User {Email} has no phone numbers\", userDto.Email);\n"
            "        }\n"
            "\n"
            "        try {\n"
            "            // Main processing logic\n"
            "            var result = _userService.Save(userDto);\n"
            "            return ProcessResult.Success(result);\n"
            "        }\n"
            "        catch (DuplicateEmailException ex) {\n"
            "            return ProcessResult.Error($\"Email {userDto.Email} already exists\");\n"
            "        }\n"
            "        catch (DatabaseException ex) {\n"
            "            _logger.LogError(ex, \"Database error processing user\");\n"
            "            return ProcessResult.Error(\"Unable to save user. Please try again.\");\n"
            "        }\n"
            "    }\n"
            "}"
        ),
    },
    {
        "instruction": "Handle async/await errors and race conditions.",
        "input": "Service: Concurrent operations with proper error handling and cancellation",
        "output": (
            "// Async Error Handling & Race Conditions\n"
            "export class DataSyncService {\n"
            "  private activeSyncs = new Map<string, AbortController>();\n"
            "\n"
            "  async syncData(\n"
            "    entityId: string,\n"
            "    data: any,\n"
            "    timeout: number = 30000\n"
            "  ): Promise<SyncResult> {\n"
            "    // Prevent concurrent syncs for same entity\n"
            "    if (this.activeSyncs.has(entityId)) {\n"
            "      return {\n"
            "        success: false,\n"
            "        error: 'Sync already in progress for this entity'\n"
            "      };\n"
            "    }\n"
            "\n"
            "    const controller = new AbortController();\n"
            "    this.activeSyncs.set(entityId, controller);\n"
            "\n"
            "    // Set timeout\n"
            "    const timeoutId = setTimeout(() => controller.abort(), timeout);\n"
            "\n"
            "    try {\n"
            "      const response = await fetch('/api/sync', {\n"
            "        method: 'POST',\n"
            "        body: JSON.stringify({ entityId, data }),\n"
            "        headers: { 'Content-Type': 'application/json' },\n"
            "        signal: controller.signal\n"
            "      });\n"
            "\n"
            "      if (!response.ok) {\n"
            "        throw new Error(`HTTP ${response.status}: ${response.statusText}`);\n"
            "      }\n"
            "\n"
            "      const result = await response.json();\n"
            "      return { success: true, data: result };\n"
            "\n"
            "    } catch (error: any) {\n"
            "      if (error.name === 'AbortError') {\n"
            "        return { success: false, error: 'Sync timed out' };\n"
            "      }\n"
            "      \n"
            "      // Network errors\n"
            "      if (error instanceof TypeError) {\n"
            "        return { success: false, error: 'Network error. Check your connection.' };\n"
            "      }\n"
            "\n"
            "      return { success: false, error: error.message };\n"
            "    } finally {\n"
            "      clearTimeout(timeoutId);\n"
            "      this.activeSyncs.delete(entityId);\n"
            "    }\n"
            "  }\n"
            "\n"
            "  cancelSync(entityId: string): void {\n"
            "    const controller = this.activeSyncs.get(entityId);\n"
            "    if (controller) {\n"
            "      controller.abort();\n"
            "      this.activeSyncs.delete(entityId);\n"
            "    }\n"
            "  }\n"
            "}"
        ),
    },
    {
        "instruction": "Handle infinite loops and recursive function safeguards.",
        "input": "Function: Recursive tree traversal with depth limit and cycle detection",
        "output": (
            "// Recursive Function with Safeguards\n"
            "export class TreeTraverser<T> {\n"
            "  private readonly MAX_DEPTH = 100;\n"
            "  private visited = new Set<string>();\n"
            "\n"
            "  traverse(\n"
            "    node: TreeNode<T>,\n"
            "    callback: (node: TreeNode<T>) => void,\n"
            "    depth: number = 0\n"
            "  ): void {\n"
            "    // Guard: Maximum depth check\n"
            "    if (depth > this.MAX_DEPTH) {\n"
            "      throw new Error(`Maximum recursion depth exceeded (${this.MAX_DEPTH})`);\n"
            "    }\n"
            "\n"
            "    // Guard: Null check\n"
            "    if (!node) {\n"
            "      return;\n"
            "    }\n"
            "\n"
            "    // Guard: Cycle detection\n"
            "    const nodeId = node.id || JSON.stringify(node);\n"
            "    if (this.visited.has(nodeId)) {\n"
            "      console.warn(`Circular reference detected at node ${nodeId}`);\n"
            "      return;\n"
            "    }\n"
            "    this.visited.add(nodeId);\n"
            "\n"
            "    // Process current node\n"
            "    try {\n"
            "      callback(node);\n"
            "    } catch (error) {\n"
            "      console.error(`Error processing node ${nodeId}:`, error);\n"
            "      // Continue traversal despite error\n"
            "    }\n"
            "\n"
            "    // Traverse children safely\n"
            "    const children = Array.isArray(node.children) ? node.children : [];\n"
            "    for (const child of children) {\n"
            "      this.traverse(child, callback, depth + 1);\n"
            "    }\n"
            "  }\n"
            "\n"
            "  reset(): void {\n"
            "    this.visited.clear();\n"
            "  }\n"
            "}"
        ),
    },
    {
        "instruction": "Handle memory leaks and resource cleanup.",
        "input": "Component: Proper cleanup of subscriptions, timers, and event listeners",
        "output": (
            "// Resource Cleanup Pattern\n"
            "import { Component, OnInit, OnDestroy } from '@angular/core';\n"
            "import { Subscription, interval } from 'rxjs';\n"
            "\n"
            "@Component({\n"
            "  selector: 'app-data-monitor',\n"
            "  template: `<div>{{ status }}</div>`\n"
            "})\n"
            "export class DataMonitorComponent implements OnInit, OnDestroy {\n"
            "  status = 'Initializing...';\n"
            "  \n"
            "  // Track all subscriptions\n"
            "  private subscriptions = new Subscription();\n"
            "  \n"
            "  // Track timers\n"
            "  private timers: number[] = [];\n"
            "  \n"
            "  // Track event listeners\n"
            "  private eventListeners: Array<{\n"
            "    element: HTMLElement | Window;\n"
            "    event: string;\n"
            "    handler: EventListener;\n"
            "  }> = [];\n"
            "\n"
            "  ngOnInit(): void {\n"
            "    // Example: Observable subscription\n"
            "    const dataSub = this.dataService.getData()\n"
            "      .subscribe({\n"
            "        next: (data) => this.status = 'Connected',\n"
            "        error: (err) => this.status = 'Error'\n"
            "      });\n"
            "    this.subscriptions.add(dataSub);\n"
            "\n"
            "    // Example: Interval subscription\n"
            "    const intervalSub = interval(1000)\n"
            "      .subscribe(() => this.checkStatus());\n"
            "    this.subscriptions.add(intervalSub);\n"
            "\n"
            "    // Example: Timer\n"
            "    const timerId = window.setTimeout(() => {\n"
            "      this.status = 'Timeout';\n"
            "    }, 30000);\n"
            "    this.timers.push(timerId);\n"
            "\n"
            "    // Example: Event listener\n"
            "    const handler = this.handleResize.bind(this);\n"
            "    window.addEventListener('resize', handler);\n"
            "    this.eventListeners.push({\n"
            "      element: window,\n"
            "      event: 'resize',\n"
            "      handler\n"
            "    });\n"
            "  }\n"
            "\n"
            "  ngOnDestroy(): void {\n"
            "    // Clean up subscriptions\n"
            "    this.subscriptions.unsubscribe();\n"
            "\n"
            "    // Clean up timers\n"
            "    this.timers.forEach(id => clearTimeout(id));\n"
            "    this.timers = [];\n"
            "\n"
            "    // Clean up event listeners\n"
            "    this.eventListeners.forEach(({ element, event, handler }) => {\n"
            "      element.removeEventListener(event, handler);\n"
            "    });\n"
            "    this.eventListeners = [];\n"
            "\n"
            "    console.log('DataMonitor cleaned up successfully');\n"
            "  }\n"
            "\n"
            "  private handleResize(): void {\n"
            "    console.log('Window resized');\n"
            "  }\n"
            "\n"
            "  private checkStatus(): void {\n"
            "    // Periodic status check\n"
            "  }\n"
            "}"
        ),
    },
    {
        "instruction": "Handle SQL injection and input sanitization.",
        "input": "Query: Safe database queries with parameterization",
        "output": (
            "// SQL Injection Prevention\n"
            "public class UserRepository {\n"
            "    private readonly IDbConnection _connection;\n"
            "\n"
            "    // ❌ WRONG: Vulnerable to SQL injection\n"
            "    public User GetUserWrong(string email) {\n"
            "        var query = $\"SELECT * FROM Users WHERE Email = '{email}'\";\n"
            "        // Attacker can input: ' OR '1'='1\n"
            "        return _connection.QueryFirstOrDefault<User>(query);\n"
            "    }\n"
            "\n"
            "    // ✅ CORRECT: Using parameterized queries\n"
            "    public User GetUserSafe(string email) {\n"
            "        var query = \"SELECT * FROM Users WHERE Email = @Email\";\n"
            "        return _connection.QueryFirstOrDefault<User>(query, new { Email = email });\n"
            "    }\n"
            "\n"
            "    // ✅ CORRECT: Using ORM (Entity Framework)\n"
            "    public User GetUserWithEF(string email) {\n"
            "        return _context.Users\n"
            "            .FirstOrDefault(u => u.Email == email);\n"
            "    }\n"
            "\n"
            "    // ✅ CORRECT: Search with LIKE (properly sanitized)\n"
            "    public List<User> SearchUsers(string searchTerm) {\n"
            "        // Escape special characters\n"
            "        var sanitized = searchTerm\n"
            "            .Replace(\"%\", \"[%]\")\n"
            "            .Replace(\"_\", \"[_]\")\n"
            "            .Replace(\"[\", \"[[]\");\n"
            "\n"
            "        var query = \"SELECT * FROM Users WHERE Name LIKE @Search\";\n"
            "        return _connection.Query<User>(query, \n"
            "            new { Search = $\"%{sanitized}%\" }\n"
            "        ).ToList();\n"
            "    }\n"
            "\n"
            "    // ✅ CORRECT: Dynamic sorting (whitelist approach)\n"
            "    public List<User> GetUsersSorted(string sortColumn, string sortOrder) {\n"
            "        // Whitelist allowed columns\n"
            "        var allowedColumns = new[] { \"Name\", \"Email\", \"CreatedAt\" };\n"
            "        if (!allowedColumns.Contains(sortColumn)) {\n"
            "            sortColumn = \"CreatedAt\"; // Default safe value\n"
            "        }\n"
            "\n"
            "        var allowedOrders = new[] { \"ASC\", \"DESC\" };\n"
            "        if (!allowedOrders.Contains(sortOrder.ToUpper())) {\n"
            "            sortOrder = \"DESC\"; // Default safe value\n"
            "        }\n"
            "\n"
            "        // Now safe to use in query\n"
            "        var query = $\"SELECT * FROM Users ORDER BY {sortColumn} {sortOrder}\";\n"
            "        return _connection.Query<User>(query).ToList();\n"
            "    }\n"
            "}"
        ),
    },
    {
        "instruction": "Handle rate limiting and throttling.",
        "input": "Middleware: Rate limiter to prevent API abuse",
        "output": (
            "// Rate Limiting Pattern\n"
            "export class RateLimiter {\n"
            "  private requests = new Map<string, number[]>();\n"
            "  private readonly windowMs: number;\n"
            "  private readonly maxRequests: number;\n"
            "\n"
            "  constructor(windowMs: number = 60000, maxRequests: number = 100) {\n"
            "    this.windowMs = windowMs;\n"
            "    this.maxRequests = maxRequests;\n"
            "  }\n"
            "\n"
            "  isAllowed(identifier: string): { allowed: boolean; retryAfter?: number } {\n"
            "    const now = Date.now();\n"
            "    const windowStart = now - this.windowMs;\n"
            "\n"
            "    // Get existing requests for this identifier\n"
            "    let timestamps = this.requests.get(identifier) || [];\n"
            "\n"
            "    // Remove old requests outside the window\n"
            "    timestamps = timestamps.filter(ts => ts > windowStart);\n"
            "\n"
            "    // Check if limit exceeded\n"
            "    if (timestamps.length >= this.maxRequests) {\n"
            "      const oldestRequest = timestamps[0];\n"
            "      const retryAfter = Math.ceil((oldestRequest + this.windowMs - now) / 1000);\n"
            "      \n"
            "      return { \n"
            "        allowed: false, \n"
            "        retryAfter \n"
            "      };\n"
            "    }\n"
            "\n"
            "    // Add current request\n"
            "    timestamps.push(now);\n"
            "    this.requests.set(identifier, timestamps);\n"
            "\n"
            "    // Cleanup old entries periodically\n"
            "    if (Math.random() < 0.01) {\n"
            "      this.cleanup();\n"
            "    }\n"
            "\n"
            "    return { allowed: true };\n"
            "  }\n"
            "\n"
            "  private cleanup(): void {\n"
            "    const now = Date.now();\n"
            "    const windowStart = now - this.windowMs;\n"
            "\n"
            "    for (const [key, timestamps] of this.requests.entries()) {\n"
            "      const validTimestamps = timestamps.filter(ts => ts > windowStart);\n"
            "      if (validTimestamps.length === 0) {\n"
            "        this.requests.delete(key);\n"
            "      } else {\n"
            "        this.requests.set(key, validTimestamps);\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "\n"
            "  reset(identifier: string): void {\n"
            "    this.requests.delete(identifier);\n"
            "  }\n"
            "}\n"
            "\n"
            "// Express middleware\n"
            "export const rateLimitMiddleware = (limiter: RateLimiter) => {\n"
            "  return (req: Request, res: Response, next: NextFunction) => {\n"
            "    const identifier = req.ip || req.headers['x-forwarded-for'] as string || 'unknown';\n"
            "    const result = limiter.isAllowed(identifier);\n"
            "\n"
            "    if (!result.allowed) {\n"
            "      res.status(429)\n"
            "        .set('Retry-After', result.retryAfter.toString())\n"
            "        .json({ \n"
            "          error: 'Too many requests', \n"
            "          retryAfter: result.retryAfter \n"
            "        });\n"
            "      return;\n"
            "    }\n"
            "\n"
            "    next();\n"
            "  };\n"
            "};"
        ),
    },
    {
        "instruction": "Handle file upload validation and security.",
        "input": "Handler: Secure file upload with size, type, and malware checks",
        "output": (
            "// Secure File Upload Handler\n"
            "public class FileUploadService {\n"
            "    private readonly ILogger<FileUploadService> _logger;\n"
            "    private const long MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB\n"
            "    private static readonly string[] ALLOWED_EXTENSIONS = { \".jpg\", \".jpeg\", \".png\", \".pdf\", \".doc\", \".docx\" };\n"
            "    private static readonly string[] ALLOWED_CONTENT_TYPES = { \n"
            "        \"image/jpeg\", \"image/png\", \"application/pdf\", \n"
            "        \"application/msword\", \"application/vnd.openxmlformats-officedocument.wordprocessingml.document\" \n"
            "    };\n"
            "\n"
            "    public async Task<UploadResult> UploadFileAsync(IFormFile file) {\n"
            "        var errors = new List<string>();\n"
            "\n"
            "        // Validate: File exists\n"
            "        if (file == null || file.Length == 0) {\n"
            "            return UploadResult.Fail(\"No file provided\");\n"
            "        }\n"
            "\n"
            "        // Validate: File size\n"
            "        if (file.Length > MAX_FILE_SIZE) {\n"
            "            return UploadResult.Fail($\"File size exceeds {MAX_FILE_SIZE / 1024 / 1024}MB limit\");\n"
            "        }\n"
            "\n"
            "        // Validate: File extension\n"
            "        var extension = Path.GetExtension(file.FileName).ToLowerInvariant();\n"
            "        if (!ALLOWED_EXTENSIONS.Contains(extension)) {\n"
            "            return UploadResult.Fail($\"File type {extension} not allowed\");\n"
            "        }\n"
            "\n"
            "        // Validate: Content type\n"
            "        if (!ALLOWED_CONTENT_TYPES.Contains(file.ContentType.ToLowerInvariant())) {\n"
            "            return UploadResult.Fail($\"Content type {file.ContentType} not allowed\");\n"
            "        }\n"
            "\n"
            "        // Validate: File signature (magic numbers)\n"
            "        if (!await IsValidFileSignature(file)) {\n"
            "            return UploadResult.Fail(\"File signature does not match extension\");\n"
            "        }\n"
            "\n"
            "        // Generate safe filename\n"
            "        var safeFileName = $\"{Guid.NewGuid()}{extension}\";\n"
            "        var uploadPath = Path.Combine(\"uploads\", safeFileName);\n"
            "\n"
            "        try {\n"
            "            // Ensure directory exists\n"
            "            Directory.CreateDirectory(\"uploads\");\n"
            "\n"
            "            // Save file\n"
            "            using (var stream = new FileStream(uploadPath, FileMode.Create)) {\n"
            "                await file.CopyToAsync(stream);\n"
            "            }\n"
            "\n"
            "            _logger.LogInformation(\"File uploaded: {FileName}\", safeFileName);\n"
            "            return UploadResult.Success(safeFileName);\n"
            "        }\n"
            "        catch (Exception ex) {\n"
            "            _logger.LogError(ex, \"File upload failed\");\n"
            "            return UploadResult.Fail(\"Upload failed. Please try again.\");\n"
            "        }\n"
            "    }\n"
            "\n"
            "    private async Task<bool> IsValidFileSignature(IFormFile file) {\n"
            "        var extension = Path.GetExtension(file.FileName).ToLowerInvariant();\n"
            "        \n"
            "        using var reader = new BinaryReader(file.OpenReadStream());\n"
            "        var headerBytes = reader.ReadBytes(8);\n"
            "\n"
            "        // Check magic numbers\n"
            "        return extension switch {\n"
            "            \".jpg\" or \".jpeg\" => headerBytes[0] == 0xFF && headerBytes[1] == 0xD8,\n"
            "            \".png\" => headerBytes[0] == 0x89 && headerBytes[1] == 0x50,\n"
            "            \".pdf\" => headerBytes[0] == 0x25 && headerBytes[1] == 0x50,\n"
            "            _ => true // Other types skip signature check\n"
            "        };\n"
            "    }\n"
            "}"
        ),
    },
    {
        "instruction": "Handle XSS (Cross-Site Scripting) prevention.",
        "input": "Function: Sanitize user input to prevent XSS attacks",
        "output": (
            "// XSS Prevention Utilities\n"
            "export class XSSProtection {\n"
            "  // Escape HTML special characters\n"
            "  static escapeHtml(unsafe: string): string {\n"
            "    if (!unsafe) return '';\n"
            "    \n"
            "    return unsafe\n"
            "      .replace(/&/g, '&amp;')\n"
            "      .replace(/</g, '&lt;')\n"
            "      .replace(/>/g, '&gt;')\n"
            "      .replace(/\"/g, '&quot;')\n"
            "      .replace(/'/g, '&#x27;')\n"
            "      .replace(/\\//g, '&#x2F;');\n"
            "  }\n"
            "\n"
            "  // Strip HTML tags completely\n"
            "  static stripHtml(html: string): string {\n"
            "    if (!html) return '';\n"
            "    return html.replace(/<[^>]*>/g, '');\n"
            "  }\n"
            "\n"
            "  // Sanitize for use in JavaScript strings\n"
            "  static escapeJs(unsafe: string): string {\n"
            "    if (!unsafe) return '';\n"
            "    \n"
            "    return unsafe\n"
            "      .replace(/\\\\/g, '\\\\\\\\')\n"
            "      .replace(/'/g, \"\\\\'\")\n"
            "      .replace(/\"/g, '\\\\\"')\n"
            "      .replace(/\\n/g, '\\\\n')\n"
            "      .replace(/\\r/g, '\\\\r')\n"
            "      .replace(/\\t/g, '\\\\t');\n"
            "  }\n"
            "\n"
            "  // Sanitize URLs\n"
            "  static sanitizeUrl(url: string): string {\n"
            "    if (!url) return '';\n"
            "\n"
            "    // Block javascript: and data: protocols\n"
            "    const dangerous = /^(javascript|data|vbscript):/i;\n"
            "    if (dangerous.test(url.trim())) {\n"
            "      return 'about:blank';\n"
            "    }\n"
            "\n"
            "    return url;\n"
            "  }\n"
            "\n"
            "  // Whitelist-based HTML sanitizer\n"
            "  static sanitizeHtml(html: string): string {\n"
            "    if (!html) return '';\n"
            "\n"
            "    const allowedTags = ['b', 'i', 'em', 'strong', 'p', 'br', 'a'];\n"
            "    const allowedAttrs = { a: ['href', 'title'] };\n"
            "\n"
            "    // Use DOMParser for safe parsing\n"
            "    const doc = new DOMParser().parseFromString(html, 'text/html');\n"
            "    const walker = document.createTreeWalker(\n"
            "      doc.body,\n"
            "      NodeFilter.SHOW_ELEMENT,\n"
            "      null\n"
            "    );\n"
            "\n"
            "    const nodesToRemove: Node[] = [];\n"
            "\n"
            "    let node: Node | null;\n"
            "    while (node = walker.nextNode()) {\n"
            "      const element = node as Element;\n"
            "      const tagName = element.tagName.toLowerCase();\n"
            "\n"
            "      // Remove disallowed tags\n"
            "      if (!allowedTags.includes(tagName)) {\n"
            "        nodesToRemove.push(element);\n"
            "        continue;\n"
            "      }\n"
            "\n"
            "      // Remove disallowed attributes\n"
            "      const allowed = allowedAttrs[tagName] || [];\n"
            "      Array.from(element.attributes).forEach(attr => {\n"
            "        if (!allowed.includes(attr.name)) {\n"
            "          element.removeAttribute(attr.name);\n"
            "        }\n"
            "      });\n"
            "\n"
            "      // Sanitize href attributes\n"
            "      if (tagName === 'a') {\n"
            "        const href = element.getAttribute('href');\n"
            "        if (href) {\n"
            "          element.setAttribute('href', this.sanitizeUrl(href));\n"
            "        }\n"
            "      }\n"
            "    }\n"
            "\n"
            "    nodesToRemove.forEach(n => n.parentNode?.removeChild(n));\n"
            "\n"
            "    return doc.body.innerHTML;\n"
            "  }\n"
            "}"
        ),
    },
    {
        "instruction": "Handle database deadlocks and transaction retries.",
        "input": "Service: Retry logic for database deadlocks with exponential backoff",
        "output": (
            "// Database Deadlock Handling\n"
            "public class TransactionService {\n"
            "    private readonly IDbConnection _connection;\n"
            "    private readonly ILogger<TransactionService> _logger;\n"
            "    private const int MAX_RETRIES = 3;\n"
            "\n"
            "    public async Task<T> ExecuteWithRetry<T>(\n"
            "        Func<IDbTransaction, Task<T>> operation,\n"
            "        IsolationLevel isolationLevel = IsolationLevel.ReadCommitted\n"
            "    ) {\n"
            "        int attempt = 0;\n"
            "        Exception lastException = null;\n"
            "\n"
            "        while (attempt < MAX_RETRIES) {\n"
            "            attempt++;\n"
            "            IDbTransaction transaction = null;\n"
            "\n"
            "            try {\n"
            "                transaction = _connection.BeginTransaction(isolationLevel);\n"
            "                var result = await operation(transaction);\n"
            "                transaction.Commit();\n"
            "                \n"
            "                if (attempt > 1) {\n"
            "                    _logger.LogInformation(\n"
            "                        \"Transaction succeeded on attempt {Attempt}\", \n"
            "                        attempt\n"
            "                    );\n"
            "                }\n"
            "                \n"
            "                return result;\n"
            "            }\n"
            "            catch (SqlException ex) when (IsDeadlock(ex) && attempt < MAX_RETRIES) {\n"
            "                transaction?.Rollback();\n"
            "                lastException = ex;\n"
            "                \n"
            "                _logger.LogWarning(\n"
            "                    \"Deadlock detected on attempt {Attempt}. Retrying...\", \n"
            "                    attempt\n"
            "                );\n"
            "                \n"
            "                // Exponential backoff: 100ms, 200ms, 400ms\n"
            "                var delayMs = 100 * (int)Math.Pow(2, attempt - 1);\n"
            "                await Task.Delay(delayMs);\n"
            "            }\n"
            "            catch (Exception ex) {\n"
            "                transaction?.Rollback();\n"
            "                _logger.LogError(ex, \"Transaction failed\");\n"
            "                throw;\n"
            "            }\n"
            "            finally {\n"
            "                transaction?.Dispose();\n"
            "            }\n"
            "        }\n"
            "\n"
            "        throw new DeadlockException(\n"
            "            $\"Transaction failed after {MAX_RETRIES} attempts due to deadlock\",\n"
            "            lastException\n"
            "        );\n"
            "    }\n"
            "\n"
            "    private bool IsDeadlock(SqlException ex) {\n"
            "        // SQL Server deadlock error number is 1205\n"
            "        return ex.Number == 1205;\n"
            "    }\n"
            "\n"
            "    // Example usage\n"
            "    public async Task<bool> TransferFunds(\n"
            "        int fromAccountId, \n"
            "        int toAccountId, \n"
            "        decimal amount\n"
            "    ) {\n"
            "        return await ExecuteWithRetry(async (transaction) => {\n"
            "            // Debit from account\n"
            "            await _connection.ExecuteAsync(\n"
            "                \"UPDATE Accounts SET Balance = Balance - @Amount WHERE Id = @Id\",\n"
            "                new { Amount = amount, Id = fromAccountId },\n"
            "                transaction\n"
            "            );\n"
            "\n"
            "            // Credit to account\n"
            "            await _connection.ExecuteAsync(\n"
            "                \"UPDATE Accounts SET Balance = Balance + @Amount WHERE Id = @Id\",\n"
            "                new { Amount = amount, Id = toAccountId },\n"
            "                transaction\n"
            "            );\n"
            "\n"
            "            return true;\n"
            "        });\n"
            "    }\n"
            "}"
        ),
    },
    {
        "instruction": "Handle timezone issues and date formatting.",
        "input": "Utility: Safe date handling with timezone awareness",
        "output": (
            "// Timezone-Aware Date Handling\n"
            "export class DateTimeUtils {\n"
            "  // Always store dates in UTC\n"
            "  static toUTC(date: Date): Date {\n"
            "    return new Date(date.toISOString());\n"
            "  }\n"
            "\n"
            "  // Convert UTC to user's local timezone\n"
            "  static toLocal(utcDate: Date): Date {\n"
            "    return new Date(utcDate);\n"
            "  }\n"
            "\n"
            "  // Format for display (always specify timezone)\n"
            "  static formatForDisplay(\n"
            "    date: Date, \n"
            "    timezone: string = 'UTC',\n"
            "    format: Intl.DateTimeFormatOptions = {}\n"
            "  ): string {\n"
            "    const defaultFormat: Intl.DateTimeFormatOptions = {\n"
            "      year: 'numeric',\n"
            "      month: '2-digit',\n"
            "      day: '2-digit',\n"
            "      hour: '2-digit',\n"
            "      minute: '2-digit',\n"
            "      timeZone: timezone,\n"
            "      ...format\n"
            "    };\n"
            "\n"
            "    return new Intl.DateTimeFormat('en-US', defaultFormat).format(date);\n"
            "  }\n"
            "\n"
            "  // Parse user input safely\n"
            "  static parseUserInput(input: string): Date | null {\n"
            "    if (!input) return null;\n"
            "\n"
            "    const parsed = new Date(input);\n"
            "    \n"
            "    // Check for invalid date\n"
            "    if (isNaN(parsed.getTime())) {\n"
            "      return null;\n"
            "    }\n"
            "\n"
            "    return parsed;\n"
            "  }\n"
            "\n"
            "  // Safe date comparison\n"
            "  static isSameDay(date1: Date, date2: Date): boolean {\n"
            "    return date1.getFullYear() === date2.getFullYear() &&\n"
            "           date1.getMonth() === date2.getMonth() &&\n"
            "           date1.getDate() === date2.getDate();\n"
            "  }\n"
            "\n"
            "  // Calculate age (handles leap years)\n"
            "  static calculateAge(birthDate: Date): number {\n"
            "    const today = new Date();\n"
            "    let age = today.getFullYear() - birthDate.getFullYear();\n"
            "    const monthDiff = today.getMonth() - birthDate.getMonth();\n"
            "    \n"
            "    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {\n"
            "      age--;\n"
            "    }\n"
            "    \n"
            "    return age;\n"
            "  }\n"
            "\n"
            "  // Add days safely (handles DST transitions)\n"
            "  static addDays(date: Date, days: number): Date {\n"
            "    const result = new Date(date);\n"
            "    result.setDate(result.getDate() + days);\n"
            "    return result;\n"
            "  }\n"
            "\n"
            "  // Format for API (ISO 8601)\n"
            "  static toISO(date: Date): string {\n"
            "    return date.toISOString();\n"
            "  }\n"
            "\n"
            "  // Parse ISO safely\n"
            "  static fromISO(iso: string): Date | null {\n"
            "    try {\n"
            "      const date = new Date(iso);\n"
            "      return isNaN(date.getTime()) ? null : date;\n"
            "    } catch {\n"
            "      return null;\n"
            "    }\n"
            "  }\n"
            "}"
        ),
    },
    # === ARTIFACT GENERATION QUALITY EXAMPLES ===
    # These examples teach the model to avoid common generation mistakes
    
    # === COMPLETE GENERATION (No Truncation) ===
    {
        "instruction": "Generate a complete React component with all methods implemented.",
        "input": "Component: User profile editor with validation and save functionality",
        "output": (
            "// ✅ COMPLETE GENERATION - All methods fully implemented\n"
            "import React, { useState, useEffect } from 'react';\n"
            "import { User } from './types';\n"
            "\n"
            "interface UserProfileProps {\n"
            "  userId: string;\n"
            "  onSave: (user: User) => Promise<void>;\n"
            "}\n"
            "\n"
            "export const UserProfile: React.FC<UserProfileProps> = ({ userId, onSave }) => {\n"
            "  const [user, setUser] = useState<User | null>(null);\n"
            "  const [loading, setLoading] = useState(false);\n"
            "  const [errors, setErrors] = useState<Record<string, string>>({});\n"
            "\n"
            "  useEffect(() => {\n"
            "    loadUser();\n"
            "  }, [userId]);\n"
            "\n"
            "  const loadUser = async () => {\n"
            "    setLoading(true);\n"
            "    try {\n"
            "      const response = await fetch(`/api/users/${userId}`);\n"
            "      const data = await response.json();\n"
            "      setUser(data);\n"
            "    } catch (error) {\n"
            "      console.error('Failed to load user:', error);\n"
            "    } finally {\n"
            "      setLoading(false);\n"
            "    }\n"
            "  };\n"
            "\n"
            "  const validate = (userData: User): boolean => {\n"
            "    const newErrors: Record<string, string> = {};\n"
            "    \n"
            "    if (!userData.name?.trim()) {\n"
            "      newErrors.name = 'Name is required';\n"
            "    }\n"
            "    \n"
            "    if (!userData.email?.match(/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/)) {\n"
            "      newErrors.email = 'Valid email is required';\n"
            "    }\n"
            "    \n"
            "    setErrors(newErrors);\n"
            "    return Object.keys(newErrors).length === 0;\n"
            "  };\n"
            "\n"
            "  const handleSave = async () => {\n"
            "    if (!user || !validate(user)) return;\n"
            "    \n"
            "    setLoading(true);\n"
            "    try {\n"
            "      await onSave(user);\n"
            "      alert('Profile saved successfully');\n"
            "    } catch (error) {\n"
            "      alert('Failed to save profile');\n"
            "    } finally {\n"
            "      setLoading(false);\n"
            "    }\n"
            "  };\n"
            "\n"
            "  if (!user) return <div>Loading...</div>;\n"
            "\n"
            "  return (\n"
            "    <div className=\"user-profile\">\n"
            "      <h2>Edit Profile</h2>\n"
            "      \n"
            "      <div className=\"form-group\">\n"
            "        <label>Name</label>\n"
            "        <input\n"
            "          type=\"text\"\n"
            "          value={user.name}\n"
            "          onChange={(e) => setUser({ ...user, name: e.target.value })}\n"
            "        />\n"
            "        {errors.name && <span className=\"error\">{errors.name}</span>}\n"
            "      </div>\n"
            "      \n"
            "      <div className=\"form-group\">\n"
            "        <label>Email</label>\n"
            "        <input\n"
            "          type=\"email\"\n"
            "          value={user.email}\n"
            "          onChange={(e) => setUser({ ...user, email: e.target.value })}\n"
            "        />\n"
            "        {errors.email && <span className=\"error\">{errors.email}</span>}\n"
            "      </div>\n"
            "      \n"
            "      <button onClick={handleSave} disabled={loading}>\n"
            "        {loading ? 'Saving...' : 'Save'}\n"
            "      </button>\n"
            "    </div>\n"
            "  );\n"
            "};"
        ),
    },
    {
        "instruction": "Generate a complete API endpoint with full request/response handling.",
        "input": "Endpoint: POST /api/orders - Create new order with items",
        "output": (
            "// ✅ COMPLETE GENERATION - Fully implemented endpoint\n"
            "[HttpPost]\n"
            "[Route(\"api/orders\")]\n"
            "public async Task<ActionResult<OrderResponse>> CreateOrder(\n"
            "    [FromBody] CreateOrderRequest request\n"
            ") {\n"
            "    // Validate request\n"
            "    if (request == null || !request.Items.Any()) {\n"
            "        return BadRequest(new { error = \"Order must contain at least one item\" });\n"
            "    }\n"
            "\n"
            "    // Calculate total\n"
            "    var total = request.Items.Sum(item => item.Price * item.Quantity);\n"
            "\n"
            "    // Create order\n"
            "    var order = new Order {\n"
            "        Id = Guid.NewGuid(),\n"
            "        CustomerId = request.CustomerId,\n"
            "        Items = request.Items.Select(i => new OrderItem {\n"
            "            ProductId = i.ProductId,\n"
            "            Quantity = i.Quantity,\n"
            "            Price = i.Price\n"
            "        }).ToList(),\n"
            "        Total = total,\n"
            "        Status = OrderStatus.Pending,\n"
            "        CreatedAt = DateTime.UtcNow\n"
            "    };\n"
            "\n"
            "    // Save to database\n"
            "    try {\n"
            "        await _context.Orders.AddAsync(order);\n"
            "        await _context.SaveChangesAsync();\n"
            "    }\n"
            "    catch (DbUpdateException ex) {\n"
            "        _logger.LogError(ex, \"Failed to create order\");\n"
            "        return StatusCode(500, new { error = \"Failed to create order\" });\n"
            "    }\n"
            "\n"
            "    // Return response\n"
            "    var response = new OrderResponse {\n"
            "        OrderId = order.Id,\n"
            "        Status = order.Status.ToString(),\n"
            "        Total = order.Total,\n"
            "        CreatedAt = order.CreatedAt\n"
            "    };\n"
            "\n"
            "    return CreatedAtAction(\n"
            "        nameof(GetOrder),\n"
            "        new { id = order.Id },\n"
            "        response\n"
            "    );\n"
            "}"
        ),
    },
    # === CORRECT IMPORTS (No Hallucinations) ===
    {
        "instruction": "Generate Angular service with correct RxJS imports.",
        "input": "Service: Data fetching service using HttpClient and RxJS operators",
        "output": (
            "// ✅ CORRECT IMPORTS - All imports are real and exist\n"
            "import { Injectable } from '@angular/core';\n"
            "import { HttpClient, HttpErrorResponse } from '@angular/common/http';\n"
            "import { Observable, throwError, of } from 'rxjs';\n"
            "import { catchError, retry, tap, map } from 'rxjs/operators';\n"
            "\n"
            "@Injectable({ providedIn: 'root' })\n"
            "export class DataService {\n"
            "  private apiUrl = '/api/data';\n"
            "  private cache = new Map<string, any>();\n"
            "\n"
            "  constructor(private http: HttpClient) {}\n"
            "\n"
            "  getData(id: string): Observable<any> {\n"
            "    // Check cache\n"
            "    if (this.cache.has(id)) {\n"
            "      return of(this.cache.get(id));\n"
            "    }\n"
            "\n"
            "    return this.http.get(`${this.apiUrl}/${id}`).pipe(\n"
            "      retry(2),\n"
            "      tap(data => this.cache.set(id, data)),\n"
            "      catchError(this.handleError)\n"
            "    );\n"
            "  }\n"
            "\n"
            "  private handleError(error: HttpErrorResponse): Observable<never> {\n"
            "    console.error('API Error:', error);\n"
            "    return throwError(() => new Error('Something went wrong'));\n"
            "  }\n"
            "}"
        ),
    },
    {
        "instruction": "Generate Python Flask endpoint with correct imports.",
        "input": "Endpoint: User authentication with JWT tokens",
        "output": (
            "# ✅ CORRECT IMPORTS - All modules exist and are properly imported\n"
            "from flask import Blueprint, request, jsonify\n"
            "from werkzeug.security import check_password_hash\n"
            "from flask_jwt_extended import create_access_token, create_refresh_token\n"
            "from datetime import timedelta\n"
            "from models import User\n"
            "from extensions import db\n"
            "\n"
            "auth_bp = Blueprint('auth', __name__)\n"
            "\n"
            "@auth_bp.route('/login', methods=['POST'])\n"
            "def login():\n"
            "    data = request.get_json()\n"
            "    \n"
            "    if not data or not data.get('email') or not data.get('password'):\n"
            "        return jsonify({'error': 'Email and password required'}), 400\n"
            "    \n"
            "    user = User.query.filter_by(email=data['email']).first()\n"
            "    \n"
            "    if not user or not check_password_hash(user.password_hash, data['password']):\n"
            "        return jsonify({'error': 'Invalid credentials'}), 401\n"
            "    \n"
            "    access_token = create_access_token(\n"
            "        identity=user.id,\n"
            "        expires_delta=timedelta(hours=1)\n"
            "    )\n"
            "    \n"
            "    refresh_token = create_refresh_token(\n"
            "        identity=user.id,\n"
            "        expires_delta=timedelta(days=30)\n"
            "    )\n"
            "    \n"
            "    return jsonify({\n"
            "        'access_token': access_token,\n"
            "        'refresh_token': refresh_token,\n"
            "        'user': {\n"
            "            'id': user.id,\n"
            "            'email': user.email,\n"
            "            'name': user.name\n"
            "        }\n"
            "    }), 200"
        ),
    },
    # === CONSISTENT NAMING CONVENTIONS ===
    {
        "instruction": "Generate TypeScript interface with consistent camelCase naming.",
        "input": "Interface: User profile with address and preferences",
        "output": (
            "// ✅ CONSISTENT NAMING - All properties use camelCase\n"
            "export interface UserProfile {\n"
            "  userId: string;\n"
            "  firstName: string;\n"
            "  lastName: string;\n"
            "  emailAddress: string;\n"
            "  phoneNumber?: string;\n"
            "  dateOfBirth: Date;\n"
            "  createdAt: Date;\n"
            "  updatedAt: Date;\n"
            "  \n"
            "  address: {\n"
            "    streetAddress: string;\n"
            "    city: string;\n"
            "    stateCode: string;\n"
            "    zipCode: string;\n"
            "    countryCode: string;\n"
            "  };\n"
            "  \n"
            "  preferences: {\n"
            "    emailNotifications: boolean;\n"
            "    smsNotifications: boolean;\n"
            "    newsletterSubscribed: boolean;\n"
            "    languageCode: string;\n"
            "    timeZone: string;\n"
            "  };\n"
            "}"
        ),
    },
    {
        "instruction": "Generate Python class with consistent snake_case naming.",
        "input": "Class: Database repository for product management",
        "output": (
            "# ✅ CONSISTENT NAMING - All methods and variables use snake_case\n"
            "from typing import List, Optional\n"
            "from sqlalchemy.orm import Session\n"
            "from models import Product\n"
            "\n"
            "class ProductRepository:\n"
            "    def __init__(self, db_session: Session):\n"
            "        self.db_session = db_session\n"
            "    \n"
            "    def find_by_id(self, product_id: int) -> Optional[Product]:\n"
            "        return self.db_session.query(Product).filter(\n"
            "            Product.id == product_id\n"
            "        ).first()\n"
            "    \n"
            "    def find_all(self, skip: int = 0, limit: int = 100) -> List[Product]:\n"
            "        return self.db_session.query(Product).offset(skip).limit(limit).all()\n"
            "    \n"
            "    def find_by_category(self, category_id: int) -> List[Product]:\n"
            "        return self.db_session.query(Product).filter(\n"
            "            Product.category_id == category_id\n"
            "        ).all()\n"
            "    \n"
            "    def create(self, product_data: dict) -> Product:\n"
            "        product = Product(**product_data)\n"
            "        self.db_session.add(product)\n"
            "        self.db_session.commit()\n"
            "        self.db_session.refresh(product)\n"
            "        return product\n"
            "    \n"
            "    def update(self, product_id: int, update_data: dict) -> Optional[Product]:\n"
            "        product = self.find_by_id(product_id)\n"
            "        if not product:\n"
            "            return None\n"
            "        \n"
            "        for key, value in update_data.items():\n"
            "            setattr(product, key, value)\n"
            "        \n"
            "        self.db_session.commit()\n"
            "        self.db_session.refresh(product)\n"
            "        return product\n"
            "    \n"
            "    def delete(self, product_id: int) -> bool:\n"
            "        product = self.find_by_id(product_id)\n"
            "        if not product:\n"
            "            return False\n"
            "        \n"
            "        self.db_session.delete(product)\n"
            "        self.db_session.commit()\n"
            "        return True"
        ),
    },
    # === PROPER MERMAID SYNTAX ===
    {
        "instruction": "Generate ERD diagram with correct Mermaid syntax.",
        "input": "ERD: Library management system with books, authors, and loans",
        "output": (
            "erDiagram\n"
            "    AUTHOR ||--o{ BOOK : writes\n"
            "    BOOK ||--o{ LOAN : borrowed_in\n"
            "    MEMBER ||--o{ LOAN : takes_out\n"
            "    \n"
            "    AUTHOR {\n"
            "        int author_id PK\n"
            "        string name\n"
            "        string bio\n"
            "        date birth_date\n"
            "    }\n"
            "    \n"
            "    BOOK {\n"
            "        int book_id PK\n"
            "        int author_id FK\n"
            "        string title\n"
            "        string isbn\n"
            "        int year_published\n"
            "        string genre\n"
            "    }\n"
            "    \n"
            "    MEMBER {\n"
            "        int member_id PK\n"
            "        string name\n"
            "        string email\n"
            "        date joined_date\n"
            "    }\n"
            "    \n"
            "    LOAN {\n"
            "        int loan_id PK\n"
            "        int book_id FK\n"
            "        int member_id FK\n"
            "        date loan_date\n"
            "        date due_date\n"
            "        date return_date\n"
            "    }"
        ),
    },
    {
        "instruction": "Generate flowchart with proper Mermaid syntax and decision points.",
        "input": "Flowchart: Password reset flow with email verification",
        "output": (
            "flowchart TD\n"
            "    Start([User Requests Password Reset]) --> CheckEmail{Email Exists?}\n"
            "    \n"
            "    CheckEmail -->|No| ShowError[Show Error: Email Not Found]\n"
            "    ShowError --> End1([End])\n"
            "    \n"
            "    CheckEmail -->|Yes| GenerateToken[Generate Reset Token]\n"
            "    GenerateToken --> SaveToken[Save Token to Database]\n"
            "    SaveToken --> SendEmail[Send Reset Email]\n"
            "    \n"
            "    SendEmail --> UserClicksLink[User Clicks Reset Link]\n"
            "    UserClicksLink --> ValidateToken{Token Valid?}\n"
            "    \n"
            "    ValidateToken -->|No| ShowExpired[Show Error: Token Expired]\n"
            "    ShowExpired --> End2([End])\n"
            "    \n"
            "    ValidateToken -->|Yes| ShowForm[Show Reset Password Form]\n"
            "    ShowForm --> UserSubmits[User Submits New Password]\n"
            "    UserSubmits --> ValidatePassword{Password Valid?}\n"
            "    \n"
            "    ValidatePassword -->|No| ShowRules[Show Password Requirements]\n"
            "    ShowRules --> ShowForm\n"
            "    \n"
            "    ValidatePassword -->|Yes| HashPassword[Hash New Password]\n"
            "    HashPassword --> UpdateDB[Update Password in Database]\n"
            "    UpdateDB --> InvalidateToken[Invalidate Reset Token]\n"
            "    InvalidateToken --> ShowSuccess[Show Success Message]\n"
            "    ShowSuccess --> End3([End])"
        ),
    },
    # === NO PLACEHOLDER CODE ===
    {
        "instruction": "Generate service class with all methods fully implemented (no TODOs).",
        "input": "Service: Email notification service with templates and queue",
        "output": (
            "// ✅ FULLY IMPLEMENTED - No TODO comments or placeholders\n"
            "import { Injectable } from '@nestjs/common';\n"
            "import { Queue } from 'bull';\n"
            "import { InjectQueue } from '@nestjs/bull';\n"
            "\n"
            "interface EmailTemplate {\n"
            "  subject: string;\n"
            "  html: string;\n"
            "  text: string;\n"
            "}\n"
            "\n"
            "@Injectable()\n"
            "export class EmailService {\n"
            "  constructor(\n"
            "    @InjectQueue('email') private emailQueue: Queue\n"
            "  ) {}\n"
            "\n"
            "  async sendWelcomeEmail(email: string, name: string): Promise<void> {\n"
            "    const template = this.getWelcomeTemplate(name);\n"
            "    await this.queueEmail(email, template);\n"
            "  }\n"
            "\n"
            "  async sendPasswordResetEmail(email: string, resetToken: string): Promise<void> {\n"
            "    const resetUrl = `https://example.com/reset?token=${resetToken}`;\n"
            "    const template = this.getPasswordResetTemplate(resetUrl);\n"
            "    await this.queueEmail(email, template);\n"
            "  }\n"
            "\n"
            "  async sendOrderConfirmation(email: string, orderDetails: any): Promise<void> {\n"
            "    const template = this.getOrderConfirmationTemplate(orderDetails);\n"
            "    await this.queueEmail(email, template);\n"
            "  }\n"
            "\n"
            "  private async queueEmail(to: string, template: EmailTemplate): Promise<void> {\n"
            "    await this.emailQueue.add('send-email', {\n"
            "      to,\n"
            "      subject: template.subject,\n"
            "      html: template.html,\n"
            "      text: template.text,\n"
            "      timestamp: new Date().toISOString()\n"
            "    }, {\n"
            "      attempts: 3,\n"
            "      backoff: {\n"
            "        type: 'exponential',\n"
            "        delay: 5000\n"
            "      }\n"
            "    });\n"
            "  }\n"
            "\n"
            "  private getWelcomeTemplate(name: string): EmailTemplate {\n"
            "    return {\n"
            "      subject: 'Welcome to Our Platform!',\n"
            "      html: `<h1>Welcome, ${name}!</h1><p>Thanks for joining us.</p>`,\n"
            "      text: `Welcome, ${name}! Thanks for joining us.`\n"
            "    };\n"
            "  }\n"
            "\n"
            "  private getPasswordResetTemplate(resetUrl: string): EmailTemplate {\n"
            "    return {\n"
            "      subject: 'Password Reset Request',\n"
            "      html: `<p>Click <a href=\"${resetUrl}\">here</a> to reset your password.</p>`,\n"
            "      text: `Reset your password: ${resetUrl}`\n"
            "    };\n"
            "  }\n"
            "\n"
            "  private getOrderConfirmationTemplate(orderDetails: any): EmailTemplate {\n"
            "    const itemsList = orderDetails.items\n"
            "      .map(item => `${item.name} x${item.quantity}`)\n"
            "      .join(', ');\n"
            "    \n"
            "    return {\n"
            "      subject: `Order Confirmation - ${orderDetails.orderNumber}`,\n"
            "      html: `<h2>Order Confirmed</h2><p>Items: ${itemsList}</p><p>Total: $${orderDetails.total}</p>`,\n"
            "      text: `Order ${orderDetails.orderNumber} confirmed. Items: ${itemsList}. Total: $${orderDetails.total}`\n"
            "    };\n"
            "  }\n"
            "}"
        ),
    },
    # === MERMAID DIAGRAM EDGE CASES ===
    # Common issues: syntax errors, special characters, complex relationships, styling
    
    {
        "instruction": "Generate ERD with many-to-many relationships and junction tables.",
        "input": "Database: Students enroll in Courses, tracked by Enrollments with grade and date",
        "output": (
            "erDiagram\n"
            "    STUDENT ||--o{ ENROLLMENT : enrolls\n"
            "    COURSE ||--o{ ENROLLMENT : \"enrolled in\"\n"
            "    STUDENT {\n"
            "        int student_id PK\n"
            "        string name\n"
            "        string email UK\n"
            "        date date_of_birth\n"
            "    }\n"
            "    COURSE {\n"
            "        int course_id PK\n"
            "        string course_code UK\n"
            "        string title\n"
            "        int credits\n"
            "    }\n"
            "    ENROLLMENT {\n"
            "        int enrollment_id PK\n"
            "        int student_id FK\n"
            "        int course_id FK\n"
            "        date enrollment_date\n"
            "        string grade\n"
            "        string status\n"
            "    }"
        ),
    },
    {
        "instruction": "Generate ERD with self-referential relationships.",
        "input": "Employee table where employees have managers (also employees)",
        "output": (
            "erDiagram\n"
            "    EMPLOYEE ||--o{ EMPLOYEE : manages\n"
            "    EMPLOYEE {\n"
            "        int employee_id PK\n"
            "        string name\n"
            "        string email UK\n"
            "        int manager_id FK \"nullable\"\n"
            "        string department\n"
            "        decimal salary\n"
            "        date hire_date\n"
            "    }"
        ),
    },
    {
        "instruction": "Generate flowchart with complex conditional branches and loops.",
        "input": "Order processing: Check inventory, reserve items, process payment with retries, handle failures",
        "output": (
            "flowchart TD\n"
            "    Start([Order Received]) --> CheckInventory{Items in stock?}\n"
            "    CheckInventory -->|Yes| ReserveItems[Reserve Items]\n"
            "    CheckInventory -->|No| NotifyBackorder[Notify: Backordered]\n"
            "    NotifyBackorder --> End([End])\n"
            "    \n"
            "    ReserveItems --> ProcessPayment[Process Payment]\n"
            "    ProcessPayment --> PaymentSuccess{Payment OK?}\n"
            "    PaymentSuccess -->|Yes| ConfirmOrder[Confirm Order]\n"
            "    PaymentSuccess -->|No| RetryCount{Retries < 3?}\n"
            "    \n"
            "    RetryCount -->|Yes| Delay[Wait 5 seconds]\n"
            "    Delay --> ProcessPayment\n"
            "    RetryCount -->|No| ReleaseReservation[Release Reservation]\n"
            "    ReleaseReservation --> NotifyFailure[Notify: Payment Failed]\n"
            "    NotifyFailure --> End\n"
            "    \n"
            "    ConfirmOrder --> SendEmail[Send Confirmation Email]\n"
            "    SendEmail --> End"
        ),
    },
    {
        "instruction": "Generate sequence diagram with error handling and rollback.",
        "input": "Distributed transaction: API calls multiple services, rolls back if any fail",
        "output": (
            "sequenceDiagram\n"
            "    participant Client\n"
            "    participant API\n"
            "    participant InventoryService\n"
            "    participant PaymentService\n"
            "    participant ShippingService\n"
            "    \n"
            "    Client->>+API: POST /orders\n"
            "    API->>+InventoryService: Reserve Items\n"
            "    InventoryService-->>-API: Reserved (ID: 123)\n"
            "    \n"
            "    API->>+PaymentService: Charge Payment\n"
            "    PaymentService-->>-API: Success (TxnID: 456)\n"
            "    \n"
            "    API->>+ShippingService: Create Shipment\n"
            "    ShippingService-->>-API: Error: Address Invalid\n"
            "    \n"
            "    Note over API: Rollback transaction\n"
            "    API->>+PaymentService: Refund (TxnID: 456)\n"
            "    PaymentService-->>-API: Refunded\n"
            "    \n"
            "    API->>+InventoryService: Release (ID: 123)\n"
            "    InventoryService-->>-API: Released\n"
            "    \n"
            "    API-->>-Client: 400 Bad Request"
        ),
    },
    {
        "instruction": "Generate class diagram with inheritance, interfaces, and composition.",
        "input": "E-commerce: Product hierarchy with abstract base, concrete types, and shared interfaces",
        "output": (
            "classDiagram\n"
            "    class Product {\n"
            "        <<abstract>>\n"
            "        +string id\n"
            "        +string name\n"
            "        +decimal price\n"
            "        +calculateTax() decimal\n"
            "        +getDescription()* string\n"
            "    }\n"
            "    \n"
            "    class PhysicalProduct {\n"
            "        +decimal weight\n"
            "        +Dimensions dimensions\n"
            "        +getDescription() string\n"
            "        +calculateShipping() decimal\n"
            "    }\n"
            "    \n"
            "    class DigitalProduct {\n"
            "        +string downloadUrl\n"
            "        +int fileSize\n"
            "        +getDescription() string\n"
            "        +generateDownloadLink() string\n"
            "    }\n"
            "    \n"
            "    class IShippable {\n"
            "        <<interface>>\n"
            "        +calculateShipping() decimal\n"
            "        +getShippingMethod() string\n"
            "    }\n"
            "    \n"
            "    class IDiscountable {\n"
            "        <<interface>>\n"
            "        +applyDiscount(decimal) decimal\n"
            "        +isEligibleForDiscount() bool\n"
            "    }\n"
            "    \n"
            "    class Dimensions {\n"
            "        +decimal length\n"
            "        +decimal width\n"
            "        +decimal height\n"
            "    }\n"
            "    \n"
            "    Product <|-- PhysicalProduct\n"
            "    Product <|-- DigitalProduct\n"
            "    IShippable <|.. PhysicalProduct\n"
            "    IDiscountable <|.. Product\n"
            "    PhysicalProduct *-- Dimensions"
        ),
    },
    {
        "instruction": "Generate state diagram with nested states and parallel regions.",
        "input": "Complex order workflow with payment and fulfillment happening in parallel",
        "output": (
            "stateDiagram-v2\n"
            "    [*] --> Pending\n"
            "    Pending --> Processing : submit\n"
            "    \n"
            "    state Processing {\n"
            "        [*] --> PaymentProcessing\n"
            "        [*] --> FulfillmentProcessing\n"
            "        --\n"
            "        PaymentProcessing --> PaymentComplete\n"
            "        FulfillmentProcessing --> FulfillmentComplete\n"
            "    }\n"
            "    \n"
            "    Processing --> Completed : both_complete\n"
            "    Processing --> Failed : either_failed\n"
            "    Failed --> Cancelled : cancel\n"
            "    Failed --> Processing : retry\n"
            "    Completed --> [*]\n"
            "    Cancelled --> [*]"
        ),
    },
    
    # === MULTI-FILE PROTOTYPE EXAMPLES ===
    # Complete, working prototypes with proper file structure
    
    {
        "instruction": "Generate complete Angular feature module with routing, service, and components.",
        "input": "Feature: Product catalog with list, detail, and search",
        "output": (
            "### FILE: product-catalog.module.ts\n"
            "```typescript\n"
            "import { NgModule } from '@angular/core';\n"
            "import { CommonModule } from '@angular/common';\n"
            "import { RouterModule, Routes } from '@angular/router';\n"
            "import { FormsModule, ReactiveFormsModule } from '@angular/forms';\n"
            "\n"
            "import { ProductListComponent } from './product-list/product-list.component';\n"
            "import { ProductDetailComponent } from './product-detail/product-detail.component';\n"
            "import { ProductSearchComponent } from './product-search/product-search.component';\n"
            "import { ProductService } from './services/product.service';\n"
            "\n"
            "const routes: Routes = [\n"
            "  { path: '', component: ProductListComponent },\n"
            "  { path: 'search', component: ProductSearchComponent },\n"
            "  { path: ':id', component: ProductDetailComponent }\n"
            "];\n"
            "\n"
            "@NgModule({\n"
            "  declarations: [\n"
            "    ProductListComponent,\n"
            "    ProductDetailComponent,\n"
            "    ProductSearchComponent\n"
            "  ],\n"
            "  imports: [\n"
            "    CommonModule,\n"
            "    FormsModule,\n"
            "    ReactiveFormsModule,\n"
            "    RouterModule.forChild(routes)\n"
            "  ],\n"
            "  providers: [ProductService]\n"
            "})\n"
            "export class ProductCatalogModule { }\n"
            "```\n"
            "\n"
            "### FILE: services/product.service.ts\n"
            "```typescript\n"
            "import { Injectable } from '@angular/core';\n"
            "import { HttpClient } from '@angular/common/http';\n"
            "import { Observable, of } from 'rxjs';\n"
            "import { catchError, map } from 'rxjs/operators';\n"
            "\n"
            "export interface Product {\n"
            "  id: number;\n"
            "  name: string;\n"
            "  price: number;\n"
            "  description: string;\n"
            "  category: string;\n"
            "}\n"
            "\n"
            "@Injectable()\n"
            "export class ProductService {\n"
            "  private apiUrl = '/api/products';\n"
            "\n"
            "  constructor(private http: HttpClient) {}\n"
            "\n"
            "  getProducts(): Observable<Product[]> {\n"
            "    return this.http.get<Product[]>(this.apiUrl)\n"
            "      .pipe(\n"
            "        catchError(err => {\n"
            "          console.error('Error fetching products:', err);\n"
            "          return of([]);\n"
            "        })\n"
            "      );\n"
            "  }\n"
            "\n"
            "  getProduct(id: number): Observable<Product | null> {\n"
            "    return this.http.get<Product>(`${this.apiUrl}/${id}`)\n"
            "      .pipe(\n"
            "        catchError(err => {\n"
            "          console.error(`Error fetching product ${id}:`, err);\n"
            "          return of(null);\n"
            "        })\n"
            "      );\n"
            "  }\n"
            "\n"
            "  searchProducts(query: string): Observable<Product[]> {\n"
            "    return this.http.get<Product[]>(`${this.apiUrl}/search`, {\n"
            "      params: { q: query }\n"
            "    }).pipe(\n"
            "      catchError(err => {\n"
            "        console.error('Search error:', err);\n"
            "        return of([]);\n"
            "      })\n"
            "    );\n"
            "  }\n"
            "}\n"
            "```\n"
            "\n"
            "### FILE: product-list/product-list.component.ts\n"
            "```typescript\n"
            "import { Component, OnInit } from '@angular/core';\n"
            "import { Product, ProductService } from '../services/product.service';\n"
            "\n"
            "@Component({\n"
            "  selector: 'app-product-list',\n"
            "  templateUrl: './product-list.component.html',\n"
            "  styleUrls: ['./product-list.component.scss']\n"
            "})\n"
            "export class ProductListComponent implements OnInit {\n"
            "  products: Product[] = [];\n"
            "  loading = true;\n"
            "  error: string | null = null;\n"
            "\n"
            "  constructor(private productService: ProductService) {}\n"
            "\n"
            "  ngOnInit(): void {\n"
            "    this.loadProducts();\n"
            "  }\n"
            "\n"
            "  loadProducts(): void {\n"
            "    this.loading = true;\n"
            "    this.productService.getProducts().subscribe({\n"
            "      next: (products) => {\n"
            "        this.products = products;\n"
            "        this.loading = false;\n"
            "      },\n"
            "      error: (err) => {\n"
            "        this.error = 'Failed to load products';\n"
            "        this.loading = false;\n"
            "      }\n"
            "    });\n"
            "  }\n"
            "}\n"
            "```"
        ),
    },
    
    # === API DOCUMENTATION COMPLETENESS ===
    {
        "instruction": "Generate complete API documentation for a CRUD resource with all endpoints.",
        "input": "API: User management with full CRUD, filtering, pagination, and bulk operations",
        "output": (
            "# User Management API\n"
            "\n"
            "## Base URL\n"
            "`https://api.example.com/v1`\n"
            "\n"
            "## Authentication\n"
            "All endpoints require Bearer token authentication.\n"
            "```\n"
            "Authorization: Bearer <token>\n"
            "```\n"
            "\n"
            "## Endpoints\n"
            "\n"
            "### 1. List Users\n"
            "**GET** `/users`\n"
            "\n"
            "Retrieve a paginated list of users.\n"
            "\n"
            "**Query Parameters:**\n"
            "- `page` (integer, optional): Page number (default: 1)\n"
            "- `per_page` (integer, optional): Items per page (default: 20, max: 100)\n"
            "- `sort` (string, optional): Sort field (name, email, created_at)\n"
            "- `order` (string, optional): Sort order (asc, desc)\n"
            "- `status` (string, optional): Filter by status (active, inactive, suspended)\n"
            "- `search` (string, optional): Search by name or email\n"
            "\n"
            "**Response:** 200 OK\n"
            "```json\n"
            "{\n"
            '  "data": [\n'
            "    {\n"
            '      "id": 1,\n'
            '      "name": "John Doe",\n'
            '      "email": "john@example.com",\n'
            '      "status": "active",\n'
            '      "created_at": "2024-01-15T10:30:00Z",\n'
            '      "updated_at": "2024-01-20T14:15:00Z"\n'
            "    }\n"
            "  ],\n"
            '  "pagination": {\n'
            '    "current_page": 1,\n'
            '    "per_page": 20,\n'
            '    "total": 150,\n'
            '    "total_pages": 8\n'
            "  }\n"
            "}\n"
            "```\n"
            "\n"
            "**Error Responses:**\n"
            "- `401 Unauthorized`: Missing or invalid token\n"
            "- `403 Forbidden`: Insufficient permissions\n"
            "- `422 Unprocessable Entity`: Invalid query parameters\n"
            "\n"
            "### 2. Get User\n"
            "**GET** `/users/{id}`\n"
            "\n"
            "Retrieve a single user by ID.\n"
            "\n"
            "**Path Parameters:**\n"
            "- `id` (integer, required): User ID\n"
            "\n"
            "**Response:** 200 OK\n"
            "```json\n"
            "{\n"
            '  "id": 1,\n'
            '  "name": "John Doe",\n'
            '  "email": "john@example.com",\n'
            '  "status": "active",\n'
            '  "role": "user",\n'
            '  "phone": "+1234567890",\n'
            '  "created_at": "2024-01-15T10:30:00Z",\n'
            '  "updated_at": "2024-01-20T14:15:00Z",\n'
            '  "last_login": "2024-02-01T08:00:00Z"\n'
            "}\n"
            "```\n"
            "\n"
            "**Error Responses:**\n"
            "- `404 Not Found`: User does not exist\n"
            "- `401 Unauthorized`: Missing or invalid token\n"
            "\n"
            "### 3. Create User\n"
            "**POST** `/users`\n"
            "\n"
            "Create a new user.\n"
            "\n"
            "**Request Body:**\n"
            "```json\n"
            "{\n"
            '  "name": "Jane Smith",\n'
            '  "email": "jane@example.com",\n'
            '  "password": "SecureP@ssw0rd",\n'
            '  "role": "user",\n'
            '  "phone": "+1234567890"\n'
            "}\n"
            "```\n"
            "\n"
            "**Validation Rules:**\n"
            "- `name`: Required, 2-100 characters\n"
            "- `email`: Required, valid email format, unique\n"
            "- `password`: Required, min 8 characters, must contain uppercase, lowercase, number, special char\n"
            "- `role`: Optional, one of: user, admin, moderator (default: user)\n"
            "- `phone`: Optional, valid phone number format\n"
            "\n"
            "**Response:** 201 Created\n"
            "```json\n"
            "{\n"
            '  "id": 2,\n'
            '  "name": "Jane Smith",\n'
            '  "email": "jane@example.com",\n'
            '  "status": "active",\n'
            '  "role": "user",\n'
            '  "created_at": "2024-02-05T09:00:00Z"\n'
            "}\n"
            "```\n"
            "\n"
            "**Error Responses:**\n"
            "- `400 Bad Request`: Invalid request body\n"
            "- `422 Unprocessable Entity`: Validation errors\n"
            "```json\n"
            "{\n"
            '  "error": "Validation failed",\n'
            '  "details": {\n'
            '    "email": ["Email already exists"],\n'
            '    "password": ["Password must contain at least one uppercase letter"]\n'
            "  }\n"
            "}\n"
            "```\n"
            "\n"
            "### 4. Update User\n"
            "**PUT** `/users/{id}`\n"
            "\n"
            "Update an existing user (full update).\n"
            "\n"
            "**PATCH** `/users/{id}`\n"
            "\n"
            "Partially update an existing user.\n"
            "\n"
            "**Request Body:**\n"
            "```json\n"
            "{\n"
            '  "name": "John Updated",\n'
            '  "phone": "+9876543210"\n'
            "}\n"
            "```\n"
            "\n"
            "**Response:** 200 OK\n"
            "```json\n"
            "{\n"
            '  "id": 1,\n'
            '  "name": "John Updated",\n'
            '  "email": "john@example.com",\n'
            '  "phone": "+9876543210",\n'
            '  "updated_at": "2024-02-05T10:00:00Z"\n'
            "}\n"
            "```\n"
            "\n"
            "**Error Responses:**\n"
            "- `404 Not Found`: User does not exist\n"
            "- `422 Unprocessable Entity`: Validation errors\n"
            "\n"
            "### 5. Delete User\n"
            "**DELETE** `/users/{id}`\n"
            "\n"
            "Soft delete a user (sets status to 'deleted').\n"
            "\n"
            "**Response:** 204 No Content\n"
            "\n"
            "**Error Responses:**\n"
            "- `404 Not Found`: User does not exist\n"
            "- `409 Conflict`: Cannot delete user with active orders\n"
            "\n"
            "### 6. Bulk Operations\n"
            "**POST** `/users/bulk`\n"
            "\n"
            "Perform bulk operations on multiple users.\n"
            "\n"
            "**Request Body:**\n"
            "```json\n"
            "{\n"
            '  "action": "update_status",\n'
            '  "ids": [1, 2, 3],\n'
            '  "data": {\n'
            '    "status": "suspended"\n'
            "  }\n"
            "}\n"
            "```\n"
            "\n"
            "**Supported Actions:**\n"
            "- `update_status`: Update status for multiple users\n"
            "- `delete`: Delete multiple users\n"
            "- `export`: Export user data (returns CSV)\n"
            "\n"
            "**Response:** 200 OK\n"
            "```json\n"
            "{\n"
            '  "success": 3,\n'
            '  "failed": 0,\n'
            '  "errors": []\n'
            "}\n"
            "```\n"
            "\n"
            "## Rate Limiting\n"
            "- 100 requests per minute per IP\n"
            "- 1000 requests per hour per user\n"
            "- Headers returned:\n"
            "  - `X-RateLimit-Limit`: Maximum requests allowed\n"
            "  - `X-RateLimit-Remaining`: Requests remaining\n"
            "  - `X-RateLimit-Reset`: Unix timestamp when limit resets\n"
            "\n"
            "## Webhooks\n"
            "Configure webhooks to receive notifications:\n"
            "- `user.created`\n"
            "- `user.updated`\n"
            "- `user.deleted`"
        ),
    },
] + RUBY_EXAMPLES + LARAVEL_EXAMPLES + MOBILE_EXAMPLES + TESTING_EXAMPLES


@dataclass
class DatasetReport:
    total_examples: int
    source_examples: int
    feedback_examples: int
    unique_files: int
    artifact_breakdown: Dict[str, int] = field(default_factory=dict)
    top_files: List[Tuple[str, int]] = field(default_factory=list)
    discarded_chunks: int = 0


class FineTuningDatasetBuilder:
    """Build instruction datasets from meeting notes and repository context."""

    def __init__(self, meeting_notes: str, max_chunks: int = 500):
        self.settings = load_finetuning_settings()
        self.meeting_notes = meeting_notes.strip()
        self.meeting_summary = " ".join(self.meeting_notes.split()[:120])
        self.max_chunks = max_chunks or self.settings.get("max_chunks", 500)
        configured_min = self.settings.get("min_examples", MIN_DATASET_SIZE)
        configured_target = self.settings.get("target_examples", DEFAULT_TARGET_EXAMPLES)
        configured_max = self.settings.get("max_examples", MAX_DATASET_SIZE)
        self.min_examples = max(MIN_DATASET_SIZE, int(configured_min))
        self.target_examples = max(self.min_examples, int(configured_target))
        self.max_examples = max(self.target_examples, int(configured_max))
        self.project_root = self._detect_project_root()
        self.user_project_dirs = [p.resolve() for p in get_user_project_directories()]
        self._intent_tokens = self._extract_intents(self.meeting_notes)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def build_incremental_dataset(self) -> Tuple[List[Dict[str, str]], DatasetReport]:
        """
        Build a minimal dataset containing ONLY feedback examples.
        Use this for incremental fine-tuning when you just want to train on user corrections
        without rebuilding the entire dataset from the repository.
        
        Returns:
            Tuple of (training_examples, report)
        """
        feedback_examples = feedback_store.to_training_examples()
        
        if not feedback_examples:
            raise ValueError("No feedback examples available for incremental training.")
        
        report = DatasetReport(
            total_examples=len(feedback_examples),
            source_examples=0,
            feedback_examples=len(feedback_examples),
            unique_files=0,
            artifact_breakdown=self._summarise_artifact_types(feedback_examples),
            top_files=[],
            discarded_chunks=0,
        )
        
        return feedback_examples, report
    
    def build_dataset(self, limit: Optional[int] = None) -> Tuple[List[Dict[str, str]], DatasetReport]:
        if not self.meeting_notes:
            raise ValueError("Meeting notes are required to build the dataset.")

        limit = limit or self.settings.get("max_chunks", self.max_chunks)
        chunks, chunk_metadata = self._retrieve_ranked_chunks(limit)
        training_examples, counts, discarded = self._synthesize_examples(chunks)

        if not training_examples:
            repo_fallback, repo_counts = self._generate_repo_wide_examples(set(), self.target_examples)
            if not repo_fallback:
                raise ValueError("No training examples could be generated from the provided meeting notes.")
            training_examples = repo_fallback
            counts = repo_counts
            chunk_metadata = [
                {
                    "path": path,
                    "score": 0.0,
                    "matched_intents": ["repo_fallback"],
                    "original_score": 0.0,
                }
                for path in repo_counts.keys()
            ]

        counts_counter = Counter(counts)
        normalized_exclusions: Set[str] = set()
        for path_key in counts_counter.keys():
            try:
                normalized_exclusions.add(str(Path(path_key).resolve()))
            except Exception:
                normalized_exclusions.add(path_key)

        # Always include core mermaid/html training snippets so models nail diagram transformations
        builtin_examples = self._generate_builtin_artifact_examples()
        builtin_count = len(builtin_examples)
        print(f"[DEBUG] Generated {builtin_count} builtin examples")
        print(f"[DEBUG] Training examples before builtin: {len(training_examples)}")
        if builtin_examples:
            training_examples.extend(builtin_examples)
            counts_counter["__builtin__/mermaid_examples.md"] += len(builtin_examples)
        print(f"[DEBUG] Training examples after builtin: {len(training_examples)}")

        # Attach feedback entries (if any)
        feedback_examples = feedback_store.to_training_examples()
        for idx, example in enumerate(feedback_examples):
            example.setdefault("source", "feedback")
            example.setdefault("source_path", f"__feedback__/entry_{idx}")
        training_examples.extend(feedback_examples)

        # If we're still below the target, sweep the repo to add more supervised pairs
        repo_examples: List[Dict[str, str]] = []
        needed = self.target_examples - len(training_examples)
        if needed > 0:
            remaining_capacity = max(0, self.max_examples - len(training_examples))
            sweep_slots = min(needed, remaining_capacity)
            repo_examples, repo_counts = self._generate_repo_wide_examples(
                exclude_paths=normalized_exclusions,
                remaining_slots=sweep_slots,
            )
            training_examples.extend(repo_examples)
            for path, count in repo_counts.items():
                counts_counter[path] += count

        # Hard cap at configured max examples
        if len(training_examples) > self.max_examples:
            training_examples = training_examples[: self.max_examples]

        # Recompute counts after potential truncation
        final_counts: Counter[str] = Counter()
        for example in training_examples:
            final_counts[example.get("source_path", "__unknown__")] += 1

        report = DatasetReport(
            total_examples=len(training_examples),
            source_examples=max(0, len(training_examples) - len(feedback_examples) - builtin_count),
            feedback_examples=len(feedback_examples),
            unique_files=len({p for p in final_counts.keys() if not p.startswith("__builtin__/") and not p.startswith("__feedback__/")}),
            artifact_breakdown=self._summarise_artifact_types(training_examples),
            top_files=sorted(final_counts.items(), key=lambda item: item[1], reverse=True)[:10],
            discarded_chunks=discarded,
        )

        self._persist_sources(chunk_metadata)
        return training_examples, report

    # ------------------------------------------------------------------
    # Chunk retrieval
    # ------------------------------------------------------------------
    def _retrieve_ranked_chunks(self, limit: int) -> Tuple[List[Tuple[Dict[str, str], float]], List[Dict[str, Any]]]:
        queries = self._build_queries()

        from rag.retrieve import merge_rerank, vector_search, bm25_search, load_docs_from_chroma
        from rag.utils import BM25Index, chroma_client
        from rag.filters import load_cfg
        import chromadb

        cfg = load_cfg()
        
        # Try to get existing client first to avoid "already exists" error
        try:
            client = chroma_client(cfg["store"]["path"])
        except (ValueError, RuntimeError) as e:
            # If client already exists with different settings, use the existing one
            if "already exists" in str(e).lower():
                try:
                    # Get the existing client using chromadb.PersistentClient
                    client = chromadb.PersistentClient(path=cfg["store"]["path"])
                except Exception as e2:
                    print(f"[FINETUNING][ERROR] Failed to connect to Chroma: {e2}")
                    # Return empty results if we can't connect
                    return [], []
            else:
                raise
        
        collection = client.get_or_create_collection("repo", metadata={"hnsw:space": "cosine"})
        docs = load_docs_from_chroma(collection)
        bm25 = BM25Index(docs)

        scored_chunks: List[Tuple[Dict[str, str], float]] = []
        metadata: List[Dict[str, Any]] = []
        seen_keys = set()

        # Balance coverage with stability; exceeding ~600 hits can cause HNSW issues
        retrieval_limit = min(600, max(400, limit * 2))
        
        for query in queries:
            try:
                vec_hits = vector_search(collection, query, min(retrieval_limit, cfg["hybrid"]["k_vector"] * 4))
            except RuntimeError as exc:
                print(f"[FINETUNING][WARN] Vector search fallback triggered: {exc}")
                vec_hits = []
            bm25_hits = bm25_search(bm25, query, min(retrieval_limit, cfg["hybrid"]["k_bm25"] * 4))
            merged_hits = merge_rerank(vec_hits, bm25_hits, min(retrieval_limit, cfg["hybrid"]["k_final"] * 4))

            for doc, score in merged_hits:
                key = f"{doc['meta'].get('path')}::{doc['meta'].get('chunk')}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                path_str = doc["meta"].get("path", "")
                if not self._is_user_project_path(path_str):
                    continue

                adjusted_score, matched_intents = self._score_chunk(doc, score)
                
                # Filter out low-scoring or non-matching chunks
                if adjusted_score < 0 or not matched_intents:
                    continue

                scored_chunks.append((doc, adjusted_score))
                metadata.append(
                    {
                        "path": doc["meta"].get("path"),
                        "score": adjusted_score,
                        "matched_intents": matched_intents,
                        "original_score": score,
                    }
                )

        # Log chunk selection for verification
        print(f"[FINETUNING] Retrieved {len(scored_chunks)} candidate chunks (pre-enforcement)")
        
        scored_chunks, metadata = self._enforce_intent_coverage(scored_chunks, metadata, limit)
        
        print(f"[FINETUNING] Final selection: {len(scored_chunks)} chunks after intent coverage enforcement")
        
        # Write debug file for inspection
        try:
            output_dir = Path("outputs/finetuning")
            output_dir.mkdir(parents=True, exist_ok=True)
            debug_file = output_dir / "chunk_selection_debug.json"
            
            debug_data = {
                "total_selected": len(metadata),
                "queries_used": queries,
                "top_20_files": sorted(
                    [(m["path"], m["score"]) for m in metadata[:20]],
                    key=lambda x: x[1],
                    reverse=True
                ),
                "all_chunks": metadata
            }
            
            debug_file.write_text(json.dumps(debug_data, indent=2), encoding="utf-8")
            print(f"[FINETUNING] Chunk selection saved to: {debug_file}")
        except Exception as e:
            print(f"[WARN] Could not write debug file: {e}")
        
        return scored_chunks, metadata

    def _build_queries(self) -> List[str]:
        """Build focused queries from meeting note intents (bullets/headings)."""
        queries: List[str] = []
        
        # Split meeting notes by structural markers (bullets, headings, numbered lists)
        lines = self.meeting_notes.splitlines()
        intent_lines: List[str] = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped or len(stripped) < 10:
                continue
            
            # Detect intent lines: headings, bullets, numbered items
            is_heading = stripped.startswith("#")
            is_bullet = any(stripped.startswith(m) for m in ["-", "*", "•", "–"])
            is_numbered = bool(re.match(r"^\d+[\.)]\s", stripped))
            
            if is_heading or is_bullet or is_numbered:
                # Clean markers
                cleaned = re.sub(r"^#+\s*", "", stripped)
                cleaned = re.sub(r"^[-*•–]\s*", "", cleaned)
                cleaned = re.sub(r"^\d+[\.)]\s*", "", cleaned)
                if len(cleaned) > 10:
                    intent_lines.append(cleaned)
        
        # If no structure found, generate multiple queries from the text
        if not intent_lines:
            # Split by sentences and extract meaningful queries
            sentences = re.split(r'[.!?]\s+', self.meeting_notes)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20:  # Only use substantial sentences
                    intent_lines.append(sentence[:150])
            
            # Also add sliding window chunks for broader coverage
            if len(self.meeting_notes) > 100:
                chunk_size = 200
                overlap = 50
                for i in range(0, len(self.meeting_notes), chunk_size - overlap):
                    chunk = self.meeting_notes[i:i + chunk_size]
                    if len(chunk) > 50:
                        intent_lines.append(chunk)
            
            # Fallback: use the full notes
            if not intent_lines:
                intent_lines = [self.meeting_notes[:500]]
        
        # Convert each intent line to a query (first 120 chars for broader matching)
        for intent_line in intent_lines[:30]:  # Increase from 20 to 30 queries
            queries.append(intent_line[:120])  # Increase from 80 to 120 chars
        
        print(f"[FINETUNING] Extracted {len(queries)} intent queries from meeting notes")
        return queries

    def _score_chunk(self, doc: Dict[str, str], base_score: float) -> Tuple[float, List[str]]:
        path = (doc.get("meta") or {}).get("path", "")
        content = doc.get("content", "")
        path_lower = path.lower()
        score = base_score

        # HARD EXCLUSIONS: scaffolding/template files and generated files
        hard_exclude_patterns = [
            "weatherforecast",
            "sampledata",
            "sample_data",
            "example",
            "template",
            "scaffold",
            "test_",
            "_test",
            ".test.",
            ".spec.",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            ".min.js",
            ".min.css",
            "node_modules",
            "dist/",
            "build/",
            ".generated.",
        ]
        
        for pattern in hard_exclude_patterns:
            if pattern in path_lower:
                return -999.0, []
        
        preferred_paths = [p.lower() for p in self.settings.get("preferred_paths", [])]
        exclude_paths = [p.lower() for p in self.settings.get("exclude_paths", [])]

        if any(excl in path_lower for excl in exclude_paths):
            score -= 2.0

        if any(pref in path_lower for pref in preferred_paths):
            score += 0.6
        
        # Boost files that match meeting note keywords in path
        meeting_keywords = self._tokenize(self.meeting_notes)
        path_tokens = self._tokenize(path_lower)
        keyword_overlap = meeting_keywords & path_tokens
        if len(keyword_overlap) >= 2:
            score += 0.8

        extension = Path(path).suffix.lower()
        if extension in {".ts", ".tsx", ".html", ".scss", ".cs"}:
            score += 0.2

        content_tokens = self._tokenize(content)
        min_overlap = 3  # STRICT: require 3 token overlap with at least one intent
        matched_intents: List[str] = []

        for idx, tokens in enumerate(self._intent_tokens):
            if not tokens:
                continue
            overlap = content_tokens & tokens
            if len(overlap) >= min_overlap:
                matched_intents.append(f"intent_{idx}")
                score += 0.1
        
        # REJECT chunks with no intent match
        if not matched_intents:
            return -999.0, []

        return score, matched_intents

    def _enforce_intent_coverage(
        self,
        scored_chunks: List[Tuple[Dict[str, str], float]],
        metadata: List[Dict[str, Any]],
        limit: int,
    ) -> Tuple[List[Tuple[Dict[str, str], float]], List[Dict[str, Any]]]:
        if not scored_chunks:
            return scored_chunks, metadata

        combined = list(zip(scored_chunks, metadata))
        combined.sort(key=lambda item: item[0][1], reverse=True)

        selected: List[Tuple[Dict[str, str], float]] = []
        selected_meta: List[Dict[str, Any]] = []
        used_keys: Set[str] = set()

        # ensure each intent represented
        for intent_idx in range(len(self._intent_tokens)):
            intent_key = f"intent_{intent_idx}"
            for (doc, score), meta in combined:
                key = f"{doc['meta'].get('path')}::{doc['meta'].get('chunk')}"
                if key in used_keys:
                    continue
                if intent_key in meta["matched_intents"]:
                    selected.append((doc, score))
                    selected_meta.append(meta)
                    used_keys.add(key)
                    break

        # fill remaining slots by overall score
        for (doc, score), meta in combined:
            if len(selected) >= limit:
                break
            key = f"{doc['meta'].get('path')}::{doc['meta'].get('chunk')}"
            if key in used_keys:
                continue
            selected.append((doc, score))
            selected_meta.append(meta)
            used_keys.add(key)

        return selected[:limit], selected_meta[:limit]

    # ------------------------------------------------------------------
    # Example generation
    # ------------------------------------------------------------------
    def _synthesize_examples(
        self, chunks: Sequence[Tuple[Dict[str, str], float]]
    ) -> Tuple[List[Dict[str, str]], Dict[str, int], int]:
        examples: List[Dict[str, str]] = []
        file_counts: Dict[str, int] = {}
        discarded = 0

        for doc, _ in chunks:
            metadata = doc.get("meta", {})
            content = doc.get("content", "").strip()
            if not content or len(content) < 40:
                discarded += 1
                continue

            file_path = metadata.get("path", "unknown")
            file_counts[file_path] = file_counts.get(file_path, 0) + 1

            file_type = self._detect_file_type(file_path, content)
            examples.extend(self._generate_examples_for_chunk(file_type, file_path, content, source="rag"))

        return examples, file_counts, discarded

    def _generate_examples_for_chunk(
        self, file_type: str, file_path: str, content: str, source: str = "rag"
    ) -> List[Dict[str, str]]:
        """Generate MULTIPLE variations per code file to reach 5000+ examples."""
        trimmed_output = content[:1200] + ("..." if len(content) > 1200 else "")
        
        # Extract actual class/component names from path
        file_name = Path(file_path).name
        component_name = Path(file_path).stem.replace(".component", "").replace(".service", "").replace("Controller", "")
        
        base_input = (
            f"File: {file_path}\n"
            f"Component/Class: {component_name}\n"
            f"Meeting Context: {self.meeting_summary}\n\n"
            f"Code:\n{trimmed_output}"
        )

        # Create 8-10 variations per file to scale up dataset
        examples = [
            {
                "instruction": f"Generate code for {component_name} following the patterns in {file_name}.",
                "input": base_input,
                "output": trimmed_output,
                "source": source,
                "source_path": file_path,
            },
            {
                "instruction": f"Implement {component_name} based on repository structure and meeting notes.",
                "input": f"Context: {self.meeting_summary}\n\nReference:\n{trimmed_output}",
                "output": trimmed_output,
                "source": source,
                "source_path": file_path,
            },
            {
                "instruction": f"Create a {file_type} component similar to {file_name}.",
                "input": f"Reference implementation:\n{trimmed_output}",
                "output": trimmed_output,
                "source": source,
                "source_path": file_path,
            },
            {
                "instruction": f"Adapt this {component_name} pattern for a new feature.",
                "input": f"Meeting notes: {self.meeting_summary}\n\nTemplate:\n{trimmed_output}",
                "output": trimmed_output,
                "source": source,
                "source_path": file_path,
            },
            {
                "instruction": f"Write {component_name} following the coding standards shown in the codebase.",
                "input": base_input,
                "output": trimmed_output,
                "source": source,
                "source_path": file_path,
            },
            {
                "instruction": f"Replicate the structure and patterns from {file_name}.",
                "input": f"Example code:\n{trimmed_output}",
                "output": trimmed_output,
                "source": source,
                "source_path": file_path,
            },
        ]

        if file_type in {"angular_component", "angular_template"}:
            examples.extend([
                {
                    "instruction": "Update the Angular component to match project styling and layout conventions.",
                    "input": base_input,
                    "output": self._generate_angular_component_stub(content, file_path),
                    "source": source,
                    "source_path": file_path,
                },
                {
                    "instruction": f"Build an Angular component like {component_name} with the same structure.",
                    "input": f"Template:\n{trimmed_output}",
                    "output": trimmed_output,
                    "source": source,
                    "source_path": file_path,
                },
            ])

        if file_type == "angular_style":
            examples.extend([
                {
                    "instruction": "Apply SCSS adjustments that align with the shared palette and typography used in the Angular app.",
                    "input": base_input,
                    "output": self._generate_style_stub(content, file_path),
                    "source": source,
                    "source_path": file_path,
                },
                {
                    "instruction": f"Create styles following the patterns in {file_name}.",
                    "input": f"Reference:\n{trimmed_output}",
                    "output": trimmed_output,
                    "source": source,
                    "source_path": file_path,
                },
            ])

        if file_type == "angular_service":
            examples.extend([
                {
                    "instruction": "Produce Angular service methods for calling the backend API defined in the repository.",
                    "input": base_input,
                    "output": self._generate_service_stub(content, file_path),
                    "source": source,
                    "source_path": file_path,
                },
                {
                    "instruction": f"Implement a service similar to {component_name} for API communication.",
                    "input": f"Pattern:\n{trimmed_output}",
                    "output": trimmed_output,
                    "source": source,
                    "source_path": file_path,
                },
            ])

        if file_type in {"dotnet_controller", "dotnet_service", "dotnet_dto"}:
            examples.extend([
                {
                    "instruction": "Generate .NET API documentation and ensure DTOs mirror existing naming and validation patterns.",
                    "input": base_input,
                    "output": self._generate_dotnet_stub(content, file_path),
                    "source": source,
                    "source_path": file_path,
                },
                {
                    "instruction": f"Create a .NET {file_type} following the MongoDB integration pattern.",
                    "input": f"Meeting: {self.meeting_summary}\n\nExample:\n{trimmed_output}",
                    "output": trimmed_output,
                    "source": source,
                    "source_path": file_path,
                },
                {
                    "instruction": f"Build {component_name} with the same dependency injection and data access patterns.",
                    "input": f"Reference:\n{trimmed_output}",
                    "output": trimmed_output,
                    "source": source,
                    "source_path": file_path,
                },
            ])

        if file_type in {"model", "entity"}:
            examples.append(
                {
                    "instruction": "Produce an ERD snippet for the following model definitions.",
                    "input": base_input,
                    "output": self._generate_erd_stub(content, file_path),
                    "source": source,
                    "source_path": file_path,
                }
            )

        if file_type in {
            "controller",
            "service",
            "component",
            "angular_component",
            "angular_service",
            "dotnet_controller",
            "dotnet_service",
        }:
            examples.append(
                {
                    "instruction": "Outline the system architecture showing how this component interacts with others in the repository.",
                    "input": base_input,
                    "output": self._generate_architecture_stub(content, file_path),
                    "source": source,
                    "source_path": file_path,
                }
            )

        return examples

    def _generate_builtin_artifact_examples(self) -> List[Dict[str, str]]:
        builtin_path = "__builtin__/mermaid_examples.md"
        print(f"[DEBUG] BUILTIN_MERMAID_ARTIFACTS has {len(BUILTIN_MERMAID_ARTIFACTS)} examples")
        try:
            examples = [
                {
                    **template,
                    "source": "builtin",
                    "source_path": builtin_path,
                }
                for template in BUILTIN_MERMAID_ARTIFACTS
            ]
            print(f"[DEBUG] Successfully created {len(examples)} builtin examples")
            return examples
        except Exception as e:
            print(f"[ERROR] Failed to generate builtin examples: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _generate_repo_wide_examples(
        self,
        exclude_paths: Set[str],
        remaining_slots: int,
    ) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
        if remaining_slots <= 0:
            return [], {}

        additional_examples: List[Dict[str, str]] = []
        additional_counts: Dict[str, int] = {}

        candidate_files: List[Path] = []
        excluded_count = 0
        total_scanned = 0
        
        print(f"[DATASET_BUILD] Scanning user project directories: {[str(d) for d in self.user_project_dirs]}")
        
        for directory in self.user_project_dirs:
            if not directory.exists():
                continue
            for path in directory.rglob("*"):
                total_scanned += 1
                if path.is_dir():
                    continue
                suffix = path.suffix.lower()
                if suffix not in SUPPORTED_DATASET_EXTENSIONS:
                    continue
                normalized = str(path.resolve())
                if normalized in exclude_paths:
                    excluded_count += 1
                    continue
                if normalized.startswith(str(self.project_root / "architect_ai_cursor_poc")):
                    excluded_count += 1
                    continue
                try:
                    if should_exclude_path(path):
                        excluded_count += 1
                        continue
                except Exception:
                    continue
                try:
                    if path.stat().st_size > MAX_FILE_BYTES:
                        excluded_count += 1
                        continue
                except OSError:
                    continue
                candidate_files.append(path)
        
        print(f"[DATASET_BUILD] Scanned {total_scanned} items, found {len(candidate_files)} valid files, excluded {excluded_count}")
        if candidate_files:
            print(f"[DATASET_BUILD] Sample files: {[str(f) for f in candidate_files[:5]]}")

        # Prioritize smaller files for more diverse coverage first
        candidate_files.sort(key=lambda p: p.stat().st_size if p.exists() else MAX_FILE_BYTES)

        for file_path in candidate_files:
            if len(additional_examples) >= remaining_slots:
                break

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            if len(content.strip()) < 40:
                continue

            repo_examples = self._generate_examples_for_chunk(
                self._detect_file_type(str(file_path), content),
                str(file_path),
                content,
                source="repo",
            )

            if not repo_examples:
                continue

            slots_left = remaining_slots - len(additional_examples)
            if len(repo_examples) > slots_left:
                repo_examples = repo_examples[:slots_left]

            additional_examples.extend(repo_examples)
            additional_counts[str(file_path)] = additional_counts.get(str(file_path), 0) + len(repo_examples)

        return additional_examples, additional_counts

    # ------------------------------------------------------------------
    # Helper stubs
    # ------------------------------------------------------------------
    def _detect_file_type(self, file_path: str, content: str) -> str:
        path_lower = file_path.lower()
        content_lower = content.lower()

        if path_lower.endswith(ANGULAR_COMPONENT_SUFFIX):
            return "angular_component"
        if path_lower.endswith(ANGULAR_TEMPLATE_SUFFIX):
            return "angular_template"
        if path_lower.endswith(ANGULAR_STYLE_SUFFIX):
            return "angular_style"
        if path_lower.endswith(ANGULAR_SERVICE_SUFFIX):
            return "angular_service"
        if path_lower.endswith(DOTNET_CONTROLLER_SUFFIX):
            return "dotnet_controller"
        if path_lower.endswith(DOTNET_DTO_SUFFIX):
            return "dotnet_dto"
        if path_lower.endswith(DOTNET_SERVICE_SUFFIX):
            return "dotnet_service"
        if any(token in path_lower for token in ["model", "entity", "schema"]):
            return "model"
        if ".cs" in path_lower and "dto" in path_lower:
            return "dotnet_dto"
        if ".cs" in path_lower and "service" in path_lower:
            return "dotnet_service"
        if ".cs" in path_lower and "controller" in path_lower:
            return "dotnet_controller"
        if "component" in path_lower:
            return "component"
        if "service" in path_lower:
            return "service"
        if any(keyword in content_lower for keyword in ["class ", "interface ", "record "]):
            return "entity"
        return "general"

    def _generate_angular_component_stub(self, content: str, file_path: str) -> str:
        """Return actual Angular component code to teach YOUR project patterns."""
        # Return the ACTUAL code so the model learns YOUR component structure,
        # template syntax, data binding patterns, etc.
        return content

    def _generate_style_stub(self, content: str, file_path: str) -> str:
        """Return actual SCSS code to teach YOUR project styling patterns."""
        # Return the ACTUAL styles so the model learns YOUR design system,
        # color scheme, spacing, typography, etc.
        return content

    def _generate_service_stub(self, content: str, file_path: str) -> str:
        """Return actual Angular service code to teach YOUR project patterns."""
        # Return the ACTUAL code so the model learns YOUR patterns, not generic templates
        return content

    def _generate_dotnet_stub(self, content: str, file_path: str) -> str:
        """Return actual .NET code to teach YOUR project patterns."""
        # Return the ACTUAL code so the model learns YOUR MongoDB integration,
        # DTO patterns, Controller structure, etc.
        return content

    def _generate_erd_stub(self, content: str, file_path: str) -> str:
        """Generate ERD from actual code structure, learning YOUR data modeling style."""
        # Extract entity name and properties from actual code
        entity = Path(file_path).stem.replace("Dto", "").replace(".", "_").title()
        
        # Try to extract actual properties from the code
        properties = []
        for line in content.split('\n'):
            # Match C# properties: public Type Name { get; set; }
            match = re.search(r'public\s+(\w+)\s+(\w+)\s*\{', line)
            if match:
                prop_type, prop_name = match.groups()
                # Map C# types to ERD types
                erd_type = {
                    'int': 'int', 'string': 'string', 'bool': 'boolean',
                    'DateTime': 'datetime', 'decimal': 'decimal', 'double': 'double',
                    'Guid': 'string', 'ObjectId': 'string'
                }.get(prop_type, 'string')
                
                # Determine if it's a PK or FK
                key_type = ''
                if 'Id' in prop_name and prop_name == 'Id':
                    key_type = ' PK'
                elif prop_name.endswith('Id'):
                    key_type = ' FK'
                
                properties.append(f"        {erd_type} {prop_name}{key_type}")
        
        if not properties:
            # Fallback if no properties extracted
            properties = [
                "        string id PK",
                "        string name",
                "        datetime createdAt"
            ]
        
        return (
            "erDiagram\n"
            f"    {entity} {{\n"
            + "\n".join(properties) + "\n"
            "    }"
        )

    def _generate_architecture_stub(self, content: str, file_path: str) -> str:
        """Extract architecture diagram concepts from actual code structure."""
        # Analyze the actual code to generate architecture showing YOUR patterns
        component = Path(file_path).stem.replace(".", "_").replace("Controller", "API").replace("Service", "BusinessLogic")
        
        # Detect architecture patterns from content
        has_controller = "Controller" in content or "[ApiController]" in content
        has_service = "Service" in content or "IService" in content
        has_repository = "Repository" in content or "IRepository" in content
        has_mongodb = "MongoClient" in content or "IMongoDBSettings" in content
        has_dto = "Dto" in content
        
        # Build architecture reflecting YOUR actual stack
        layers = []
        layers.append(f"    Client --> {component}")
        
        if has_controller:
            layers.append(f"    {component} --> ServiceLayer")
        if has_service:
            layers.append("    ServiceLayer --> DataAccess")
        if has_repository:
            layers.append("    DataAccess --> Repository")
        if has_mongodb:
            layers.append("    DataAccess --> MongoDB[(MongoDB)]")
        if has_dto:
            layers.append(f"    {component} -.->|returns| DTO")
        
        return (
            "graph TD\n"
            + "\n".join(layers or ["    Client --> API", "    API --> MongoDB"])
        )

    def _infer_resource_names(self, file_path: str) -> Tuple[str, str]:
        """Derive a REST resource slug and a PascalCase model name from a file path."""
        name = Path(file_path).stem.lower()
        for suffix in [".service", ".component", "controller", ".dto", ".spec"]:
            name = name.replace(suffix, "")
        # resource slug for URLs
        slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-") or "resource"
        # PascalCase model name
        parts = re.split(r"[^a-z0-9]+", name)
        model = "".join(p.capitalize() for p in parts if p) or "Record"
        return slug, model

    def _summarise_artifact_types(self, examples: Iterable[Dict[str, str]]) -> Dict[str, int]:
        summary: Dict[str, int] = {"code": 0, "erd": 0, "architecture": 0, "api": 0, "ui": 0, "style": 0}
        for example in examples:
            instruction = example.get("instruction", "").lower()
            if "erd" in instruction:
                summary["erd"] += 1
            elif "architecture" in instruction:
                summary["architecture"] += 1
            elif "api" in instruction:
                summary["api"] += 1
            elif "scss" in instruction or "style" in instruction:
                summary["style"] += 1
            elif "angular" in instruction or "component" in instruction:
                summary["ui"] += 1
            else:
                summary["code"] += 1
        return summary

    def _generate_builtin_artifact_examples(self) -> List[Dict[str, str]]:
        """Generate examples from BUILTIN_MERMAID_ARTIFACTS + ALL_EXPANDED_EXAMPLES (100+ examples)."""
        examples: List[Dict[str, str]] = []
        
        # Original builtin examples
        for artifact in BUILTIN_MERMAID_ARTIFACTS:
            instruction = artifact["instruction"]
            input_text = artifact["input"]
            output_text = artifact["output"]
            source_path = f"__builtin__/mermaid_examples.md"

            examples.append({
                "instruction": instruction,
                "input": input_text,
                "output": output_text,
                "source": "builtin_mermaid",
                "source_path": source_path,
            })
        
        # Add 100+ expanded artifact examples (ERDs, architectures, sequences, code)
        for idx, artifact in enumerate(ALL_EXPANDED_EXAMPLES):
            instruction = artifact["instruction"]
            input_text = artifact["input"]
            output_text = artifact["output"]
            source_path = f"__builtin__/expanded_examples_{idx}.md"

            examples.append({
                "instruction": instruction,
                "input": input_text,
                "output": output_text,
                "source": "expanded_artifacts",
                "source_path": source_path,
            })
        
        print(f"[DATASET] Generated {len(examples)} builtin artifact examples")
        return examples


    def _detect_project_root(self) -> Path:
        return get_user_project_root().resolve()

    def _is_user_project_path(self, path_str: str) -> bool:
        if not path_str:
            return False

        raw_path = Path(path_str)
        if not raw_path.is_absolute():
            raw_path = (self.project_root / raw_path).resolve()
        else:
            raw_path = raw_path.resolve()

        try:
            if should_exclude_path(raw_path):
                return False
        except Exception:
            pass

        return any(self._is_within_directory(raw_path, user_dir) for user_dir in self.user_project_dirs)

    @staticmethod
    def _is_within_directory(path: Path, directory: Path) -> bool:
        try:
            path.relative_to(directory)
            return True
        except ValueError:
            return False

    def _tokenize(self, text: str) -> Set[str]:
        return {
            token
            for token in re.findall(r"[A-Za-z0-9_]+", text.lower())
            if len(token) > 2
        }

    def _extract_intents(self, meeting_notes: str) -> List[Set[str]]:
        intents: List[Set[str]] = []
        if not meeting_notes:
            return intents

        markers = set(self.settings.get("intent_split_markers", ["-", "*", "•"]))
        for line in meeting_notes.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            while stripped and (
                stripped[0] in markers or stripped[0].isdigit() or stripped[0] in {".", ")"}
            ):
                stripped = stripped[1:].strip()
            tokens = self._tokenize(stripped)
            if tokens:
                intents.append(tokens)

        if not intents:
            intents.append(self._tokenize(meeting_notes))
        return intents

    def _persist_sources(self, metadata: List[Dict[str, Any]]) -> None:
        output_dir = Path("outputs/finetuning")
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "dataset_sources.json"
        path.write_text(json.dumps(metadata[:500], indent=2), encoding="utf-8")

