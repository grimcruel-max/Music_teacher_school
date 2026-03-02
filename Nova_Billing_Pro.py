import streamlit as st
from fpdf import FPDF
import pandas as pd
import datetime

DEFAULT_RATES = {
    "Einzel 30 Min (14 EUR)": {"price": 14.00, "dur": 0.5},
    "Einzel 45 Min (21 EUR)": {"price": 21.00, "dur": 0.75},
    "Einzel 60 Min (25 EUR)": {"price": 25.00, "dur": 1.0},
    "Gruppe 30 Min 2er (21 EUR)": {"price": 21.00, "dur": 0.5},
    "Gruppe 30 Min 3er (24 EUR)": {"price": 24.00, "dur": 0.5},
    "Gruppe 45 Min 2er (22 EUR)": {"price": 22.00, "dur": 0.75},
    "Gruppe 45 Min 3er (30 EUR)": {"price": 30.00, "dur": 0.75},
    "Schnupperstunde (10 EUR)": {"price": 10.00, "dur": 0.5},
}

STUDENT_LIST = ["Dominik", "Filippa", "Lilly-Marlene", "Louisa", "Maxi", "Nay", "Taym", "Ulrike"]

# ── PDF ────────────────────────────────────────────────────────────────────────
# Columns: Standort | Datum | Schueler | Dauer | Betrag | Notiz
# Widths sum to exactly 170 mm (A4 210 - 20 left - 20 right)
#           Standort  Datum  Schueler  Dauer  Betrag  Notiz
COL_W    = [30,       18,    42,       18,    22,     40]   # total = 170 mm
ROW_H    = 8
HEADER_H = 9

GREY_DARK  = (60,  60,  60)
GREY_MID   = (120, 120, 120)
GREY_LIGHT = (220, 220, 220)
GREY_ROW   = (247, 247, 247)
WHITE      = (255, 255, 255)
BLACK      = (20,  20,  20)

def _font(pdf, bold=False, size=9):
    pdf.set_font("Arial", "B" if bold else "", size)

def _header_row(pdf):
    labels = ["Standort", "Datum", "Schueler", "Dauer Std.", "Betrag EUR", "Notiz"]
    pdf.set_fill_color(*GREY_LIGHT)
    pdf.set_text_color(*GREY_DARK)
    _font(pdf, bold=True, size=9)
    for w, lbl in zip(COL_W, labels):
        pdf.cell(w, HEADER_H, lbl, border=1, ln=0, align="C", fill=True)
    pdf.ln()
    pdf.set_text_color(*BLACK)

def _merged_cell(pdf, x, y, w, h, text, bg, align="C", size=9):
    """Draw a filled rect then place centred text inside it."""
    pdf.set_fill_color(*bg)
    pdf.set_draw_color(*GREY_LIGHT)
    pdf.rect(x, y, w, h, style="FD")
    _font(pdf, bold=False, size=size)
    pdf.set_text_color(*BLACK)
    pdf.set_xy(x, y + (h - ROW_H) / 2)
    pdf.cell(w, ROW_H, text, border=0, align=align)

def _draw_location_block(pdf, loc_df, stripe: bool):
    """
    One block per Standort.
      Col 0 (Standort) : single merged cell for the entire location
      Col 1 (Datum)    : merged cell per date within the location
      Cols 2-5         : one row per student (sorted alphabetically)
    """
    n_total = len(loc_df)
    total_h = n_total * ROW_H
    x0      = pdf.get_x()
    y0      = pdf.get_y()
    bg      = GREY_ROW if stripe else WHITE

    # ── Col 0: merged Standort spanning whole block ───────────────────────────
    _merged_cell(pdf, x0, y0, COL_W[0], total_h,
                 loc_df.iloc[0]["Standort"], bg, align="C")

    # ── Col 1+: iterate date sub-groups ──────────────────────────────────────
    # sort within location: by date then name
    loc_df = loc_df.sort_values(by=["raw_date", "Schueler"]).reset_index(drop=True)

    date_groups = []
    for _, row in loc_df.iterrows():
        if date_groups and date_groups[-1][0] == row["Datum"]:
            date_groups[-1][1].append(row)
        else:
            date_groups.append((row["Datum"], [row]))

    row_offset = 0
    for date_str, rows in date_groups:
        n_date = len(rows)
        date_h = n_date * ROW_H
        date_y = y0 + row_offset * ROW_H

        # merged Datum cell
        _merged_cell(pdf, x0 + COL_W[0], date_y, COL_W[1], date_h,
                     date_str, bg, align="C")

        # student rows
        cx = x0 + COL_W[0] + COL_W[1]
        for i, row in enumerate(rows):
            ry = date_y + i * ROW_H
            pdf.set_fill_color(*bg)
            pdf.set_draw_color(*GREY_LIGHT)
            pdf.set_xy(cx, ry)
            _font(pdf, bold=False, size=9)
            pdf.cell(COL_W[2], ROW_H, row["Schueler"],         border="LRB", align="L", fill=True)
            pdf.cell(COL_W[3], ROW_H, f"{row['Dauer']:.2f}",  border="LRB", align="C", fill=True)
            pdf.cell(COL_W[4], ROW_H, f"{row['Betrag']:.2f}", border="LRB", align="R", fill=True)
            pdf.cell(COL_W[5], ROW_H, row.get("notiz", ""),   border="LRB", align="L", fill=True)

        row_offset += n_date

    # outer border around whole location block
    pdf.set_draw_color(*GREY_MID)
    pdf.rect(x0, y0, sum(COL_W), total_h)
    pdf.set_draw_color(*GREY_LIGHT)
    pdf.set_xy(x0, y0 + total_h)


def create_pdf(df: pd.DataFrame, month_name: str, year: int, school_name: str, teacher_name: str) -> bytes:
    MARGIN = 20
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_auto_page_break(auto=True, margin=MARGIN)

    # ── Title ─────────────────────────────────────────────────────────────────
    _font(pdf, bold=True, size=15)
    pdf.set_text_color(*BLACK)
    pdf.cell(0, 10, school_name, ln=1, align="C")

    _font(pdf, bold=False, size=10)
    pdf.set_text_color(*GREY_MID)
    pdf.cell(0, 6, f"Stundennachweis  {teacher_name}", ln=1, align="C")
    pdf.cell(0, 6, f"{month_name} {year}", ln=1, align="C")

    pdf.set_draw_color(*GREY_LIGHT)
    pdf.ln(3)
    pdf.line(MARGIN, pdf.get_y(), 210 - MARGIN, pdf.get_y())
    pdf.ln(5)

    # ── Sort: location → date → name ─────────────────────────────────────────
    df_sorted = df.sort_values(by=["Standort", "raw_date", "Schueler"]).reset_index(drop=True)

    # ── Table ─────────────────────────────────────────────────────────────────
    pdf.set_x(MARGIN)
    _header_row(pdf)

    for stripe_idx, (_, loc_group) in enumerate(df_sorted.groupby("Standort", sort=True)):
        needed = len(loc_group) * ROW_H + 4
        if pdf.get_y() + needed > pdf.h - pdf.b_margin:
            pdf.add_page()
            pdf.set_x(MARGIN)
            _header_row(pdf)

        pdf.set_x(MARGIN)
        _draw_location_block(pdf, loc_group, stripe=stripe_idx % 2 == 1)
        pdf.ln(1)

    # ── Totals ────────────────────────────────────────────────────────────────
    total_h = df_sorted["Dauer"].sum()
    total_e = df_sorted["Betrag"].sum()

    pdf.ln(3)
    pdf.set_x(MARGIN)
    pdf.set_draw_color(*GREY_MID)
    pdf.line(MARGIN, pdf.get_y(), 210 - MARGIN, pdf.get_y())
    pdf.ln(2)
    pdf.set_x(MARGIN)

    _font(pdf, bold=True, size=10)
    pdf.set_text_color(*GREY_DARK)
    label_w = COL_W[0] + COL_W[1] + COL_W[2]
    pdf.cell(label_w, 9, f"Auszahlung {month_name} {year}", ln=0, align="R")
    pdf.cell(COL_W[3], 9, f"{total_h:.2f}", ln=0, align="C")
    pdf.cell(COL_W[4], 9, f"{total_e:.2f} EUR", ln=0, align="R")
    pdf.cell(COL_W[5], 9, "", ln=1, align="C")

    return pdf.output(dest="S").encode("latin-1")


# ── Streamlit App ──────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="Nova Billing", layout="wide")
    if "lessons" not in st.session_state:
        st.session_state.lessons = []

    # SIDEBAR
    with st.sidebar:
        st.header("⚙️ Einstellungen")
        target_year = st.selectbox("Jahr", [2025, 2026], index=1)
        st.session_state.month_name = st.selectbox(
            "Monat",
            ["Januar","Februar","Maerz","April","Mai","Juni",
             "Juli","August","September","Oktober","November","Dezember"],
            index=2,
        )
        st.divider()
        st.subheader("Titel")
        school_name  = st.text_input("Musikschule", value="Nova Musikschule")
        teacher_name = st.text_input("Lehrerin / Lehrer", value="Hyunjin Lim")
        st.divider()
        st.subheader("Preise anpassen")
        active_prices = {}
        for key, val in DEFAULT_RATES.items():
            active_prices[key] = st.number_input(f"{key}", value=val["price"], step=0.5)

    st.title(f"Abrechnung: {st.session_state.month_name} {target_year}")

    # ENTRY FORM
    with st.expander("Neuen Eintrag hinzufügen", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            loc      = st.text_input("Standort", "Südstadt")
            sel_date = st.date_input("Datum", datetime.date.today())

            # Free text with known students as quick-pick buttons
            if "name_input" not in st.session_state:
                st.session_state.name_input = ""
            name = st.text_input("Schüler (frei eingeben)", value=st.session_state.name_input, key="name_field")
            st.caption("Schnellauswahl:")
            # show known students + any new ones added this session
            known = sorted(set(STUDENT_LIST + [l["Schueler"] for l in st.session_state.lessons]))
            btn_cols = st.columns(4)
            for i, s in enumerate(known):
                if btn_cols[i % 4].button(s, key=f"quick_{s}", use_container_width=True):
                    st.session_state.name_input = s
                    st.rerun()
        with c2:
            kind = st.selectbox("Art des Unterrichts", list(DEFAULT_RATES.keys()))

            NOTIZ_OPTIONS = ["", "Schnupperstd."]
            notiz_choice = st.selectbox("Notiz", NOTIZ_OPTIONS)
            if notiz_choice == "":
                # allow free text when the empty option is selected
                notiz_custom = st.text_input("Eigene Notiz (optional)", value="", placeholder="z.B. Krank, Nachholstd. ...")
                notiz = notiz_custom.strip()
            else:
                notiz = notiz_choice

            st.write("")
            if st.button("Hinzufuegen", use_container_width=True):
                student_name = st.session_state.get("name_field", "").strip()
                if student_name:
                    st.session_state.lessons.append({
                        "Standort": loc,
                        "Datum":    sel_date.strftime("%d.%m"),
                        "raw_date": sel_date,
                        "Schueler": student_name,
                        "Dauer":    round(DEFAULT_RATES[kind]["dur"], 2),
                        "Betrag":   round(active_prices[kind], 2),
                        "notiz":    notiz,
                    })
                    st.session_state.name_input = ""
                    st.rerun()

    # LESSON TABLE WITH INDIVIDUAL DELETION
    if st.session_state.lessons:
        df = pd.DataFrame(st.session_state.lessons)
        df_display = df.sort_values(by=["raw_date", "Schueler"]).reset_index(drop=True)

        st.subheader(f"Einträge ({len(df_display)})")

        # Build display table with delete buttons
        header_cols = st.columns([1, 1.2, 1.5, 1.5, 1, 1, 1, 0.6])
        for col, label in zip(header_cols, ["Standort","Datum","Schüler","Unterricht","Dauer","Betrag","Notiz",""]):
            col.markdown(f"**{label}**")

        st.divider()

        # Map back from sorted display index to original lesson index
        sorted_indices = df_display.index.tolist()  # original positions in df
        original_lesson_indices = df.sort_values(by=["raw_date", "Schueler"]).index.tolist()

        for display_pos, orig_idx in enumerate(original_lesson_indices):
            row = st.session_state.lessons[orig_idx]
            cols = st.columns([1, 1.2, 1.5, 1.5, 1, 1, 1, 0.6])
            cols[0].write(row["Standort"])
            cols[1].write(row["Datum"])
            cols[2].write(row["Schueler"])
            rate_label = next(
                (k for k, v in DEFAULT_RATES.items()
                 if abs(v["dur"] - row["Dauer"]) < 0.01 and abs(v["price"] - row["Betrag"]) < 0.01),
                "-"
            )
            cols[3].write(rate_label.split(" (")[0])
            cols[4].write(f"{row['Dauer']:.2f}")
            cols[5].write(f"{row['Betrag']:.2f} €")
            cols[6].write(row.get("notiz", ""))
            if cols[7].button("X", key=f"del_{orig_idx}_{display_pos}"):
                st.session_state.lessons.pop(orig_idx)
                st.rerun()

        st.divider()

        # Summary
        total_h = sum(r["Dauer"] for r in st.session_state.lessons)
        total_e = sum(r["Betrag"] for r in st.session_state.lessons)
        sum_cols = st.columns([1, 1.2, 1.5, 1.5, 1, 1, 1, 0.6])
        sum_cols[3].markdown("**Gesamt**")
        sum_cols[4].markdown(f"**{total_h:.2f}**")
        sum_cols[5].markdown(f"**{total_e:.2f} €**")

        st.write("")
        st.divider()

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Alle loeschen", use_container_width=True):
                st.session_state.lessons = []
                st.session_state.pdf_bytes = None
                st.rerun()
        with c2:
            if st.button("PDF generieren", use_container_width=True, type="primary"):
                st.session_state.pdf_bytes = create_pdf(df, st.session_state.month_name, target_year, school_name, teacher_name)
        with c3:
            if st.session_state.get("pdf_bytes"):
                st.download_button(
                    "PDF herunterladen",
                    data=st.session_state.pdf_bytes,
                    file_name=f"Nova_Abrechnung_{st.session_state.month_name}_{target_year}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.button("PDF herunterladen", disabled=True, use_container_width=True)


if __name__ == "__main__":
    main()

