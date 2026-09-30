import streamlit as st
import re
import numpy as np
import pandas as pd
 
 
class complaintprocessor:
 
    # keywords for issue detection
 
    ISSUE_KEYWORDS = {
        'Broken': ['broken', 'snap', 'fracture', 'cracked'],
        'Damaged': ['damaged', 'dent', 'bent', 'torn', 'wear', 'worn'],
        'Not Working': ['not working', 'malfunction', 'failed', 'failure', 'inoperative', 'non-functional'],
        'Loose': ['loose', 'rattling', 'vibration', 'shaking'],
        'Leaking': ['leak', 'leaking', 'seeping'],
        'Corrosion': ['corrosion', 'rust', 'oxidation'],
        'Electrical': ['short', 'electrical', 'power', 'circuit'],
        'Mechanical': ['mechanical', 'bearing', 'friction', 'gear'],
        'Missing': ['missing', 'lost', 'absent'],
        'Other': []
    }
 
    # keywords for treatment detection
 
    TREATMENT_KEYWORDS = {
        'Replaced': ['replaced', 'replacement', 'substitute','replace','same provided'],
        'Repaired': ['repaired', 'repair', 'fixed','secure','sequre'],
        'Tightened': ['tightened', 'torque', 'fastened'],
        'Cleaned': ['cleaned', 'cleaning', 'wash'],
        'Lubricated': ['lubricant', 'oil', 'grease'],
        'Adjusted': ['adjusted', 'alignment', 'calibration'],
        'Inspected': ['inspected', 'inspection', 'checked', 'verified'],
        'Tested': ['tested', 'test', 'function', 'working'],
        'Reinstalled': ['reinstalled', 'install', 'mounted'],
        'Other': []
    }
 
    def __init__(self,excel_file_path):
        self.excel_file_path = excel_file_path
        self.df=None
        self.processed_data=None
 
   
    def load_data(self):
        try:
            self.df= pd.read_excel(self.excel_file_path)
            return self.df
       
        except Exception as e:
            raise Exception(f"Error loading Excel file:{str(e)}")
   
   
   
    def detect_columns(self):
        cols={c: c.strip().lower() for c in self.df.columns}
 
        def find(checks):
            for orig, low in cols.items():
                for check in checks:
                    if check(low):
                        return orig
            return None
       
        return {
            'date':      find([lambda l: l == 'date']),
            'day':   find([lambda l: l == 'day']),
            'airline':    find([lambda l: l == 'airline']),
            'tail':       find([lambda l: l == 'tail']),
            'bay':       find([lambda l: l == 'bay']),
            'team':       find([lambda l: l == 'team']),
            'class':       find([lambda l: l == 'class']),
            'zone':       find([lambda l: l == 'zone']),
            'location_of_failure':       find([lambda l: l == 'location of failure']),
            'seat/Lav/Door/Oven/Others_no.':       find([lambda l: l == 'Seat/Lav/Door/Oven/Others No.']),
            'seat/Lav/Door/Oven/Others_(Alphabet)':       find([lambda l: l == 'Seat/Lav/Door/Oven/Others (Alphabet)']),
            'seat_type':       find([lambda l: l == 'seat type']),
            'part_name':       find([lambda l: l == 'part name']),
            'part_no':       find([lambda l: l == 'part no.']),
            'detail_of_failure':       find([lambda l: l == 'detail of failure']),
            'repair_type':       find([lambda l: l == 'repair type']),
            'attended_technician':       find([lambda l: l == 'attended technician']),
            }
   
 
    def extract_issue(self,text):
        # extract the issue type using the keywords
 
        if not isinstance(text,str) or not text.strip():
            return 'Other'
       
        text_lower = text.lower()
 
        # check issue category
 
        for issue,keywords in self.ISSUE_KEYWORDS.items():
            if issue =='Other':
                continue
            for keyword in keywords:
                if keyword in text_lower:
                    return issue
        return 'Other'
   
 
    def extract_treatment(self,text):
 
        if not isinstance(text,str) or not text.strip():
            return 'Other'
       
        text_lower=text.lower()
 
        for treatment, keywords in self.TREATMENT_KEYWORDS.items():
            if treatment=='Other':
                continue
            for keyword in keywords:
                if keyword in text_lower:
                    return treatment
               
        return 'Other'
   
 
    # Process data
 
    def process_data(self):
        if self.df is None:
             self.load_data()
       
        cm=self.detect_columns()
        processed = pd.DataFrame()
 
        # Map columns that exist
        column_mappings = [
            ('day', 'Day'),
            ('date', 'Date'),
            ('airline', 'Airline'),
            ('tail', 'Tail'),
            ('bay', 'Bay'),
            ('team', 'Team'),
            ('class', 'Class'),
            ('zone', 'Zone'),
            ('location_of_failure', 'Location_of_Failure'),
            ('seat/Lav/Door/Oven/Others_no.', 'Seat/Lav/Door/Oven/Others_no.'),
            ('seat/Lav/Door/Oven/Others_(Alphabet)', 'Seat/Lav/Door/Oven/Others_(Alphabet)'),
            ('seat_type', 'Seat_Type'),
            ('part_name', 'Part_Name'),
            ('part_no', 'Part_No'),
            ('detail_of_failure', 'Detail_of_Failure'),
            ('repair_type', 'Repair_Type'),
            ('attended_technician','Attended_Technician')
        ]
 
        for key,label in column_mappings:
            if cm[key] and cm[key] in self.df.columns:
                processed[label] = self.df[cm[key]]
 
        # convert date column
 
        if 'Date' in processed.columns:
            processed['Date'] = pd.to_datetime(processed['Date'],errors='coerce')
            processed['Week'] = processed['Date'].dt.to_period('W').dt.start_time
 
       
        if 'Repair_Type' in processed.columns:
            combined_text = processed['Repair_Type'].fillna('')
            if 'Detail_of_Failure' in processed.columns:
                combined_text = combined_text + ' ' + processed['Detail_of_Failure'].fillna('')
           
            processed['Issue'] = combined_text.apply(self.extract_issue)
            processed['Treatment'] = combined_text.apply(self.extract_treatment)
        elif 'Detail_of_Failure' in processed.columns:
            combined_text = processed['Detail_of_Failure'].fillna('')
            processed['Issue'] = combined_text.apply(self.extract_issue)
            processed['Treatment'] = combined_text.apply(self.extract_treatment)
 
        # Ensure Airline column exists
        if 'Airline' not in processed.columns:
            processed['Airline'] = 'Unknown'
 
        self.processed_data = processed
        return processed
   
 
    def get_summary_stats(self):
         
        if self.processed_data is None:
            return {}
       
        d=self.processed_data
        return{
            'total_records':len(d),
            'unique_airlines':d['Airline'].nunique() if 'Airline' in d.columns else 0,
            'unique_parts':d['Part_Name'].nunique() if 'Part_Name' in d.columns else 0,
            'unique_tails':d['Tail'].nunique() if 'Tail' in d.columns else 0,
        }
   
 
    def get_date_range(self):
        if self.processed_data is None or 'Date' not in self.processed_data.columns:
            return None, None
       
        valid_dates = pd.to_datetime(self.processed_data['Date'], errors='coerce')
        return valid_dates.min(), valid_dates.max()
   
 
   
    def get_airlines(self):
        if self.processed_data is None or 'Airline' not in self.processed_data.columns:
            return[]
        airlines = (self.processed_data['Airline'].fillna('Unknown').astype(str).unique().tolist())
        return sorted(airlines)
   
    def get_tail(self):
        if self.processed_data is None or 'Tail' not in self.processed_data.columns:
            return[]
        tail = (self.processed_data['Tail'].fillna('Unknown').astype(str).unique().tolist())
        return sorted(tail)
 
 
    def get_parts_by_airline(self,airline=None, start_date=None, end_date=None):
    # Get parts (Part_No, Part_Name, Count) grouped by airline.
 
        if self.processed_data is None:
            return {}
       
        data = self.processed_data.copy()
 
        #apply filters
        if airline and airline !='All':
            data=data[data['Airline']==airline]
       
        if start_date and end_date:
            data = data[
            (data['Date'].dt.date >= start_date) &
            (data['Date'].dt.date <= end_date)
        ]
           
        # Group by airline and get part data
        if airline and airline != 'All':
            # Return data for single airline
            #part_groups = (data.groupby('Part_Name',dropna=False).agg(Part_No=('Part_No', 'first'),Count=('Part_Name', 'size')).reset_index())
            part_groups = (data.groupby(['Part_Name', 'Part_No'],dropna=False).size().reset_index(name='Count').sort_values('Count', ascending=False))
            #part_groups = part_groups.sort_values('Count', ascending=False)
            return {airline: part_groups}
           
        else:
            # Return data for all airlines
            result = {}
            for air in self.get_airlines():
                airline_data = data[data['Airline'] == air]
                #part_groups = (airline_data.groupby('Part_Name',dropna = False).agg(Part_No=('Part_No', 'first'),Count=('Part_Name', 'size')).reset_index())
                part_groups = (airline_data.groupby(['Part_Name', 'Part_No'],dropna=False).size().reset_index(name='Count').sort_values('Count', ascending=False))
                #part_groups = part_groups.sort_values('Count', ascending=False)
               
                result[air] = part_groups
            return result
       
       
               
    def get_filtered_data(self,airline = None, date=None, part_name=None,issue=None,treatment=None,tail=None,team=None):
 
        if self.processed_data is None:
            return pd.DataFrame()
       
        data = self.processed_data.copy()
 
        if airline and airline != 'All':
            data = data[data['Airline'] == airline]
       
        if date and date != 'All':
            if 'Date' in data.columns:
                data = data[data['Date'] == date]
       
        if part_name and part_name != 'All':
            if 'Part_Name' in data.columns:
                data = data[data['Part_Name'] == part_name]
       
        if issue and issue != 'All':
            if 'Issue' in data.columns:
                data = data[data['Issue'] == issue]
       
        if treatment and treatment != 'All':
            if 'Treatment' in data.columns:
                data = data[data['Treatment'] == treatment]
       
        if tail and tail != 'All':
            if 'Tail' in data.columns:
                data = data[data['Tail'] == tail]
 
        if team and team != 'All':
            if 'Team' in data.columns:
                data = data[data['Team'] == team]
       
        return data
   
 
    def get_part_names(self):
        if self.processed_data is None or 'Part_Name' not in self.processed_data.columns:
            return[]
        return sorted(self.processed_data['Part_Name'].dropna().unique().tolist())
   
    def get_issues(self):
        if self.processed_data is None or 'Issue' not in self.processed_data.columns:
            return[]
        return sorted(self.processed_data['Issue'].unique().tolist())
   
 
    def get_treatments(self):
        if self.processed_data is None or 'Treatment' not in self.processed_data.columns:
            return[]
        return sorted(self.processed_data['Treatment'].unique().tolist())
   
    def get_team(self):
        if self.processed_data is None or 'Team' not in self.processed_data.columns:
            return[]
        return sorted(self.processed_data['Team'].unique().tolist())

    def get_weekly_failed_parts(self, start_date=None, end_date=None, limit=5):
        if self.processed_data is None or self.processed_data.empty:
            return pd.DataFrame()
            
        data = self.processed_data.copy()
        if 'Date' not in data.columns:
            return pd.DataFrame()
            
        data = data.dropna(subset=['Date'])
        if data.empty:
            return pd.DataFrame()
            
        if 'Week' not in data.columns:
            data['Week'] = data['Date'].dt.to_period('W').dt.start_time
            
        if start_date and end_date:
            data = data[
                (data['Date'].dt.date >= start_date) &
                (data['Date'].dt.date <= end_date)
            ]
            
        if 'Part_Name' not in data.columns or data.empty:
            return pd.DataFrame()
            
        top_parts = data['Part_Name'].value_counts().head(limit).index.tolist()
        if not top_parts:
            return pd.DataFrame()
            
        filtered_data = data[data['Part_Name'].isin(top_parts)]
        weekly_parts = (filtered_data.groupby(['Week', 'Part_Name'])
                        .size()
                        .reset_index(name='Failed Part Count')
                        .sort_values('Week'))
        return weekly_parts

    def get_weekly_airlines_parts(self, start_date=None, end_date=None, limit=5):
        if self.processed_data is None or self.processed_data.empty:
            return pd.DataFrame()
            
        data = self.processed_data.copy()
        if 'Date' not in data.columns:
            return pd.DataFrame()
            
        data = data.dropna(subset=['Date'])
        if data.empty:
            return pd.DataFrame()
            
        if 'Week' not in data.columns:
            data['Week'] = data['Date'].dt.to_period('W').dt.start_time
            
        if start_date and end_date:
            data = data[
                (data['Date'].dt.date >= start_date) &
                (data['Date'].dt.date <= end_date)
            ]
            
        if 'Airline' not in data.columns or data.empty:
            return pd.DataFrame()
            
        top_airlines = data['Airline'].value_counts().head(limit).index.tolist()
        if not top_airlines:
            return pd.DataFrame()
            
        filtered_data = data[data['Airline'].isin(top_airlines)]
        weekly_airlines = (filtered_data.groupby(['Week', 'Airline'])
                           .size()
                           .reset_index(name='Failed Part Count')
                           .sort_values('Week'))
        return weekly_airlines

   
 