# clinical/multi_rule_engine.py
from typing import Dict, Any, List
from database.connection import SessionLocal
from sqlalchemy import text

class MultiRuleEngine:
    """Engine for evaluating multiple blood test parameters together"""
    
    def __init__(self):
        self.rule_tables = {
            'cbc': 'cbc_rules',
            'lft': 'lft_rules',
            'rft': 'rft_rules',
            'vitamins': 'vitamin_rules',
            'diabetes': 'diabetes_rules'
        }
    
    def evaluate_all(self, blood_values: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate all blood test parameters"""
        results = {}
        
        with SessionLocal() as db:
            for category, table in self.rule_tables.items():
                for param, value in blood_values.items():
                    if value is None:
                        continue
                    
                    query = text(f"""
                        SELECT status, recommendation
                        FROM {table}
                        WHERE parameter = :param
                          AND min_value <= :value
                          AND max_value >= :value
                          AND is_active = TRUE
                        ORDER BY id
                        LIMIT 1
                    """)
                    
                    try:
                        row = db.execute(query, {"param": param, "value": value}).fetchone()
                        if row:
                            results[param] = {
                                'value': value,
                                'status': row.status,
                                'recommendation': row.recommendation or '',
                                'category': category
                            }
                    except Exception as e:
                        continue
        
        return results
    
    def get_disease_risks(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify disease risks based on multiple parameters"""
        risks = []
        
        # Diabetes risk
        if 'fasting_glucose' in results:
            fg = results['fasting_glucose']
            if fg['status'] == 'Prediabetes':
                risks.append({
                    'disease': 'Prediabetes',
                    'confidence': 'Medium',
                    'reason': 'Fasting glucose is elevated',
                    'recommendation': 'Lifestyle modifications, regular monitoring'
                })
            elif fg['status'] == 'Diabetes':
                risks.append({
                    'disease': 'Type 2 Diabetes',
                    'confidence': 'High',
                    'reason': 'Fasting glucose is in diabetic range',
                    'recommendation': 'Consult physician immediately'
                })
        
        # Check HbA1c with Fasting Glucose
        if 'hba1c' in results and results['hba1c']['status'] in ['Prediabetes', 'Diabetes']:
            risks.append({
                'disease': 'Diabetes Risk',
                'confidence': 'High',
                'reason': f"HbA1c: {results['hba1c']['status']}",
                'recommendation': 'Consult physician for diabetes management'
            })
        
        # Liver disease risk (ALT + AST)
        if 'alt_sgpt' in results and 'ast_sgot' in results:
            alt = results['alt_sgpt']
            ast = results['ast_sgot']
            if 'Moderate' in alt['status'] and 'Moderate' in ast['status']:
                risks.append({
                    'disease': 'Liver Dysfunction',
                    'confidence': 'High',
                    'reason': 'Both ALT and AST are elevated',
                    'recommendation': 'Consult gastroenterologist'
                })
        
        # Kidney disease risk
        if 'creatinine' in results and 'bun' in results:
            cr = results['creatinine']
            bun = results['bun']
            if cr['status'] == 'Elevated' or bun['status'] == 'Elevated':
                risks.append({
                    'disease': 'Kidney Stress',
                    'confidence': 'Medium',
                    'reason': 'Creatinine and/or BUN is elevated',
                    'recommendation': 'Consult nephrologist'
                })
        
        # Vitamin deficiency
        vitamin_deficiencies = []
        if 'vitamin_b12' in results and results['vitamin_b12']['status'] == 'Deficiency':
            vitamin_deficiencies.append('B12')
        if 'vitamin_d' in results and results['vitamin_d']['status'] in ['Insufficient', 'Deficient']:
            vitamin_deficiencies.append('Vitamin D')
        if 'vitamin_b9_folate' in results and results['vitamin_b9_folate']['status'] == 'Deficiency':
            vitamin_deficiencies.append('Folate')
        
        if len(vitamin_deficiencies) >= 2:
            risks.append({
                'disease': 'Multiple Vitamin Deficiencies',
                'confidence': 'High',
                'reason': f'Deficient in {", ".join(vitamin_deficiencies)}',
                'recommendation': 'Consult physician for supplementation'
            })
        
        # Homocysteine + B12/Folate deficiency
        if 'homocysteine' in results and results['homocysteine']['status'] == 'Elevated':
            if ('vitamin_b12' in results and results['vitamin_b12']['status'] == 'Deficiency') or \
               ('vitamin_b9_folate' in results and results['vitamin_b9_folate']['status'] == 'Deficiency'):
                risks.append({
                    'disease': 'Hyperhomocysteinemia',
                    'confidence': 'High',
                    'reason': 'Elevated homocysteine with B vitamin deficiency',
                    'recommendation': 'B vitamin supplementation, consult physician'
                })
        
        # Uric acid risk
        if 'uric_acid' in results and results['uric_acid']['status'] == 'Elevated':
            risks.append({
                'disease': 'Hyperuricemia',
                'confidence': 'Medium',
                'reason': 'Elevated uric acid levels',
                'recommendation': 'Monitor for gout, consult physician'
            })
        
        # Sodium/Potassium imbalance
        if 'sodium' in results and results['sodium']['status'] != 'Normal':
            risks.append({
                'disease': 'Electrolyte Imbalance',
                'confidence': 'Medium',
                'reason': f"Sodium: {results['sodium']['status']}",
                'recommendation': 'Consult physician for electrolyte management'
            })
        
        return risks
    
    def calculate_overall_risk(self, results: Dict[str, Any]) -> str:
        """Calculate overall risk level"""
        risk_score = 0
        count = 0
        
        for param, data in results.items():
            status = data.get('status', 'Normal')
            if 'Normal' in status or 'Good' in status:
                risk_score += 0
            elif 'Mild' in status or 'Borderline' in status or 'Insufficient' in status:
                risk_score += 2
            elif 'Moderate' in status or 'Elevated' in status or 'Prediabetes' in status:
                risk_score += 3
            elif 'Severe' in status or 'High' in status or 'Diabetes' in status:
                risk_score += 4
            count += 1
        
        avg_risk = risk_score / count if count > 0 else 0
        
        if avg_risk >= 3.5:
            return "High Risk"
        elif avg_risk >= 2.5:
            return "Moderate Risk"
        elif avg_risk >= 1.5:
            return "Low Risk"
        else:
            return "Normal"