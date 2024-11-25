#!/usr/bin/env python3

"""
Efficient Reed-Solomon Error Correction Script
==============================================
This script implements error checking and correction using the Reed-Solomon
algorithm with parameters specified for RS_6(52, 10).

Details:
- Message Length: 42 * 6b = 31.5 bytes
- Checksum: 10 * 6b = 7.5 bytes
- RS_6(52, 10): Total length 52 symbols (312 bits)
"""

import reedsolo6

# Reed-Solomon Parameters
GENERATOR = 2          # Generator integer
FCR = 54               # First consecutive root
NSYM = 10              # Number of ECC symbols (n - k)
ELEN = 0               # Erasure length (bytes erased at the end)
C_EXP = 6              # Bits per symbol (GF(2^6))
PRIM = 0x43            # Primitive polynomial

# Initialize Reed-Solomon tables
reedsolo6.init_tables(prim=PRIM, generator=GENERATOR, c_exp=C_EXP)


def rs_check(data):
    """
    Verifies if the given data has valid Reed-Solomon ECC.

    Args:
        data (bytearray): Input data including ECC.

    Returns:
        bool: True if the ECC matches, False otherwise.
    """
    try:
        message_length = len(data) - NSYM
        # Generate ECC from the input message
        encoded_msg = reedsolo6.rs_encode_msg(data[:message_length], NSYM + ELEN, fcr=FCR)
        # Validate the provided ECC
        return bytearray(data[message_length:]) == encoded_msg[message_length:]
    except Exception as e:
        print(f"Error during RS check: {e}")
        return False


def rs_fix(data):
    """
    Attempts to correct errors in the given data using Reed-Solomon.

    Args:
        data (bytearray): Input data including ECC.

    Returns:
        tuple:
            - bool: True if correction was successful, False otherwise.
            - bytearray: Corrected message (if successful), otherwise None.
            - bytearray: Corrected ECC symbols (if successful), otherwise None.
    """
    # Add erasure bytes to the input data
    data += [0] * ELEN
    # Erasure positions
    erase_positions = list(range(len(data) - ELEN, len(data)))

    try:
        # Correct the message using Reed-Solomon
        corrected_msg, corrected_ecc = reedsolo6.rs_correct_msg(data, NSYM + ELEN, FCR, GENERATOR, erase_positions)
        return True, corrected_msg, corrected_ecc[:NSYM]
    except (reedsolo6.ReedSolomonError, ZeroDivisionError) as e:
        print(f"Error during RS correction: {e}")
        return False, None, None


if __name__ == "__main__":
    # Example usage
    example_data = bytearray(b"example data with errors") + bytearray([0] * NSYM)
    print("Running RS check...")
    if rs_check(example_data):
        print("Data is valid.")
    else:
        print("Data is corrupted. Attempting to fix...")
        success, fixed_msg, fixed_ecc = rs_fix(example_data)
        if success:
            print("Data successfully corrected.")
            print(f"Corrected Message: {fixed_msg}")
            print(f"Corrected ECC: {fixed_ecc}")
        else:
            print("Failed to correct the data.")