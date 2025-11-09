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
You are a database architect. Generate an ERD (Entity Relationship Diagram) in Mermaid format for a NEW FEATURE.

CRITICAL INSTRUCTIONS - FOCUS ON THE NEW FEATURE:
- Analyze the MEETING NOTES below to identify the NEW FEATURE being requested
- Create entities and fields REQUIRED BY THIS NEW FEATURE
- Use RAG CONTEXT only for understanding existing database patterns (naming conventions, field types)
- DO NOT diagram the existing codebase - diagram the NEW FEATURE ONLY
- Extract specific requirements from meeting notes (e.g., "Phone Swap Request Feature" → PhoneSwapRequest entity)
- Include ALL relevant fields for the NEW feature (minimum 3-5 fields per entity)
- Use proper data types: int, string, decimal, date, boolean, etc.

**NEW FEATURE REQUIREMENTS (PRIMARY CONTEXT):**
{meeting_notes}

**EXISTING DATABASE PATTERNS (for reference only):**
{rag_context}

DETECTED TABLES FROM NOTES: {', '.join(tables) if tables else 'Extract from meeting notes'}

**DIAGRAM FOCUS:**
1. If meeting notes describe "Phone Swap Request Feature":
   - Create PhoneSwapRequest entity with fields: requesterId, requestedPhoneId, offeredPhoneId, status, requestDate, etc.
   - Show relationships to existing User/Phone entities (if mentioned)
   - DO NOT create generic User/Phone diagrams - focus on the SWAP REQUEST
2. If meeting notes describe a new registration API:
   - Create entities for the NEW registration flow
   - Reference existing patterns but diagram the NEW feature
3. Use meeting notes as the SOURCE OF TRUTH for what to diagram

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
6. Maximum 8 entities (focus on NEW feature entities)
7. Show only essential fields (3-5 per entity)

EXAMPLES:
✅ Good (Phone Swap Feature): 
PhoneSwapRequest {{ 
    int id PK 
    int requesterId FK
    int requestedPhoneId FK
    int offeredPhoneId FK
    string status
    datetime requestDate
    string reason
}}

❌ Bad (existing codebase focus):
User {{ int id PK, string email }}
Phone {{ int id PK, string model }}

**REMEMBER**: Diagram the NEW FEATURE from meeting notes, not the existing codebase!

Generate a complete ERD diagram following these EXACT rules.
Output ONLY the Mermaid ERD code. Start with 'erDiagram'.
NO markdown blocks, NO explanations after the diagram.
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

