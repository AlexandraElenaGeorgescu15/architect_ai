"""
Database Migration Service

Production-grade database migration generation from ERD diagrams.
Supports multiple ORM frameworks and database systems:
- Entity Framework Core (C#/.NET)
- Django ORM (Python)
- Prisma (TypeScript/Node.js)
- Knex.js (JavaScript/Node.js)
- Raw SQL (PostgreSQL, MySQL, SQLite)
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MigrationFramework(str, Enum):
    """Supported migration frameworks."""
    EF_CORE = "ef_core"  # Entity Framework Core (C#)
    DJANGO = "django"  # Django migrations (Python)
    PRISMA = "prisma"  # Prisma (TypeScript)
    SQL_POSTGRES = "sql_postgres"  # Raw PostgreSQL
    SQL_MYSQL = "sql_mysql"  # Raw MySQL
    SQL_SQLITE = "sql_sqlite"  # Raw SQLite
    KNEX = "knex"  # Knex.js migrations


@dataclass
class ERDEntity:
    """Parsed entity from ERD diagram."""
    name: str
    fields: List[Dict[str, str]]  # {name, type, constraints}
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ERDRelationship:
    """Parsed relationship from ERD diagram."""
    source: str
    target: str
    relationship_type: str  # "one-to-one", "one-to-many", "many-to-many"
    label: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedMigration:
    """Generated migration result."""
    framework: str
    migration_name: str
    content: str
    entities_created: List[str]
    relationships_created: List[str]
    notes: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ERDParser:
    """Parses Mermaid ERD diagrams."""
    
    def parse(self, erd_content: str) -> Tuple[List[ERDEntity], List[ERDRelationship]]:
        """
        Parse a Mermaid ERD diagram.
        
        Args:
            erd_content: Mermaid ERD diagram string
            
        Returns:
            Tuple of (entities, relationships)
        """
        entities = []
        relationships = []
        
        # Clean up the content
        content = erd_content.strip()
        if content.startswith("```"):
            content = re.sub(r'^```(?:mermaid)?\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
        
        # Find all entity definitions
        entity_pattern = r'(\w+)\s*\{([^}]*)\}'
        for match in re.finditer(entity_pattern, content, re.DOTALL):
            entity_name = match.group(1)
            fields_text = match.group(2)
            fields = self._parse_fields(fields_text)
            
            entities.append(ERDEntity(name=entity_name, fields=fields))
        
        # Find all relationships
        rel_patterns = [
            # entity1 ||--o{ entity2 : "label"
            r'(\w+)\s*(\|\|--o\{|\}o--\|\||\|\|--\|\||\}o--o\{)\s*(\w+)\s*:\s*["\']?([^"\']+)?["\']?',
            # entity1 ||--|{ entity2
            r'(\w+)\s*(\|\|--\|\{|\}?\|--\|\||\|\|--o\|)\s*(\w+)',
        ]
        
        for pattern in rel_patterns:
            for match in re.finditer(pattern, content):
                groups = match.groups()
                source = groups[0]
                rel_symbol = groups[1]
                target = groups[2]
                label = groups[3] if len(groups) > 3 else None
                
                rel_type = self._parse_relationship_type(rel_symbol)
                
                relationships.append(ERDRelationship(
                    source=source,
                    target=target,
                    relationship_type=rel_type,
                    label=label
                ))
        
        logger.info(f"Parsed ERD: {len(entities)} entities, {len(relationships)} relationships")
        return entities, relationships
    
    def _parse_fields(self, fields_text: str) -> List[Dict[str, str]]:
        """Parse field definitions from entity body."""
        fields = []
        
        for line in fields_text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Parse: type name [constraint]
            parts = line.split()
            if len(parts) >= 2:
                field_type = parts[0]
                field_name = parts[1]
                constraints = parts[2] if len(parts) > 2 else ""
                
                fields.append({
                    "name": field_name,
                    "type": field_type,
                    "constraints": constraints
                })
        
        return fields
    
    def _parse_relationship_type(self, symbol: str) -> str:
        """Parse relationship type from Mermaid symbol."""
        if "o{" in symbol or "{o" in symbol:
            return "one-to-many"
        if "||--||" in symbol:
            return "one-to-one"
        if "o--o" in symbol or "}o--o{" in symbol:
            return "many-to-many"
        return "one-to-many"  # Default


class MigrationGenerator:
    """
    Generates database migrations from ERD diagrams.
    
    Features:
    - Parse Mermaid ERD diagrams
    - Generate migrations for multiple frameworks
    - Handle relationships and foreign keys
    - Include proper indexes and constraints
    """
    
    def __init__(self):
        self.erd_parser = ERDParser()
        
        # Type mappings for different frameworks
        self.type_mappings = {
            MigrationFramework.EF_CORE: {
                "int": "int",
                "string": "string",
                "datetime": "DateTime",
                "boolean": "bool",
                "decimal": "decimal",
                "text": "string",
                "float": "double",
                "uuid": "Guid",
            },
            MigrationFramework.DJANGO: {
                "int": "models.IntegerField()",
                "string": "models.CharField(max_length=255)",
                "datetime": "models.DateTimeField()",
                "boolean": "models.BooleanField(default=False)",
                "decimal": "models.DecimalField(max_digits=10, decimal_places=2)",
                "text": "models.TextField()",
                "float": "models.FloatField()",
                "uuid": "models.UUIDField()",
            },
            MigrationFramework.PRISMA: {
                "int": "Int",
                "string": "String",
                "datetime": "DateTime",
                "boolean": "Boolean",
                "decimal": "Decimal",
                "text": "String",
                "float": "Float",
                "uuid": "String @db.Uuid",
            },
            MigrationFramework.SQL_POSTGRES: {
                "int": "INTEGER",
                "string": "VARCHAR(255)",
                "datetime": "TIMESTAMP",
                "boolean": "BOOLEAN",
                "decimal": "DECIMAL(10,2)",
                "text": "TEXT",
                "float": "DOUBLE PRECISION",
                "uuid": "UUID",
            },
        }
    
    def generate_migration(
        self,
        erd_content: str,
        framework: MigrationFramework = MigrationFramework.EF_CORE,
        migration_name: Optional[str] = None
    ) -> GeneratedMigration:
        """
        Generate a migration from ERD diagram.
        
        Args:
            erd_content: Mermaid ERD diagram content
            framework: Target migration framework
            migration_name: Optional migration name
            
        Returns:
            GeneratedMigration with the migration code
        """
        # Parse ERD
        entities, relationships = self.erd_parser.parse(erd_content)
        
        if not entities:
            return GeneratedMigration(
                framework=framework.value,
                migration_name="Empty",
                content="// No entities found in ERD",
                entities_created=[],
                relationships_created=[],
                notes=["ERD parsing found no entities. Please check the diagram format."]
            )
        
        # Generate migration based on framework
        if framework == MigrationFramework.EF_CORE:
            content = self._generate_ef_core_migration(entities, relationships, migration_name)
        elif framework == MigrationFramework.DJANGO:
            content = self._generate_django_models(entities, relationships)
        elif framework == MigrationFramework.PRISMA:
            content = self._generate_prisma_schema(entities, relationships)
        elif framework in [MigrationFramework.SQL_POSTGRES, MigrationFramework.SQL_MYSQL, MigrationFramework.SQL_SQLITE]:
            content = self._generate_sql_migration(entities, relationships, framework)
        elif framework == MigrationFramework.KNEX:
            content = self._generate_knex_migration(entities, relationships, migration_name)
        else:
            content = self._generate_sql_migration(entities, relationships, MigrationFramework.SQL_POSTGRES)
        
        name = migration_name or f"Create{entities[0].name}Tables"
        
        return GeneratedMigration(
            framework=framework.value,
            migration_name=name,
            content=content,
            entities_created=[e.name for e in entities],
            relationships_created=[f"{r.source} -> {r.target}" for r in relationships],
            notes=self._generate_notes(entities, relationships)
        )
    
    def _generate_ef_core_migration(
        self,
        entities: List[ERDEntity],
        relationships: List[ERDRelationship],
        name: Optional[str]
    ) -> str:
        """Generate Entity Framework Core migration."""
        migration_name = name or f"Add{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        lines = [
            "using Microsoft.EntityFrameworkCore.Migrations;",
            "",
            "namespace YourNamespace.Migrations",
            "{",
            f"    public partial class {migration_name} : Migration",
            "    {",
            "        protected override void Up(MigrationBuilder migrationBuilder)",
            "        {",
        ]
        
        # Generate CreateTable for each entity
        for entity in entities:
            table_name = self._to_table_name(entity.name)
            lines.append(f"            migrationBuilder.CreateTable(")
            lines.append(f'                name: "{table_name}",')
            lines.append("                columns: table => new")
            lines.append("                {")
            
            for field in entity.fields:
                cs_type = self._map_type(field["type"], MigrationFramework.EF_CORE)
                constraints = field.get("constraints", "")
                nullable = "true" if "PK" not in constraints else "false"
                
                line = f'                    {field["name"]} = table.Column<{cs_type}>(nullable: {nullable})'
                
                if "PK" in constraints:
                    line += '\n                        .Annotation("SqlServer:Identity", "1, 1")'
                
                lines.append(line + ",")
            
            lines.append("                },")
            lines.append("                constraints: table =>")
            lines.append("                {")
            
            # Find primary key
            pk_field = next((f for f in entity.fields if "PK" in f.get("constraints", "")), None)
            if pk_field:
                lines.append(f'                    table.PrimaryKey("PK_{table_name}", x => x.{pk_field["name"]});')
            
            lines.append("                });")
            lines.append("")
        
        # Generate foreign keys for relationships
        for rel in relationships:
            source_table = self._to_table_name(rel.source)
            target_table = self._to_table_name(rel.target)
            fk_column = f"{rel.target}Id"
            
            lines.append(f"            migrationBuilder.AddForeignKey(")
            lines.append(f'                name: "FK_{source_table}_{target_table}",')
            lines.append(f'                table: "{source_table}",')
            lines.append(f'                column: "{fk_column}",')
            lines.append(f'                principalTable: "{target_table}",')
            lines.append(f'                principalColumn: "Id",')
            lines.append(f'                onDelete: ReferentialAction.Cascade);')
            lines.append("")
        
        lines.extend([
            "        }",
            "",
            "        protected override void Down(MigrationBuilder migrationBuilder)",
            "        {",
        ])
        
        # Generate DropTable for Down method
        for entity in reversed(entities):
            table_name = self._to_table_name(entity.name)
            lines.append(f'            migrationBuilder.DropTable(name: "{table_name}");')
        
        lines.extend([
            "        }",
            "    }",
            "}",
        ])
        
        return "\n".join(lines)
    
    def _generate_django_models(
        self,
        entities: List[ERDEntity],
        relationships: List[ERDRelationship]
    ) -> str:
        """Generate Django models."""
        lines = [
            "from django.db import models",
            "",
        ]
        
        for entity in entities:
            lines.append(f"class {entity.name}(models.Model):")
            
            for field in entity.fields:
                field_name = self._to_snake_case(field["name"])
                constraints = field.get("constraints", "")
                
                if "PK" in constraints:
                    # Skip ID field - Django adds it automatically
                    continue
                
                if "FK" in constraints:
                    # Find related model
                    related = field_name.replace("_id", "")
                    lines.append(f"    {related} = models.ForeignKey('{related.title()}', on_delete=models.CASCADE)")
                else:
                    django_type = self._map_type(field["type"], MigrationFramework.DJANGO)
                    lines.append(f"    {field_name} = {django_type}")
            
            lines.append("")
            lines.append("    class Meta:")
            lines.append(f"        db_table = '{self._to_table_name(entity.name)}'")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_prisma_schema(
        self,
        entities: List[ERDEntity],
        relationships: List[ERDRelationship]
    ) -> str:
        """Generate Prisma schema."""
        lines = [
            "// Prisma Schema",
            "// Generated from ERD diagram",
            "",
            "datasource db {",
            '  provider = "postgresql"',
            '  url      = env("DATABASE_URL")',
            "}",
            "",
            "generator client {",
            '  provider = "prisma-client-js"',
            "}",
            "",
        ]
        
        for entity in entities:
            lines.append(f"model {entity.name} {{")
            
            for field in entity.fields:
                prisma_type = self._map_type(field["type"], MigrationFramework.PRISMA)
                constraints = field.get("constraints", "")
                
                line = f"  {field['name']} {prisma_type}"
                
                if "PK" in constraints:
                    line += " @id @default(autoincrement())"
                if "UK" in constraints:
                    line += " @unique"
                
                lines.append(line)
            
            # Add relationships
            for rel in relationships:
                if rel.source == entity.name:
                    lines.append(f"  {rel.target.lower()}s {rel.target}[]")
                elif rel.target == entity.name:
                    lines.append(f"  {rel.source.lower()} {rel.source} @relation(fields: [{rel.source.lower()}Id], references: [id])")
                    lines.append(f"  {rel.source.lower()}Id Int")
            
            lines.append("}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_sql_migration(
        self,
        entities: List[ERDEntity],
        relationships: List[ERDRelationship],
        framework: MigrationFramework
    ) -> str:
        """Generate raw SQL migration."""
        lines = [
            "-- Migration generated from ERD diagram",
            f"-- Database: {framework.value.replace('sql_', '').upper()}",
            f"-- Generated: {datetime.now().isoformat()}",
            "",
        ]
        
        for entity in entities:
            table_name = self._to_table_name(entity.name)
            lines.append(f"CREATE TABLE {table_name} (")
            
            field_lines = []
            pk_field = None
            
            for field in entity.fields:
                sql_type = self._map_type(field["type"], MigrationFramework.SQL_POSTGRES)
                constraints = field.get("constraints", "")
                
                line = f"    {field['name']} {sql_type}"
                
                if "PK" in constraints:
                    pk_field = field["name"]
                    if framework == MigrationFramework.SQL_POSTGRES:
                        line = f"    {field['name']} SERIAL PRIMARY KEY"
                    else:
                        line += " PRIMARY KEY AUTO_INCREMENT"
                elif "NOT NULL" in constraints:
                    line += " NOT NULL"
                
                field_lines.append(line)
            
            lines.append(",\n".join(field_lines))
            lines.append(");")
            lines.append("")
        
        # Add foreign key constraints
        for rel in relationships:
            source_table = self._to_table_name(rel.source)
            target_table = self._to_table_name(rel.target)
            fk_column = f"{rel.target.lower()}_id"
            
            lines.append(f"ALTER TABLE {source_table}")
            lines.append(f"    ADD CONSTRAINT fk_{source_table}_{target_table}")
            lines.append(f"    FOREIGN KEY ({fk_column}) REFERENCES {target_table}(id);")
            lines.append("")
        
        # Add indexes
        lines.append("-- Indexes")
        for entity in entities:
            table_name = self._to_table_name(entity.name)
            for field in entity.fields:
                if "FK" in field.get("constraints", ""):
                    lines.append(f"CREATE INDEX idx_{table_name}_{field['name']} ON {table_name}({field['name']});")
        
        return "\n".join(lines)
    
    def _generate_knex_migration(
        self,
        entities: List[ERDEntity],
        relationships: List[ERDRelationship],
        name: Optional[str]
    ) -> str:
        """Generate Knex.js migration."""
        lines = [
            "// Knex.js Migration",
            f"// Generated: {datetime.now().isoformat()}",
            "",
            "exports.up = function(knex) {",
            "  return knex.schema",
        ]
        
        for idx, entity in enumerate(entities):
            table_name = self._to_table_name(entity.name)
            prefix = "    " if idx == 0 else "    ."
            
            lines.append(f"{prefix}createTable('{table_name}', function(table) {{")
            
            for field in entity.fields:
                constraints = field.get("constraints", "")
                
                if "PK" in constraints:
                    lines.append(f"      table.increments('{field['name']}').primary();")
                elif "FK" in constraints:
                    lines.append(f"      table.integer('{field['name']}').unsigned().references('id').inTable('target');")
                else:
                    knex_type = self._get_knex_type(field["type"])
                    lines.append(f"      table.{knex_type}('{field['name']}');")
            
            lines.append("      table.timestamps(true, true);")
            lines.append("    })")
        
        lines.append("};")
        lines.append("")
        lines.append("exports.down = function(knex) {")
        lines.append("  return knex.schema")
        
        for idx, entity in enumerate(reversed(entities)):
            table_name = self._to_table_name(entity.name)
            prefix = "    " if idx == 0 else "    ."
            lines.append(f"{prefix}dropTableIfExists('{table_name}')")
        
        lines.append("};")
        
        return "\n".join(lines)
    
    def _map_type(self, erd_type: str, framework: MigrationFramework) -> str:
        """Map ERD type to framework-specific type."""
        type_lower = erd_type.lower()
        mappings = self.type_mappings.get(framework, self.type_mappings[MigrationFramework.SQL_POSTGRES])
        return mappings.get(type_lower, mappings.get("string", "VARCHAR(255)"))
    
    def _get_knex_type(self, erd_type: str) -> str:
        """Get Knex.js column type."""
        type_map = {
            "int": "integer",
            "string": "string",
            "datetime": "datetime",
            "boolean": "boolean",
            "decimal": "decimal",
            "text": "text",
            "float": "float",
            "uuid": "uuid",
        }
        return type_map.get(erd_type.lower(), "string")
    
    def _to_table_name(self, entity_name: str) -> str:
        """Convert entity name to table name (snake_case, pluralized)."""
        # Convert PascalCase to snake_case
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()
        # Simple pluralization
        if snake.endswith('y'):
            return snake[:-1] + 'ies'
        elif snake.endswith('s'):
            return snake + 'es'
        return snake + 's'
    
    def _to_snake_case(self, name: str) -> str:
        """Convert to snake_case."""
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    
    def _generate_notes(
        self,
        entities: List[ERDEntity],
        relationships: List[ERDRelationship]
    ) -> List[str]:
        """Generate helpful notes about the migration."""
        notes = []
        
        notes.append(f"Created {len(entities)} tables")
        notes.append(f"Created {len(relationships)} foreign key relationships")
        
        # Check for missing IDs
        for entity in entities:
            has_pk = any("PK" in f.get("constraints", "") for f in entity.fields)
            if not has_pk:
                notes.append(f"Warning: {entity.name} has no primary key defined")
        
        return notes
    
    def get_available_frameworks(self) -> List[Dict[str, str]]:
        """Get list of available migration frameworks."""
        return [
            {"id": MigrationFramework.EF_CORE.value, "name": "Entity Framework Core (C#)", "language": "C#"},
            {"id": MigrationFramework.DJANGO.value, "name": "Django Models (Python)", "language": "Python"},
            {"id": MigrationFramework.PRISMA.value, "name": "Prisma Schema (TypeScript)", "language": "TypeScript"},
            {"id": MigrationFramework.SQL_POSTGRES.value, "name": "PostgreSQL", "language": "SQL"},
            {"id": MigrationFramework.SQL_MYSQL.value, "name": "MySQL", "language": "SQL"},
            {"id": MigrationFramework.SQL_SQLITE.value, "name": "SQLite", "language": "SQL"},
            {"id": MigrationFramework.KNEX.value, "name": "Knex.js (Node.js)", "language": "JavaScript"},
        ]


# Singleton instance
_migration_generator: Optional[MigrationGenerator] = None


def get_migration_generator() -> MigrationGenerator:
    """Get or create migration generator singleton."""
    global _migration_generator
    if _migration_generator is None:
        _migration_generator = MigrationGenerator()
    return _migration_generator
