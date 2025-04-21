# Function to reverse a string
def reverse_string(input_string):
    return input_string[::-1]

# Example usage
input_str = "aaaaaaaabbbbbbbbccccccccddddddddeeeeeeeeffffffffgggggggghhhhhhhhiiiiiiiijjjjjjjjkkkkkkkkllllllllmmmmmmmmnnnnnnnnooooooooppppppppqqqqqqqqrrrrrrrrssssssssttttttttuuuuuuuuvvvvvvvvwwwwwwwwxxxxxxxxyyyyyyyyzzzzzzzz111111112222222233333333444444445555555566666666"
reversed_str = reverse_string(input_str)

print("Original String:")
print(input_str)
print("\nReversed String:")
print(reversed_str)
