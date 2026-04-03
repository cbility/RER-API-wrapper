"""
Check for hidden characters in the password from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

password = os.getenv("GMAIL_PASSWORD", "")

print("Password analysis:")
print(f"Length: {len(password)}")
print(f"Repr: {repr(password)}")
print(f"Bytes: {password.encode('utf-8')}")
print()
print("Character breakdown:")
for i, char in enumerate(password):
    print(f"  [{i}] '{char}' (ord={ord(char)}, hex={hex(ord(char))})")

print()
if any(ord(c) < 32 or ord(c) > 126 for c in password):
    print("⚠ WARNING: Password contains non-printable or special characters!")
    print("This could cause authentication issues.")
    print("Re-type the password manually in the .env file.")
else:
    print("✓ No hidden characters detected")

print()
print("Cleaned password (alphanumeric only):")
cleaned = ''.join(c for c in password if c.isalnum())
print(f"Original length: {len(password)}")
print(f"Cleaned length: {len(cleaned)}")
if len(password) != len(cleaned):
    print(f"⚠ Removed {len(password) - len(cleaned)} non-alphanumeric characters")
    print(f"Try using: {cleaned}")
