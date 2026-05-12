from __future__ import annotations
from models import UserPreferences

_LEVEL_LABELS = {
    "principiante": "Principiante (0-1 anno)",
    "intermedio": "Intermedio (1-3 anni)",
    "avanzato": "Avanzato (3+ anni)",
}
_EQUIPMENT_LABELS = {
    "palestra": "Palestra completa (tutte le macchine)",
    "home": "Home gym (bilanciere, manubri, panca)",
    "corpo-libero": "Solo corpo libero",
}
_MUSCLE_LABELS = {
    "petto": "Petto", "schiena": "Schiena", "spalle": "Spalle",
    "bicipiti": "Bicipiti", "tricipiti": "Tricipiti",
    "quadricipiti": "Quadricipiti", "femorali": "Femorali", "glutei": "Glutei",
}


def build_system_prompt(knowledge_chunks: list[str]) -> str:
    knowledge_section = ""
    if knowledge_chunks:
        knowledge_section = (
            "\n\n=== LINEE GUIDA CONTESTUALI (dalla knowledge base scientifica) ===\n"
            + "\n---\n".join(knowledge_chunks)
        )

    return (
        "Sei un preparatore atletico certificato con 15 anni di esperienza, "
        "aggiornato con la letteratura scientifica 2015-2025 "
        "(Schoenfeld, Israetel, Maeo, Roberts, Nunes)."
        f"{knowledge_section}\n\n"
        "REGOLE ASSOLUTE - NON violarle mai:\n"
        "1. Rispondi SOLO con JSON valido. Nessun testo prima o dopo.\n"
        "2. USA SOLO esercizi presenti nella lista ESERCIZI DISPONIBILI. "
        'Il campo "name" deve essere copia letterale del nome nella lista.\n'
        "3. MULTI-ARTICOLARI sempre PRIMA degli isolamenti (Nunes et al. 2021).\n"
        "4. Stesso esercizio in 2 giorni: usa SCHEMI DIVERSI "
        "(es. Giorno A 4x5-7 pesante, Giorno B 3x12-15 leggero).\n"
        "5. Esercizi lower body (Squat, Deadlift, Leg press, Hip thrust) "
        "SOLO in sessioni Lower/Full Body. Braccia isolate NON in sessioni Lower.\n"
        '6. Ogni "notes" = 1 cue tecnico specifico in italiano. Solo lettere e numeri.\n'
        "7. Rest: 2-3 min per compound, 60-90s per isolamenti.\n"
        "8. Se la lista non ha abbastanza esercizi per un giorno, usa meno — non inventare."
    )


def build_user_prompt(
    prefs: UserPreferences,
    exercises: list[dict],
    knowledge_chunks: list[str],
) -> str:
    level_label = _LEVEL_LABELS.get(prefs.level, prefs.level)
    gender_label = "Donna" if prefs.gender == "donna" else "Uomo"
    muscles_labels = [_MUSCLE_LABELS.get(m, m) for m in prefs.targetMuscles]
    equip_label = _EQUIPMENT_LABELS.get(prefs.equipment, prefs.equipment)

    priority_line = (
        f"- Muscoli prioritari (volume maggiore): {', '.join(muscles_labels)}\n"
        "- Altri muscoli: volume di mantenimento (MEV)"
        if prefs.targetMuscles
        else "- Volume equilibrato su tutti i gruppi"
    )

    exercise_context = _build_exercise_context(exercises)
    volume_targets = _get_volume_targets(prefs.level, prefs.gender)
    level_rules = _get_level_rules(prefs.level)
    split_advice = _get_split_advice(prefs.frequency, prefs.level)
    set_rep_structure = _get_set_rep_structure(prefs.level)
    gender_specific = _get_donna_adaptations() if prefs.gender == "donna" else ""

    return (
        f"Crea una scheda settimanale COMPLETA (allena TUTTI i gruppi muscolari) per:\n"
        f"- Livello: {level_label}\n"
        f"- Sesso: {gender_label}\n"
        f"- Frequenza: {prefs.frequency} sessioni/settimana\n"
        f"{priority_line}\n"
        f"- Attrezzatura: {equip_label}\n"
        f"- Note utente: {prefs.notes or 'nessuna'}\n\n"
        f"{level_rules}\n\n"
        f"VOLUME SETTIMANALE TARGET (serie per gruppo muscolare/settimana):\n"
        f"{volume_targets}\n\n"
        "LINEE GUIDA EVIDENCE-BASED OBBLIGATORIE (letteratura 2021-2025):\n"
        "- TRICIPITI: includi SEMPRE almeno 1 estensione sopra la testa. "
        "Maeo et al. 2023: capo lungo +45% crescita vs pushdown.\n"
        "- BICIPITI: preferire curl in posizione allungata (incline curl, high cable curl). "
        "Alix-Fages, Cyrino: massimizzano ipertrofia capo lungo.\n"
        "- FEMORALI: preferire leg curl seduto > sdraiato. "
        "Maeo et al. 2021: posizione allungata = maggiore ipertrofia.\n"
        "- GLUTEI: Hip thrust OBBLIGATORIO in ogni sessione Lower/Full Body (Plotkin 2023).\n"
        "- SCHIENA: SEMPRE 1 verticale (lat machine, pull-up) + 1 orizzontale (rematore, pulley).\n"
        "- GEMELLI: sia calf in piedi (gastrocnemio) che seduto (soleo) nelle sessioni Lower.\n"
        f"{gender_specific}\n\n"
        "ROTAZIONE ATTREZZI OBBLIGATORIA nella stessa sessione:\n"
        "- Pos 1-2 (compound principali): BILANCIERE\n"
        "- Pos 3-4 (compound accessori): MANUBRI o MACCHINA (non ripetere bilanciere)\n"
        "- Pos 5-6 (isolamento): CAVI o MACCHINE\n\n"
        "FASI SESSIONE:\n"
        "1. FORZA (pos. 1-2): compound bilanciere, top set + back-off, reps 5-10\n"
        "2. IPERTROFIA (pos. 3-4): compound accessori manubri/macchina, reps 8-12\n"
        "3. METABOLICO (pos. 5-6+): isolamenti cavi/macchine, reps 12-20, 1 tecnica intensita'\n\n"
        f"SPLIT CONSIGLIATO PER {prefs.frequency} GIORNI:\n"
        f"{split_advice}\n\n"
        f"ESERCIZI DISPONIBILI (pre-selezionati e ranked per SFR+ROM+rilevanza al tuo profilo):\n"
        f"{exercise_context}\n\n"
        f"{set_rep_structure}\n\n"
        "OUTPUT JSON RICHIESTO:\n"
        "{{\n"
        '  "planName": "string",\n'
        '  "description": "string (2 frasi: obiettivo e struttura)",\n'
        '  "days": [\n'
        "    {{\n"
        '      "dayNumber": 1,\n'
        '      "name": "Upper A",\n'
        '      "focus": "Petto + Schiena",\n'
        '      "exercises": [\n'
        "        {{\n"
        '          "id": "d1_e1",\n'
        '          "name": "NOME ESATTO dalla lista",\n'
        '          "primaryMuscle": "string",\n'
        '          "category": "string",\n'
        '          "sets": 3,\n'
        '          "reps": "8-10",\n'
        '          "rest": "90s",\n'
        '          "notes": "cue tecnico specifico",\n'
        '          "intensityTechnique": null,\n'
        '          "equipment": "string"\n'
        "        }}\n"
        "      ]\n"
        "    }}\n"
        "  ]\n"
        "}}\n\n"
        f"Genera ESATTAMENTE {prefs.frequency} giorni. "
        "6-8 esercizi per giorno. La scheda deve essere scientificamente fondata, varia e progressiva."
    )


def _build_exercise_context(exercises: list[dict]) -> str:
    lines: list[str] = []
    compounds = [e for e in exercises if _is_compound_meta(e)]
    isolations = [e for e in exercises if not _is_compound_meta(e)]

    if compounds:
        lines.append("=== MULTI-ARTICOLARI (mettili PRIMA nella sessione) ===")
        for e in compounds:
            lines.append(_fmt_exercise(e))

    if isolations:
        lines.append("\n=== MONO-ARTICOLARI / ISOLAMENTO ===")
        for e in isolations:
            lines.append(_fmt_exercise(e))

    return "\n".join(lines)


def _is_compound_meta(e: dict) -> bool:
    _COMPOUND_KEYWORDS = {
        "squat", "deadlift", "stacco", "panca", "rematore", "press",
        "pull-up", "chin-up", "dip", "hip thrust", "affondi", "bulgarian",
        "lat machine", "t-bar", "hyperextension", "good morning",
    }
    n = str(e.get("name", "")).lower()
    return any(k in n for k in _COMPOUND_KEYWORDS)


def _fmt_exercise(e: dict) -> str:
    name = e.get("name", "")
    primary = e.get("primaryMuscle", "")
    equipment = e.get("equipment", "")
    sfr = e.get("sfr_score", 0.6)
    rom = e.get("rom_score", 0.6)
    return f"  {name} | {primary} | {equipment} | SFR:{sfr:.1f} ROM:{rom:.1f}"


def _get_volume_targets(level: str, gender: str) -> str:
    is_donna = gender == "donna"
    lv = level.lower()
    if "avanzato" in lv:
        glutei = "14-16" if is_donna else "10-14"
        return (
            f"Petto: 16-20 set | Schiena: 18-22 set | Trapezi: 12-16 set\n"
            f"Spalle: 16-22 set | Bicipiti: 14-20 set | Tricipiti: 12-14 set\n"
            f"Quadricipiti: 14-18 set | Femorali: 12-16 set | Glutei: {glutei} set | Gemelli: 14-16 set"
        )
    if "intermedio" in lv:
        glutei = "10-14" if is_donna else "6-10"
        return (
            f"Petto: 12-16 set | Schiena: 14-18 set | Trapezi: 10-14 set\n"
            f"Spalle: 12-16 set | Bicipiti: 12-14 set | Tricipiti: 10-12 set\n"
            f"Quadricipiti: 12-14 set | Femorali: 10-12 set | Glutei: {glutei} set | Gemelli: 12-14 set"
        )
    glutei = "8-12" if is_donna else "4-8"
    return (
        f"Petto: 6-10 set | Schiena: 8-12 set | Trapezi: 6-8 set\n"
        f"Spalle: 8-12 set | Bicipiti: 6-8 set | Tricipiti: 6-8 set\n"
        f"Quadricipiti: 8-10 set | Femorali: 6-8 set | Glutei: {glutei} set | Gemelli: 8-10 set"
    )


def _get_donna_adaptations() -> str:
    return (
        "\nADATTAMENTI PER DONNA (Roberts et al. 2020, Hunter 2014):\n"
        "- Treno inferiore: volume MAGGIORE (glutei e quadricipiti priorita' fisiologica)\n"
        "- Recupero inter-serie: 90s per multi-articolari, 45-60s per isolamenti\n"
        "- Glutei: Hip thrust + Glute kickback o Abductor machine in ogni sessione Lower\n"
        "- Petto/tricipiti: volume RIDOTTO di 2-3 set rispetto all'uomo\n"
        "- Esercizi unilaterali gambe preferiti (affondi, Bulgarian split squat)"
    )


def _get_set_rep_structure(level: str) -> str:
    lv = level.lower()
    if "principiante" in lv:
        return (
            "STRUTTURA SET/REP — PRINCIPIANTE (3-4 set, top set incluso):\n"
            "A) COMPOUND bilanciere (pos.1-2): TOP SET + BACK-OFF, 3-4 sets\n"
            '   Es: "sets":3,"reps":"1x8 + 2x10-12". Top set RPE 7-8. Rest: 3 min.\n'
            "B) COMPOUND accessori manubri/macchina (pos.3-4): 3 set\n"
            '   Es: "sets":3,"reps":"10-12". Rest: 2 min.\n'
            "C) ISOLAMENTI cavi/macchine (pos.5+): 3 set\n"
            '   Es: "sets":3,"reps":"12-15". Rest: 60-90s.'
        )
    if "intermedio" in lv:
        return (
            "STRUTTURA SET/REP — INTERMEDIO (3 set, top set incluso):\n"
            "A) COMPOUND bilanciere (pos.1-2): TOP SET + BACK-OFF, 3 sets\n"
            '   Es: "sets":3,"reps":"1x5 + 2x8-10". Top set RPE 8-9. Rest: 3-4 min.\n'
            "B) COMPOUND accessori manubri/macchina (pos.3-4): 3 set\n"
            '   Es: "sets":3,"reps":"8-12". Rest: 90s-2 min.\n'
            "C) ISOLAMENTI (pos.5+): 3 set, 1 tecnica intensita' sull'ultimo\n"
            '   Es: "sets":3,"reps":"12-15". Rest: 60-90s.'
        )
    return (
        "!!!! STRUTTURA SET/REP — AVANZATO — REGOLA CRITICA !!!!\n"
        "DEFAULT OBBLIGATORIO: 2 set per esercizio. NON usare 3 set come default.\n"
        "A) COMPOUND bilanciere: TOP SET + BACK-OFF, 2 set\n"
        '   DEFAULT: "sets":2,"reps":"1x3 + 1x5-7". Top set RPE 9-10. Rest: 4-5 min.\n'
        "B) COMPOUND accessori manubri/macchina: 2 set\n"
        '   "sets":2,"reps":"6-10". Rest: 2-3 min.\n'
        "C) ISOLAMENTI (pos.5+): 2 set\n"
        '   "sets":2,"reps":"10-15". Rest: 60-90s.\n'
        "VERIFICA FINALE: la maggioranza degli esercizi DEVE avere sets:2."
    )


def _get_level_rules(level: str) -> str:
    lv = level.lower()
    if "principiante" in lv:
        return (
            "REGOLE LIVELLO PRINCIPIANTE:\n"
            "- Top set: RPE 7-8 (tecnica prioritaria, non massimizzare carico)\n"
            "- Rep range compound: 8-12\n"
            "- Rep range isolamento: 12-15\n"
            "- NO tecniche avanzate di intensita' (drop set, myo-reps)\n"
            "- RIR 2-3 su tutti gli esercizi"
        )
    if "intermedio" in lv:
        return (
            "REGOLE LIVELLO INTERMEDIO:\n"
            "- Top set: RPE 8-9, compound principali 5-8 rep, accessori 8-12 rep\n"
            "- Rep range isolamento: 10-15\n"
            "- 1 tecnica intensita' per sessione, solo sull'ultimo isolamento\n"
            "- RIR 1-2 sui compound, RIR 0-1 sugli isolamenti"
        )
    return (
        "REGOLE LIVELLO AVANZATO:\n"
        "- Top set: RPE 9-10, compound principali 3-6 rep (forza massimale)\n"
        "- Back-off: 5-8 rep, RPE 8, intensita' 80-85%\n"
        "- Rep range compound accessori: 6-10 rep\n"
        "- Rep range isolamento: 10-15, near-failure\n"
        "- 1-2 tecniche intensita' per sessione\n"
        "- RIR 0-1 su tutti gli esercizi"
    )


def _get_split_advice(frequency: int, level: str) -> str:
    is_principiante = "principiante" in level.lower()

    splits: dict[int, str] = {
        2: (
            "Full Body A + Full Body B (ogni gruppo 2x/settimana)\n"
            "  - Giorno A (Squat-dominant): Squat + Panca piana + Rematore + Hip thrust + Alzate laterali + Curl + Polpacci\n"
            "  - Giorno B (Hinge-dominant): Stacco rumeno + Military press + Lat machine + Leg press + Croci + Pushdown + Polpacci"
        ),
        3: (
            "Full Body A / Full Body B / Full Body C\n"
            "  - Giorno A: Squat + Panca piana + Rematore + Hip thrust + Alzate laterali + Curl manubri + Polpacci\n"
            "  - Giorno B: Stacco rumeno + Military press + Lat machine + Leg press + Cable crossover + Pushdown + Polpacci\n"
            "  - Giorno C: Bulgarian split squat + Panca inclinata + Pulley + Leg extension + Reverse fly + Hammer curl + Calf seduto"
            if is_principiante else
            "Lower / Upper / Full Body (ogni gruppo 2x/settimana)\n"
            "  - Lower: Squat + Hip thrust + Stacco rumeno + Leg curl seduto + Leg extension + Polpacci x2\n"
            "  - Upper: Panca piana + Rematore + Panca inclinata + Lat machine + Alzate laterali + Overhead ext. + Curl\n"
            "  - Full Body: 3-4 esercizi lower hinge-dominant + 2-3 upper varianti diverse da Upper"
        ),
        4: (
            "Upper A / Lower A / Upper B / Lower B (split ottimale per ipertrofia, Schoenfeld 2019)\n"
            "  - Upper A: Panca bil. + Rematore bil. + Panca inclinata manubri + Lat machine + Alzate laterali cavi + Overhead ext.\n"
            "  - Lower A (quad-dom): Squat bil. + Hip thrust bil. + Leg press + Leg curl seduto + Calf piedi + Calf seduto\n"
            "  - Upper B: Rematore manubrio + Panca piana manubri + Pulley cavi + Chest press macchina + Incline curl + Pushdown\n"
            "  - Lower B (hinge-dom): RDL bil. + Bulgarian split squat + Leg extension + Glute kickback cavi + Single-leg RDL + Calf seduto"
        ),
        5: (
            "Push / Pull / Legs / Upper / Lower (PPLUL - ogni gruppo 2x/settimana)\n"
            "  - Push: panca bilanciere + military + panca inclinata + alzate laterali + overhead extension + pushdown\n"
            "  - Pull: stacco + lat machine + rematore + face pull + incline curl + hammer curl\n"
            "  - Legs: squat + hip thrust + RDL + leg curl seduto + leg extension + polpacci x2\n"
            "  - Upper (accessorio): varianti petto/schiena diverse + braccia\n"
            "  - Lower (accessorio): hinge-dominant + glutei + polpacci"
        ),
        6: (
            "Push / Pull / Legs x 2 (ogni muscolo 2x/settimana)\n"
            "  - Push A: panca bilanciere, military press, panca inclinata manubri, alzate laterali, overhead ext., pushdown\n"
            "  - Pull A: stacco, lat machine, rematore bilanciere, face pull, incline curl, hammer curl\n"
            "  - Legs A: squat, hip thrust, RDL, leg curl seduto, leg extension, calf piedi\n"
            "  - Push B: panca manubri, shoulder press macchina, alzate laterali cavi, croci, kickback (SCHEMA DIVERSO da Push A)\n"
            "  - Pull B: stacco rumeno, pull-up, rematore manubrio, pulley, curl EZ, curl cavi alti\n"
            "  - Legs B: hack squat/leg press, hip thrust (SCHEMA DIVERSO), Bulgarian split, adductor/abductor, leg curl seduto, calf seduto"
        ),
    }
    return splits.get(frequency, f"{frequency} sessioni — split Upper/Lower o PPL appropriato")
