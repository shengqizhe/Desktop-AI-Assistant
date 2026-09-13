from typing import Optional

def chat_once(system_prompt: str, user_text: str, api_key: str, base_url: str, model: str) -> Optional[str]:
    """
    Use LangChain (ChatOpenAI) for a single chat completion and return content text.
    Returns None on failure.
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
    except Exception as e:
        print(f"[LangChain] 导入失败：{e}")
        return None

    try:
        llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0.7,
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}")
        ])
        chain = prompt | llm
        resp = chain.invoke({"input": user_text})
        # langchain_openai 返回的 resp 包含 .content
        content = getattr(resp, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
        # 兼容 Message 对象
        try:
            return resp.content if resp and hasattr(resp, "content") else None
        except Exception:
            return None
    except Exception as e:
        print(f"[LangChain] 调用失败：{e}")
        return None

