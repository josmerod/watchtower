import pandas as pd
import json

url = 'https://docs.google.com/spreadsheets/d/1AZ3pw48rDAHZM3C_5S-GkKS7t8dkX9PiGLy39VAYe2U/export?format=csv&gid=2134015255'
df = pd.read_csv(url)
out = {
    "columns": df.columns.tolist(),
    "row_0": df.iloc[0].to_dict()
}
print(json.dumps(out, indent=2))
