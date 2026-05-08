import json

with open("template.json", encoding="utf-8") as f:
    survey = json.load(f)
    
out_path = "temp2.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(survey, f, ensure_ascii=False, indent=2)