from abc import ABC

from argon2 import PasswordHasher, Type, low_level

pw = "outsideAnotherYellowMoon"
# Using the default parameters. Just hard-coding them so they don't cause error when argon2-cffi updates the default parameters
ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, type=Type.ID)
hash = ph.hash(pw)

print(hash)
print(ph.verify(hash, "outsideAnotherYellowMoon"))

params = hash[:31] # upload params to environment variable
salt, pw = hash[31:].split("$") # upload salt and hashed password to user db
print(params)
print(salt)
print(pw)

reconstructed = params + "$".join([salt, pw])
print(ph.verify(reconstructed, "outsideAnotherYellowMoon"))

print(len("1-1039-00190-38-8"))

# Might suffice as equivalent of Typescript type interface
from typing import Dict, List


class testInterface(ABC):
    def __init__(self, property1: int, property2: str):
        self.property1 = property1
        self.property2 = property2

g = testInterface # ...man
f: testInterface = {
    "property1": 2,
    "property2": "dhb"
}
print(f)
# Can't do it like f: testInterface
# So probably can't do something like .forEach((row: a_type) => ({...})) in TS though :(
# AKA can't have static typing?
# We can do at most type hinting and MyPy, it seems...
