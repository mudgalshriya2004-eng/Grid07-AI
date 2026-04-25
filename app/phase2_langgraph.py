from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain.tools import tool
from langchain_ollama import ChatOllama

from pydantic import BaseModel
from langchain_core.output_parsers import PydanticOutputParser


# =========================
# LLM SETUP
# =========================

llm = ChatOllama(
    model="llama3",
    temperature=0.7
)


# =========================
# BOT PERSONAS
# =========================

BOT_PERSONAS = {

    "Bot A": """
    You are a Tech Maximalist.
    You believe AI, crypto, and tech will solve humanity's problems.
    You support Elon Musk, innovation, and space exploration.
    """,

    "Bot B": """
    You are a Doomer Skeptic.
    You believe AI and tech monopolies harm society.
    You criticize billionaires and value privacy.
    """,

    "Bot C": """
    You are a Finance Bro.
    You care only about markets, ROI, trading, and money.
    """
}


# =========================
# MOCK SEARCH TOOL
# =========================

@tool
def mock_searxng_search(query: str):
    """
    Fake search tool returning news based on keywords.
    """

    query = query.lower()

    if "ai" in query:
        return "OpenAI releases new AI model that may replace junior developers."

    elif "crypto" in query:
        return "Bitcoin hits all-time high after ETF approval."

    elif "finance" in query:
        return "Federal Reserve hints at interest rate cuts."

    else:
        return "Tech industry continues rapid innovation."


# =========================
# STATE
# =========================

class BotState(TypedDict):
    bot_id: str
    persona: str
    topic: str
    search_results: str
    post_content: dict


# =========================
# OUTPUT SCHEMA (10/10 FIX)
# =========================

class PostSchema(BaseModel):
    bot_id: str
    topic: str
    post_content: str


parser = PydanticOutputParser(pydantic_object=PostSchema)


# =========================
# NODE 1: DECIDE TOPIC
# =========================

def decide_search(state):

    prompt = f"""
    Based on this persona:

    {state["persona"]}

    Decide a trending topic to post about.

    Return only a short topic.
    """

    response = llm.invoke(prompt)

    topic = response.content.strip()

    print("\nTOPIC:", topic)

    return {"topic": topic}


# =========================
# NODE 2: SEARCH
# =========================

def web_search(state):

    topic = state["topic"]

    result = mock_searxng_search.invoke(topic)

    print("\nSEARCH:", result)

    return {"search_results": result}


# =========================
# NODE 3: DRAFT POST (STRICT JSON)
# =========================

def draft_post(state):

    prompt = f"""
    You are a strict JSON generator.

    Persona:
    {state["persona"]}

    Topic:
    {state["topic"]}

    Context:
    {state["search_results"]}

    RULES:
    - Return ONLY valid JSON
    - No explanation
    - Must follow schema

    {parser.get_format_instructions()}

    IMPORTANT:
    Post must be under 280 characters.
    """

    response = llm.invoke(prompt)

    parsed = parser.parse(response.content)

    # enforce 280 char limit
    if len(parsed.post_content) > 280:
        parsed.post_content = parsed.post_content[:277] + "..."

    print("\nFINAL JSON:", parsed.model_dump())

    return {"post_content": parsed.model_dump()}


# =========================
# BUILD GRAPH
# =========================

builder = StateGraph(BotState)

builder.add_node("decide_search", decide_search)
builder.add_node("web_search", web_search)
builder.add_node("draft_post", draft_post)

builder.set_entry_point("decide_search")

builder.add_edge("decide_search", "web_search")
builder.add_edge("web_search", "draft_post")
builder.add_edge("draft_post", END)

graph = builder.compile()


if __name__ == "__main__":

    for bot_id, persona in BOT_PERSONAS.items():

        result = graph.invoke({
            "bot_id": bot_id,
            "persona": persona,
            "topic": "",
            "search_results": "",
            "post_content": {}
        })

        print("\n====================")
        print("FINAL OUTPUT")
        print("====================")
        print(result)