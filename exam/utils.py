# exam/utils.py (create this file)
import string
from collections import Counter

# def validate_activation_code(code):
#     """
#     Validate activation code format:
#     - Exactly 15 characters
#     - Contains at least 1 digit
#     - Contains at least 1 special character
#     - Contains the exact letters: B,A,K,A,N,A,K,U,F,O
#     """
#     code = code.upper()
    
#     # 1. Length check
#     if len(code) != 15:
#         return False, "Code must be exactly 15 characters"
    
#     # 2. Digit check
#     if not any(char.isdigit() for char in code):
#         return False, "Code must contain at least one digit"
    
#     # 3. Special character check
#     special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?/"
#     if not any(char in special_chars for char in code):
#         return False, "Code must contain at least one special character"
    
#     # 4. Required letters check with EXACT counts
#     required_letters = {
#         'B': 1, 'A': 3, 'K': 2, 
#         'N': 1, 'U': 1, 'F': 1, 'O': 1
#     }
    
#     letter_counts = Counter(char for char in code if char.isalpha())
    
#     # Check for EXACT required counts
#     for letter, required_count in required_letters.items():
#         if letter_counts.get(letter, 0) < required_count:
#             return False, f"Code requires {required_count} '{letter}' character(s)"
    
#     return True, "Valid code"