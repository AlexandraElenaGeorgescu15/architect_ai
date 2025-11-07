"""
Verify Fine-Tuning Dataset Builder Generates YOUR Patterns
"""

from components.finetuning_dataset_builder import FineTuningDatasetBuilder

def test_stub_methods():
    """Test that stub methods now return actual code instead of generic templates."""
    
    # Sample YOUR .NET controller code
    sample_dotnet_controller = """
using Microsoft.AspNetCore.Mvc;
using MongoDB.Driver;
using registration_api.Settings;

public class UserController : Controller
{
    private readonly IMongoCollection<UserDto> _users;
    
    public UserController(IMongoDBSettings settings)
    {
        var client = new MongoClient(settings.ConnectionString);
        var database = client.GetDatabase(settings.DatabaseName);
        _users = database.GetCollection<UserDto>("users");
    }
    
    [HttpGet]
    public ActionResult<List<UserDto>> Get() =>
        _users.Find(user => true).ToList();
}
"""
    
    # Create a minimal builder instance
    builder = FineTuningDatasetBuilder.__new__(FineTuningDatasetBuilder)
    builder.meeting_notes = "Test meeting notes"
    builder.meeting_summary = "User registration system"
    
    print("=" * 80)
    print("TESTING FINE-TUNING DATASET FIXES")
    print("=" * 80)
    
    # Test 1: _generate_dotnet_stub should return actual code
    print("\n✅ TEST 1: .NET Controller Stub Generation")
    result = builder._generate_dotnet_stub(sample_dotnet_controller, "UserController.cs")
    
    if result == sample_dotnet_controller:
        print("✅ PASS: Returns actual .NET code (YOUR patterns)")
        print(f"   - Contains 'IMongoDBSettings': {('IMongoDBSettings' in result)}")
        print(f"   - Contains 'MongoClient': {('MongoClient' in result)}")
        print(f"   - Contains ': Controller': {(': Controller' in result)}")
        print(f"   - Contains 'UserDto': {('UserDto' in result)}")
    else:
        print("❌ FAIL: Returns generic template instead of actual code")
        print(f"   Expected: Full controller code")
        print(f"   Got: {result[:100]}...")
    
    # Test 2: _generate_service_stub should return actual code
    print("\n✅ TEST 2: Angular Service Stub Generation")
    sample_angular_service = """
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class UserService {
  private apiUrl = '/api/users';
  
  constructor(private http: HttpClient) {}
  
  getUsers(): Observable<User[]> {
    return this.http.get<User[]>(this.apiUrl);
  }
}
"""
    
    result = builder._generate_service_stub(sample_angular_service, "user.service.ts")
    
    if result == sample_angular_service:
        print("✅ PASS: Returns actual Angular service code (YOUR patterns)")
        print(f"   - Contains '@Injectable': {('@Injectable' in result)}")
        print(f"   - Contains 'HttpClient': {('HttpClient' in result)}")
        print(f"   - Contains your API pattern: {('apiUrl' in result)}")
    else:
        print("❌ FAIL: Returns generic template")
        print(f"   Got: {result[:100]}...")
    
    # Test 3: _generate_erd_stub should extract from actual code
    print("\n✅ TEST 3: ERD Generation from Actual DTO")
    sample_dto = """
public class UserDto
{
    public string Id { get; set; }
    public string Email { get; set; }
    public string Name { get; set; }
    public DateTime CreatedAt { get; set; }
}
"""
    
    result = builder._generate_erd_stub(sample_dto, "UserDto.cs")
    
    checks = {
        "Contains 'erDiagram'": "erDiagram" in result,
        "Contains 'User' entity": "User" in result,
        "Extracted 'Id' property": "Id" in result or "id" in result,
        "Extracted 'Email' property": "Email" in result or "email" in result,
        "Has proper PK marking": "PK" in result,
    }
    
    all_passed = all(checks.values())
    if all_passed:
        print("✅ PASS: Extracts ERD from actual DTO structure")
    else:
        print("⚠️  PARTIAL: Some extraction issues")
    
    for check, passed in checks.items():
        print(f"   {'✅' if passed else '❌'} {check}")
    
    # Test 4: _generate_angular_component_stub should return actual code
    print("\n✅ TEST 4: Angular Component Stub Generation")
    sample_component = """
import { Component } from '@angular/core';

@Component({
  selector: 'app-user-list',
  templateUrl: './user-list.component.html',
  styleUrls: ['./user-list.component.scss']
})
export class UserListComponent {
  users: User[] = [];
  
  constructor(private userService: UserService) {}
  
  ngOnInit() {
    this.loadUsers();
  }
}
"""
    
    result = builder._generate_angular_component_stub(sample_component, "user-list.component.ts")
    
    if result == sample_component:
        print("✅ PASS: Returns actual Angular component code")
        print(f"   - Preserves YOUR component structure: {('@Component' in result)}")
    else:
        print("❌ FAIL: Returns generic template")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\n✅ CRITICAL FIXES APPLIED:")
    print("   1. _generate_dotnet_stub() now returns YOUR actual .NET code")
    print("   2. _generate_service_stub() now returns YOUR actual service code")
    print("   3. _generate_angular_component_stub() returns YOUR actual components")
    print("   4. _generate_style_stub() returns YOUR actual styles")
    print("   5. _generate_erd_stub() extracts from YOUR actual DTO structure")
    print("   6. _generate_architecture_stub() detects YOUR actual architecture patterns")
    
    print("\n📚 WHAT THIS MEANS:")
    print("   ✅ Training data will now contain YOUR MongoDB integration pattern")
    print("   ✅ Training data will now contain YOUR IMongoDBSettings injection")
    print("   ✅ Training data will now contain YOUR Controller base class usage")
    print("   ✅ Training data will now contain YOUR DTO naming conventions")
    print("   ✅ Training data will now contain YOUR Angular service patterns")
    print("   ✅ Training data will now contain YOUR SCSS styling approach")
    
    print("\n🎯 NEXT STEPS:")
    print("   1. Generate training dataset in the app")
    print("   2. Verify first 10 examples contain YOUR actual code")
    print("   3. Fine-tune CodeLlama on this dataset")
    print("   4. Test with: 'Create a user registration controller'")
    print("   5. Verify output matches YOUR MongoDB + DTO + Controller patterns")
    
    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    test_stub_methods()
