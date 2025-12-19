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
        # Get the real list of tabs from the live sheet
        available_tabs = self.seo_agent.find_best_tab()
        
        # Ask LLM: "Is this SEO or GA4? And which tab do I need?"
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
            
            # 1. Fetch data (Limited to 500 rows for speed)
            df = self.seo_agent.get_data(target_tab)
            if isinstance(df, str) or df.empty:
                return f"Could not retrieve data from tab '{target_tab}'."

            # 2. Generate Filter
            columns = list(df.columns)
            filter_plan = self.llm.get_structured_completion(
                SEO_FILTER_PROMPT,
                f"Columns: {columns}\nUser Query: {query}"
            )
            
            query_str = filter_plan.get("pandas_query", "")
            
            # 3. Apply Filter Locally
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
                
                # --- NEW: CALCULATE STATS (The "Brain" Upgrade) ---
                stats_summary = f"Total Rows: {len(filtered_df)}"
                
                profile_cols = ["Indexability", "Status Code", "Content Type"]
                for col in profile_cols:
                    if col in filtered_df.columns:
                        counts = filtered_df[col].value_counts().head(5).to_dict()
                        stats_summary += f"\n   - {col} Breakdown: {counts}"

                # Smart Column Selection
                relevant_columns = ["Address", "URL", "Title 1", "Status Code", "Indexability", "Content Type"]
                if query_str:
                    for col in columns:
                        if col in query_str: relevant_columns.append(col)
                
                final_cols = [c for c in relevant_columns if c in filtered_df.columns]
                if not final_cols: final_cols = filtered_df.columns[:5]

                # Create Sample
                sample_data = filtered_df[final_cols].head(5).to_dict(orient="records")
                
                # Truncate long text
                for row in sample_data:
                    for key, val in row.items():
                        if isinstance(val, str) and len(val) > 100:
                            row[key] = val[:100] + "..."

                # 4. Create Context-Rich Prompt
                data_context = {
                    "statistics": stats_summary,
                    "sample_data": sample_data,
                    "note": "Use the 'statistics' field for counts and percentages. Do not count the sample rows manually."
                }
                
                return self._summarize_results(query, data_context)
                
            except Exception as e:
                return f"I found the data in '{target_tab}', but couldn't filter it. Error: {e}"

        # === PATH B: GA4 AGENT ===
        elif intent == "GA4" or property_id:
            if not property_id:
                return "This looks like an analytics request, but I need a propertyId to proceed."
                
            reporting_plan = self.llm.get_structured_completion(ANALYTICS_SYSTEM_PROMPT, query)
            if "error" in reporting_plan: return reporting_plan["error"]
            
            validated_plan = self.analytics_agent.validate_plan(reporting_plan)
            raw_data = self.analytics_agent.run(property_id, validated_plan)
            return self._summarize_results(query, raw_data)


        # === PATH C: FUSION (Tier 3 Multi-Agent) ===
        elif intent == "BOTH":
            if not property_id:
                return "To combine Analytics and SEO data, I need a propertyId."
            
            print("🔄 Starting Multi-Agent Fusion...")

            # 1. Step A: Get GA4 Data (The "Lead" Data)
            ga4_plan = {
                "metrics": ["activeUsers", "screenPageViews"],
                "dimensions": ["pagePath"],
                "days_ago": 30 
            }
            ga4_data = self.analytics_agent.run(property_id, ga4_plan)
            
            if isinstance(ga4_data, str): return f"GA4 Failed: {ga4_data}"
            
            df_ga4 = pd.DataFrame(ga4_data)
            if df_ga4.empty: return "GA4 returned no data to merge."
            
            # 2. Step B: Get SEO Data (The "Enrichment" Data)
            target_tab = target_tab if target_tab else "internal_all"
            df_seo = self.seo_agent.get_data(target_tab)
            
            if isinstance(df_seo, str) or df_seo.empty:
                return f"Got GA4 data, but failed to fetch SEO data from '{target_tab}'."

            # 3. Step C: Normalize URLs for Matching (The Logic Core)
            try:
                print("🔗 Merging Datasets...")
                
                # Normalize SEO URLs: Remove 'http(s)://domain.com' AND trailing slashes
                # Find the URL column (handles 'Address', 'URL', 'Destination')
                url_col = next((c for c in df_seo.columns if c.lower() in ['address', 'url', 'destination']), None)
                
                if url_col:
                    # Regex logic: 
                    # 1. Remove https://... (protocol & domain)
                    # 2. rstrip('/') removes trailing slash so /blog/ becomes /blog
                    df_seo['match_key'] = (
                        df_seo[url_col]
                        .astype(str)
                        .str.replace(r'^https?://[^/]+', '', regex=True)
                        .str.rstrip('/')
                    )
                    # Edge case: Homepage might become empty string, set it back to '/'
                    df_seo.loc[df_seo['match_key'] == '', 'match_key'] = '/'
                else:
                    return "Could not find a URL column in SEO data to merge with."

                # Normalize GA4 URLs (Just strip trailing slash)
                df_ga4['match_key'] = df_ga4['pagePath'].astype(str).str.rstrip('/')
                df_ga4.loc[df_ga4['match_key'] == '', 'match_key'] = '/'

                # Debug logs to verify keys
                print(f"   Sample GA4 Keys: {df_ga4['match_key'].head(3).tolist()}")
                print(f"   Sample SEO Keys: {df_seo['match_key'].head(3).tolist()}")

                # 4. Step D: Merge (Left Join on GA4 data)
                merged_df = pd.merge(df_ga4, df_seo, on='match_key', how='left')
                
                # 5. Prepare Final Summary
                if 'screenPageViews' in merged_df.columns:
                    merged_df = merged_df.sort_values(by='screenPageViews', ascending=False)
                
                # Select only useful columns
                useful_cols = ['pagePath', 'screenPageViews', 'activeUsers', 'Title 1', 'Title', 'Meta Description 1', 'Indexability']
                final_cols = [c for c in useful_cols if c in merged_df.columns]
                
                final_data = merged_df[final_cols].head(10).to_dict(orient="records")
                
                # Truncate text for LLM
                for row in final_data:
                    for k, v in row.items():
                        if isinstance(v, str) and len(v) > 100: row[k] = v[:100] + "..."

                return self._summarize_results(query, final_data)
                
            except Exception as e:
                return f"Fusion failed during data merging. Error: {e}"
            
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