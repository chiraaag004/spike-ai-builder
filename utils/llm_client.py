import time
import json
from openai import OpenAI, APIError, APITimeoutError, APIConnectionError

class LLMClient:
    def __init__(self, api_key: str, base_url: str = "http://3.110.18.218"):
        self.client = OpenAI(
            api_key=api_key, 
            base_url=base_url,
            timeout=60.0  # Increased to 60s to give the proxy plenty of time
        )
        self.model = "gemini-2.5-flash"

    def get_structured_completion(self, system_prompt: str, user_query: str, max_retries: int = 3):
        base_delay = 2
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ],
                    response_format={"type": "json_object"}
                )
                return json.loads(response.choices[0].message.content)
            
            except (APITimeoutError, APIConnectionError) as e:
                wait_time = base_delay * (2 ** attempt)
                print(f"⚠️ Connection/Timeout Error (Attempt {attempt+1}/{max_retries}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                
            except APIError as e:
                # Safely check for status_code if it exists
                status_code = getattr(e, "status_code", None)
                if status_code == 429:
                    wait_time = base_delay * (2 ** attempt)
                    print(f"⏳ Rate limited. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    return {"error": f"API Error: {str(e)}"}
        
        return {"error": "Failed to reach the LLM proxy after multiple attempts. Please check your internet or proxy status."}