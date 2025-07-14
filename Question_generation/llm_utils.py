import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

class LLMThread(threading.Thread):
    def __init__(self, messages, api_key):
        threading.Thread.__init__(self)
        self.messages = messages
        self.api_key = api_key
        self.result = None
        self.error = None

    def run(self):
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "messages": self.messages,
                "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"
            }
            response = requests.post(
                "https://router.huggingface.co/nscale/v1/chat/completions",
                headers=headers,
                json=payload
            )
            if response.status_code == 200:
                self.result = response.json()["choices"][0]["message"]["content"]
            else:
                self.error = f"Error: {response.status_code}\n{response.text}"
        except Exception as e:
            self.error = str(e)

def parallel_llm_queries(tasks):
    """
    Run multiple LLM queries in parallel
    
    tasks: list of tuples (messages, api_key)
    returns: list of results in the same order as tasks
    """
    threads = []
    for messages, api_key in tasks:
        thread = LLMThread(messages, api_key)
        threads.append(thread)
        thread.start()

    results = []
    for thread in threads:
        thread.join()
        if thread.error:
            results.append(thread.error)
        else:
            results.append(thread.result)

    return results
