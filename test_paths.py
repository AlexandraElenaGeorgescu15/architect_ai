
from pathlib import Path

def test_relative_to():
    p1 = Path("C:/Users/test/file.txt")
    p2 = Path("c:/Users/test")
    
    print(f"p1: {p1}")
    print(f"p2: {p2}")
    
    try:
        rel = p1.relative_to(p2)
        print(f"p1 is relative to p2: {rel}")
    except ValueError:
        print("p1 is NOT relative to p2 (ValueError)")

    p1_res = p1.resolve()
    p2_res = p2.resolve()
    print(f"p1.resolve(): {p1_res}")
    print(f"p2.resolve(): {p2_res}")
    
    try:
        rel = p1_res.relative_to(p2_res)
        print(f"p1.resolve() is relative to p2.resolve(): {rel}")
    except ValueError:
        print("p1.resolve() is NOT relative to p2.resolve() (ValueError)")

if __name__ == "__main__":
    test_relative_to()
