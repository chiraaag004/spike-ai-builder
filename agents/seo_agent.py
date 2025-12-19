import os
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class SEOAgent:
    def __init__(self):
        # 1. IDENTIFY THE SPREADSHEET ID (Prioritize .env, fallback to hardcoded)
        self.spreadsheet_id = os.getenv(
            "SEO_SPREADSHEET_ID", 
            "1zzf4ax_H2WiTBVrJigGjF2Q3Yz-qy2qMCbAMKvl6VEE" # Hardcoded fallback
        )
        
        # 2. LOCATE CREDENTIALS
        base_dir = Path(__file__).resolve().parent.parent
        self.creds_path = base_dir / "credentials.json"
        
        self.service = self._get_sheets_service()

    def _get_sheets_service(self):
        """Authenticates with Google Sheets API using Service Account."""
        if not self.creds_path.exists():
            print(f"⚠️ SEO Agent: credentials.json not found at {self.creds_path}")
            return None
        
        try:
            scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
            creds = service_account.Credentials.from_service_account_file(
                str(self.creds_path), scopes=scopes
            )
            return build('sheets', 'v4', credentials=creds)
        except Exception as e:
            print(f"❌ Failed to initialize Sheets Service: {e}")
            return None

    def find_best_tab(self):
        """Discovers all tab names in the spreadsheet."""
        if not self.service:
            return ["Internal"] # Minimum fallback guess
            
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            return [s['properties']['title'] for s in spreadsheet.get('sheets', [])]
        except Exception as e:
            print(f"Error fetching sheet metadata: {e}")
            return []

    def get_data(self, tab_name):
        if not self.service:
            return "Error: Sheets Service not initialized."

        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{tab_name}'!A1:Z1000"
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return pd.DataFrame()
            
            # 1. Get headers and the expected column count
            headers = [str(h).strip() for h in values[0]]
            num_cols = len(headers)
            
            # 2. PAD THE ROWS: Ensure every row has 'num_cols' elements
            padded_values = []
            for row in values[1:]:
                # If the row is shorter than headers, add empty strings
                if len(row) < num_cols:
                    row.extend([''] * (num_cols - len(row)))
                # If for some reason a row is longer, truncate it
                padded_values.append(row[:num_cols])
                
            # 3. Create DataFrame safely
            df = pd.DataFrame(padded_values, columns=headers)

            # Keeps the first occurrence of a column name, drops the rest
            df = df.loc[:, ~df.columns.duplicated()]
            
            # --- NEW FIX: Convert numbers loop (Correct way) ---
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    continue

            # Final cleanup
            df = df.dropna(how='all').dropna(axis=1, how='all')
            return df
        except Exception as e:
            return f"Error fetching tab '{tab_name}': {str(e)}"