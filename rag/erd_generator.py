"""
ERD (Entity Relationship Diagram) Generator
Detects database/table discussions and generates ERD diagrams
"""

import re
from typing import List, Dict, Tuple, Optional

class ERDGenerator:
    """Generates ERD diagrams from meeting notes and requirements"""
    
    # Keywords that indicate database/table discussions
    DB_KEYWORDS = [
        'table', 'database', 'schema', 'entity', 'model',
        'column', 'field', 'primary key', 'foreign key',
        'relationship', 'one-to-many', 'many-to-many',
        'sql', 'nosql', 'mongodb', 'postgres', 'mysql',
        'collection', 'document', 'record'
    ]
    
    @staticmethod
    def detect_database_discussion(text: str) -> bool:
        """
        Detect if the text contains database/table discussions.
        
        Returns:
            True if database discussions are present
        """
        text_lower = text.lower()
        keyword_count = sum(1 for keyword in ERDGenerator.DB_KEYWORDS if keyword in text_lower)
        return keyword_count >= 3  # At least 3 database-related keywords
    
    @staticmethod
    def extract_table_mentions(text: str) -> List[str]:
        """
        Extract table/entity names from text.
        
        Returns:
            List of potential table names
        """
        tables = []
        
        # Pattern: "create table X", "table X", "X table"
        patterns = [
            r'create\s+table\s+(\w+)',
            r'table\s+(?:named\s+)?(\w+)',
            r'(\w+)\s+table',
            r'entity\s+(?:named\s+)?(\w+)',
            r'(\w+)\s+entity',
            r'model\s+(?:named\s+)?(\w+)',
            r'(\w+)\s+model'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            tables.extend(matches)
        
        # Clean and deduplicate
        tables = [t.strip().title() for t in tables if len(t) > 2]
        return list(set(tables))
    
    @staticmethod
    def generate_erd_prompt(meeting_notes: str, rag_context: str = "") -> str:
        """
        Generate a prompt for ERD diagram creation.
        
        Args:
            meeting_notes: The meeting notes text
            rag_context: RAG context from repository
            
        Returns:
            Prompt for LLM to generate ERD diagram
        """
        tables = ERDGenerator.extract_table_mentions(meeting_notes)
        
        prompt = f"""
You are a database architect. Generate an ERD (Entity Relationship Diagram) in Mermaid format.

MEETING NOTES:
{meeting_notes}

RAG CONTEXT (existing data models):
{rag_context}

DETECTED TABLES: {', '.join(tables) if tables else 'Extract from notes'}

OUTPUT RULES (CRITICAL):
1. First line MUST be: erDiagram
2. NO markdown blocks (NO ```, NO ```mermaid)
3. Use proper ERD syntax:
   - ENTITY_NAME {{
   -     type field_name
   - }}
4. Show relationships:
   - ENTITY1 ||--o{{ ENTITY2 : "relationship"
   - Use: ||--|| (one-to-one), ||--o{{ (one-to-many), }}--o{{ (many-to-many)
5. Include primary keys (PK) and foreign keys (FK)
6. Maximum 8 entities
7. Show only essential fields (3-5 per entity)

VALID EXAMPLE:
erDiagram
    USER ||--o{{ ORDER : places
    USER {{
        int id PK
        string email
        string name
    }}
    ORDER ||--|{{ ORDER_ITEM : contains
    ORDER {{
        int id PK
        int user_id FK
        date created_at
    }}
    PRODUCT ||--o{{ ORDER_ITEM : "ordered in"
    PRODUCT {{
        int id PK
        string name
        decimal price
    }}
    ORDER_ITEM {{
        int id PK
        int order_id FK
        int product_id FK
        int quantity
    }}

Generate a complete ERD diagram following these EXACT rules.
Focus on the entities and relationships discussed in the meeting notes.
"""
        return prompt
    
    @staticmethod
    def should_generate_erd(meeting_notes: str) -> bool:
        """
        Determine if ERD diagram should be generated.
        
        Returns:
            True if ERD generation is recommended
        """
        return ERDGenerator.detect_database_discussion(meeting_notes)


def get_erd_generator():
    """Get ERD generator instance"""
    return ERDGenerator()

