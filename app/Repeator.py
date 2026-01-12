import json5

# Example usage
dirty_json = ""
with open("/home/chaincode/Desktop/acmeimp/microsecai/output/111.json", "r") as f:
    dirty_json = f.read()

parsed = json5.loads(dirty_json)
print(parsed)  # {'user': 'Alice'}
