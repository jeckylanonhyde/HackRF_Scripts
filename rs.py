#!/usr/bin/env python3

"""
Reed-Solomon Error Correction
==============================
This script implements error detection and correction using the Reed-Solomon
algorithm with parameters specified for RS(47, 31).

Details:
- Message Length: 31 bytes
- Checksum: 8 bytes
- Erasure Length: 8 bytes
- RS(47, 31): Total length 47 symbols (376 bits)
"""

import reedsolo

# Parameters
GENERATOR = 2          # Generator integer
FCR = 0                # First consecutive root
NSYM = 8               # Number of ECC symbols (n - k)
ELEN = 8               # Erasure length (bytes erased at the end)
C_EXP = 8              # Bits per symbol (GF(2^8))
PRIM = 0x11d           # Primitive polynomial

# Initialize Reed-Solomon tables
reedsolo.init_tables(prim=PRIM, generator=GENERATOR, c_exp=C_EXP)


def rs_check(data):
    """
    Verifies if the given data has valid Reed-Solomon ECC.

    Args:
        data (bytearray): Input data including ECC.

    Returns:
        bool: True if the ECC matches, False otherwise.
    """
    mlen = len(data) - NSYM
    try:
        # Encode the message portion to generate the ECC
        encoded_msg = reedsolo.rs_encode_msg(data[:mlen], NSYM + ELEN, fcr=FCR)
        # Compare the provided ECC with the generated ECC
        return bytearray(data[mlen:]) == encoded_msg[mlen:len(data)]
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
    # Extend the input data with erasure symbols
    data += [0] * ELEN
    # Define erasure positions (last ELEN bytes)
    erase_positions = list(range(len(data) - ELEN, len(data)))

    try:
        # Correct the message using Reed-Solomon
        corrected_msg, corrected_ecc = reedsolo.rs_correct_msg(
            data, NSYM + ELEN, FCR, GENERATOR, erase_pos=erase_positions
        )
        return True, corrected_msg, corrected_ecc[:NSYM]
    except (reedsolo.ReedSolomonError, ZeroDivisionError) as e:
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