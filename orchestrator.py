from utils.llm_client import LLMClient
from utils.prompts import ANALYTICS_SYSTEM_PROMPT, ROUTING_SYSTEM_PROMPT, SEO_FILTER_PROMPT
from agents.analytics_agent import AnalyticsAgent
from agents.seo_agent import SEOAgent
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

class Orchestrator:
    def __init__(self):
        api_key = os.getenv("LITELLM_API_KEY") 
        self.llm = LLMClient(api_key=api_key)
        self.analytics_agent = AnalyticsAgent()
        self.seo_agent = SEOAgent() # Initialize once

    async def handle_query(self, query: str, property_id: str = None):
        # --- PHASE 1: INTENT ROUTING & TAB SELECTION ---
        available_tabs = self.seo_agent.find_best_tab()
        
        routing_response = self.llm.get_structured_completion(
            ROUTING_SYSTEM_PROMPT.format(tab_names=available_tabs),
            query
        )
        
        intent = routing_response.get("intent")
        target_tab = routing_response.get("selected_tab")
        
        print(f"🧠 Orchestrator Decision: {intent} (Tab: {target_tab})")

        # --- PHASE 2: EXECUTION ---
        
        # === PATH A: SEO AGENT ===
        if intent == "SEO":
            if not target_tab: target_tab = "Internal" 
            
            df = self.seo_agent.get_data(target_tab)
            if isinstance(df, str) or df.empty:
                return f"Could not retrieve data from tab '{target_tab}'."

            columns = list(df.columns)
            filter_plan = self.llm.get_structured_completion(
                SEO_FILTER_PROMPT,
                f"Columns: {columns}\nUser Query: {query}"
            )
            
            query_str = filter_plan.get("pandas_query", "")
            
            try:
                if query_str:
                    print(f"🐍 Executing Pandas Query: {query_str}")
                    for col in df.columns:
                        try: 
                            df[col] = pd.to_numeric(df[col])
                        except: 
                            pass
                    filtered_df = df.query(query_str)
                else:
                    filtered_df = df
                
                stats_summary = f"Total Rows: {len(filtered_df)}"
                
                profile_cols = ["Indexability", "Status Code", "Content Type"]
                for col in profile_cols:
                    if col in filtered_df.columns:
                        counts = filtered_df[col].value_counts().head(5).to_dict()
                        stats_summary += f"\n   - {col} Breakdown: {counts}"

                relevant_columns = ["Address", "URL", "Title 1", "Status Code", "Indexability", "Content Type"]
                if query_str:
                    for col in columns:
                        if col in query_str: relevant_columns.append(col)
                
                final_cols = [c for c in relevant_columns if c in filtered_df.columns]
                if not final_cols: final_cols = filtered_df.columns[:5]

                sample_data = filtered_df[final_cols].head(5).to_dict(orient="records")
                
                for row in sample_data:
                    for key, val in row.items():
                        if isinstance(val, str) and len(val) > 100:
                            row[key] = val[:100] + "..."

                data_context = {
                    "statistics": stats_summary,
                    "sample_data": sample_data,
                    "note": "Use the 'statistics' field for counts and percentages. Do not count the sample rows manually."
                }
                
                return self._summarize_results(query, data_context)
                
            except Exception as e:
                return f"I found the data in '{target_tab}', but couldn't filter it. Error: {e}"

        # === PATH C: FUSION (Tier 3 Multi-Agent) ===
        elif intent == "BOTH":
            if not property_id:
                return "To combine Analytics and SEO data, I need a propertyId."
            
            print("🔄 Starting Multi-Agent Fusion...")

            # 1. Step A: Get GA4 Data
            ga4_plan = {
                "metrics": ["activeUsers", "screenPageViews"],
                "dimensions": ["pagePath"],
                "days_ago": 30 
            }
            ga4_data = self.analytics_agent.run(property_id, ga4_plan)
            
            if isinstance(ga4_data, str): return f"GA4 Failed: {ga4_data}"
            
            df_ga4 = pd.DataFrame(ga4_data)
            if df_ga4.empty: return "GA4 returned no data to merge."
            
            # 2. Step B: Get SEO Data (WITH FORCED OVERRIDE)
            # CRITICAL FIX: We ignore the LLM's tab choice and FORCE 'internal_all'
            # This ensures we have the master list of all pages + all columns
            target_tab = "internal_all"
            print(f"🔒 FUSION OVERRIDE: Forcing data fetch from '{target_tab}'")
            
            df_seo = self.seo_agent.get_data(target_tab)
            
            if isinstance(df_seo, str) or df_seo.empty:
                return f"Got GA4 data, but failed to fetch SEO data from '{target_tab}'."

            # 3. Step C: Normalize URLs & Cleanup
            try:
                print("🔗 Merging Datasets...")
                
                # A. Filter for HTML pages only
                if 'Content Type' in df_seo.columns:
                     df_seo = df_seo[df_seo['Content Type'].astype(str).str.contains("html", case=False, na=False)]
                
                # B. Normalize SEO URLs
                url_col = next((c for c in df_seo.columns if c.lower() in ['address', 'url', 'destination']), None)
                
                if url_col:
                    df_seo['match_key'] = (
                        df_seo[url_col]
                        .astype(str)
                        .str.replace(r'^https?://[^/]+', '', regex=True) # Remove Domain
                        .str.replace(r'\?.*', '', regex=True)            # Remove Params
                        .str.rstrip('/')                                 # Remove Slash
                    )
                    df_seo.loc[df_seo['match_key'] == '', 'match_key'] = '/'
                    
                    # --- CRITICAL FIX: KILL THE GHOST ROW ---
                    # Your debug showed an empty row for '/'. This line deletes it.
                    if 'Title 1' in df_seo.columns:
                        # Convert to string, calculate length, sort descending
                        df_seo = df_seo.sort_values(
                            by='Title 1', 
                            key=lambda x: x.astype(str).str.len(), 
                            ascending=False
                        )
                    
                    # 2. NOW drop duplicates (It keeps the top one, which is now the Good Row)
                    df_seo = df_seo.drop_duplicates(subset='match_key', keep='first')
                    
                else:
                    return "Could not find a URL column in SEO data."

                # D. Normalize GA4 URLs
                df_ga4['match_key'] = df_ga4['pagePath'].astype(str).str.rstrip('/')
                df_ga4.loc[df_ga4['match_key'] == '', 'match_key'] = '/'

                # 4. Step D: Merge
                merged_df = pd.merge(df_ga4, df_seo, on='match_key', how='left')
                
                # ... (Rest of logic remains the same) ...
                
                # 5. Prepare Final Summary
                if 'screenPageViews' in merged_df.columns:
                    merged_df = merged_df.sort_values(by='screenPageViews', ascending=False)
                
                # --- FINAL COLUMN SELECTOR ---
                useful_cols = ['pagePath', 'screenPageViews', 'activeUsers', 'Indexability', 'Status Code']
                
                for col in merged_df.columns:
                    lower_col = col.lower()
                    if 'title' in lower_col or 'description' in lower_col or 'h1' in lower_col:
                        useful_cols.append(col)
                
                useful_cols = list(set(useful_cols))
                final_cols = [c for c in useful_cols if c in merged_df.columns]
                
                # DEBUG PRINT: Verify what we are sending
                print(f"📦 COLUMNS SENT TO LLM: {final_cols}")
                
                final_data = merged_df[final_cols].head(10).to_dict(orient="records")
                
                # Truncate text
                for row in final_data:
                    for k, v in row.items():
                        if isinstance(v, str) and len(v) > 100: row[k] = v[:100] + "..."

                return self._summarize_results(query, final_data)
                
            except Exception as e:
                return f"Fusion failed during data merging. Error: {e}"
            
        # === PATH B: GA4 AGENT ===
        elif intent == "GA4" or property_id:
            if not property_id:
                return "This looks like an analytics request, but I need a propertyId to proceed."
                
            reporting_plan = self.llm.get_structured_completion(ANALYTICS_SYSTEM_PROMPT, query)
            if "error" in reporting_plan: return reporting_plan["error"]
            
            validated_plan = self.analytics_agent.validate_plan(reporting_plan)
            raw_data = self.analytics_agent.run(property_id, validated_plan)
            return self._summarize_results(query, raw_data)

        return "I'm not sure how to handle that. Try asking about 'page views' (GA4) or 'broken links' (SEO)."

    def _summarize_results(self, original_query, data):
        is_empty = "No data found" in str(data) or not data
        
        system_context = "You are a helpful analytics assistant."
        if is_empty:
            system_context += " The API returned no data. Explain that the connection works but no traffic was found for this specific request."

        summary_prompt = f"""
        User Question: {original_query}
        Retrieved Data: {data}
        
        Provide a concise, professional summary.
        """
        return self.client_summarize(system_context, summary_prompt)

    def client_summarize(self, system, user):
        response = self.llm.client.chat.completions.create(
            model=self.llm.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        return response.choices[0].message.content