#!/usr/bin/env python3
import random

def generate_prime_interval_sequence(length=3):
    primes = [2,3,5,7,11,13,17,19,23,29]
    return [random.choice(primes) for _ in range(length)]

if __name__ == "__main__":
    seq = generate_prime_interval_sequence()
    print(f"Generated paradox sequence: {seq}")