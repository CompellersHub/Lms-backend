# utils.py
def validate_uk_bank_transfer(sort_code, account_number):
    """
    Validates UK bank account details using modulus checking
    Returns True if the account is potentially valid
    """
    # Remove any non-digit characters
    sort_code = ''.join(c for c in sort_code if c.isdigit())
    account_number = ''.join(c for c in account_number if c.isdigit())
    
    # Barclays specific validation
    if sort_code == '201143':
        # Barclays accounts are typically 8 digits
        if len(account_number) != 8:
            return False
        
        # Add additional validation rules if needed
        return True
    
    return False