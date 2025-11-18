import sys
import json

data = json.load(sys.stdin)
print('Últimos 3 timestamps:')
for i in range(-3, 0):
    print(f'  {data["timestamps"][i]} - Download: {data["download"][i]:.2f} Mbps')
