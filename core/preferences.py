"""Preference serialization: persistent in URL across Streamlit page refreshes."""

def theme_from_query(value: str | None) -> str:
    return "Tối" if isinstance(value, str) and value.lower() in {"dark", "tối"} else "Sáng"

def theme_to_query(value: str) -> str:
    return "dark" if value == "Tối" else "light"
