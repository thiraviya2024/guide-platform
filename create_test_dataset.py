import pandas as pd

# Create sample lipid data
data = {
    'Patient ID': ['P001', 'P002', 'P003', 'P004', 'P005'],
    'Total Cholesterol': [220, 180, 250, 195, 210],
    'LDL': [150, 100, 170, 120, 140],
    'HDL': [45, 55, 35, 50, 42],
    'Triglycerides': [180, 120, 200, 150, 160],
    'VLDL': [36, 24, 40, 30, 32],
    'Non-HDL': [175, 125, 215, 145, 168]
}

df = pd.DataFrame(data)
df.to_excel('test_lipid_dataset.xlsx', index=False)
print("✅ test_lipid_dataset.xlsx created successfully!")
print(f"📊 Rows: {len(df)}")
print(f"📋 Columns: {list(df.columns)}")
