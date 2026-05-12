import openpyxl

_MUSCLE_KEYS = {"muscoli", "muscles", "muscle", "gruppi muscolari", "gruppo muscolare"}
_EQUIPMENT_KEYS = {"attrezzatura", "equipment", "attrezzi", "attrezzo"}
_NAME_KEYS = {"nome", "name", "esercizio", "exercise"}
_DIFF_KEYS = {"difficolta", "difficoltà", "difficulty", "livello"}
_CAT_KEYS = {"categoria", "category", "tipologia", "tipo"}


def _find_col(headers_lower: list[str], aliases: set[str]) -> int | None:
    for i, h in enumerate(headers_lower):
        if h in aliases:
            return i
    return None


def _split_list(value: str) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in str(value).replace(";", ",").split(",") if v.strip()]


def chunk_excel(filepath: str) -> list[dict]:
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return []

    headers = [str(h).strip() if h else "" for h in rows[0]]
    headers_lower = [h.lower() for h in headers]

    idx_name = _find_col(headers_lower, _NAME_KEYS)
    idx_muscles = _find_col(headers_lower, _MUSCLE_KEYS)
    idx_equipment = _find_col(headers_lower, _EQUIPMENT_KEYS)
    idx_diff = _find_col(headers_lower, _DIFF_KEYS)
    idx_cat = _find_col(headers_lower, _CAT_KEYS)

    chunks = []
    for row in rows[1:]:
        if all(v is None for v in row):
            continue
        data = dict(zip(headers, row))
        name = str(row[idx_name]).strip() if idx_name is not None and idx_name < len(row) and row[idx_name] else ""
        muscles = _split_list(row[idx_muscles]) if idx_muscles is not None and idx_muscles < len(row) else []
        equipment = _split_list(row[idx_equipment]) if idx_equipment is not None and idx_equipment < len(row) else []
        difficulty = str(row[idx_diff]).strip() if idx_diff is not None and idx_diff < len(row) and row[idx_diff] else ""
        category = str(row[idx_cat]).strip() if idx_cat is not None and idx_cat < len(row) and row[idx_cat] else ""

        lines = [f"Esercizio: {name}"]
        if muscles:
            lines.append(f"Muscoli: {', '.join(muscles)}")
        if equipment:
            lines.append(f"Attrezzatura: {', '.join(equipment)}")
        if difficulty:
            lines.append(f"Difficoltà: {difficulty}")
        if category:
            lines.append(f"Categoria: {category}")
        # aggiunge campi extra non mappati
        mapped = {i for i in [idx_name, idx_muscles, idx_equipment, idx_diff, idx_cat] if i is not None}
        for i, (h, v) in enumerate(zip(headers, row)):
            if i not in mapped and v is not None and str(v).strip():
                lines.append(f"{h}: {v}")

        content = "\n".join(lines)
        meta = {
            "doc_type": "exercise",
            "name": name,
            "muscles": muscles,
            "equipment": equipment,
            "difficulty": difficulty,
            "category": category,
        }
        chunks.append({
            "content": content,
            "metadata": meta,
            "source": filepath,
            "doc_type": "exercise",
        })

    return chunks
