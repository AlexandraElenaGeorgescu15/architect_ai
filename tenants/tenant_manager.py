"""
Multi-Tenant Support System
Manages multiple organizations/projects with isolated data
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
from pathlib import Path
import hashlib

@dataclass
class TenantConfig:
    """Tenant configuration"""
    tenant_id: str
    name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    config: Dict[str, Any] = field(default_factory=dict)
    rag_index_name: str = ""
    api_keys: Dict[str, str] = field(default_factory=dict)
    usage_limits: Dict[str, int] = field(default_factory=dict)
    active: bool = True
    
    def __post_init__(self):
        if not self.rag_index_name:
            self.rag_index_name = f"repo_{self.tenant_id}"

class TenantManager:
    """Manage multiple tenants"""
    
    def __init__(self, storage_path: str = "tenants/data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.tenants: Dict[str, TenantConfig] = {}
        self._load_tenants()
    
    def _load_tenants(self):
        """Load tenants from storage"""
        tenant_file = self.storage_path / "tenants.json"
        if tenant_file.exists():
            with open(tenant_file, 'r') as f:
                data = json.load(f)
                for tenant_data in data.get('tenants', []):
                    tenant = TenantConfig(**tenant_data)
                    self.tenants[tenant.tenant_id] = tenant
    
    def _save_tenants(self):
        """Save tenants to storage"""
        tenant_file = self.storage_path / "tenants.json"
        data = {
            'tenants': [asdict(t) for t in self.tenants.values()],
            'updated_at': datetime.now().isoformat()
        }
        with open(tenant_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_tenant(self, name: str, config: Dict[str, Any] = None) -> TenantConfig:
        """Create a new tenant"""
        # Generate tenant ID
        tenant_id = hashlib.md5(f"{name}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        tenant = TenantConfig(
            tenant_id=tenant_id,
            name=name,
            config=config or {},
            usage_limits={
                'max_requests_per_day': 1000,
                'max_storage_mb': 1000,
                'max_rag_documents': 10000
            }
        )
        
        self.tenants[tenant_id] = tenant
        self._save_tenants()
        
        # Create tenant-specific directories
        tenant_dir = self.storage_path / tenant_id
        tenant_dir.mkdir(exist_ok=True)
        (tenant_dir / "outputs").mkdir(exist_ok=True)
        (tenant_dir / "inputs").mkdir(exist_ok=True)
        
        return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantConfig]:
        """Get tenant by ID"""
        return self.tenants.get(tenant_id)
    
    def update_tenant(self, tenant_id: str, updates: Dict[str, Any]) -> Optional[TenantConfig]:
        """Update tenant configuration"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return None
        
        for key, value in updates.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        self._save_tenants()
        return tenant
    
    def delete_tenant(self, tenant_id: str) -> bool:
        """Delete a tenant"""
        if tenant_id in self.tenants:
            del self.tenants[tenant_id]
            self._save_tenants()
            return True
        return False
    
    def list_tenants(self, active_only: bool = True) -> List[TenantConfig]:
        """List all tenants"""
        tenants = list(self.tenants.values())
        if active_only:
            tenants = [t for t in tenants if t.active]
        return tenants
    
    def get_tenant_path(self, tenant_id: str, subdir: str = "") -> Path:
        """Get tenant-specific path"""
        tenant_dir = self.storage_path / tenant_id
        if subdir:
            return tenant_dir / subdir
        return tenant_dir
    
    def check_usage_limit(self, tenant_id: str, limit_type: str, current_value: int) -> bool:
        """Check if tenant is within usage limits"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        limit = tenant.usage_limits.get(limit_type, float('inf'))
        return current_value < limit
    
    def increment_usage(self, tenant_id: str, metric: str, amount: int = 1):
        """Increment usage counter for tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return
        
        if 'usage' not in tenant.config:
            tenant.config['usage'] = {}
        
        tenant.config['usage'][metric] = tenant.config['usage'].get(metric, 0) + amount
        self._save_tenants()
    
    def get_usage_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get usage statistics for tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return {}
        
        return {
            'tenant_id': tenant_id,
            'name': tenant.name,
            'usage': tenant.config.get('usage', {}),
            'limits': tenant.usage_limits,
            'active': tenant.active
        }


# Global tenant manager
_tenant_manager = None

def get_tenant_manager() -> TenantManager:
    """Get or create global tenant manager"""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager()
    return _tenant_manager

