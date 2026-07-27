import requests


class CortexError(Exception):
    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body


def ask(account_url: str, token: str, source: str, question: str) -> dict:
    resp = requests.post(
        f"{account_url.rstrip('/')}/api/v2/cortex/analyst/message",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": question}]}
            ],
            # Stage YAML files start with '@'; native Semantic View objects use semantic_view.
            "semantic_model_file" if source.startswith("@") else "semantic_view": source,
        },
        timeout=60,
    )

    if not resp.ok:
        raise CortexError(resp.status_code, resp.text)

    contents = resp.json().get("message", {}).get("content", [])
    result: dict = {}
    for item in contents:
        if item.get("type") == "text":
            result["interpretation"] = item["text"]
        elif item.get("type") == "sql":
            result["sql"] = item["statement"]
    return result
