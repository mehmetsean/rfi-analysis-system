"""
RFI Analysis System - Core Module
Enterprise-grade document analysis for engineering RFIs
"""

import pandas as pd
import numpy as np
import re
from collections import defaultdict, Counter
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class RFIAnalyzer:
    """
    Production-ready RFI Analysis System
    Analyzes RFIs to identify standards issues and improvement opportunities
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the RFI Analyzer
        
        Parameters:
        -----------
        config : dict, optional
            Configuration parameters for analysis
        """
        self.df = None
        self.enriched_df = None
        self.analysis_results = {}
        self.config = config or {}
        self._initialize_patterns()
        
    def _initialize_patterns(self):
        """Initialize regex patterns for standards extraction"""
        
        self.standards_patterns = {
            'IEEE': [
                r'IEEE[-\s]?(\d{3,4}(?:\.\d+)?(?:-\d{4})?)',
                r'IEEE[-\s]?C(\d{2,3}\.\d+(?:-\d{4})?)'
            ],
            'ANSI': [
                r'ANSI[-\s]?([A-Z]?\d{2,3}\.?\d*(?:[-\.]\d+)?)'
            ],
            'NESC': [
                r'NESC[-\s]?(?:RULE[-\s]?)?(\d{3}[A-Z]?\d?)',
                r'RULE[-\s]?(\d{3}[A-Z]?\d?)'
            ],
            'IEC': [
                r'IEC[-\s]?(\d{4,5}(?:[-\.]\d+)?(?::\d{4})?)'
            ],
            'ASTM': [
                r'ASTM[-\s]?([A-Z]?\d{2,4})'
            ],
            'NEMA': [
                r'NEMA[-\s]?([A-Z]{2,3}[-\s]?\d+)'
            ]
        }
        
        self.issue_categories = {
            'Design Clarification': ['design', 'clarify', 'explain', 'interpret'],
            'Missing Specification': ['not specified', 'missing', 'not shown'],
            'Standard Conflict': ['conflict', 'contradict', 'inconsistent'],
            'Calculation/Formula': ['calculat', 'formula', 'equation'],
            'Equipment Specification': ['rating', 'size', 'type', 'model'],
            'Safety/Compliance': ['safety', 'code', 'compliance', 'requirement'],
            'Documentation': ['drawing', 'document', 'revision', 'update']
        }
        
        self.equipment_patterns = {
            'Transformer': ['transform', 'xfmr', 'mvt'],
            'Circuit Breaker': ['breaker', 'circuit breaker', 'cb'],
            'Grounding': ['ground', 'earth', 'grd'],
            'Protection/Relay': ['protection', 'relay', 'differential'],
            'Control/SCADA': ['control', 'scada', 'rtu', 'hmi']
        }
    
    def load_data(self, file_path: str) -> bool:
        """
        Load and prepare RFI data
        
        Parameters:
        -----------
        file_path : str
            Path to the Excel file
            
        Returns:
        --------
        bool : Success status
        """
        try:
            self.df = pd.read_excel(file_path)
            self.enriched_df = self.df.copy()
            
            # Add analysis columns
            self.enriched_df['Extracted_Standards'] = ''
            self.enriched_df['Issue_Category'] = ''
            self.enriched_df['Equipment_Type'] = ''
            self.enriched_df['Complexity_Score'] = 0
            self.enriched_df['Priority_Level'] = ''
            
            return True
            
        except Exception as e:
            print(f"Error loading file: {e}")
            return False
    
    def extract_standards(self) -> Dict[str, int]:
        """
        Extract standards references from RFI content
        
        Returns:
        --------
        dict : Standards and their occurrence counts
        """
        standards_list = []
        
        for idx, row in self.enriched_df.iterrows():
            combined_text = ''
            text_columns = ['Subject', 'Questions', 'Responses']
            
            for col in text_columns:
                if col in self.enriched_df.columns and pd.notna(row[col]):
                    combined_text += ' ' + str(row[col])
            
            found_standards = []
            
            for std_type, patterns in self.standards_patterns.items():
                for pattern in patterns:
                    matches = re.findall(pattern, combined_text, re.IGNORECASE)
                    if matches:
                        for match in matches:
                            std_ref = f"{std_type}-{match}"
                            found_standards.append(std_ref)
            
            unique_standards = list(set(found_standards))
            standards_list.append(', '.join(unique_standards) if unique_standards else '')
        
        self.enriched_df['Extracted_Standards'] = standards_list
        
        # Count all standards
        all_standards = []
        for std_str in standards_list:
            if std_str:
                all_standards.extend(std_str.split(', '))
        
        return Counter(all_standards)
    
    def categorize_issues(self) -> Dict[str, int]:
        """
        Categorize issues based on content analysis
        
        Returns:
        --------
        dict : Issue categories and counts
        """
        categories = []
        
        for idx, row in self.enriched_df.iterrows():
            question = str(row.get('Questions', '')).lower() if pd.notna(row.get('Questions', '')) else ''
            subject = str(row.get('Subject', '')).lower() if pd.notna(row.get('Subject', '')) else ''
            combined_text = question + ' ' + subject
            
            found_category = 'Other'
            for category, keywords in self.issue_categories.items():
                for keyword in keywords:
                    if keyword in combined_text:
                        found_category = category
                        break
                if found_category != 'Other':
                    break
            
            categories.append(found_category)
        
        self.enriched_df['Issue_Category'] = categories
        return Counter(categories)
    
    def calculate_priority(self):
        """Calculate priority scores for each RFI"""
        
        complexity_scores = []
        priority_levels = []
        
        for idx, row in self.enriched_df.iterrows():
            score = 0
            
            # Length-based scoring
            question = str(row.get('Questions', '')) if pd.notna(row.get('Questions', '')) else ''
            if len(question) > 500:
                score += 3
            elif len(question) > 200:
                score += 2
            elif len(question) > 100:
                score += 1
            
            # Standards complexity
            if row['Extracted_Standards']:
                std_count = len(row['Extracted_Standards'].split(', '))
                score += min(std_count, 3)
            
            # Critical categories
            if row['Issue_Category'] in ['Standard Conflict', 'Safety/Compliance']:
                score += 2
            
            complexity_scores.append(min(score, 10))
            
            # Assign priority
            if score >= 7:
                priority_levels.append('HIGH')
            elif score >= 4:
                priority_levels.append('MEDIUM')
            else:
                priority_levels.append('LOW')
        
        self.enriched_df['Complexity_Score'] = complexity_scores
        self.enriched_df['Priority_Level'] = priority_levels
    
    def run_analysis(self):
        """Run complete analysis pipeline"""
        
        print("Starting RFI Analysis...")
        
        # Extract standards
        standards = self.extract_standards()
        self.analysis_results['standards'] = standards
        print(f"✓ Found {len(standards)} unique standards")
        
        # Categorize issues
        categories = self.categorize_issues()
        self.analysis_results['categories'] = categories
        print(f"✓ Categorized into {len(categories)} issue types")
        
        # Calculate priorities
        self.calculate_priority()
        priority_dist = self.enriched_df['Priority_Level'].value_counts()
        print(f"✓ Priority distribution: {priority_dist.to_dict()}")
        
        return self.analysis_results
    
    def save_results(self, output_dir: str = '.'):
        """
        Save analysis results
        
        Parameters:
        -----------
        output_dir : str
            Directory to save output files
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save Excel
        excel_file = f"{output_dir}/rfi_analysis_{timestamp}.xlsx"
        with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
            self.enriched_df.to_excel(writer, sheet_name='Analysis', index=False)
        
        # Save JSON summary
        json_file = f"{output_dir}/rfi_summary_{timestamp}.json"
        summary = {
            'timestamp': timestamp,
            'total_rfis': len(self.enriched_df),
            'standards': dict(self.analysis_results.get('standards', Counter()).most_common(10)),
            'categories': dict(self.analysis_results.get('categories', Counter()))
        }
        
        with open(json_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"✓ Results saved to {output_dir}")
        return excel_file, json_file
