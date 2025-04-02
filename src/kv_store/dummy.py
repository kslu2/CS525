value = 907507751940624169017

# Convert integer to bytes (big-endian, 8 bytes)
value_bytes = value.to_bytes(10, byteorder='big')

# Decode bytes as UTF-8 string
decoded_str = value_bytes.decode('utf-8')

print(decoded_str)
