import os
import sys
sys.path.append(os.path.abspath('.'))
from core.audit_engine import get_canonical_key

print(f"SAFE App: '{get_canonical_key('South Alabama', 'Appalachian St.')}'")
print(f"FULL App: '{get_canonical_key('South Alabama', 'App State')}'")
print(f"SAFE Md:  '{get_canonical_key('Lehigh', 'Maryland')}'")
print(f"FULL Md:  '{get_canonical_key('Lehigh', 'Loyola MD')}'")
