# app/services/dataset_service.py
"""
Dataset Management Service
Handles Excel/CSV upload, column mapping, and dataset versioning
"""

import pandas as pd
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import text
from app.core.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class DatasetService:
    """Service for managing clinical datasets."""
    
    # Standard parameter mappings
    STANDARD_PARAMETERS = {
        'lipid': {
            'total_cholesterol': ['tc', 'chol', 'cholesterol', 'total cholesterol', 'chol total', 'chol'],
            'ldl': ['ldl', 'ldl-c', 'ldl cholesterol', 'ldl direct', 'ldl-c'],
            'hdl': ['hdl', 'hdl-c', 'hdl cholesterol', 'hdl-c'],
            'triglycerides': ['tg', 'trigs', 'triglyceride', 'trig', 'triglycerides'],
            'vldl': ['vldl', 'vldl cholesterol'],
            'non_hdl': ['non.hdl', 'non hdl', 'non-hdl', 'non-hdl cholesterol'],
        },
        'cbc': {
            'hemoglobin': ['hb', 'hgb', 'hemoglobin', 'hb%', 'hgb'],
            'wbc': ['wbc', 'white blood cells', 'white cells', 'white blood cell count'],
            'platelets': ['plt', 'platelet', 'platelets', 'platelet count'],
            'rbc': ['rbc', 'red blood cells', 'red cells', 'red blood cell count'],
            'neutrophils': ['neut', 'neutrophils', 'neutrophil count'],
            'lymphocytes': ['lymph', 'lymphocytes', 'lymphocyte count'],
        },
        'lft': {
            'alt': ['alt', 'sgpt', 'alanine transaminase'],
            'ast': ['ast', 'sgot', 'aspartate transaminase'],
            'alp': ['alp', 'alkaline phosphatase'],
            'total_bilirubin': ['total bilirubin', 't.bilirubin', 'tbili', 'bilirubin total'],
            'direct_bilirubin': ['direct bilirubin', 'd.bilirubin', 'dbili', 'bilirubin direct'],
            'total_protein': ['total protein', 't.protein', 'protein total'],
            'albumin': ['albumin', 'alb'],
            'globulin': ['globulin', 'glob'],
            'ag_ratio': ['a/g ratio', 'ag ratio', 'albumin/globulin ratio'],
            'ggt': ['ggt', 'gamma-glutamyl transferase'],
        },
        'kft': {
            'creatinine': ['creat', 'creatinine', 'serum creatinine', 'cr'],
            'bun': ['bun', 'urea', 'blood urea nitrogen'],
            'uric_acid': ['uric acid', 'urate', 'ua'],
            'sodium': ['na', 'sodium', 'serum sodium'],
            'potassium': ['k', 'potassium', 'serum potassium'],
            'chloride': ['cl', 'chloride', 'serum chloride'],
            'bicarbonate': ['hco3', 'bicarbonate', 'bicarb'],
            'egfr': ['egfr', 'gfr', 'estimated gfr', 'estimated gfr'],
        },
        'thyroid': {
            'tsh': ['tsh', 'thyroid stimulating hormone'],
            't3': ['t3', 'triiodothyronine'],
            't4': ['t4', 'thyroxine'],
            'free_t3': ['free t3', 'ft3', 'free triiodothyronine'],
            'free_t4': ['free t4', 'ft4', 'free thyroxine'],
        },
        'diabetes': {
            'fasting_glucose': ['fasting glucose', 'fbs', 'fbg', 'glucose fasting'],
            'hba1c': ['hba1c', 'a1c', 'hemoglobin a1c', 'glycated hemoglobin'],
            'insulin': ['insulin'],
            'homa_ir': ['homa-ir', 'homa ir', 'homa index'],
            'postprandial_glucose': ['postprandial', 'ppbs', 'post meal glucose', '2hr glucose'],
        },
        'vitamins': {
            'vitamin_b12': ['vitamin b12', 'b12', 'cobalamin', 'b-12'],
            'vitamin_d': ['vitamin d', 'vitamin d3', '25-oh d', '25-hydroxy vitamin d'],
            'folate': ['folate', 'folic acid'],
            'iron': ['iron', 'serum iron'],
            'ferritin': ['ferritin'],
        },
        'electrolytes': {
            'calcium': ['ca', 'calcium', 'serum calcium'],
            'magnesium': ['mg', 'magnesium', 'serum magnesium'],
            'phosphorus': ['phos', 'phosphorus', 'phosphate', 'serum phosphorus'],
        }
    }
    
    def __init__(self):
        self.upload_dir = "uploads/datasets"
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def process_upload(self, file, filename: str, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Process uploaded Excel/CSV file.
        
        Args:
            file: Uploaded file object
            filename: Original filename
            category: Optional report category
            
        Returns:
            Processing results with mapping preview
        """
        try:
            # Save file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(self.upload_dir, safe_filename)
            
            with open(file_path, "wb") as f:
                f.write(file.read())
            
            # Read file
            if filename.lower().endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path, engine='openpyxl')
            
            # Detect category if not provided
            if not category:
                detected_category, confidence = self.detect_category(df.columns.tolist())
                category = detected_category
            
            # Map columns
            mapping, unknown_columns = self.map_columns(df.columns.tolist(), category)
            
            # Prepare sample data
            sample_data = df.head(5).to_dict('records')
            
            return {
                'success': True,
                'file_path': file_path,
                'filename': safe_filename,
                'row_count': len(df),
                'column_count': len(df.columns),
                'detected_category': category,
                'confidence': confidence if not category else 1.0,
                'columns': df.columns.tolist(),
                'mapping': mapping,
                'unknown_columns': unknown_columns,
                'preview': sample_data,
                'sample_values': df.head(2).to_dict('records')
            }
            
        except Exception as e:
            logger.error(f"Failed to process upload: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def detect_category(self, columns: List[str]) -> Tuple[str, float]:
        """Detect report category from column names."""
        scores = {}
        categories = ['lipid', 'cbc', 'lft', 'kft', 'thyroid', 'diabetes', 'vitamins', 'electrolytes']
        
        for category in categories:
            score = 0
            total_params = len(self.STANDARD_PARAMETERS.get(category, {}))
            
            for col in columns:
                col_lower = col.lower().strip()
                # Check if column matches any parameter in this category
                for param, aliases in self.STANDARD_PARAMETERS.get(category, {}).items():
                    if any(alias.lower() in col_lower or col_lower in alias.lower() for alias in aliases):
                        score += 1
                        break
            
            # Normalize score by total possible parameters
            scores[category] = score / total_params if total_params > 0 else 0
        
        # Get best match
        best = max(scores, key=scores.get)
        confidence = scores[best]
        
        # If confidence is very low, mark as uncertain
        if confidence < 0.3:
            best = 'unknown'
            confidence = 0.0
        
        return best, confidence
    
    def map_columns(self, columns: List[str], category: str) -> Tuple[Dict[str, str], List[str]]:
        """
        Map columns to standard parameter names.
        
        Args:
            columns: List of column names
            category: Report category
            
        Returns:
            Mapping dictionary and list of unknown columns
        """
        mapping = {}
        unknown_columns = []
        
        category_params = self.STANDARD_PARAMETERS.get(category, {})
        
        for col in columns:
            col_lower = col.lower().strip()
            mapped = None
            
            # Try exact match first
            for param, aliases in category_params.items():
                if col_lower == param or col_lower in aliases:
                    mapped = param
                    break
            
            # Try partial match
            if not mapped:
                for param, aliases in category_params.items():
                    for alias in aliases:
                        if alias.lower() in col_lower or col_lower in alias.lower():
                            mapped = param
                            break
                    if mapped:
                        break
            
            if mapped:
                mapping[col] = mapped
            else:
                mapping[col] = 'unknown'
                unknown_columns.append(col)
        
        return mapping, unknown_columns
    
    def save_dataset(self, mapping: Dict[str, str], category: str, file_path: str, uploaded_by: str = "doctor") -> Dict[str, Any]:
        """
        Save mapped dataset to database.
        
        Args:
            mapping: Column to parameter mapping
            category: Report category
            file_path: Path to the uploaded file
            uploaded_by: User who uploaded
            
        Returns:
            Save result with version info
        """
        try:
            # Read file
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path, engine='openpyxl')
            
            # Create version
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            with SessionLocal() as db:
                # Insert version
                version_result = db.execute(text("""
                    INSERT INTO dataset_versions 
                    (version, report_category, status, uploaded_by, source_file, change_summary, is_active)
                    VALUES (:version, :category, 'draft', :uploaded_by, :source_file, :summary, FALSE)
                    RETURNING id
                """), {
                    'version': version,
                    'category': category,
                    'uploaded_by': uploaded_by,
                    'source_file': os.path.basename(file_path),
                    'summary': f'Dataset upload from {os.path.basename(file_path)}'
                })
                
                version_id = version_result.fetchone()[0]
                
                # Insert upload record
                db.execute(text("""
                    INSERT INTO dataset_uploads 
                    (version_id, original_filename, file_path, row_count, column_count, upload_status)
                    VALUES (:version_id, :filename, :file_path, :rows, :cols, 'completed')
                """), {
                    'version_id': version_id,
                    'filename': os.path.basename(file_path),
                    'file_path': file_path,
                    'rows': len(df),
                    'cols': len(df.columns)
                })
                
                # Insert rows
                for _, row in df.iterrows():
                    row_data = row.to_dict()
                    # Map columns
                    mapped_row = {}
                    for col, value in row_data.items():
                        std_name = mapping.get(col, 'unknown')
                        mapped_row[std_name] = value if not pd.isna(value) else None
                    
                    db.execute(text("""
                        INSERT INTO dataset_rows (upload_id, row_data)
                        VALUES (:upload_id, :row_data)
                    """), {
                        'upload_id': version_id,
                        'row_data': json.dumps(mapped_row)
                    })
                
                db.commit()
                
                return {
                    'success': True,
                    'version_id': version_id,
                    'version': version,
                    'category': category,
                    'row_count': len(df),
                    'column_count': len(df.columns),
                    'message': f'Dataset imported successfully as version {version}'
                }
                
        except Exception as e:
            logger.error(f"Failed to save dataset: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_versions(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all dataset versions.
        
        Args:
            category: Optional filter by category
            
        Returns:
            List of versions
        """
        try:
            with SessionLocal() as db:
                query = """
                    SELECT id, version, report_category, status, 
                           uploaded_by, source_file, change_summary, 
                           is_active, created_at, activated_at
                    FROM dataset_versions
                """
                
                params = {}
                if category:
                    query += " WHERE report_category = :category"
                
                query += " ORDER BY created_at DESC"
                
                if category:
                    params['category'] = category
                
                result = db.execute(text(query), params)
                
                versions = []
                for row in result:
                    versions.append({
                        'id': row.id,
                        'version': row.version,
                        'category': row.report_category,
                        'status': row.status,
                        'uploaded_by': row.uploaded_by,
                        'source_file': row.source_file,
                        'change_summary': row.change_summary,
                        'is_active': row.is_active,
                        'created_at': row.created_at.isoformat() if row.created_at else None,
                        'activated_at': row.activated_at.isoformat() if row.activated_at else None
                    })
                
                return {
                    'success': True,
                    'versions': versions
                }
                
        except Exception as e:
            logger.error(f"Failed to get versions: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def activate_version(self, version_id: int) -> Dict[str, Any]:
        """
        Activate a dataset version.
        
        Args:
            version_id: ID of the version to activate
            
        Returns:
            Activation result
        """
        try:
            with SessionLocal() as db:
                # Get the category of this version
                category_result = db.execute(text("""
                    SELECT report_category FROM dataset_versions WHERE id = :version_id
                """), {'version_id': version_id})
                
                category_row = category_result.fetchone()
                if not category_row:
                    return {'success': False, 'error': 'Version not found'}
                
                category = category_row[0]
                
                # Deactivate all versions for this category
                db.execute(text("""
                    UPDATE dataset_versions 
                    SET is_active = FALSE, status = 'archived'
                    WHERE report_category = :category
                """), {'category': category})
                
                # Activate the selected version
                db.execute(text("""
                    UPDATE dataset_versions 
                    SET is_active = TRUE, status = 'active', activated_at = NOW()
                    WHERE id = :version_id
                """), {'version_id': version_id})
                
                db.commit()
                
                return {
                    'success': True,
                    'message': 'Version activated successfully'
                }
                
        except Exception as e:
            logger.error(f"Failed to activate version: {e}")
            return {
                'success': False,
                'error': str(e)
            }