"""Payload encoding, packing, and unpacking module for QR code implementation."""

def encode_text(text: str) -> bytes:
    """Encode text to UTF-8 bytes with strict encoding.
    
    Args:
        text: Input string to encode
        
    Returns:
        UTF-8 encoded bytes
        
    Raises:
        UnicodeEncodeError: If text cannot be encoded as UTF-8
    """
    return text.encode("utf-8")


def pack_payload(data: bytes) -> list[int]:
    """Pack payload bytes into a list of bits with length and checksum.
    
    The format is: [length_byte] + [data_bits] + [checksum_byte]
    where data_bits are most-significant-bit first.
    
    Args:
        data: Bytes to pack (max 40 bytes)
        
    Returns:
        List of integers (0 or 1) representing the packed bits
        
    Raises:
        ValueError: If data is longer than 40 bytes
    """
    if len(data) > 40:
        raise ValueError("Payload exceeds maximum 40 bytes")
    
    # Length byte
    length = len(data)
    bits = []
    
    # Add length as 8-bit value
    for i in range(7, -1, -1):
        bits.append((length >> i) & 1)
    
    # Add data bits (MSB first)
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    
    # Calculate checksum
    checksum = sum(data) % 256
    
    # Add checksum as 8-bit value
    for i in range(7, -1, -1):
        bits.append((checksum >> i) & 1)
    
    return bits


def unpack_payload(bits: list[int]) -> bytes:
    """Unpack bits into payload bytes, validating length, checksum, and padding.
    
    Args:
        bits: List of integers (0 or 1) to unpack
        
    Returns:
        Decoded bytes
        
    Raises:
        ValueError: If bits are invalid, length exceeds 40, checksum fails,
                    or padding is not zero
    """
    if not bits:
        raise ValueError("Empty bits list")
        
    # Validate all bits are 0 or 1
    for bit in bits:
        if bit != 0 and bit != 1:
            raise ValueError("Invalid bit value")
    
    # Read length (first 8 bits)
    if len(bits) < 8:
        raise ValueError("Insufficient bits for length field")
    
    length = 0
    for i in range(8):
        length |= bits[i] << (7 - i)
    
    # Validate length
    if length > 40:
        raise ValueError("Length exceeds maximum 40 bytes")
    
    # Calculate expected total bits: 8 (length) + 8 * length (data) + 8 (checksum)
    expected_total_bits = 16 + 8 * length
    if len(bits) < expected_total_bits:
        raise ValueError("Insufficient bits for payload")
    
    # Check that remaining bits are all zero (padding)
    if len(bits) > expected_total_bits:
        # Check if all trailing bits are zero
        for i in range(expected_total_bits, len(bits)):
            if bits[i] != 0:
                raise ValueError("Non-zero padding bits found")
    
    # Extract data bits
    data_bits = bits[8:8 + 8 * length]
    
    # Convert data bits back to bytes
    data = bytearray()
    for i in range(length):
        byte_value = 0
        for j in range(8):
            byte_value |= data_bits[i * 8 + j] << (7 - j)
        data.append(byte_value)
    
    # Verify checksum
    if length > 0:
        calculated_checksum = sum(data) % 256
        received_checksum = 0
        for i in range(8):
            received_checksum |= bits[8 + 8 * length + i] << (7 - i)
        if calculated_checksum != received_checksum:
            raise ValueError("Checksum mismatch")
    
    return bytes(data)