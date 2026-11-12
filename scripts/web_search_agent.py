import argparse
import json
import sys

from ddgs import DDGS
from openai import OpenAI

SYSTEM_PROMPT = (
    "Eres un asistente con acceso a busqueda web mediante la herramienta web_search. "
    "Usala cuando la pregunta requiera informacion actual, externa o que no conoces con certeza. "
    "No busques para preguntas de conocimiento general obvias. "
    "Responde en el idioma del usuario y cita las URLs de las fuentes que utilices."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Busca informacion en internet. Devuelve titulos, URLs y fragmentos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Consulta de busqueda, breve y especifica",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Numero de resultados a devolver (por defecto 5)",
                    },
                },
                "required": ["query"],
            },
        },
    }
]


def web_search(query: str, max_results: int = 5) -> list[dict]:
    raw = DDGS().text(query, max_results=max_results)
    results = []
    for r in raw:
        results.append(
            {
                "title": r.get("title", ""),
                "url": r.get("href") or r.get("url", ""),
                "snippet": (r.get("body") or r.get("snippet", ""))[:500],
            }
        )
    return results


def run_tool(args: dict) -> str:
    try:
        data = web_search(args["query"], int(args.get("max_results", 5)))
        print(f"  [buscando] {args['query']!r} -> {len(data)} resultados", file=sys.stderr)
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"web_search fallo: {e}"}, ensure_ascii=False)


def chat(client: OpenAI, model: str, user_msg: str, max_iterations: int = 4) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]
    for _ in range(max_iterations):
        r = client.chat.completions.create(model=model, messages=messages, tools=TOOLS)
        m = r.choices[0].message
        if not m.tool_calls:
            return m.content or ""
        messages.append(m.model_dump(exclude_none=True))
        for call in m.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": run_tool(args),
                }
            )
    r = client.chat.completions.create(model=model, messages=messages)
    return r.choices[0].message.content or ""


def rag_chat(client: OpenAI, model: str, user_msg: str, max_results: int = 5) -> str:
    results = web_search(user_msg, max_results=max_results)
    ctx = "\n".join(f"- {r['title']} ({r['url']}): {r['snippet']}" for r in results)
    print(f"  [buscando] {user_msg!r} -> {len(results)} resultados", file=sys.stderr)
    r = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Usa este contexto web si es util, y cita las URLs:\n" + ctx,
            },
            {"role": "user", "content": user_msg},
        ],
    )
    return r.choices[0].message.content or ""


def main() -> None:
    p = argparse.ArgumentParser(description="Agente con web search sobre llama-server")
    p.add_argument("query", nargs="*", help="Pregunta unica; si se omite, entra en modo REPL")
    p.add_argument("--url", default="http://localhost:8080/v1", help="Base URL OpenAI-compatible")
    p.add_argument("--model", default="qwen", help="Nombre de modelo (llama-server lo ignora)")
    p.add_argument("--rag", action="store_true", help="Modo fallback: buscar siempre, sin tool-calling")
    p.add_argument("--max-results", type=int, default=5)
    p.add_argument("--max-iterations", type=int, default=4)
    args = p.parse_args()

    client = OpenAI(base_url=args.url, api_key="local")

    def answer(msg: str) -> str:
        if args.rag:
            return rag_chat(client, args.model, msg, args.max_results)
        return chat(client, args.model, msg, args.max_iterations)

    if args.query:
        print(answer(" ".join(args.query)))
        return

    print("Modo REPL. Ctrl-D o 'exit' para salir.", file=sys.stderr)
    while True:
        try:
            msg = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not msg:
            continue
        if msg.lower() in ("exit", "quit", "salir"):
            break
        print(answer(msg))


if __name__ == "__main__":
    main()
