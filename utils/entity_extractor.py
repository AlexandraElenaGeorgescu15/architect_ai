"""
Entity Extractor - Extract entities and fields from ERD diagrams
Enables project-specific code generation instead of generic scaffolding
"""

import re
from typing import Dict, List, Any, Optional
from pathlib import Path


class EntityField:
    """Represents a field in an entity"""
    def __init__(self, name: str, field_type: str, is_pk: bool = False, is_fk: bool = False):
        self.name = name
        self.field_type = field_type
        self.is_pk = is_pk
        self.is_fk = is_fk
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'type': self.field_type,
            'is_pk': self.is_pk,
            'is_fk': self.is_fk
        }
    
    def to_csharp_property(self) -> str:
        """Generate C# property declaration"""
        return f"public {self.field_type} {self.name} {{ get; set; }}"
    
    def to_typescript_property(self) -> str:
        """Generate TypeScript property declaration"""
        ts_type = {
            'int': 'number',
            'decimal': 'number',
            'DateTime': 'Date',
            'bool': 'boolean'
        }.get(self.field_type, 'string')
        return f"{self.name}: {ts_type};"


class Entity:
    """Represents an entity extracted from ERD"""
    def __init__(self, name: str, fields: List[EntityField]):
        self.name = name
        self.fields = fields
    
    @property
    def primary_key(self) -> Optional[EntityField]:
        """Get the primary key field"""
        for field in self.fields:
            if field.is_pk:
                return field
        return None
    
    @property
    def foreign_keys(self) -> List[EntityField]:
        """Get all foreign key fields"""
        return [f for f in self.fields if f.is_fk]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'fields': [f.to_dict() for f in self.fields],
            'has_id': self.primary_key is not None,
            'field_count': len(self.fields)
        }


class EntityRelationship:
    """Represents a relationship between entities"""
    def __init__(self, from_entity: str, to_entity: str, relationship_type: str, label: str):
        self.from_entity = from_entity
        self.to_entity = to_entity
        self.relationship_type = relationship_type  # one-to-one, one-to-many, many-to-many
        self.label = label
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'from': self.from_entity,
            'to': self.to_entity,
            'type': self.relationship_type,
            'label': self.label
        }


def map_mermaid_type_to_csharp(mermaid_type: str) -> str:
    """Map Mermaid ERD types to C# types"""
    type_map = {
        'int': 'int',
        'integer': 'int',
        'string': 'string',
        'text': 'string',
        'varchar': 'string',
        'decimal': 'decimal',
        'float': 'decimal',
        'money': 'decimal',
        'date': 'DateTime',
        'datetime': 'DateTime',
        'timestamp': 'DateTime',
        'boolean': 'bool',
        'bool': 'bool',
        'guid': 'Guid',
        'uuid': 'Guid'
    }
    return type_map.get(mermaid_type.lower(), 'string')


def map_mermaid_type_to_typescript(mermaid_type: str) -> str:
    """Map Mermaid ERD types to TypeScript types"""
    type_map = {
        'int': 'number',
        'integer': 'number',
        'decimal': 'number',
        'float': 'number',
        'money': 'number',
        'string': 'string',
        'text': 'string',
        'varchar': 'string',
        'date': 'Date',
        'datetime': 'Date',
        'timestamp': 'Date',
        'boolean': 'boolean',
        'bool': 'boolean',
        'guid': 'string',
        'uuid': 'string'
    }
    return type_map.get(mermaid_type.lower(), 'string')


def extract_entities_from_erd(erd_content: str) -> Dict[str, Any]:
    """
    Extract entities, fields, and relationships from ERD diagram.
    
    Parses Mermaid ERD syntax to extract:
    - Entity names
    - Field names and types
    - Primary and foreign keys
    - Relationships between entities
    
    Args:
        erd_content: Mermaid ERD diagram content
    
    Returns:
        Dictionary with entities, relationships, and metadata
    """
    entities = []
    relationships = []
    
    # Extract entity blocks: EntityName { field1 type1, field2 type2 }
    # Pattern handles multi-line entity definitions
    entity_pattern = r'(\w+)\s*\{([^}]+)\}'
    
    for match in re.finditer(entity_pattern, erd_content, re.MULTILINE):
        entity_name = match.group(1)
        fields_text = match.group(2)
        
        # Skip if this looks like a relationship or comment
        if entity_name.lower() in ['graph', 'erdiagram', 'flowchart']:
            continue
        
        # Extract individual fields
        # Pattern: type fieldName [PK] [FK] [NOT NULL] etc.
        field_pattern = r'(\w+)\s+(\w+)(?:\s+(PK|FK|NOT\s+NULL|UNIQUE))*'
        fields = []
        
        for field_match in re.finditer(field_pattern, fields_text):
            field_type = field_match.group(1)
            field_name = field_match.group(2)
            constraints = field_match.group(3) or ''
            
            # Skip if field_name looks like a constraint
            if field_name.upper() in ['PK', 'FK', 'NOT', 'NULL', 'UNIQUE']:
                continue
            
            # Map to C# type
            csharp_type = map_mermaid_type_to_csharp(field_type)
            
            field = EntityField(
                name=field_name,
                field_type=csharp_type,
                is_pk='PK' in constraints.upper() or 'pk' in fields_text.lower(),
                is_fk='FK' in constraints.upper() or 'fk' in fields_text.lower()
            )
            fields.append(field)
        
        if fields:  # Only add entities with valid fields
            entity = Entity(name=entity_name, fields=fields)
            entities.append(entity)
    
    # Extract relationships
    # Patterns: Entity1 ||--o{ Entity2 : label
    rel_patterns = [
        r'(\w+)\s+(\|\|--\|\|)\s+(\w+)\s+:\s+(\w+)',  # one-to-one
        r'(\w+)\s+(\|\|--o\{)\s+(\w+)\s+:\s+(\w+)',   # one-to-many
        r'(\w+)\s+(\}o--o\{)\s+(\w+)\s+:\s+(\w+)',    # many-to-many
    ]
    
    for pattern in rel_patterns:
        for match in re.finditer(pattern, erd_content):
            from_entity = match.group(1)
            rel_type_symbol = match.group(2)
            to_entity = match.group(3)
            label = match.group(4)
            
            # Determine relationship type
            rel_type = 'one-to-many'
            if '||--||' in rel_type_symbol:
                rel_type = 'one-to-one'
            elif '}o--o{' in rel_type_symbol or '}--o{' in rel_type_symbol:
                rel_type = 'many-to-many'
            
            relationship = EntityRelationship(
                from_entity=from_entity,
                to_entity=to_entity,
                relationship_type=rel_type,
                label=label
            )
            relationships.append(relationship)
    
    # Build result
    result = {
        'entities': [e.to_dict() for e in entities],
        'relationships': [r.to_dict() for r in relationships],
        'entity_names': [e.name for e in entities],
        'primary_entities': [e.name for e in entities if len(e.fields) > 2],  # Entities with more than just ID and name
        'entity_count': len(entities),
        'relationship_count': len(relationships)
    }
    
    return result


def extract_entities_from_file(erd_file_path: Path) -> Dict[str, Any]:
    """
    Extract entities from an ERD file.
    
    Args:
        erd_file_path: Path to the .mmd ERD file
    
    Returns:
        Dictionary with entities and relationships, or empty dict if file not found
    """
    if not erd_file_path.exists():
        print(f"[ENTITY_EXTRACTOR] ERD file not found: {erd_file_path}")
        return {
            'entities': [],
            'relationships': [],
            'entity_names': [],
            'primary_entities': [],
            'entity_count': 0,
            'relationship_count': 0
        }
    
    erd_content = erd_file_path.read_text(encoding='utf-8')
    result = extract_entities_from_erd(erd_content)
    
    print(f"[ENTITY_EXTRACTOR] Extracted {result['entity_count']} entities: {', '.join(result['entity_names'])}")
    print(f"[ENTITY_EXTRACTOR] Extracted {result['relationship_count']} relationships")
    
    return result


def get_entity_by_name(entities_data: Dict[str, Any], entity_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific entity by name"""
    for entity in entities_data.get('entities', []):
        if entity['name'] == entity_name:
            return entity
    return None


def generate_csharp_dto(entity: Dict[str, Any]) -> str:
    """Generate C# DTO class from entity"""
    class_name = f"{entity['name']}Dto"
    
    properties = []
    for field in entity['fields']:
        prop = f"    public {field['type']} {field['name']} {{ get; set; }}"
        properties.append(prop)
    
    dto_code = f"""public class {class_name}
{{
{chr(10).join(properties)}
}}"""
    
    return dto_code


def generate_typescript_interface(entity: Dict[str, Any]) -> str:
    """Generate TypeScript interface from entity"""
    interface_name = entity['name']
    
    properties = []
    for field in entity['fields']:
        # Map C# types to TypeScript
        ts_type = {
            'int': 'number',
            'decimal': 'number',
            'DateTime': 'Date',
            'bool': 'boolean',
            'Guid': 'string'
        }.get(field['type'], 'string')
        
        # Convert to camelCase for TypeScript
        field_name_camel = field['name'][0].lower() + field['name'][1:] if field['name'] else field['name']
        prop = f"  {field_name_camel}: {ts_type};"
        properties.append(prop)
    
    interface_code = f"""export interface {interface_name} {{
{chr(10).join(properties)}
}}"""
    
    return interface_code


if __name__ == "__main__":
    # Test with sample ERD
    sample_erd = """
erDiagram
    RequestSwap {
        int id PK
        string userId FK
        int phoneIdOffered FK
        int phoneIdRequested FK
        string status
        DateTime createdAt
    }
    Phone {
        int id PK
        string brand
        string model
        int storage
        decimal price
        string condition
    }
    User {
        int id PK
        string email
        string name
    }
    RequestSwap ||--o{ Phone : involves
    User ||--o{ RequestSwap : creates
"""
    
    result = extract_entities_from_erd(sample_erd)
    print(f"\nExtracted {result['entity_count']} entities:")
    for entity in result['entities']:
        print(f"  - {entity['name']} ({len(entity['fields'])} fields)")
    
    print(f"\nGenerated C# DTO:")
    print(generate_csharp_dto(result['entities'][0]))
    
    print(f"\nGenerated TypeScript interface:")
    print(generate_typescript_interface(result['entities'][0]))

