from llm_commons.proxy.openai import ChatCompletion


# Use the OpenAI API to execute the prompt
def get_completion(prompt, model="gpt-4-32K", temperature=0.5, role="user"):
    messages = [{"role": role, "content": prompt}]
    response = ChatCompletion.create(  # <---
        deployment_id=model,  # <---
        messages=messages,
        temperature=temperature,
        stream=True,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message["content"]
