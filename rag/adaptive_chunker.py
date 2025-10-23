"""
Adaptive Chunking by Code Structure
Chunks code by AST (functions, classes) and documents by semantic sections
"""

from typing import List, Dict, Any
from pathlib import Path
import re

class AdaptiveChunker:
    """Chunk content adaptively based on structure"""
    
    def __init__(self):
        self.code_extensions = {'.py', '.ts', '.tsx', '.js', '.jsx', '.java', '.cs', '.go', '.rs'}
        self.doc_extensions = {'.md', '.txt', '.rst'}
    
    def chunk(self, file_path: str, content: str, max_tokens: int = 500) -> List[Dict[str, Any]]:
        """
        Chunk content adaptively based on file type
        
        Args:
            file_path: Path to the file
            content: File content
            max_tokens: Maximum tokens per chunk
        
        Returns:
            List of chunks with metadata
        """
        ext = Path(file_path).suffix.lower()
        
        if ext in self.code_extensions:
            return self._chunk_code(file_path, content, max_tokens)
        elif ext in self.doc_extensions:
            return self._chunk_document(file_path, content, max_tokens)
        else:
            return self._chunk_generic(file_path, content, max_tokens)
    
    def _chunk_code(self, file_path: str, content: str, max_tokens: int) -> List[Dict[str, Any]]:
        """Chunk code by logical units (functions, classes)"""
        ext = Path(file_path).suffix.lower()
        
        if ext == '.py':
            return self._chunk_python(file_path, content, max_tokens)
        elif ext in {'.ts', '.tsx', '.js', '.jsx'}:
            return self._chunk_typescript_javascript(file_path, content, max_tokens)
        elif ext == '.cs':
            return self._chunk_csharp(file_path, content, max_tokens)
        else:
            return self._chunk_generic(file_path, content, max_tokens)
    
    def _chunk_python(self, file_path: str, content: str, max_tokens: int) -> List[Dict[str, Any]]:
        """Chunk Python code by functions and classes"""
        chunks = []
        lines = content.split('\n')
        
        # Simple regex-based chunking (fallback if AST fails)
        current_chunk = []
        current_start = 0
        in_function = False
        in_class = False
        indent_level = 0
        
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            
            # Detect function or class definition
            if stripped.startswith('def ') or stripped.startswith('async def '):
                if current_chunk:
                    chunks.append(self._create_chunk(
                        file_path, '\n'.join(current_chunk), current_start, i-1
                    ))
                current_chunk = [line]
                current_start = i
                in_function = True
                indent_level = len(line) - len(stripped)
            
            elif stripped.startswith('class '):
                if current_chunk:
                    chunks.append(self._create_chunk(
                        file_path, '\n'.join(current_chunk), current_start, i-1
                    ))
                current_chunk = [line]
                current_start = i
                in_class = True
                indent_level = len(line) - len(stripped)
            
            else:
                current_chunk.append(line)
                
                # Check if we've exited the function/class
                if (in_function or in_class) and stripped and not line.startswith(' ' * (indent_level + 1)):
                    if len(line) - len(stripped) <= indent_level:
                        chunks.append(self._create_chunk(
                            file_path, '\n'.join(current_chunk), current_start, i
                        ))
                        current_chunk = []
                        current_start = i + 1
                        in_function = False
                        in_class = False
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                file_path, '\n'.join(current_chunk), current_start, len(lines)-1
            ))
        
        return chunks if chunks else [self._create_chunk(file_path, content, 0, len(lines)-1)]
    
    def _chunk_typescript_javascript(self, file_path: str, content: str, max_tokens: int) -> List[Dict[str, Any]]:
        """Chunk TypeScript/JavaScript by functions and classes"""
        chunks = []
        lines = content.split('\n')
        
        current_chunk = []
        current_start = 0
        brace_count = 0
        in_function = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Detect function/class/component
            if any(keyword in stripped for keyword in ['function ', 'class ', 'const ', 'export ', 'async ']):
                if '{' in stripped:
                    if current_chunk and brace_count == 0:
                        chunks.append(self._create_chunk(
                            file_path, '\n'.join(current_chunk), current_start, i-1
                        ))
                        current_chunk = []
                        current_start = i
                    in_function = True
            
            current_chunk.append(line)
            
            # Count braces
            brace_count += stripped.count('{') - stripped.count('}')
            
            # End of function/class
            if in_function and brace_count == 0 and '}' in stripped:
                chunks.append(self._create_chunk(
                    file_path, '\n'.join(current_chunk), current_start, i
                ))
                current_chunk = []
                current_start = i + 1
                in_function = False
        
        # Add remaining
        if current_chunk:
            chunks.append(self._create_chunk(
                file_path, '\n'.join(current_chunk), current_start, len(lines)-1
            ))
        
        return chunks if chunks else [self._create_chunk(file_path, content, 0, len(lines)-1)]
    
    def _chunk_csharp(self, file_path: str, content: str, max_tokens: int) -> List[Dict[str, Any]]:
        """Chunk C# by methods and classes"""
        # Similar to TypeScript chunking
        return self._chunk_typescript_javascript(file_path, content, max_tokens)
    
    def _chunk_document(self, file_path: str, content: str, max_tokens: int) -> List[Dict[str, Any]]:
        """Chunk markdown/text by headings"""
        chunks = []
        lines = content.split('\n')
        
        current_chunk = []
        current_start = 0
        current_heading = ""
        
        for i, line in enumerate(lines):
            # Detect markdown heading
            if line.startswith('#'):
                if current_chunk:
                    chunks.append(self._create_chunk(
                        file_path, '\n'.join(current_chunk), current_start, i-1,
                        extra_meta={'heading': current_heading}
                    ))
                current_chunk = [line]
                current_start = i
                current_heading = line.lstrip('#').strip()
            else:
                current_chunk.append(line)
        
        # Add remaining
        if current_chunk:
            chunks.append(self._create_chunk(
                file_path, '\n'.join(current_chunk), current_start, len(lines)-1,
                extra_meta={'heading': current_heading}
            ))
        
        return chunks if chunks else [self._create_chunk(file_path, content, 0, len(lines)-1)]
    
    def _chunk_generic(self, file_path: str, content: str, max_tokens: int) -> List[Dict[str, Any]]:
        """Generic sliding window chunking"""
        chunks = []
        lines = content.split('\n')
        
        # Estimate lines per chunk (rough: 1 line ≈ 10 tokens)
        lines_per_chunk = max(max_tokens // 10, 10)
        overlap = lines_per_chunk // 4
        
        for i in range(0, len(lines), lines_per_chunk - overlap):
            chunk_lines = lines[i:i + lines_per_chunk]
            if chunk_lines:
                chunks.append(self._create_chunk(
                    file_path, '\n'.join(chunk_lines), i, min(i + lines_per_chunk - 1, len(lines) - 1)
                ))
        
        return chunks if chunks else [self._create_chunk(file_path, content, 0, len(lines)-1)]
    
    def _create_chunk(self, file_path: str, content: str, start_line: int, end_line: int,
                     extra_meta: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a chunk with metadata"""
        chunk = {
            'id': f"{file_path}:{start_line}-{end_line}",
            'content': content,
            'meta': {
                'path': file_path,
                'file': Path(file_path).name,
                'start': start_line,
                'end': end_line,
                'lines': end_line - start_line + 1,
                'file_type': Path(file_path).suffix
            }
        }
        
        if extra_meta:
            chunk['meta'].update(extra_meta)
        
        return chunk


# Global chunker
_adaptive_chunker = None

def get_adaptive_chunker() -> AdaptiveChunker:
    """Get or create global adaptive chunker"""
    global _adaptive_chunker
    if _adaptive_chunker is None:
        _adaptive_chunker = AdaptiveChunker()
    return _adaptive_chunker

