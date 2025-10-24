import sys
import json
print(json.dumps({"test": "immediate"}), flush=True)
print("Line 2", file=sys.stderr)
import time
time.sleep(5)
print("Done", file=sys.stderr)
