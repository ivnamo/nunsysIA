from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


KNOWN_CUSTOMER_IDS = frozenset({"ALFKI", "ANATR", "BONAP"})


@dataclass(frozen=True)
class ToolPolicy:
    needs_memory: bool
    needs_isolated_clarification: bool
    needs_documents: bool
    needs_penalty: bool
    needs_economic_impact: bool
    needs_customer_orders: bool
    needs_production: bool
    needs_blocked_cross: bool
    needs_erp: bool
    rag_budget: int


def tool_policy(
    question: str,
    conversation_history: list[dict],
) -> ToolPolicy:
    text = normalize_text(question)
    has_history = bool(conversation_history)
    needs_isolated_clarification = looks_like_follow_up(text) and not has_history
    mentions_penalty = contains_any(text, ("penaliz", "sla"))
    document_first = contains_any(text, ("segun", "pdf", "document", "contrato", "anexo"))
    needs_penalty = mentions_penalty and not document_first and contains_any(
        text,
        ("pedido", "pedidos", "estado", "erp", "produccion"),
    )
    needs_economic_impact = has_history and contains_any(
        text,
        ("impacto economico", "importe", "importes", "valor", "cuanto suman"),
    )
    needs_documents = mentions_penalty or contains_any(
        text,
        (
            "segun",
            "contrato",
            "document",
            "pdf",
            "anexo",
            "clausul",
            "criptomon",
            "bitcoin",
            "divisa",
            "plazo contractual",
            "logistic",
            "receta",
            "cocina",
            "vegana",
        ),
    )
    has_known_customer = any(customer_id.lower() in text for customer_id in KNOWN_CUSTOMER_IDS)
    needs_customer_orders = has_known_customer or (
        "cliente" in text and "pedido" in text and "pendiente" in text
    )
    needs_blocked_cross = "bloque" in text and contains_any(
        text,
        ("produccion", "erp", "cliente", "cruza", "cruce"),
    )
    needs_production = contains_any(
        text,
        ("produccion", "estado", "bloque", "retras", "fabricacion"),
    )
    needs_erp = needs_customer_orders or needs_economic_impact or contains_any(
        text,
        ("erp", "pedido"),
    )
    needs_memory = has_history and (
        looks_like_follow_up(text) or not has_explicit_business_anchor(text)
    )

    if needs_penalty or needs_blocked_cross:
        needs_erp = True
        needs_production = True
    if needs_memory and contains_any(text, ("estado", "produccion")):
        needs_production = True

    return ToolPolicy(
        needs_memory=needs_memory,
        needs_isolated_clarification=needs_isolated_clarification,
        needs_documents=needs_documents,
        needs_penalty=needs_penalty,
        needs_economic_impact=needs_economic_impact,
        needs_customer_orders=needs_customer_orders,
        needs_production=needs_production,
        needs_blocked_cross=needs_blocked_cross,
        needs_erp=needs_erp,
        rag_budget=1 if needs_documents else 0,
    )


def contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def looks_like_follow_up(text: str) -> bool:
    tokenized = f" {word_text(text)} "
    return text.startswith(("y ", "ademas", "tambien")) or contains_any(
        tokenized,
        (" esos ", " esas ", " ellos ", " ellas ", " anterior ", " antes "),
    )


def has_explicit_business_anchor(text: str) -> bool:
    return bool(order_ids_from_text(text)) or contains_any(
        text,
        ("alfki", "bonap", "anatr", "cliente", "pedido", "contrato", "document", "pdf"),
    )


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def word_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def order_ids_from_text(text: str) -> list[int]:
    order_ids = []
    for raw_word in text.replace(",", " ").replace(".", " ").split():
        if not raw_word.isdigit():
            continue
        value = int(raw_word)
        if value > 0 and value not in order_ids:
            order_ids.append(value)
    return order_ids
