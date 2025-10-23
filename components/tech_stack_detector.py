"""
Technology Stack Detection System.

Analyzes the repository to detect the technology stack and
provides appropriate configuration for prototype generation.

Author: Alexandra Georgescu
"""

from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class DetectedTechStack:
    """Complete technology stack detection result"""
    framework: str
    language: str
    styling: str
    components: List[str]
    api_tech: str
    confidence: float  # 0-100


class TechStackDetector:
    """
    Detects technology stack from repository structure and files.
    
    Supports: Angular, React, Vue, Blazor, WPF, Streamlit, Flask, Django,
    FastAPI, .NET API, Spring Boot, Express, and more.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize detector.
        
        Args:
            project_root: Root directory of project to analyze.
                         If None, looks for common project structures.
        """
        self.project_root = project_root or Path.cwd()
    
    def detect(self) -> DetectedTechStack:
        """
        Detect technology stack from project files.
        
        Returns:
            DetectedTechStack with all detected information
        """
        
        # Check for various tech stacks
        if self._is_angular():
            return self._detect_angular()
        elif self._is_react():
            return self._detect_react()
        elif self._is_vue():
            return self._detect_vue()
        elif self._is_blazor():
            return self._detect_blazor()
        elif self._is_wpf():
            return self._detect_wpf()
        elif self._is_streamlit():
            return self._detect_streamlit()
        elif self._is_flask():
            return self._detect_flask()
        elif self._is_django():
            return self._detect_django()
        elif self._is_fastapi():
            return self._detect_fastapi()
        elif self._is_dotnet_api():
            return self._detect_dotnet_api()
        elif self._is_spring_boot():
            return self._detect_spring_boot()
        elif self._is_express():
            return self._detect_express()
        else:
            return self._detect_generic_html()
    
    def _is_angular(self) -> bool:
        """Check if project is Angular"""
        return (self.project_root / "angular.json").exists() or \
               self._file_contains("package.json", "@angular/core")
    
    def _detect_angular(self) -> DetectedTechStack:
        """Detect Angular-specific stack"""
        components = []
        
        # Check for UI libraries
        if self._file_contains("package.json", "@angular/material"):
            components.append("Angular Material")
        if self._file_contains("package.json", "primeng"):
            components.append("PrimeNG")
        if self._file_contains("package.json", "ng-bootstrap"):
            components.append("ng-bootstrap")
        
        # Check for styling
        styling = "CSS"
        if (self.project_root / "src" / "styles.scss").exists():
            styling = "SCSS"
        elif (self.project_root / "src" / "styles.sass").exists():
            styling = "SASS"
        
        # Detect backend
        api_tech = self._detect_backend_tech()
        
        return DetectedTechStack(
            framework="Angular",
            language="TypeScript",
            styling=styling,
            components=components,
            api_tech=api_tech,
            confidence=95.0
        )
    
    def _is_react(self) -> bool:
        """Check if project is React"""
        return self._file_contains("package.json", "react") and \
               not self._file_contains("package.json", "@angular/core")
    
    def _detect_react(self) -> DetectedTechStack:
        """Detect React-specific stack"""
        components = []
        
        # Check for UI libraries
        if self._file_contains("package.json", "@mui/material"):
            components.append("Material-UI")
        if self._file_contains("package.json", "antd"):
            components.append("Ant Design")
        if self._file_contains("package.json", "react-bootstrap"):
            components.append("React Bootstrap")
        if self._file_contains("package.json", "chakra-ui"):
            components.append("Chakra UI")
        
        # Check language
        language = "JavaScript"
        if self._file_contains("package.json", "typescript"):
            language = "TypeScript"
        
        # Styling
        styling = "CSS"
        if self._file_contains("package.json", "styled-components"):
            styling = "Styled Components"
        elif self._file_contains("package.json", "emotion"):
            styling = "Emotion"
        elif self._file_contains("package.json", "sass"):
            styling = "SCSS"
        
        return DetectedTechStack(
            framework="React",
            language=language,
            styling=styling,
            components=components,
            api_tech=self._detect_backend_tech(),
            confidence=90.0
        )
    
    def _is_vue(self) -> bool:
        """Check if project is Vue"""
        return self._file_contains("package.json", "vue")
    
    def _detect_vue(self) -> DetectedTechStack:
        """Detect Vue-specific stack"""
        components = []
        
        if self._file_contains("package.json", "vuetify"):
            components.append("Vuetify")
        if self._file_contains("package.json", "element-plus"):
            components.append("Element Plus")
        
        return DetectedTechStack(
            framework="Vue",
            language="JavaScript",
            styling="CSS",
            components=components,
            api_tech=self._detect_backend_tech(),
            confidence=85.0
        )
    
    def _is_blazor(self) -> bool:
        """Check if project is Blazor"""
        return any((self.project_root / "**" / "*.razor").glob() for _ in [1])
    
    def _detect_blazor(self) -> DetectedTechStack:
        """Detect Blazor-specific stack"""
        return DetectedTechStack(
            framework="Blazor",
            language="C#",
            styling="CSS",
            components=["Bootstrap"],
            api_tech=".NET API",
            confidence=90.0
        )
    
    def _is_wpf(self) -> bool:
        """Check if project is WPF"""
        return any(self.project_root.rglob("*.xaml"))
    
    def _detect_wpf(self) -> DetectedTechStack:
        """Detect WPF-specific stack"""
        return DetectedTechStack(
            framework="WPF",
            language="C#",
            styling="XAML",
            components=[],
            api_tech=".NET API",
            confidence=95.0
        )
    
    def _is_streamlit(self) -> bool:
        """Check if project is Streamlit"""
        return self._file_contains("requirements.txt", "streamlit") or \
               any(self.project_root.rglob("*streamlit*.py"))
    
    def _detect_streamlit(self) -> DetectedTechStack:
        """Detect Streamlit-specific stack"""
        return DetectedTechStack(
            framework="Streamlit",
            language="Python",
            styling="Streamlit Components",
            components=[],
            api_tech="FastAPI" if self._file_contains("requirements.txt", "fastapi") else "Flask",
            confidence=85.0
        )
    
    def _is_flask(self) -> bool:
        """Check if project is Flask"""
        return self._file_contains("requirements.txt", "flask")
    
    def _detect_flask(self) -> DetectedTechStack:
        """Detect Flask-specific stack"""
        return DetectedTechStack(
            framework="Flask",
            language="Python",
            styling="CSS",
            components=["Jinja2"],
            api_tech="Flask",
            confidence=80.0
        )
    
    def _is_django(self) -> bool:
        """Check if project is Django"""
        return self._file_contains("requirements.txt", "django")
    
    def _detect_django(self) -> DetectedTechStack:
        """Detect Django-specific stack"""
        return DetectedTechStack(
            framework="Django",
            language="Python",
            styling="CSS",
            components=["Django Templates"],
            api_tech="Django REST",
            confidence=85.0
        )
    
    def _is_fastapi(self) -> bool:
        """Check if project is FastAPI"""
        return self._file_contains("requirements.txt", "fastapi")
    
    def _detect_fastapi(self) -> DetectedTechStack:
        """Detect FastAPI-specific stack"""
        return DetectedTechStack(
            framework="FastAPI",
            language="Python",
            styling="N/A",
            components=[],
            api_tech="FastAPI",
            confidence=85.0
        )
    
    def _is_dotnet_api(self) -> bool:
        """Check if project is .NET API"""
        return any(self.project_root.rglob("*.csproj")) and \
               any("Microsoft.AspNetCore" in f.read_text() 
                   for f in self.project_root.rglob("*.csproj") if f.is_file())
    
    def _detect_dotnet_api(self) -> DetectedTechStack:
        """Detect .NET API-specific stack"""
        return DetectedTechStack(
            framework=".NET API",
            language="C#",
            styling="N/A",
            components=[],
            api_tech=".NET Core",
            confidence=90.0
        )
    
    def _is_spring_boot(self) -> bool:
        """Check if project is Spring Boot"""
        return self._file_contains("pom.xml", "spring-boot") or \
               self._file_contains("build.gradle", "spring-boot")
    
    def _detect_spring_boot(self) -> DetectedTechStack:
        """Detect Spring Boot-specific stack"""
        return DetectedTechStack(
            framework="Spring Boot",
            language="Java",
            styling="N/A",
            components=[],
            api_tech="Spring Boot",
            confidence=85.0
        )
    
    def _is_express(self) -> bool:
        """Check if project is Express"""
        return self._file_contains("package.json", "express")
    
    def _detect_express(self) -> DetectedTechStack:
        """Detect Express-specific stack"""
        return DetectedTechStack(
            framework="Express",
            language="JavaScript",
            styling="CSS",
            components=[],
            api_tech="Express",
            confidence=80.0
        )
    
    def _detect_generic_html(self) -> DetectedTechStack:
        """Fallback to generic HTML/CSS/JS"""
        return DetectedTechStack(
            framework="HTML5",
            language="JavaScript",
            styling="CSS",
            components=[],
            api_tech="Unknown",
            confidence=50.0
        )
    
    def _detect_backend_tech(self) -> str:
        """Detect backend/API technology"""
        if any(self.project_root.rglob("*.csproj")):
            return ".NET API"
        elif self._file_contains("pom.xml", "spring"):
            return "Spring Boot"
        elif self._file_contains("requirements.txt", "fastapi"):
            return "FastAPI"
        elif self._file_contains("requirements.txt", "flask"):
            return "Flask"
        elif self._file_contains("requirements.txt", "django"):
            return "Django"
        elif self._file_contains("package.json", "express"):
            return "Express"
        else:
            return "Unknown"
    
    def _file_contains(self, filename: str, search_term: str) -> bool:
        """Check if file exists and contains search term"""
        file_path = self.project_root / filename
        if not file_path.exists():
            return False
        
        try:
            content = file_path.read_text(encoding='utf-8')
            return search_term.lower() in content.lower()
        except Exception:
            return False


def get_tech_stack_from_context(rag_context: str) -> DetectedTechStack:
    """
    Extract tech stack from RAG context string.
    
    Args:
        rag_context: Retrieved RAG context about the repository
        
    Returns:
        DetectedTechStack based on context analysis
    """
    context_lower = rag_context.lower()
    
    # Angular detection
    if "angular" in context_lower or "@angular" in context_lower:
        components = []
        if "material" in context_lower:
            components.append("Angular Material")
        
        return DetectedTechStack(
            framework="Angular",
            language="TypeScript",
            styling="SCSS" if "scss" in context_lower else "CSS",
            components=components,
            api_tech=".NET" if ".net" in context_lower or "csharp" in context_lower else "Unknown",
            confidence=85.0
        )
    
    # React detection
    elif "react" in context_lower:
        components = []
        if "material" in context_lower or "mui" in context_lower:
            components.append("Material-UI")
        
        return DetectedTechStack(
            framework="React",
            language="TypeScript" if "typescript" in context_lower else "JavaScript",
            styling="CSS",
            components=components,
            api_tech="Express" if "express" in context_lower else "Unknown",
            confidence=80.0
        )
    
    # Vue detection
    elif "vue" in context_lower:
        return DetectedTechStack(
            framework="Vue",
            language="JavaScript",
            styling="CSS",
            components=[],
            api_tech="Unknown",
            confidence=75.0
        )
    
    # Blazor detection
    elif "blazor" in context_lower or (".razor" in context_lower and "csharp" in context_lower):
        return DetectedTechStack(
            framework="Blazor",
            language="C#",
            styling="CSS",
            components=["Bootstrap"],
            api_tech=".NET API",
            confidence=85.0
        )
    
    # WPF detection
    elif "wpf" in context_lower or "xaml" in context_lower:
        return DetectedTechStack(
            framework="WPF",
            language="C#",
            styling="XAML",
            components=[],
            api_tech=".NET",
            confidence=90.0
        )
    
    # Python frameworks
    elif "streamlit" in context_lower:
        return DetectedTechStack(
            framework="Streamlit",
            language="Python",
            styling="Streamlit",
            components=[],
            api_tech="FastAPI" if "fastapi" in context_lower else "Flask",
            confidence=85.0
        )
    
    elif "django" in context_lower:
        return DetectedTechStack(
            framework="Django",
            language="Python",
            styling="CSS",
            components=["Django Templates"],
            api_tech="Django REST",
            confidence=80.0
        )
    
    elif "flask" in context_lower:
        return DetectedTechStack(
            framework="Flask",
            language="Python",
            styling="CSS",
            components=["Jinja2"],
            api_tech="Flask",
            confidence=75.0
        )
    
    # Fallback
    else:
        return DetectedTechStack(
            framework="HTML5",
            language="JavaScript",
            styling="CSS",
            components=[],
            api_tech="Unknown",
            confidence=50.0
        )

